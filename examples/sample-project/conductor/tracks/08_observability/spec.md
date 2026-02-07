<!-- ARCHITECT CONTEXT v2 | Track: 08_observability | Wave: 1 | CC: v1 -->
<!-- Full context header omitted for brevity — see tracks 01/02 for full examples -->

# Track 08_observability: Observability Stack

## Overview

Configures the observability infrastructure: OpenTelemetry collector in Docker Compose, Grafana + Loki for log aggregation, structlog integration with OTel trace IDs, health check dashboard, and base alert rules. Wave 1 — no dependencies (runs in parallel with infrastructure scaffold).

## Scope

### In Scope
- OTel Collector configuration in Docker Compose (receives OTLP, exports to Grafana)
- Grafana + Loki stack in Docker Compose for log aggregation
- structlog processor that injects OTel trace_id and span_id into log entries
- Base Grafana dashboard: service health, request latency (p50/p95/p99), error rate
- FastAPI OTel middleware for automatic trace/span creation on HTTP requests
- Alert rules: error rate > 5%, p99 latency > 2s, health check failures

### Out of Scope
- Application-specific dashboards (added by individual tracks)
- Production monitoring infrastructure (Datadog, New Relic, etc.)
- Log retention policies (backlog)
- Custom metrics beyond OTel auto-instrumentation (added per-track)

## Acceptance Criteria

1. OTel Collector receives traces from backend service
2. Logs appear in Grafana/Loki with trace_id correlation
3. Base dashboard renders with health, latency, and error rate panels
4. Alert rules fire on simulated error spike
5. `make dev` includes observability stack in Docker Compose
