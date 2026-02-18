# =====================
# DecisionVault Makefile
# =====================

PYTHON=.venv/bin/python


# ---------------------
# Django
# ---------------------

run:
	$(PYTHON) manage.py runserver

migrate:
	$(PYTHON) manage.py migrate

migrations:
	$(PYTHON) manage.py makemigrations

shell:
	$(PYTHON) manage.py shell

superuser:
	$(PYTHON) manage.py createsuperuser


# ---------------------
# Environment
# ---------------------

venv:
	uv sync


# ---------------------
# Redis
# ---------------------

redis:
	redis-server

redis-cli:
	redis-cli


# ---------------------
# RabbitMQ
# ---------------------

rabbitmq:
	rabbitmq-server

rabbitmq-status:
	rabbitmqctl status


# ---------------------
# Postgres
# ---------------------

postgres:
	psql decisionvault


# ---------------------
# All-in-one Dev
# ---------------------

dev:
	make venv
	make migrate
	make run


# ---------------------
# Clean
# ---------------------

clean:
	rm -rf .venv
	find . -name "__pycache__" -delete
