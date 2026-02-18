# DecisionVault Backend - L1 Architecture Overview

## Executive Summary

**DecisionVault** is a Django-based backend system designed for decision processing and workflow management. The architecture follows a modular, service-oriented design pattern with clear separation of concerns across multiple functional domains.

---

## 1. System Context Diagram (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────────┐
│                     DecisionVault System                         │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   API       │  │   Core      │  │  Ingestion  │              │
│  │   Module    │  │   Module    │  │   Module    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │Verification │  │   Workers   │  │  Messaging  │              │
│  │   Module    │  │   Module    │  │   (RabbitMQ)│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
          ▲                    ▲                    ▲
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Frontend     │  │   PostgreSQL    │  │     Redis       │
│   (External)    │  │    Database     │  │     Cache       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 2. High-Level Components

### 2.1 Core Module (`core/`)
**Responsibility**: Central configuration and application bootstrap

| Sub-component | Purpose |
|--------------|---------|
| `settings.py` | Django configuration (DB, cache, middleware, logging) |
| `urls.py` | Root URL routing |
| `wsgi.py` | WSGI application entry point |
| `asgi.py` | ASGI application entry point |
| `rabbitmq.py` | RabbitMQ client wrapper for message publishing |
| `cache_test.py` | Redis cache testing utility |
| `test_rabbitmq.py` | RabbitMQ integration test |

### 2.2 API Module (`api/`)
**Responsibility**: RESTful API endpoints and data exposure

| Sub-component | Purpose |
|--------------|---------|
| `views.py` | HTTP request handlers (placeholder) |
| `models.py` | Database models (placeholder) |
| `admin.py` | Django admin configuration |
| `urls.py` | API-specific URL patterns |

### 2.3 Ingestion Module (`ingestion/`)
**Responsibility**: Data ingestion and intake processing

| Sub-component | Purpose |
|--------------|---------|
| `views.py` | Ingestion endpoints (placeholder) |
| `models.py` | Ingestion data models (placeholder) |
| `admin.py` | Admin interface for ingestion data |

### 2.4 Verification Module (`verification/`)
**Responsibility**: Data validation and verification workflows

| Sub-component | Purpose |
|--------------|---------|
| `views.py` | Verification logic handlers |
| `models.py` | Verification record models |
| `admin.py` | Admin management interface |

### 2.5 Workers Module (`workers/`)
**Responsibility**: Background job processing and async tasks

| Sub-component | Purpose |
|--------------|---------|
| `views.py` | Worker management endpoints |
| `models.py` | Worker job models |
| `admin.py` | Worker administration |

---

## 3. External Dependencies

### 3.1 Database Layer
- **PostgreSQL** - Primary relational database
  - Host: `localhost` (dev) / `postgres` (docker)
  - Database: `decisionvault`
  - User: `dvuser`
  - Port: `5432`

### 3.2 Caching Layer
- **Redis** - Distributed cache and session store
  - Host: `localhost`
  - Port: `6379`
  - Backend: `django_redis.cache.RedisCache`

### 3.3 Message Broker
- **RabbitMQ** - Async task queue and messaging
  - Host: `localhost`
  - Port: `5672` (AMQP) / `15672` (Management UI)
  - Queue: `decision_tasks` (durable)

---

## 4. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Django | ≥6.0.2 |
| API | Django REST Framework | ≥3.16.1 |
| Language | Python | ≥3.12 |
| WSGI Server | Gunicorn | ≥25.1.0 |
| ASGI Server | Uvicorn | ≥0.41.0 |
| Database Driver | psycopg | ≥3.3.2 |
| HTTP Client | httpx | ≥0.28.1 |
| Message Queue | pika | ≥1.3.2 |
| Cache Client | redis | ≥7.2.0 |
| Configuration | python-dotenv | ≥1.2.1 |
| Cache Integration | django-redis | ≥5.4 |

---

## 5. Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Docker Environment                       │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   Django Service                       │  │
│  │  - 3 Gunicorn Workers                                  │  │
│  │  - Port: 8000                                          │  │
│  │  - Timeout: 120s                                       │  │
│  └────────────────────────────────────────────────────────┘  │
│                       │         │                             │
│                       ▼         ▼                             │
│  ┌──────────────────────┐   ┌──────────────────────┐         │
│  │     Redis:7          │   │  RabbitMQ:3-mgmt     │         │
│  │     Port: 6379       │   │  Port: 5672/15672    │         │
│  └──────────────────────┘   └──────────────────────┘         │
│                                                               │
│  ┌──────────────────────┐                                     │
│  │    PostgreSQL        │  (External/Linked)                  │
│  └──────────────────────┘                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Request Flow (High-Level)

```
Client Request
      │
      ▼
┌─────────────┐
│  Gunicorn   │  (WSGI Server - 3 workers)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Django    │  (core.wsgi.application)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Middleware │  (Security, Session, CSRF, Auth, Messages)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Views    │  (api/ingestion/verification/workers)
└──────┬──────┘
       │
       ├─────────────┬─────────────┬──────────────┐
       ▼             ▼             ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│PostgreSQL│  │  Redis   │  │ RabbitMQ │  │  Logs    │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

---

## 7. Module Registration Status

| Module | Registered in `INSTALLED_APPS` | Status |
|--------|-------------------------------|--------|
| `api` | ❌ Not registered | Skeleton only |
| `ingestion` | ❌ Not registered | Skeleton only |
| `verification` | ❌ Not registered | Skeleton only |
| `workers` | ❌ Not registered | Skeleton only |
| `core` | ✅ Implicit (settings module) | Active |

**Note**: Modules exist as Django apps but are not yet registered in `settings.py`. Registration required for full functionality.

---

## 8. Key Configuration Points

### 8.1 Security Settings
- `DEBUG = True` (Development mode)
- `SECRET_KEY`: Django insecure key (requires production update)
- `ALLOWED_HOSTS`: Empty (requires configuration)

### 8.2 Logging Configuration
- **File Handler**: `logs/app.log` (INFO level)
- **Console Handler**: stdout (INFO level)
- **Root Logger**: INFO level with dual handlers

### 8.3 Cache Configuration
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

---

## 9. Entry Points

| Entry Point | File | Purpose |
|------------|------|---------|
| Development Server | `manage.py runserver` | Django dev server |
| Production Server | `gunicorn core.wsgi:application` | WSGI production server |
| Docker Entry | `entrypoint.sh` | Container bootstrap |
| Main Function | `main.py` | Package entry (placeholder) |

---

## 10. Related Documents

- **[L2 Architecture](./ARCHITECTURE_L2_DETAILED.md)** - Detailed component design
- **[L3 Architecture](./ARCHITECTURE_L3_IMPLEMENTATION.md)** - Implementation specifications
- **[Deployment Guide](../README.md)** - Setup and deployment instructions

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Author**: Architecture Documentation Generator
