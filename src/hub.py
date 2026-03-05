"""Main orchestration loop for LAN-LLM-Hub."""

import argparse
import sys
from pathlib import Path
from src.session import Session
from src.utils.config import ConfigLoader
from src.utils.debug import get_debug_logger


def run_session(session: Session) -> None:
    """Run the main orchestration loop.

    The main loop:
    1. Checks session limits (turns, time, tokens)
    2. Checks for loops/convergence
    3. Selects next agent to speak (round-robin)
    4. Calls agent's LLM adapter
    5. Records response and routes to other agents
    6. Repeats until stop condition

    Args:
        session: Session instance to run
    """
    debug = get_debug_logger()
    session.logger.log_status(f"Starting orchestration loop")
    debug.info(f"Orchestration loop starting for session {session.session_id}")

    # Add initial prompt to first agent (admin)
    if session.start_prompt:
        admin_agent = session.get_all_agents()[0]
        admin_agent.memory.add_message("user", session.start_prompt, turn=0)
        session.logger.log_event("ADMIN", session.start_prompt)

    # Main loop
    while True:
        # Check session limits
        should_continue, stop_reason = session.guardrails.check_session_limits()
        if not should_continue:
            session.logger.log_status(f"Session stopping: {stop_reason}")
            session.stats.record_session_end(stop_reason)
            break

        # Advance turn
        session.guardrails.advance_turn()
        session.stats.record_turn_advance()
        turn = session.guardrails.current_turn

        # Check for loops
        is_looping, looping_agent = session.guardrails.check_for_loops()
        if is_looping:
            session.logger.log_status(f"Loop detected: agent {looping_agent} repeating")
            session.stats.record_session_end(f"loop_detected")
            break

        # Check convergence
        if session.guardrails.check_convergence():
            session.logger.log_status("Convergence detected (low novelty)")
            session.stats.record_session_end("convergence_detected")
            break

        # Pick next speaker (simple round-robin for now)
        agents = session.get_all_agents()
        current_speaker = agents[turn % len(agents)]

        # Check agent limits
        can_speak, reason = session.guardrails.check_agent_limits(current_speaker.id)
        if not can_speak:
            session.logger.log_status(f"Agent {current_speaker.id}: {reason}")
            continue

        # Get memory context
        context_messages = current_speaker.memory.get_context_messages()

        # Add system prompt
        system_prompt = current_speaker.get_system_prompt()
        if system_prompt:
            context_messages.insert(0, {"role": "system", "content": system_prompt})

        # Call LLM
        debug.debug(f"Turn {turn}: Agent '{current_speaker.id}' will speak. Context: {len(context_messages)} messages")
        try:
            session.logger.log_status(f"Calling agent {current_speaker.id}")
            response = current_speaker.adapter.generate(
                messages=context_messages,
                temperature=current_speaker.temperature,
                max_tokens=current_speaker.max_tokens,
            )
            debug.debug(f"Turn {turn}: Agent '{current_speaker.id}' response received ({len(response.text)} chars)")

            # Record metrics
            session.guardrails.record_agent_call(
                current_speaker.id,
                response.usage_input_tokens,
                response.usage_output_tokens,
            )
            session.stats.record_agent_call(
                current_speaker.id,
                tokens_in=response.usage_input_tokens,
                tokens_out=response.usage_output_tokens,
                latency_ms=response.latency_ms,
            )
            debug.debug(f"Turn {turn}: Recorded usage for '{current_speaker.id}': {response.usage_input_tokens}→{response.usage_output_tokens}")

            # Store message in memory
            current_speaker.memory.add_message(
                "assistant",
                response.text,
                turn=turn,
            )

            # Record for loop detection
            session.guardrails.record_message(current_speaker.id, response.text)

            # Log the response
            session.logger.log_event(
                current_speaker.id,
                response.text,
                event_type="message",
                metadata={
                    "turn": turn,
                    "input_tokens": response.usage_input_tokens,
                    "output_tokens": response.usage_output_tokens,
                    "latency_ms": round(response.latency_ms, 2),
                },
            )

            # Broadcast to other agents (hub-spoke topology by default)
            recipients = session.router.get_recipients(current_speaker.id)
            debug.debug(f"Turn {turn}: Routing to {len(recipients)} recipients: {recipients}")
            session.stats.record_routing(current_speaker.id, recipients)
            for recipient_id in recipients:
                recipient = session.get_agent(recipient_id)
                if recipient:
                    recipient.memory.add_message(
                        "user",
                        f"[{current_speaker.id}]: {response.text}",
                        turn=turn,
                    )
                    session.stats.record_message_received(recipient_id)

            # Check if memory needs summarization
            if current_speaker.memory.needs_summary():
                session.logger.log_status(
                    f"Agent {current_speaker.id} memory exceeds threshold, summarization would occur here"
                )
                session.stats.record_memory_event(
                    current_speaker.id,
                    "summarization_triggered",
                    f"Memory exceeded threshold ({len(current_speaker.memory.raw_messages)} messages)"
                )
                debug.warning(f"Agent '{current_speaker.id}' memory needs summary ({len(current_speaker.memory.raw_messages)} messages)")

        except RuntimeError as e:
            # API adapter errors (connection, auth, malformed responses)
            error_msg = str(e)
            debug.error(f"Adapter error for agent {current_speaker.id} on turn {turn}: {error_msg}", exc=e)
            session.logger.log_error(
                f"Agent {current_speaker.id} failed: {error_msg}\n"
                f"Provider: {current_speaker.provider}/{current_speaker.model}\n"
                f"Turn: {turn}"
            )
            session.stats.record_agent_call(
                current_speaker.id,
                tokens_in=0,
                tokens_out=0,
                latency_ms=0,
                error=error_msg
            )
            session.stats.record_session_end("adapter_error")
            raise RuntimeError(
                f"Agent '{current_speaker.id}' ({current_speaker.provider}/{current_speaker.model}) failed on turn {turn}:\n{error_msg}"
            ) from e
        except Exception as e:
            # Unexpected errors
            error_msg = str(e)
            debug.error(f"Unexpected error for agent {current_speaker.id} on turn {turn}", exc=e)
            session.logger.log_error(f"Unexpected error calling agent {current_speaker.id}: {e}")
            session.stats.record_agent_call(
                current_speaker.id,
                tokens_in=0,
                tokens_out=0,
                latency_ms=0,
                error=error_msg
            )
            session.stats.record_session_end("error")
            break

    # Log session end
    session.logger.log_session_end(
        "Orchestration complete",
        session.guardrails.get_status(),
    )

    # Write stats to file
    stats_file = session.stats.write_stats()
    session.logger.log_status(f"Stats written to: {stats_file}")


def main():
    """Main entry point with error handling and debug logging."""
    debug = get_debug_logger()
    debug.info("=" * 80)
    debug.info("LAN-LLM-Hub starting")

    parser = argparse.ArgumentParser(
        description="LAN-LLM-Hub: Multi-agent LLM orchestrator"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Path to config.toml file",
    )
    parser.add_argument(
        "-p",
        "--prompt-file",
        type=str,
        help="Path to initial prompt file",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Initial prompt as string (alternative to --prompt-file)",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Override session ID (default: timestamp)",
    )

    args = parser.parse_args()
    debug.debug(f"CLI arguments: config={args.config}, prompt_file={args.prompt_file}, session_id={args.session_id}")

    # Load config
    try:
        debug.info(f"Loading config from: {args.config}")
        loader = ConfigLoader(args.config)
        config = loader.load()
        debug.info("Config loaded successfully")
    except FileNotFoundError as e:
        debug.error(f"Config file not found: {args.config}", exc=e)
        print(f"ERROR: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        debug.error(f"Config validation failed", exc=e)
        print(f"ERROR: Config validation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        debug.error(f"Failed to load config", exc=e)
        print(f"ERROR loading config: {e}", file=sys.stderr)
        sys.exit(1)

    # Load initial prompt
    start_prompt = ""
    if args.prompt_file:
        try:
            debug.info(f"Loading prompt file: {args.prompt_file}")
            with open(args.prompt_file, "r") as f:
                start_prompt = f.read()
            debug.debug(f"Prompt loaded ({len(start_prompt)} chars)")
        except FileNotFoundError as e:
            debug.error(f"Prompt file not found: {args.prompt_file}", exc=e)
            print(f"ERROR: Prompt file not found: {args.prompt_file}", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            debug.error(f"Failed to read prompt file", exc=e)
            print(f"ERROR reading prompt file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.prompt:
        debug.debug(f"Using prompt from CLI ({len(args.prompt)} chars)")
        start_prompt = args.prompt
    else:
        debug.debug("No initial prompt provided")

    # Create and run session
    try:
        debug.info("Creating session")
        session = Session(config, start_prompt=start_prompt, session_id=args.session_id)
        print(f"Session {session.session_id} created", flush=True)
        print(f"Log file: {session.logger.get_log_file()}", flush=True)
        print(f"Debug log: ./logs/debug.log", flush=True)

        debug.info("Starting orchestration")
        run_session(session)
        debug.info("Session orchestration complete")
        print(f"Session complete", flush=True)
    except ValueError as e:
        error_msg = str(e)
        debug.error(f"Session initialization failed: {error_msg}", exc=e)
        print(f"ERROR: Session initialization failed", file=sys.stderr)
        print(f"Details: {error_msg}", file=sys.stderr)
        print(f"\nDebug log: ./logs/debug.log", file=sys.stderr)
        print(f"Session log: {session.logger.get_log_file() if 'session' in locals() else 'N/A'}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        error_msg = str(e)
        debug.error(f"Runtime error during session: {error_msg}", exc=e)
        print(f"ERROR: API call or adapter failure", file=sys.stderr)
        print(f"Details: {error_msg}", file=sys.stderr)
        print(f"\nThis indicates a system configuration fault. Check:", file=sys.stderr)
        print(f"  1. API keys are valid and not expired", file=sys.stderr)
        print(f"  2. Network connectivity to API endpoints", file=sys.stderr)
        print(f"  3. API rate limits are not exceeded", file=sys.stderr)
        print(f"  4. Model names match provider's available models", file=sys.stderr)
        print(f"\nDebug log: ./logs/debug.log (contains API responses and detailed errors)", file=sys.stderr)
        print(f"Session log: {session.logger.get_log_file() if 'session' in locals() else 'N/A'}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_msg = str(e)
        debug.error(f"Unexpected error: {error_msg}", exc=e)
        print(f"ERROR: Unexpected failure", file=sys.stderr)
        print(f"Details: {error_msg}", file=sys.stderr)
        print(f"\nDebug log: ./logs/debug.log", file=sys.stderr)
        print(f"Session log: {session.logger.get_log_file() if 'session' in locals() else 'N/A'}", file=sys.stderr)
        sys.exit(1)
    finally:
        debug.info("=" * 80)


if __name__ == "__main__":
    main()
