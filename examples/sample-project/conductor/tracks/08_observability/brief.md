<!-- ARCHITECT CONTEXT | Track: 08_observability | Wave: 1 | CC: v1 -->

# Track 08: Observability Stack

## What This Track Delivers

Configures the observability infrastructure for FlowForge: an OpenTelemetry collector in Docker Compose, Grafana + Loki for log aggregation and dashboards, structlog integration with OTel trace ID injection, FastAPI middleware for automatic tracing, base dashboards for service health and performance, and alert rules for error rate and latency thresholds.

## Scope

### IN
- OTel Collector configuration in Docker Compose (receives OTLP, exports to Grafana)
- Grafana + Loki stack in Docker Compose for log aggregation
- structlog processor that injects OTel trace_id and span_id into log entries
- Base Grafana dashboard: service health, request latency (p50/p95/p99), error rate
- FastAPI OTel middleware for automatic trace/span creation on HTTP requests
- Alert rules: error rate > 5%, p99 latency > 2s, health check failures

### OUT
- Application-specific dashboards (added incrementally by individual tracks)
- Production monitoring infrastructure (Datadog, New Relic, etc.)
- Log retention policies (backlog)
- Custom metrics beyond OTel auto-instrumentation (added per-track as needed)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. Trace backend: Grafana Tempo vs Jaeger vs Zipkin?
   Trade-off: Grafana ecosystem integration (Tempo) vs standalone maturity + UI (Jaeger) vs simplicity (Zipkin)
2. Log aggregation: Loki vs Elasticsearch/OpenSearch vs stdout-only for dev?
   Trade-off: lightweight + Grafana-native (Loki) vs full-text search power (ES) vs minimal setup (stdout)
3. OTel instrumentation: auto-instrumentation (opentelemetry-instrument) vs manual spans?
   Trade-off: coverage with zero code changes (auto) vs precision and meaningful span names (manual)
4. Alert delivery: Grafana alerting vs Alertmanager vs log-based alerts only?
   Trade-off: unified dashboard (Grafana) vs flexible routing (Alertmanager) vs simplicity (log-based)

## Architectural Notes

- The OTel Collector and Grafana stack extend the Docker Compose defined in Track 01_infra_scaffold. Coordinate service definitions to avoid port conflicts and ensure the `make dev` target includes these services.
- The structlog + OTel trace ID processor configured here becomes the logging standard for all Python services. Track 01's `backend/common/logging.py` should be updated or extended by this track.
- Dashboard and alert configurations should be provisioned as code (Grafana provisioning YAML) so they are version-controlled and reproducible across environments.

## Complexity: M
## Estimated Phases: ~2
