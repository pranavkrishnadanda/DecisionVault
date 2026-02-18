# DecisionVault MVP v1 Architecture Specification

**Version**: 1.0.0  
**Status**: Approved  
**Date**: 2026-02-18

---

## Executive Summary

DecisionVault MVP v1 delivers a **minimal verifiable decision workflow** with:

- Core decision intake and lifecycle
- Single-worker workflow execution
- Basic audit logging (append-only, non-cryptographic)
- Schema verification
- Single RabbitMQ queue

This document defines the scoped architecture for MVP v1.

---

## Scope: MVP v1 vs v2

### MVP v1 (In Scope)
- Core decision workflow (create, submit, process, complete)
- Single queue (`decision_queue`)
- Single worker type (`SchemaValidator`)
- Basic audit logging (append-only, no cryptographic chaining)
- Schema verification only

### MVP v2 (Out of Scope - Deferred)
- Cryptographic audit chaining
- Multi-agent marketplace
- Advanced verification types (signature, checksum, rule)
- Priority queue orchestration
- Distributed worker supervisor
- Multi-tenant isolation
- Complex workflow orchestration (multi-step)

---

## 1. System Context (C4 Level 1)

```
┌────────────────────────────────────────────────────────────────────┐
│                        DecisionVault Platform                       │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Decision│  │  Workflow│  │  Audit   │  │  Schema  │           │
│  │  Service │  │  Service │  │  Service │  │ Verifier │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Single Queue Worker                        │ │
│  │              (SchemaValidator - processes decision_queue)     │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
         ▲               ▲              ▲              ▲
         │               │              │              │
         ▼               ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Client    │ │  RabbitMQ   │ │  PostgreSQL │ │   Redis     │
│  (Frontend) │ │  (1 queue)  │ │  (Storage)  │ │  (Cache)    │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 2. Core Domain Model (MVP v1)

### 2.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│    Decision     │       │    AuditLog     │
├─────────────────┤       ├─────────────────┤
│ id (UUID)       │1─────*│ id (UUID)       │
│ title           │       │ entity_type     │
│ description     │       │ entity_id       │
│ status          │       │ action          │
│ priority        │       │ actor_type      │
│ created_by      │       │ actor_id        │
│ created_at      │       │ timestamp       │
│ updated_at      │       │ previous_state  │
│ metadata (JSON) │       │ current_state   │
│ workflow_id     │       │ metadata (JSON) │
└─────────────────┘       └─────────────────┘
```

**Note**: MVP v1 simplifies the model by:
- Embedding workflow state in Decision (no separate Workflow table)
- Single-step workflow (no WorkflowStep table)
- Basic audit logging (no cryptographic chaining)
- Single agent result embedded in Decision

### 2.2 Core Entities

#### Decision
```python
from django.db import models
import uuid

class DecisionStatus(models.TextChoices):
    DRAFT = "draft"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Decision(models.Model):
    """
    Core decision entity for MVP v1.
    
    Simplified single-step workflow:
    DRAFT -> PENDING -> PROCESSING -> COMPLETED|FAILED
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=DecisionStatus.choices,
        default=DecisionStatus.DRAFT
    )
    priority = models.IntegerField(default=0)  # Reserved for v2
    created_by = models.CharField(max_length=255)  # User ID (string for MVP)
    metadata = models.JSONField(default=dict)
    
    # Embedded workflow state (simplified for MVP)
    workflow_started_at = models.DateTimeField(null=True, blank=True)
    workflow_completed_at = models.DateTimeField(null=True, blank=True)
    agent_result = models.JSONField(default=dict, blank=True)
    agent_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "decisions"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
```

#### AuditLog
```python
class AuditAction(models.TextChoices):
    CREATE = "create"
    UPDATE = "update"
    SUBMIT = "submit"
    PROCESSING_START = "processing_start"
    PROCESSING_COMPLETE = "processing_complete"
    PROCESSING_FAILED = "processing_failed"

class AuditLog(models.Model):
    """
    Basic append-only audit log for MVP v1.
    
    No cryptographic chaining - added in v2.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    entity_type = models.CharField(max_length=50)  # "decision"
    entity_id = models.UUIDField()
    action = models.CharField(max_length=30, choices=AuditAction.choices)
    actor_type = models.CharField(max_length=30)  # "user", "system"
    actor_id = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    previous_state = models.JSONField(null=True, blank=True)
    current_state = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["action"]),
        ]
```

---

## 3. API Design (MVP v1)

### 3.1 Decision Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/decisions/` | Create a new decision |
| GET | `/api/v1/decisions/` | List decisions (paginated, filtered by status) |
| GET | `/api/v1/decisions/{id}/` | Get decision details with workflow state |
| GET | `/api/v1/decisions/{id}/workflow/` | Get decision workflow state |
| PUT | `/api/v1/decisions/{id}/` | Update decision (draft status only) |
| POST | `/api/v1/decisions/{id}/submit/` | Submit decision for processing |
| GET | `/api/v1/decisions/{id}/audit/` | Get audit trail for decision |

**Phase 2.5 Access Policy**:
- `GET /api/v1/decisions/{id}/workflow/` requires authentication.
- Access is limited to decision owner or staff/superuser.

### 3.2 Health Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health/live/` | Liveness probe (service is running) |
| GET | `/api/v1/health/ready/` | Readiness probe (dependencies connected) |

### 3.3 Request/Response Examples

#### Create Decision
```http
POST /api/v1/decisions/
Content-Type: application/json

{
  "title": "Loan Application #12345",
  "description": "Process loan application for customer",
  "priority": 5,
  "metadata": {
    "customer_id": "cust_123",
    "amount": 50000,
    "product": "personal_loan"
  }
}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Loan Application #12345",
  "status": "draft",
  "created_by": "user_abc",
  "created_at": "2026-02-18T10:30:00Z",
  "workflow_started_at": null,
  "workflow_completed_at": null
}
```

#### Submit Decision
```http
POST /api/v1/decisions/{id}/submit/
Content-Type: application/json

{}
```

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Decision queued for processing"
}
```

---

## 4. Queue Architecture (MVP v1)

### 4.1 Queue Topology (Simplified)

```
┌─────────────────────────────────────────────────────────────────┐
│                         RabbitMQ                                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Single Queue for MVP v1                      │   │
│  │                                                           │   │
│  │  ┌─────────────┐                                          │   │
│  │  │  decision   │                                          │   │
│  │  │  (direct)   │                                          │   │
│  │  └──────┬──────┘                                          │   │
│  │         │                                                  │   │
│  └─────────┼──────────────────────────────────────────────────┘   │
│            │                                                      │
│            ▼                                                      │
│  ┌─────────────────┐                                              │
│  │ decision_queue  │                                              │
│  │ (durable)       │                                              │
│  └─────────────────┘                                              │
│                                                                  │
│  Note: Priority queues, worker_results queue deferred to v2      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Message Format

#### Decision Submission Message
```json
{
  "message_id": "msg_abc123",
  "correlation_id": "decision_550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-02-18T10:30:00Z",
  "type": "decision.process",
  "payload": {
    "decision_id": "550e8400-e29b-41d4-a716-446655440000",
    "metadata": {...}
  },
  "routing": {
    "expiration": 3600
  }
}
```

### 4.3 Queue Configuration

| Queue | Type | Durable | Max Priority | TTL |
|-------|------|---------|--------------|-----|
| `decision_queue` | Direct | Yes | 1 (reserved for v2) | 1h |

---

## 5. Worker Architecture (MVP v1)

### 5.1 Single Worker Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    SchemaValidator Worker                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Single Worker Instance (MVP v1)               │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  SchemaValidator                                     │  │ │
│  │  │  - Validates decision metadata against JSON schema   │  │ │
│  │  │  - Updates decision status to completed/failed       │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Note: Multi-worker pool, supervisor deferred to v2             │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Worker Interface (Simplified)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class TaskContext:
    decision_id: str
    correlation_id: str
    timeout_sec: int

@dataclass
class TaskResult:
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    execution_time_ms: int = 0

class BaseAgent(ABC):
    """Base class for all workflow agents."""
    
    agent_type: str = "base"
    default_timeout: int = 300
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any], context: TaskContext) -> TaskResult:
        """Execute the agent's task."""
        pass
```

### 5.3 Agent Implementation (MVP v1 Only)

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| `SchemaValidator` | Validate decision metadata schema | `metadata` dict | `{valid: bool, errors: list}` |

**Deferred to v2:**
- DataEnricher
- RuleVerifier
- SignatureVerifier
- NotificationAgent

### 5.4 Worker Execution Flow (MVP v1)

```
┌─────────────┐
│  Receive    │
│  Message    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Parse &    │
│  Validate   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Execute    │
│  Schema     │
│  Validator  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Update     │
│  Decision   │
│  Status     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Log        │
│  Audit      │
└─────────────┘
```

---

## 6. Audit Log System (MVP v1)

### 6.1 Audit Log Design Principles (MVP)

1. **Immutable**: Once written, audit logs cannot be modified
2. **Append-only**: All changes create new entries

**Deferred to v2:**
- Cryptographic linking (hash chaining)
- Tamper-evident signatures

### 6.2 Audit Events (MVP v1)

| Event | Entity | Action | Triggered By |
|-------|--------|--------|--------------|
| `decision.created` | Decision | CREATE | API |
| `decision.updated` | Decision | UPDATE | API |
| `decision.submitted` | Decision | SUBMIT | API |
| `decision.processing_started` | Decision | PROCESSING_START | Worker |
| `decision.completed` | Decision | PROCESSING_COMPLETE | Worker |
| `decision.failed` | Decision | PROCESSING_FAILED | Worker |

---

## 7. Verification Layer (MVP v1)

### 7.1 Verification Type (MVP v1 Only)

| Type | Purpose | Method | Evidence |
|------|---------|--------|----------|
| Schema | Validate decision metadata structure | JSON Schema validation | `{valid: bool, errors: []}` |

**Deferred to v2:**
- Signature verification (ECDSA/EdDSA)
- Checksum verification (SHA-256)
- Rule-based verification
- Consistency checks

### 7.2 Schema Verification (MVP v1)

```python
import jsonschema

DECISION_SCHEMA = {
    "type": "object",
    "required": ["title", "description"],
    "properties": {
        "title": {"type": "string", "maxLength": 255},
        "description": {"type": "string"},
        "priority": {"type": "integer", "minimum": -10, "maximum": 10},
        "metadata": {"type": "object"}
    }
}

def validate_decision_schema(metadata: dict) -> dict:
    """
    Validate decision metadata against schema.
    
    Returns:
        {"valid": True, "errors": []} or
        {"valid": False, "errors": ["error1", "error2"]}
    """
    try:
        jsonschema.validate(instance=metadata, schema=DECISION_SCHEMA)
        return {"valid": True, "errors": []}
    except jsonschema.ValidationError as e:
        return {"valid": False, "errors": [e.message]}
```

---

## 8. Data Model (Django ORM - MVP v1)

### 8.1 Models Summary (MVP v1)

| Model | Table | Purpose |
|-------|-------|---------|
| `Decision` | `decisions` | Core decision entity with embedded workflow state |
| `AuditLog` | `audit_logs` | Append-only audit trail |

**Deferred to v2:**
- `Workflow` (separate table)
- `WorkflowStep`
- `AgentResult`
- `Verification`
- `QueueMessage`

### 8.2 Key Indexes

```sql
-- Decision indexes
CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_decisions_created_by ON decisions(created_by);
CREATE INDEX idx_decisions_created_at ON decisions(created_at);
CREATE INDEX idx_decisions_status_created ON decisions(status, created_at);

-- AuditLog indexes
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_action ON audit_logs(action);
```

---

## 9. TDD Implementation Plan (MVP v1)

### Phase 1: Foundation (Week 1)

#### Day 1-2: Data Models
```
├── tests/test_models/
│   ├── test_decision_model.py      # 12 tests
│   └── test_audit_log_model.py     # 8 tests
└── tests/test_models/test_constraints.py  # 5 tests
```

**Tests to write:**
- Model field validation
- Status transitions (DRAFT -> PENDING -> PROCESSING -> COMPLETED|FAILED)
- Default values
- Index existence

#### Day 3-4: API Endpoints
```
├── tests/test_api/
│   ├── test_decision_create.py     # 10 tests
│   ├── test_decision_list.py       # 8 tests
│   ├── test_decision_retrieve.py   # 6 tests
│   ├── test_decision_update.py     # 8 tests
│   ├── test_decision_submit.py     # 10 tests
│   └── test_health_endpoints.py    # 6 tests
└── tests/test_api/test_serializers.py  # 12 tests
```

**Tests to write:**
- Request validation
- Response structure
- Error handling
- Status code verification

### Phase 2: Queue & Worker (Week 2)

#### Day 1-2: Queue Infrastructure
```
├── tests/test_queue/
│   ├── test_queue_config.py        # 6 tests
│   ├── test_message_publish.py     # 10 tests
│   └── test_message_consume.py     # 10 tests
```

#### Day 3-5: SchemaValidator Worker
```
├── tests/test_workers/
│   ├── test_base_agent.py          # 8 tests
│   ├── test_schema_validator.py    # 15 tests
│   └── test_worker_consumer.py     # 12 tests
```

### Phase 3: Audit & Integration (Week 3)

#### Day 1-2: Audit Log System
```
├── tests/test_audit/
│   ├── test_audit_logging.py       # 10 tests
│   └── test_audit_immutability.py  # 6 tests
```

#### Day 3-5: End-to-End Integration
```
├── tests/test_integration/
│   └── test_decision_workflow.py   # 20 tests
```

### TDD Test Count Summary (MVP v1)

| Phase | Category | Test Count |
|-------|----------|------------|
| 1 | Models | 25 |
| 1 | API | 60 |
| 2 | Queue | 26 |
| 2 | Worker | 35 |
| 3 | Audit | 16 |
| 3 | Integration | 20 |
| **Total** | | **182 tests** |

**Note:** Reduced from 463 tests (full architecture) to 182 tests (MVP v1 scoped).

---

## 10. Risk Analysis (MVP v1)

| Risk | Impact | Mitigation |
|------|--------|------------|
| Queue message loss | High | Durable queues, persistent messages, acknowledgments |
| Audit log modification | Medium | Database-level permissions, append-only application logic |
| Worker deadlock | High | Timeout handling, manual restart procedure |
| Database bottleneck | Low (MVP) | Proper indexing, single instance sufficient for MVP |
| Schema validation bypass | High | Mandatory validation before status change |

---

## 11. Deployment (MVP v1)

### 11.1 Environment Variables
```bash
# Application
DEBUG=false
SECRET_KEY=<generated>

# Database
DB_HOST=localhost
DB_NAME=decisionvault
DB_USER=dvuser
DB_PASSWORD=<secret>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672

# Worker
WORKER_CONCURRENCY=2
WORKER_TIMEOUT=300
```

### 11.2 Health Checks
```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/live/
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/v1/health/ready/
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## 12. Next Steps

1. **Review and approve** this MVP v1 architecture document
2. **Set up GitHub project board** with TDD tasks (182 tests)
3. **Begin Phase 1** - Decision and AuditLog models with TDD
4. **Establish CI/CD** pipeline for automated testing
5. **Deploy MVP v1** to staging environment

---

**Document Version**: 1.0.0 (MVP v1 Scoped)  
**Status**: Approved  
**Date**: 2026-02-18

### MVP v1 Summary

| Aspect | Decision |
|--------|----------|
| Models | 2 (Decision, AuditLog) |
| API Endpoints | 6 (decisions CRUD + submit + audit) |
| Queues | 1 (decision_queue) |
| Workers | 1 (SchemaValidator) |
| Verification | 1 (Schema) |
| Total Tests | 182 |
| Timeline | 3 weeks |
