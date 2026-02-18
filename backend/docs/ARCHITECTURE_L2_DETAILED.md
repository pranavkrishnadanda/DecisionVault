# DecisionVault Backend - L2 Architecture (Detailed Component Design)

**Governance**: This document is governed by `ARCHITECTURE_LOCK_V1_1.md`.

## Document Purpose

This document provides detailed component-level architecture for the DecisionVault backend system. It describes internal structures, data flows, interfaces, and interactions between all system components.

---

## Table of Contents

1. [Core Module Architecture](#1-core-module-architecture)
2. [API Module Architecture](#2-api-module-architecture)
3. [Ingestion Module Architecture](#3-ingestion-module-architecture)
4. [Verification Module Architecture](#4-verification-module-architecture)
5. [Workers Module Architecture](#5-workers-module-architecture)
6. [Data Architecture](#6-data-architecture)
7. [Integration Architecture](#7-integration-architecture)
8. [Deployment Architecture](#8-deployment-architecture)

---

## 1. Core Module Architecture

### 1.1 Module Structure

```
core/
├── __init__.py          # Package initializer (empty)
├── settings.py          # Django configuration center
├── urls.py              # Root URL configuration
├── wsgi.py              # WSGI application
├── asgi.py              # ASGI application
├── rabbitmq.py          # RabbitMQ client wrapper
├── cache_test.py        # Cache testing utility
└── test_rabbitmq.py     # RabbitMQ integration test
```

### 1.2 Settings Module (`settings.py`)

#### 1.2.1 Configuration Categories

| Category | Settings | Description |
|----------|----------|-------------|
| **Base** | `BASE_DIR`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Core Django settings |
| **Apps** | `INSTALLED_APPS` | Registered Django applications |
| **Middleware** | `MIDDLEWARE` | Request/response processing pipeline |
| **Templates** | `TEMPLATES` | Template engine configuration |
| **Database** | `DATABASES` | PostgreSQL connection settings |
| **Auth** | `AUTH_PASSWORD_VALIDATORS` | Password validation rules |
| **i18n** | `LANGUAGE_CODE`, `TIME_ZONE`, `USE_I18N`, `USE_TZ` | Internationalization |
| **Static** | `STATIC_URL` | Static file serving |
| **Logging** | `LOGGING` | Logging configuration |
| **Cache** | `REDIS_HOST`, `REDIS_PORT`, `CACHES` | Redis cache settings |
| **Messaging** | `RABBITMQ_HOST`, `RABBITMQ_PORT` | RabbitMQ connection |

#### 1.2.2 Middleware Stack (Request → Response Order)

```
1. SecurityMiddleware              → SSL, HSTS, security headers
2. SessionMiddleware               → Session management
3. CommonMiddleware                → ETags, content-type
4. CsrfViewMiddleware              → CSRF protection
5. AuthenticationMiddleware        → User auth on each request
6. MessageMiddleware               → Flash messages
7. XFrameOptionsMiddleware         → Clickjacking protection
```

### 1.3 RabbitMQ Client (`rabbitmq.py`)

#### 1.3.1 Class Design

```python
class RabbitMQClient:
    """
    Synchronous RabbitMQ client for publishing decision tasks.
    
    Attributes:
        connection: pika.BlockingConnection
        channel: pika.channel.Channel
    """
    
    def __init__(self):
        """Initialize connection and declare durable queue."""
        
    def publish(data: dict) -> None:
        """Publish JSON-serialized message to decision_tasks queue."""
        
    def close() -> None:
        """Close connection."""
```

#### 1.3.2 Queue Configuration

| Property | Value | Description |
|----------|-------|-------------|
| Queue Name | `decision_tasks` | Task queue name |
| Durable | `True` | Survives broker restart |
| Exchange | `""` (default) | Direct exchange |
| Delivery Mode | `2` (persistent) | Messages survive restart |

#### 1.3.3 Message Format

```json
{
    "type": "string",
    "message": "string",
    "metadata": {}
}
```

### 1.4 URL Configuration (`urls.py`)

#### 1.4.1 Current Routes

| Path | Handler | Description |
|------|---------|-------------|
| `/admin/` | `admin.site.urls` | Django admin interface |

#### 1.4.2 Planned Routes (To Implement)

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('ingest/', include('ingestion.urls')),
    path('verify/', include('verification.urls')),
    path('workers/', include('workers.urls')),
]
```

### 1.5 WSGI/ASGI Applications

#### 1.5.1 WSGI (`wsgi.py`)
- **Purpose**: Production HTTP server interface
- **Application**: `core.wsgi.application`
- **Server**: Gunicorn (3 workers)

#### 1.5.2 ASGI (`asgi.py`)
- **Purpose**: Async protocol interface (future use)
- **Application**: `core.asgi.application`
- **Server**: Uvicorn (available but not configured)

---

## 2. API Module Architecture

### 2.1 Module Structure

```
api/
├── __init__.py          # Package initializer
├── apps.py              # AppConfig (name='api')
├── models.py            # Database models (empty)
├── views.py             # HTTP handlers (empty)
├── admin.py             # Admin registration (empty)
├── urls.py              # API routes (to create)
├── serializers.py       # DRF serializers (to create)
└── tests.py             # Unit tests (empty)
```

### 2.2 Planned API Structure

#### 2.2.1 REST Endpoints (Proposed)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health/` | Health check |
| `POST` | `/api/v1/decisions/` | Create decision |
| `GET` | `/api/v1/decisions/{id}/` | Get decision |
| `PUT` | `/api/v1/decisions/{id}/` | Update decision |
| `DELETE` | `/api/v1/decisions/{id}/` | Delete decision |
| `GET` | `/api/v1/decisions/` | List decisions |

#### 2.2.2 View Layer Pattern

```python
# Class-Based Views (DRF)
class DecisionViewSet(viewsets.ModelViewSet):
    queryset = Decision.objects.all()
    serializer_class = DecisionSerializer
    permission_classes = [IsAuthenticated]
```

---

## 3. Ingestion Module Architecture

### 3.1 Module Structure

```
ingestion/
├── __init__.py
├── apps.py              # AppConfig (name='ingestion')
├── models.py            # Data intake models (empty)
├── views.py             # Ingestion handlers (empty)
├── admin.py             # Admin config (empty)
├── serializers.py       # Data serializers (to create)
├── services.py          # Business logic (to create)
└── tests.py             # Tests (empty)
```

### 3.2 Ingestion Flow

```
┌─────────────┐
│   External  │
│   Data      │
│   Source    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Ingestion  │
│   Endpoint  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Validation  │
│   Layer     │
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│Transform │  │  Queue   │  │  Store   │
│          │  │  (RabbitMQ)│ │  (Postgres)│
└──────────┘  └──────────┘  └──────────┘
```

### 3.3 Planned Models

```python
class IngestionRecord(models.Model):
    """Track incoming data ingestion jobs."""
    source = CharField()
    status = CharField(choices=STATUS_CHOICES)
    payload = JSONField()
    created_at = DateTimeField(auto_now_add=True)
    processed_at = DateTimeField(null=True)
```

---

## 4. Verification Module Architecture

### 4.1 Module Structure

```
verification/
├── __init__.py
├── apps.py              # AppConfig (name='verification')
├── models.py            # Verification models (empty)
├── views.py             # Verification handlers (empty)
├── admin.py             # Admin config (empty)
├── services.py          # Verification logic (to create)
├── validators.py        # Custom validators (to create)
└── tests.py             # Tests (empty)
```

### 4.2 Verification Workflow

```
┌─────────────┐
│  Ingestion  │
│   Record    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Schema    │
│  Validation │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Business  │
│   Rules     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Result    │
│  (Pass/Fail)│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Publish   │
│   to Queue  │
└─────────────┘
```

---

## 5. Workers Module Architecture

### 5.1 Module Structure

```
workers/
├── __init__.py
├── apps.py              # AppConfig (name='workers')
├── models.py            # Job tracking models (empty)
├── views.py             # Worker management (empty)
├── admin.py             # Admin config (empty)
├── tasks.py             # Background tasks (to create)
├── consumers.py         # RabbitMQ consumers (to create)
└── tests.py             # Tests (empty)
```

### 5.2 Worker Architecture

```
┌─────────────────────────────────────────────────────┐
│                  RabbitMQ Broker                     │
│                  (decision_tasks queue)              │
└────────────────────┬────────────────────────────────┘
                     │
                     │ basic_consume
                     ▼
┌─────────────────────────────────────────────────────┐
│                  Worker Process                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  Consumer                                     │  │
│  │  - Connect to RabbitMQ                        │  │
│  │  - Acknowledge messages                       │  │
│  │  - Handle retries                             │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │                               │
│                      ▼                               │
│  ┌───────────────────────────────────────────────┐  │
│  │  Task Handler                                 │  │
│  │  - Deserialize payload                        │  │
│  │  - Execute business logic                     │  │
│  │  - Update database                            │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │                               │
│                      ▼                               │
│  ┌───────────────────────────────────────────────┐  │
│  │  Result Handler                               │  │
│  │  - Store results                              │  │
│  │  - Publish to result queue                    │  │
│  │  - Send notifications                         │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 5.3 Task Types (Planned)

| Task Type | Description | Priority |
|-----------|-------------|----------|
| `decision.process` | Execute decision logic | High |
| `data.validate` | Validate ingested data | Medium |
| `report.generate` | Generate reports | Low |
| `notification.send` | Send notifications | Medium |

---

## 6. Data Architecture

### 6.1 Database Schema (PostgreSQL)

#### 6.1.1 Connection Configuration

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "decisionvault",
        "USER": "dvuser",
        "PASSWORD": "dvpass",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

#### 6.1.2 Planned Tables

| Table | Module | Description |
|-------|--------|-------------|
| `django_*` | Django | System tables (auth, sessions, contenttypes) |
| `api_decision` | api | Decision records |
| `ingestion_record` | ingestion | Ingestion job tracking |
| `verification_result` | verification | Verification outcomes |
| `workers_job` | workers | Background job status |

### 6.2 Cache Architecture (Redis)

#### 6.2.1 Cache Configuration

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
```

#### 6.2.2 Cache Usage Patterns

| Use Case | Key Pattern | TTL |
|----------|-------------|-----|
| Session Storage | `session:<session_id>` | 2 weeks |
| Query Cache | `query:<hash>` | 5 min |
| Rate Limiting | `ratelimit:<user>:<endpoint>` | 1 min |
| Lock Management | `lock:<resource>` | 30 sec |

### 6.3 Message Queue Architecture (RabbitMQ)

#### 6.3.1 Queue Topology

```
┌──────────────────────────────────────────────────────────┐
│                    RabbitMQ Broker                        │
│                                                            │
│  ┌─────────────┐         ┌─────────────────────────┐     │
│  │  Publisher  │────────▶│  decision_tasks         │     │
│  │  (Django)   │         │  (durable, persistent)  │     │
│  └─────────────┘         └───────────┬─────────────┘     │
│                                      │                    │
│                                      │ consume            │
│                                      ▼                    │
│                              ┌───────────────┐           │
│                              │   Workers     │           │
│                              │  (Consumers)  │           │
│                              └───────────────┘           │
└──────────────────────────────────────────────────────────┘
```

#### 6.3.2 Message Properties

| Property | Value | Purpose |
|----------|-------|---------|
| `delivery_mode` | 2 | Persistent messages |
| `content_type` | application/json | JSON payload |
| `timestamp` | Unix epoch | Message creation time |
| `message_id` | UUID | Unique message identifier |

---

## 7. Integration Architecture

### 7.1 External System Interfaces

```
┌─────────────────────────────────────────────────────────┐
│                  DecisionVault Backend                   │
└────────────┬──────────────────────────────┬─────────────┘
             │                              │
             ▼                              ▼
    ┌────────────────┐            ┌────────────────┐
    │    Frontend    │            │  External APIs │
    │   (HTTP/REST)  │            │   (HTTP/HTTPS) │
    └────────────────┘            └────────────────┘
```

### 7.2 HTTP Client Configuration

```python
# httpx client for outbound requests
import httpx

async def fetch_external_data(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

---

## 8. Deployment Architecture

### 8.1 Docker Compose Topology

```yaml
version: "3.9"
services:
  redis:      → Redis 7 (Port 6379)
  rabbitmq:   → RabbitMQ 3-management (Ports 5672, 15672)
  django:     → Django app (Port 8000, 3 workers)
  postgres:   → PostgreSQL (External/Linked)
```

### 8.2 Container Specifications

#### 8.2.1 Django Service

| Property | Value |
|----------|-------|
| Base Image | `python:3.12-slim` |
| Working Dir | `/app` |
| Exposed Port | `8000` |
| Workers | 3 (Gunicorn) |
| Timeout | 120s |
| Volume | `./backend:/app` |

#### 8.2.2 Entry Point Script

```bash
#!/usr/bin/env bash
set -e

uv sync                          # Install dependencies
python manage.py migrate         # Run migrations
exec gunicorn core.wsgi:application  # Start server
```

### 8.3 Environment Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `DB_HOST` | docker-compose | Database hostname |
| `DB_NAME` | docker-compose | Database name |
| `DB_USER` | docker-compose | Database user |
| `DB_PASSWORD` | docker-compose | Database password |
| `UV_LINK_MODE` | docker-compose | UV package linking |

---

## 9. Logging Architecture

### 9.1 Logging Configuration

```python
LOGGING = {
    "version": 1,
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "level": "INFO",
        },
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "INFO",
    },
}
```

### 9.2 Log Flow

```
┌─────────────┐
│ Application │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Logger    │
└──────┬──────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│ File Handler│   │Console Handler│
│ logs/app.log│   │   stdout    │
└─────────────┘   └─────────────┘
```

---

## 10. Security Architecture

### 10.1 Security Middleware

| Middleware | Protection |
|------------|------------|
| `SecurityMiddleware` | SSL redirect, HSTS, content-type sniffing |
| `CsrfViewMiddleware` | CSRF token validation |
| `XFrameOptionsMiddleware` | Clickjacking prevention |
| `AuthenticationMiddleware` | User authentication |

### 10.2 Password Validators

| Validator | Rule |
|-----------|------|
| `UserAttributeSimilarityValidator` | No username/email in password |
| `MinimumLengthValidator` | Minimum 8 characters |
| `CommonPasswordValidator` | Not in common passwords list |
| `NumericPasswordValidator` | Not entirely numeric |

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Related**: [Architecture Lock v1.1](./ARCHITECTURE_LOCK_V1_1.md) | [L1 Overview](./ARCHITECTURE_L1_OVERVIEW.md) | [L3 Implementation](./ARCHITECTURE_L3_IMPLEMENTATION.md)
