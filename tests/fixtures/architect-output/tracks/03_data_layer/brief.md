<!-- ARCHITECT CONTEXT | Track: 03_data_layer | Wave: 2 | CC: v1.0 -->
## Cross-Cutting Constraints
- CC-01: All services must use structured JSON logging
- CC-02: Repository pattern for all data access
## Interfaces
Owns: IDataAccess
Consumes: IInfraConfig (from Track 01)
## Dependencies
01_infra_scaffold
<!-- END ARCHITECT CONTEXT -->

# Track 03: Data Layer

## What This Track Delivers
Implements the data access layer using SQLAlchemy with repository pattern.

## Scope
IN:
- SQLAlchemy model base classes
- Repository pattern implementation
- Database migration scripts

OUT:
- Specific domain models (handled by feature tracks)

## Key Design Decisions
1. **ORM style:** Declarative vs imperative mapping?
   Trade-off: Simplicity vs flexibility.
2. **Repository granularity:** One repo per model vs shared base?
   Trade-off: Type safety vs DRY.
3. **Async support:** sync SQLAlchemy vs async?
   Trade-off: Simplicity vs performance.

## Architectural Notes
- Must use the database configuration from Track 01

## Complexity: XL
## Estimated Phases: ~5
