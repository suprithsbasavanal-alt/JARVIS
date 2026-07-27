# Developer Dashboard Module (`src/dashboard`)

## Purpose
Provides developer inspection capabilities, OpenTelemetry trace collectors, real-time agent state visualization, tool call debugging, and memory inspection interfaces.

## Architectural Layer
**Presentation & Observability Layer (ISP)**. Operates via non-blocking telemetry collectors so agent reasoning loops remain unhindered.

## Subdirectories
- `telemetry/`: Metrics aggregator, execution latency tracker, and OpenTelemetry trace exporters.
- `inspector/`: Live agent state, active tool execution log viewer, and vector memory inspection UI shell.
