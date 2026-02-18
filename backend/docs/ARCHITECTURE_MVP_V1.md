# DecisionVault MVP v1 Architecture Specification

**Version**: 1.0.0  
**Status**: Draft  
**Date**: 2026-02-18

---

## Executive Summary

DecisionVault MVP v1 delivers a **verifiable decision orchestration platform** with:

- Decision intake and validation
- Agent-based workflow execution
- Cryptographic audit trails
- Multi-stage verification
- Async worker processing

This document defines the complete architecture for MVP v1.

---

## 1. System Context (C4 Level 1)

```
┌────────────────────────────────────────────────────────────────────┐
│                        DecisionVault Platform                       │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Decision│  │  Agent   │  │ Workflow │  │  Audit   │           │
│  │  Service │  │  Service │  │  Engine  │  │  Service │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │   API    │  │  Queue   │  │  Worker  │  │Verification│          │
│  │ Gateway  │  │  Manager │  │  Pool    │  │  Service  │          │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└────────────────────────────────────────────────────────────────────┘
         ▲               ▲              ▲              ▲
         │               │              │              │
         ▼               ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Client    │ │  RabbitMQ   │ │  PostgreSQL │ │   Redis     │
│  (Frontend) │ │  (Broker)   │ │  (Storage)  │ │  (Cache)    │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 2. Core Domain Model

### 2.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Decision     │       │    Workflow     │       │   WorkflowStep  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (UUID)       │1─────*│ id (UUID)       │1─────*│ id (UUID)       │
│ title           │       │ decision_id     │       │ workflow_id     │
│ description     │       │ status          │       │ step_number     │
│ status          │       │ created_at      │       │ agent_type      │
│ priority        │       │ updated_at      │       │ action          │
│ created_by      │       │ completed_at    │       │ status          │
│ created_at      │       │                 │       │ result          │
│ updated_at      │       │                 │       │ started_at      │
│ metadata (JSON) │       │                 │       │ completed_at    │
└─────────────────┘       └─────────────────┘       │ error (JSON)    │
        │                                           │ retry_count     │
        │1                                          │ timeout_sec     │
        │                                           └─────────────────┘
        │                                                   │
        │*                                                  │1
┌─────────────────┐       ┌─────────────────┐               │
│   AuditLog      │       │  Verification   │               │
├─────────────────┤       ├─────────────────┤               │
│ id (UUID)       │       │ id (UUID)       │               │
│ entity_type     │       │ workflow_step_id│               │
│ entity_id       │       │ verifier_type   │               │
│ action          │       │ status          │               │
│ actor_id        │       │ result          │               │
│ actor_type      │       │ evidence (JSON) │               │
│ timestamp       │       │ verified_at     │               │
│ previous_state  │       │ verified_by     │               │
│ current_state   │       │ error_message   │               │
│ ip_address      │       └─────────────────┘               │
│ user_agent      │                                         │
│ correlation_id  │       ┌─────────────────┐               │
└─────────────────┘       │   AgentResult   │               │
                          ├─────────────────┤               │
                          │ id (UUID)       │◄──────────────┘
                          │ workflow_step_id│
                          │ agent_type      │
                          │ input (JSON)    │
                          │ output (JSON)   │
                          │ status          │
                          │ execution_time  │
                          │ created_at      │
                          └─────────────────┘
```

### 2.2 Core Entities

#### Decision
```python
class DecisionStatus(models.TextChoices):
    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Decision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=DecisionStatus.choices)
    priority = models.IntegerField(default=0)  # -10 (low) to 10 (critical)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### Workflow
```python
class WorkflowStatus(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    decision = models.ForeignKey(Decision, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=WorkflowStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
```

#### WorkflowStep
```python
class StepStatus(models.TextChoices):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"

class WorkflowStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    step_number = models.IntegerField()
    agent_type = models.CharField(max_length=50)  # e.g., "validator", "enricher"
    action = models.CharField(max_length=100)     # e.g., "validate_schema"
    status = models.CharField(max_length=20, choices=StepStatus.choices)
    result = models.JSONField(default=dict, blank=True)
    error = models.JSONField(default=dict, blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    timeout_sec = models.IntegerField(default=300)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
```

#### AuditLog
```python
class AuditAction(models.TextChoices):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STATE_CHANGE = "state_change"
    VERIFICATION = "verification"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAILED = "workflow_failed"

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    entity_type = models.CharField(max_length=50)  # "decision", "workflow", "step"
    entity_id = models.UUIDField()
    action = models.CharField(max_length=30, choices=AuditAction.choices)
    actor_id = models.UUIDField(null=True, blank=True)  # User ID or system
    actor_type = models.CharField(max_length=30)  # "user", "system", "agent"
    timestamp = models.DateTimeField(auto_now_add=True)
    previous_state = models.JSONField(null=True, blank=True)
    current_state = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)  # Request tracing
```

#### Verification
```python
class VerificationStatus(models.TextChoices):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"

class Verification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow_step = models.OneToOneField(WorkflowStep, on_delete=models.CASCADE)
    verifier_type = models.CharField(max_length=50)  # "signature", "checksum", "rule"
    status = models.CharField(max_length=20, choices=VerificationStatus.choices)
    result = models.JSONField(default=dict)
    evidence = models.JSONField(default=dict)  # Cryptographic proof, hashes
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=100)  # Agent identifier
    error_message = models.TextField(blank=True)
```

#### AgentResult
```python
class AgentStatus(models.TextChoices):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"

class AgentResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow_step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE)
    agent_type = models.CharField(max_length=50)
    input = models.JSONField(default=dict)
    output = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=AgentStatus.choices)
    execution_time_ms = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 3. API Design (REST)

### 3.1 Decision Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/decisions/` | Create a new decision |
| GET | `/api/v1/decisions/` | List decisions (paginated) |
| GET | `/api/v1/decisions/{id}/` | Get decision details |
| PUT | `/api/v1/decisions/{id}/` | Update decision |
| DELETE | `/api/v1/decisions/{id}/` | Cancel/delete decision |
| POST | `/api/v1/decisions/{id}/submit/` | Submit for processing |

### 3.2 Workflow Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/decisions/{id}/workflow/` | Get workflow for decision |
| GET | `/api/v1/workflows/` | List workflows |
| GET | `/api/v1/workflows/{id}/` | Get workflow details |
| POST | `/api/v1/workflows/{id}/cancel/` | Cancel workflow |

### 3.3 Audit Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/audit/` | List audit logs (filtered) |
| GET | `/api/v1/audit/{entity_type}/{entity_id}/` | Get audit trail for entity |
| GET | `/api/v1/audit/{id}/` | Get specific audit log |

### 3.4 Verification Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/verifications/` | List verifications |
| GET | `/api/v1/verifications/{id}/` | Get verification details |
| GET | `/api/v1/verifications/{id}/evidence/` | Get verification evidence |

### 3.5 Request/Response Examples

#### Create Decision
```http
POST /api/v1/decisions/
Content-Type: application/json
Authorization: Bearer <token>

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
  "workflow_url": "/api/v1/decisions/550e8400-e29b-41d4-a716-446655440000/workflow/"
}
```

#### Submit Decision
```http
POST /api/v1/decisions/{id}/submit/
Content-Type: application/json

{
  "correlation_id": "req_abc123"
}
```

---

## 4. Queue Architecture

### 4.1 Queue Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                         RabbitMQ                                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Exchanges                              │   │
│  │                                                           │   │
│  │  ┌─────────────┐      ┌─────────────┐                    │   │
│  │  │  decisions  │      │   workers   │                    │   │
│  │  │  (direct)   │      │  (topic)    │                    │   │
│  │  └──────┬──────┘      └──────┬──────┘                    │   │
│  │         │                    │                            │   │
│  └─────────┼────────────────────┼────────────────────────────┘   │
│            │                    │                                │
│            ▼                    ▼                                │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │ decision_queue  │  │ worker_results  │                       │
│  │ (durable)       │  │ (durable)       │                       │
│  └─────────────────┘  └─────────────────┘                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Priority Queues (per agent type)             │   │
│  │                                                           │   │
│  │  validator_queue (high)    enricher_queue (normal)        │   │
│  │  verifier_queue (high)     notifier_queue (low)           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Message Formats

#### Decision Submission Message
```json
{
  "message_id": "msg_abc123",
  "correlation_id": "req_xyz789",
  "timestamp": "2026-02-18T10:30:00Z",
  "type": "decision.submit",
  "payload": {
    "decision_id": "550e8400-e29b-41d4-a716-446655440000",
    "priority": 5,
    "metadata": {...}
  },
  "routing": {
    "reply_to": "worker_results",
    "expiration": 3600
  }
}
```

#### Worker Task Message
```json
{
  "message_id": "msg_def456",
  "correlation_id": "workflow_abc",
  "timestamp": "2026-02-18T10:31:00Z",
  "type": "worker.task",
  "payload": {
    "step_id": "step_123",
    "workflow_id": "workflow_abc",
    "agent_type": "validator",
    "action": "validate_schema",
    "input": {...},
    "timeout_sec": 300,
    "retry_count": 0
  }
}
```

#### Worker Result Message
```json
{
  "message_id": "msg_ghi789",
  "correlation_id": "workflow_abc",
  "timestamp": "2026-02-18T10:35:00Z",
  "type": "worker.result",
  "payload": {
    "step_id": "step_123",
    "status": "success",
    "output": {...},
    "execution_time_ms": 4500,
    "error": null
  }
}
```

### 4.3 Queue Configuration

| Queue | Type | Durable | Priority | TTL |
|-------|------|---------|----------|-----|
| `decision_queue` | Direct | Yes | High | 1h |
| `worker_results` | Direct | Yes | High | 1h |
| `validator_queue` | Topic | Yes | High | 5m |
| `verifier_queue` | Topic | Yes | High | 5m |
| `enricher_queue` | Topic | Yes | Normal | 10m |
| `notifier_queue` | Topic | Yes | Low | 30m |

---

## 5. Worker Architecture

### 5.1 Worker Pool Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        Worker Supervisor                         │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Worker Pool                               │ │
│  │                                                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ Validator│  │ Validator│  │ Verifier │  │ Enricher │   │ │
│  │  │ Worker 1 │  │ Worker 2 │  │ Worker 1 │  │ Worker 1 │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  │                                                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │ │
│  │  │ Enricher │  │ Notifier │  │ Validator│  │ Verifier │   │ │
│  │  │ Worker 2 │  │ Worker 1 │  │ Worker 3 │  │ Worker 2 │   │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Health Monitor                             │ │
│  │  - Heartbeat tracking                                       │ │
│  │  - Auto-restart on failure                                  │ │
│  │  - Queue depth monitoring                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Worker Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

@dataclass
class TaskContext:
    step_id: str
    workflow_id: str
    decision_id: str
    correlation_id: str
    retry_count: int
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
    max_retries: int = 3
    default_timeout: int = 300
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any], context: TaskContext) -> TaskResult:
        """Execute the agent's task."""
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input before execution."""
        return True
    
    def on_retry(self, input_data: Dict[str, Any], context: TaskContext, last_error: str):
        """Hook called before retry."""
        pass
    
    def on_timeout(self, context: TaskContext):
        """Hook called on timeout."""
        pass
```

### 5.3 Agent Implementations (MVP)

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| `SchemaValidator` | Validate decision schema | Raw metadata | Validation result |
| `DataEnricher` | Enrich with external data | Decision ID | Enriched metadata |
| `RuleVerifier` | Apply business rules | Enriched data | Rule evaluation |
| `SignatureVerifier` | Verify cryptographic signatures | Signed payload | Verification proof |
| `NotificationAgent` | Send notifications | Event data | Delivery status |

### 5.4 Worker Execution Flow

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
┌─────────────┐     ┌─────────────┐
│  Acquire    │────▶│  Timeout    │
│  Lock       │     │  Watcher    │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│  Execute    │
│  Agent      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Verify     │
│  Result     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Publish    │
│  Result     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Log        │
│  Audit      │
└─────────────┘
```

---

## 6. Audit Log System

### 6.1 Audit Log Design Principles

1. **Immutable**: Once written, audit logs cannot be modified
2. **Append-only**: All changes create new entries
3. **Cryptographically linked**: Each entry references previous hash
4. **Tamper-evident**: Any modification is detectable

### 6.2 Audit Log Structure

```python
class AuditLogEntry:
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    actor_id: Optional[UUID]
    actor_type: str
    timestamp: datetime
    previous_state_hash: Optional[str]  # SHA-256 of previous state
    current_state_hash: str             # SHA-256 of current state
    previous_state: Optional[Dict]      # Full state (encrypted if sensitive)
    current_state: Optional[Dict]       # Full state
    ip_address: Optional[str]
    user_agent: Optional[str]
    correlation_id: Optional[UUID]
    signature: str                      # Digital signature for integrity
```

### 6.3 Audit Chain

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Entry 1   │────▶│   Entry 2   │────▶│   Entry 3   │
│  prev=null  │     │prev=hash(1) │     │prev=hash(2) │
│  sig=sig1   │     │  sig=sig2   │     │  sig=sig3   │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 6.4 Audit Events

| Event | Entity | Action | Triggered By |
|-------|--------|--------|--------------|
| `decision.created` | Decision | CREATE | API |
| `decision.submitted` | Decision | STATE_CHANGE | API |
| `workflow.started` | Workflow | WORKFLOW_START | System |
| `step.started` | WorkflowStep | STATE_CHANGE | Worker |
| `step.completed` | WorkflowStep | STATE_CHANGE | Worker |
| `verification.performed` | Verification | VERIFICATION | Agent |
| `workflow.completed` | Workflow | WORKFLOW_COMPLETE | System |

---

## 7. Verification Layer

### 7.1 Verification Types

| Type | Purpose | Method | Evidence |
|------|---------|--------|----------|
| Schema | Validate structure | JSON Schema | Validation report |
| Signature | Verify authenticity | ECDSA/EdDSA | Signature blob |
| Checksum | Verify integrity | SHA-256 | Hash value |
| Rule | Business logic | Rule engine | Rule evaluation |
| Consistency | Cross-field validation | Custom logic | Consistency report |

### 7.2 Verification Flow

```
┌─────────────┐
│  Step       │
│  Completed  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Select     │
│  Verifiers  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Run        │
│  Verifiers  │◀───────┐
└──────┬──────┘        │
       │               │
       ▼               │
┌─────────────┐   No   │
│  All Pass?  │───────┘
└──────┬──────┘
       │ Yes
       ▼
┌─────────────┐
│  Generate   │
│  Evidence   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Store &    │
│  Sign       │
└─────────────┘
```

### 7.3 Evidence Structure

```json
{
  "verification_id": "ver_abc123",
  "workflow_step_id": "step_xyz",
  "verifier_type": "signature",
  "timestamp": "2026-02-18T10:35:00Z",
  "input_hash": "sha256:abc123...",
  "output_hash": "sha256:def456...",
  "verification_method": "ECDSA-P256",
  "public_key_id": "key_789",
  "signature": "base64:MEUCI...",
  "certificate_chain": [...],
  "metadata": {
    "verifier_version": "1.0.0",
    "environment": "production"
  }
}
```

---

## 8. Data Model (Django ORM)

### 8.1 Models Summary

| Model | Table | Purpose |
|-------|-------|---------|
| `Decision` | `decisions` | Core decision entity |
| `Workflow` | `workflows` | Workflow instance |
| `WorkflowStep` | `workflow_steps` | Individual workflow steps |
| `AgentResult` | `agent_results` | Agent execution results |
| `Verification` | `verifications` | Verification records |
| `AuditLog` | `audit_logs` | Immutable audit trail |
| `QueueMessage` | `queue_messages` | Message tracking (idempotency) |

### 8.2 Key Indexes

```sql
-- Decision indexes
CREATE INDEX idx_decisions_status ON decisions(status);
CREATE INDEX idx_decisions_created_by ON decisions(created_by);
CREATE INDEX idx_decisions_created_at ON decisions(created_at);
CREATE INDEX idx_decisions_status_created ON decisions(status, created_at);

-- Workflow indexes
CREATE INDEX idx_workflows_decision ON workflows(decision_id);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_created_at ON workflows(created_at);

-- WorkflowStep indexes
CREATE INDEX idx_steps_workflow ON workflow_steps(workflow_id);
CREATE INDEX idx_steps_status ON workflow_steps(status);
CREATE INDEX idx_steps_agent ON workflow_steps(agent_type, status);

-- AuditLog indexes
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_correlation ON audit_logs(correlation_id);
```

---

## 9. TDD Implementation Plan

### Phase 1: Foundation (Week 1)

#### Day 1-2: Data Models
```
├── tests/test_models/
│   ├── test_decision_model.py      # 15 tests
│   ├── test_workflow_model.py      # 12 tests
│   ├── test_workflow_step_model.py # 10 tests
│   ├── test_audit_log_model.py     # 8 tests
│   └── test_verification_model.py  # 8 tests
├── tests/test_models/test_constraints.py  # 10 tests
└── tests/test_models/test_indexes.py      # 5 tests
```

**Tests to write:**
- Model field validation
- Status transitions
- Foreign key relationships
- Default values
- Unique constraints
- Index existence

#### Day 3-4: API Endpoints (Decisions)
```
├── tests/test_api/
│   ├── test_decision_create.py     # 12 tests
│   ├── test_decision_list.py       # 10 tests
│   ├── test_decision_retrieve.py   # 8 tests
│   ├── test_decision_update.py     # 10 tests
│   └── test_decision_submit.py     # 15 tests
└── tests/test_api/test_serializers.py  # 20 tests
```

**Tests to write:**
- Request validation
- Response structure
- Authentication/authorization
- Error handling
- Status code verification

#### Day 5: API Endpoints (Workflows)
```
├── tests/test_api/
│   ├── test_workflow_retrieve.py   # 8 tests
│   ├── test_workflow_list.py       # 8 tests
│   └── test_workflow_cancel.py     # 10 tests
```

### Phase 2: Queue & Workers (Week 2)

#### Day 1-2: Queue Infrastructure
```
├── tests/test_queue/
│   ├── test_queue_config.py        # 10 tests
│   ├── test_message_publish.py     # 15 tests
│   ├── test_message_consume.py     # 15 tests
│   └── test_message_serialization.py  # 10 tests
```

#### Day 3-5: Worker Framework
```
├── tests/test_workers/
│   ├── test_base_agent.py          # 12 tests
│   ├── test_worker_supervisor.py   # 15 tests
│   ├── test_task_execution.py      # 20 tests
│   ├── test_retry_logic.py         # 15 tests
│   └── test_timeout_handling.py    # 10 tests
```

### Phase 3: Audit & Verification (Week 3)

#### Day 1-2: Audit Log System
```
├── tests/test_audit/
│   ├── test_audit_logging.py       # 15 tests
│   ├── test_audit_immutability.py  # 10 tests
│   ├── test_audit_chain.py         # 8 tests
│   └── test_audit_querying.py      # 10 tests
```

#### Day 3-5: Verification Layer
```
├── tests/test_verification/
│   ├── test_schema_validator.py    # 12 tests
│   ├── test_signature_verifier.py  # 15 tests
│   ├── test_rule_verifier.py       # 12 tests
│   └── test_evidence_generation.py # 10 tests
```

### Phase 4: Integration (Week 4)

#### Day 1-3: End-to-End Tests
```
├── tests/test_integration/
│   ├── test_decision_workflow.py   # 25 tests
│   ├── test_agent_orchestration.py # 20 tests
│   └── test_audit_completeness.py  # 15 tests
```

#### Day 4-5: Performance & Reliability
```
├── tests/test_performance/
│   ├── test_concurrent_decisions.py  # 10 tests
│   ├── test_queue_throughput.py      # 8 tests
│   └── test_worker_scaling.py        # 7 tests
```

### TDD Test Count Summary

| Phase | Category | Test Count |
|-------|----------|------------|
| 1 | Models | 63 |
| 1 | API (Decisions) | 75 |
| 1 | API (Workflows) | 26 |
| 2 | Queue | 50 |
| 2 | Workers | 72 |
| 3 | Audit | 43 |
| 3 | Verification | 49 |
| 4 | Integration | 60 |
| 4 | Performance | 25 |
| **Total** | | **463 tests** |

---

## 10. Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| Queue message loss | High | Durable queues, persistent messages, acknowledgments |
| Audit log tampering | Critical | Cryptographic chaining, write-once storage |
| Worker deadlock | High | Timeout handling, heartbeat monitoring |
| Database bottleneck | Medium | Proper indexing, connection pooling, read replicas |
| Verification bypass | Critical | Mandatory verification gates, defense in depth |

---

## 11. Deployment Considerations

### 11.1 Environment Variables
```bash
# Application
DV_ENVIRONMENT=production
DV_SECRET_KEY=<generated>
DV_DEBUG=false

# Database
DV_DB_HOST=postgres
DV_DB_NAME=decisionvault
DV_DB_USER=dvuser
DV_DB_PASSWORD=<secret>

# Redis
DV_REDIS_HOST=redis
DV_REDIS_PORT=6379

# RabbitMQ
DV_RABBITMQ_HOST=rabbitmq
DV_RABBITMQ_PORT=5672
DV_RABBITMQ_VHOST=/decisionvault

# Workers
DV_WORKER_CONCURRENCY=4
DV_WORKER_MAX_TASKS=1000
DV_WORKER_TIMEOUT=300
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

1. **Review and approve** this architecture document
2. **Set up project board** with TDD tasks
3. **Begin Phase 1** - Data Models with TDD
4. **Establish CI/CD** pipeline for automated testing
5. **Set up monitoring** stack (Prometheus, Grafana)

---

**Document Version**: 1.0.0  
**Author**: Architecture Team  
**Review Date**: 2026-02-18
