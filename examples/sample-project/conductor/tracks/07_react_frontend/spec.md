<!-- ARCHITECT CONTEXT v2 | Track: 07_react_frontend | Wave: 4 | CC: v1 -->
<!-- Full context header omitted for brevity — see tracks 01/02 for full examples -->

# Track 07_react_frontend: React Frontend & Workflow Builder

## Overview

Full React UI for FlowForge: authentication pages, workflow list/detail views, drag-and-drop workflow builder using React Flow, run monitoring dashboard with live updates, and settings pages. Wave 4 — depends on the API layer being available.

## Scope

### In Scope
- Auth pages: login, register, password reset
- Dashboard: recent workflows, active runs summary, quick actions
- Workflow list with search, filter, and pagination
- Workflow builder: React Flow canvas, step palette, property editor, save/validate
- Run monitoring: live status, step-by-step progress, log viewer, cancel button
- Settings: profile, API keys management
- Responsive layout with sidebar navigation

### Out of Scope
- Admin panel (backlog)
- Real-time WebSocket updates (backlog — polling MVP)
- Mobile-specific layouts (backlog)
- Workflow version history / diff view (backlog)

## Acceptance Criteria

1. User can register, login, and see dashboard
2. User can create a workflow with 5+ steps using drag-and-drop builder
3. User can trigger a workflow and monitor execution in real time (polling)
4. Step property editor validates configuration before save
5. Workflow list supports search by name and filter by status
6. All API errors displayed with user-friendly messages
7. Lighthouse accessibility score >= 80
