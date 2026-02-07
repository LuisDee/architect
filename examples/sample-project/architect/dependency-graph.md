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
| 01_infra_scaffold | — | — |
| 08_observability | — | — |
| 02_database_schema | 01_infra_scaffold | Docker Compose PostgreSQL |
| 06_event_system | 01_infra_scaffold | Docker Compose Redis |
| 03_auth_system | 01_infra_scaffold, 02_database_schema | Backend structure, User/ApiKey models |
| 04_workflow_engine | 02_database_schema, 06_event_system | Workflow/Run models, Celery + outbox relay |
| 05_api_layer | 02_database_schema, 03_auth_system, 04_workflow_engine, 06_event_system | DB models, Auth middleware, Engine API, Event bus |
| 07_react_frontend | 05_api_layer | REST API endpoints |

---

## DAG Visualization

```
Wave 1:  [01_infra_scaffold]                              [08_observability]
               │
          ┌────┴────────────────┐
          │                     │
Wave 2:  [02_database_schema]  [06_event_system]
          │                     │
     ┌────┴─────┐         ┌────┘
     │          │         │
Wave 3:  [03_auth_system]  [04_workflow_engine]
          │                     │
          └────┬────────────────┘
               │
Wave 4:  [05_api_layer]
               │
          [07_react_frontend]
```

---

## Edge Change Log

| Date | Source | Edge Added | Reason |
|------|--------|------------|--------|
| 2026-02-07 | /architect-decompose | Initial DAG | Generated from architecture analysis |

<!-- New edges from discoveries are appended here by /architect-sync -->
