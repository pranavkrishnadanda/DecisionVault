# DecisionVault

AI-enabled platform for verifiable decision-making, agent orchestration, and auditable workflows.

## Overview

DecisionVault is a Django-based backend system designed for decision processing and workflow management. It follows a modular, service-oriented design with clear separation of concerns across multiple functional domains.

## Architecture

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
└─────────────────────────────────────────────────────────────────┘
          ▲                    ▲                    ▲
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    Frontend     │  │   PostgreSQL    │  │     Redis       │
│   (External)    │  │    Database     │  │     Cache       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Django | ≥6.0.2 |
| API | Django REST Framework | ≥3.16.1 |
| Language | Python | ≥3.12 |
| WSGI Server | Gunicorn | ≥25.1.0 |
| Database | PostgreSQL | 15+ |
| Cache | Redis | 7 |
| Message Queue | RabbitMQ | 3-management |
| Testing | pytest, pytest-django | latest |

## Project Structure

```
decisionvault/
├── backend/
│   ├── api/              # REST API endpoints
│   ├── core/             # Django configuration & settings
│   ├── ingestion/        # Data ingestion module
│   ├── verification/     # Verification workflows
│   ├── workers/          # Background job processing
│   ├── tests/            # Test suite (49+ tests)
│   ├── docs/             # Architecture documentation
│   ├── manage.py         # Django management script
│   ├── pyproject.toml    # Python dependencies
│   └── pytest.ini        # Pytest configuration
├── frontend/             # Next.js frontend (TBD)
└── docker-compose.yml    # Local development stack
```

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- uv (Python package manager)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/21bq1a4232/DecisionVault.git
   cd decisionvault
   ```

2. **Start infrastructure (PostgreSQL, Redis, RabbitMQ)**
   ```bash
   docker-compose up -d redis rabbitmq
   ```

3. **Set up Python environment**
   ```bash
   cd backend
   uv sync
   source .venv/bin/activate
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

7. **Verify health endpoint**
   ```bash
   curl http://localhost:8000/api/health/
   # Expected: {"status": "ok", "version": "0.1.0"}
   ```

### Docker Development

```bash
docker-compose up -d
docker-compose exec django python manage.py migrate
```

Access the API at `http://localhost:8000`.

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Test Coverage

| Category | Tests | Description |
|----------|-------|-------------|
| Module Registration | 7 | Verifies app registration in INSTALLED_APPS |
| URL Routing | 9 | Tests endpoint availability and namespaces |
| Settings | 15 | Environment variable configuration |
| Redis Integration | 10 | Cache connectivity and operations |
| RabbitMQ Integration | 8 | Message queue connectivity |
| **Total** | **49** | All passing |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/` | GET | Health check for load balancers |
| `/api/ingestion/` | GET | Ingestion module base |
| `/api/verification/` | GET | Verification module base |
| `/api/workers/` | GET | Workers module base |
| `/admin/` | GET | Django admin interface |

## Environment Variables

Create a `.env` file in `backend/` based on `.env.example`:

```bash
# Django Settings
DEBUG=False
SECRET_KEY=your-super-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# PostgreSQL Database
DB_NAME=decisionvault
DB_USER=dvuser
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# RabbitMQ Message Broker
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
```

## Development Workflow

This project follows **Test-Driven Development (TDD)**:

1. Write failing tests first
2. Implement minimal working code
3. Refactor safely
4. Add integration tests

No feature is accepted without tests.

## Architecture Documents

- [L1 Architecture Overview](backend/docs/ARCHITECTURE_L1_OVERVIEW.md) - High-level system context
- [L2 Architecture Detailed](backend/docs/ARCHITECTURE_L2_DETAILED.md) - Component design
- [L3 Implementation](backend/docs/ARCHITECTURE_L3_IMPLEMENTATION.md) - Implementation specs

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest tests/ -v`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Contact

Repository: https://github.com/21bq1a4232/DecisionVault

---

**Version**: 0.1.0  
**Last Updated**: 2026-02-18
