<!-- ARCHITECT CONTEXT | Track: 07_react_frontend | Wave: 4 | CC: v1 -->

# Track 07: React Frontend & Workflow Builder

## What This Track Delivers

The full React user interface for FlowForge: authentication pages, a workflow list and detail view, a drag-and-drop workflow builder powered by React Flow, a run monitoring dashboard with live status polling, and settings/profile pages. Builds on the frontend scaffold from Track 01 and consumes the REST API from Track 05.

## Scope

### IN
- Auth pages: login, register, password reset
- Dashboard: recent workflows, active runs summary, quick actions
- Workflow list with search, filter, and pagination
- Workflow builder: React Flow canvas, step palette, property editor, save/validate
- Run monitoring: live status polling, step-by-step progress, log viewer, cancel button
- Settings: profile editing, API key management
- Responsive layout with sidebar navigation

### OUT
- Admin panel (backlog)
- Real-time WebSocket updates (backlog -- polling for MVP)
- Mobile-specific layouts (backlog)
- Workflow version history / diff view (backlog)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. State management: Zustand vs Redux Toolkit vs React Query + context?
   Trade-off: simplicity + small bundle (Zustand) vs ecosystem + devtools (Redux) vs server-state focus (React Query)
2. Workflow builder library: React Flow vs xyflow vs custom canvas with D3?
   Trade-off: out-of-the-box features (React Flow) vs full control + lighter weight (custom)
3. UI component library: shadcn/ui vs MUI vs Ant Design vs fully custom?
   Trade-off: styling flexibility (shadcn) vs feature completeness (MUI/Ant) vs design control (custom)
4. Data fetching: React Query/TanStack Query vs SWR vs plain Axios with useEffect?
   Trade-off: caching + refetch logic (Query/SWR) vs simplicity + full control (plain Axios)
5. Form handling: React Hook Form vs Formik vs native controlled components?
   Trade-off: performance + validation (RHF) vs familiarity (Formik) vs simplicity (native)

## Architectural Notes

- The frontend scaffold from Track 01 provides the Vite config, routing setup, and Axios client. This track extends that foundation -- do not restructure the base scaffold.
- All API contracts are defined in `architect/interfaces.md`. The frontend must implement against those exact response shapes (envelope format, cursor pagination, error format).
- Token refresh must be transparent to the user experience. The Axios interceptor should automatically retry failed 401 requests after refreshing the access token.

## Complexity: L
## Estimated Phases: ~4
