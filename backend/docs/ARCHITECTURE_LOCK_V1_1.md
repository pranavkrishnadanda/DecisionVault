# DecisionVault Architecture Lock v1.1

**Version**: 1.1.0  
**Status**: Locked  
**Date**: 2026-02-18

## Purpose
This file is the architectural lock contract for backend implementation.
When this file conflicts with other architecture docs, this file wins.

## Canonical Contracts

### Messaging
- Canonical RabbitMQ queue name: `decision_tasks`
- Queue constant must be imported from `core.constants.DECISION_TASKS_QUEUE`
- Task type for decision processing: `decision.process`

### Decision Lifecycle
- Allowed lifecycle states:
  - `draft`
  - `pending`
  - `processing`
  - `completed`
  - `failed`
- Worker processing transition:
  - `pending -> processing -> completed|failed`

### Audit Actions
- Required decision audit actions:
  - `create`
  - `submit`
  - `processing_start`
  - `processing_complete`
  - `processing_failed`

### API Baseline (MVP)
- `POST /api/v1/decisions/`
- `GET /api/v1/decisions/`
- `GET /api/v1/decisions/{id}/`
- `POST /api/v1/decisions/{id}/submit/`
- `GET /api/v1/decisions/{id}/audit/`

### Security Baseline
- Anonymous mutation is not allowed.
- Ownership enforcement is required for decision mutations and protected reads.

## Change Control
- Any change to queue names, decision states, or audit action semantics requires:
  1. Update to this lock file
  2. Matching code change
  3. Matching tests
  4. Linked PR note describing compatibility impact

## Documentation Discipline
- Any backend module change must include doc alignment updates in `backend/docs/`.
- Architecture drift is a blocking defect.
