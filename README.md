# AgentShield

AgentShield is a Python runtime-protection SDK for AI agents. It actively
blocks unsafe next operations when configured budget, duration, step, circuit,
or behavioral limits are reached.

Its goal is to help developers control AI-agent execution by enforcing
runtime limits such as budgets, execution steps, latency limits, and
anomaly-detection policies.

## Installation

AgentShield requires Python 3.12 or newer.

```bash
python -m pip install agentshield-1-sdk
```

For local development, install the test dependencies with:

```bash
python -m pip install -e ".[dev]"
```

## Quick Start

Decorate an agent function and check the control gateway before each
operation. Record completed steps, tool calls, and responses when the
corresponding protections are enabled.

```python
from agentshield import current_shield, shield


@shield(
	budget_limit=5.0,
	max_duration_seconds=60.0,
	max_steps=20,
	max_loops=3,
	cycle_length=2,
	max_tool_repetitions=6,
	max_stagnation_steps=20,
)
def agent():
	control = current_shield()

	control.check_before_step()
	control.record_tool("search")
	control.record_response("The latest agent response")
	control.record_step("search")

	return "done"
```

`@shield` supports synchronous and asynchronous functions. Protection errors
are raised from the public control path and are available from the package
root, for example `BudgetExceededError`, `DurationLimitExceededError`,
`LoopDetectedError`, `ToolRepetitionError`, and `StagnationDetectedError`.

## Features

- configurable budget, duration, and step limits
- token usage and estimated model cost tracking
- exact cycle, tool repetition, and response stagnation detection
- circuit-breaker enforcement with structured protection decisions
- optional bounded telemetry with failure isolation
- synchronous, asynchronous, nested, and concurrent session isolation

## Who It Is For

AgentShield is for developers building Python agents that call language
models, tools, or other external services and need explicit runtime limits.
It is a library-level control surface. It does not execute agents, replace
provider safety controls, or provide a hosted monitoring service.

## Protection Controls

- `budget_limit` blocks the next operation after recorded estimated cost
	reaches the configured amount.
- `max_duration_seconds` limits elapsed session time.
- `max_steps` limits completed agent steps.
- `max_loops` and `cycle_length` detect exact repeated step cycles.
- `max_tool_repetitions` detects consecutive calls to the same tool.
- `max_stagnation_steps` and `stagnation_similarity` detect similar responses.
- The circuit breaker blocks operations after a protection trip and supports
	cooldown and half-open probing.

The SDK can only block an operation before the caller sends it to an external
service. Call `check_before_step()` at that boundary and record completed
usage with `record_llm_call()` or `record_step()`.

## Async Usage

The same decorator works with async functions and preserves the active session
across awaits:

```python
from agentshield import current_shield, shield


@shield(budget_limit=2.0, max_duration_seconds=30.0)
async def async_agent():
		control = current_shield()
		control.check_before_step()
		# await the external operation here
		control.record_step("external-operation")
		return "done"
```

## Telemetry and Privacy

Pass an object implementing `EventSink.emit(event)` to receive bounded,
metadata-only events. Telemetry is disabled by default, and sink failures are
isolated from agent execution. The built-in events do not record prompts, raw
responses, tool arguments, or model outputs.

## Exceptions and Support

Protection failures derive from `AgentShieldError`, including budget,
duration, step, loop, tool-repetition, and stagnation errors. There is no
separate support service or hosted dashboard at this time. Use the repository
issue tracker for project questions and bug reports.

## Project Status

This is an early public library release. The API and model pricing table may
change as real-world use informs future releases. See `CHANGELOG.md` for
release history and `SECURITY.md` for vulnerability reporting guidance.

## Commercial / Enterprise

The core SDK remains free and open source. Potential paid work is described in
`COMMERCIAL.md` and is intentionally limited to professional implementation,
support, policy design, security reviews, and future enterprise integrations.
No paid service, hosted dashboard, or payment system is currently represented
as active in this repository.

Telemetry is disabled unless an `EventSink` is supplied. By default, events
record metadata and counters rather than prompts, raw responses, tool
arguments, or model outputs.

## Initial Architecture

```text
AgentShield
│
├── src/agentshield/   Core Python SDK
└── tests/             Automated tests
```

## Design Goal

AgentShield is designed around a simple principle:

> AI agents should have enforceable runtime boundaries.

The system should make it possible for developers to define limits before an agent starts executing.

Examples include maximum estimated spend, execution steps, runtime duration,
anomaly thresholds, and circuit-breaker policies.

## Safety Principle

AgentShield should fail safely.

A protection mechanism must never claim that an operation was stopped if that operation has already been sent to an external service.

The SDK will therefore distinguish between:
1. a decision to block the next operation
2. an operation that has already started
3. an operation that has completed

This distinction is important for accurate cost and execution reporting.

## License

AgentShield is released under the MIT License. See `LICENSE`.
