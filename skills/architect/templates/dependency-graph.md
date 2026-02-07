# Dependency Graph

> Directed Acyclic Graph (DAG) of track dependencies.
> An edge A → B means "A depends on B" (B must complete before A starts).
>
> Validated by: `python scripts/validate_dag.py`
> Sequenced by: `python scripts/topological_sort.py`

---

## Track Dependencies

| Track | Depends On | Interfaces Consumed |
|-------|-----------|---------------------|
| {{TRACK_ID}} | {{DEPENDENCY_LIST}} | {{INTERFACES}} |

<!-- Example:

| Track | Depends On | Interfaces Consumed |
|-------|-----------|---------------------|
| 01_infra_scaffold | — | — |
| 02_database_schema | 01_infra_scaffold | Docker Compose base |
| 03_auth | 01_infra_scaffold, 02_database_schema | PostgreSQL schema |
| 04_api_core | 01_infra_scaffold, 02_database_schema, 03_auth | Auth middleware, DB schema |
| 05_frontend_shell | 01_infra_scaffold | Dev server config |
| 06_redis_queue | 01_infra_scaffold | Docker Compose base |
| 07_background_jobs | 04_api_core, 06_redis_queue | REST API, Queue abstraction |
| 08_notifications | 04_api_core, 06_redis_queue | REST API, Queue abstraction |
| 09_workflows | 04_api_core, 06_redis_queue | REST API, Queue abstraction |
| 10_frontend_features | 05_frontend_shell, 04_api_core | Frontend shell, REST API |
| 11_realtime | 04_api_core, 06_redis_queue | REST API, Redis pub/sub |
| 12_admin | 04_api_core, 03_auth | REST API, Auth (admin role) |
| 13_observability | 01_infra_scaffold | Docker Compose base |

-->

---

## DAG Visualization

```
{{DAG_ASCII}}
```

<!-- Example:

```
Wave 1:  [01_infra]  [13_observability]
              │
Wave 2:  [02_db_schema]  [05_frontend_shell]  [06_redis_queue]
              │                    │                   │
Wave 3:  [03_auth]                │                   │
              │                    │                   │
Wave 4:  [04_api_core]───────────┼───────────────────┤
              │                    │                   │
Wave 5:  [07_bg_jobs] [08_notify] [09_workflows] [10_fe_features] [11_realtime] [12_admin]
```

-->

---

## Edge Change Log

<!-- When new dependencies are added via discovery, record them here.

| Date | Source | Edge Added | Reason |
|------|--------|------------|--------|
| {{DATE}} | Discovery {{ID}} | {{FROM}} → {{TO}} | {{REASON}} |

Example:
| 2026-02-08 | track-09-...-a3f2b8 | 11_realtime → 06_redis_queue | WebSocket needs pub/sub |

-->
