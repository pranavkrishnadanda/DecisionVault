# Slack Integration Operations Guide

## Current Architecture
- Frontend route: `/integrations/slack`
- Frontend callback route: `/oauth/slack/callback`
- Backend install URL API: `/api/v1/integrations/{integration_id}/slack/install-url/`
- Backend OAuth callback exchange API: `/api/v1/integrations/{integration_id}/slack/oauth-callback/`
- Backend channel listing API: `/api/v1/integrations/{integration_id}/slack/channels/`
- Backend test message API: `/api/v1/integrations/{integration_id}/slack/test/`

## Environment Split
- Frontend env file: `frontend/.env.local`
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_SLACK_REDIRECT_URI`
- Backend env file: `backend/.env`
  - Django/DB/Redis/RabbitMQ settings
  - Slack credentials and secrets
  - `SLACK_REDIRECT_BASE_URL`
  - `TOKEN_ENCRYPTION_KEY`

No shared keys should be duplicated between these files.

## Local Runtime (No Docker for Redis/RabbitMQ)
1. Redis:
```bash
redis-server
```
2. RabbitMQ:
```bash
rabbitmq-server
```
3. Backend:
```bash
cd backend
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```
4. Frontend:
```bash
cd frontend
npm run dev
```

## Tunnel and Callback Setup
Run:
```bash
./scripts/setup-tunnel.sh 3000
```
This script now:
- stops stale ngrok process
- starts tunnel to frontend port `3000`
- updates `frontend/.env.local` with `NEXT_PUBLIC_SLACK_REDIRECT_URI=https://<ngrok>/oauth/slack/callback`
- updates `backend/.env` with `SLACK_REDIRECT_BASE_URL=https://<ngrok>`
- appends ngrok host to `ALLOWED_HOSTS` in `backend/.env`

In Slack app settings, set Redirect URL exactly to:
```text
https://<ngrok-domain>/oauth/slack/callback
```

## Encryption Key Rotation
Generate and auto-write key:
```bash
./scripts/generate-encryption-key.sh
```
This updates `backend/.env` key `TOKEN_ENCRYPTION_KEY`.

## Known Failure Modes
- `redirect_uri did not match any configured URIs`
  - callback URL in Slack app does not exactly match `NEXT_PUBLIC_SLACK_REDIRECT_URI`
- `DisallowedHost`
  - ngrok host missing from `ALLOWED_HOSTS`
- `/oauth/slack/callback` 404 on Django
  - ngrok tunnel points to `8000` instead of `3000`

## Verification Checklist
- `curl http://127.0.0.1:4040/api/tunnels` shows `addr: http://localhost:3000`
- `frontend/.env.local` has `NEXT_PUBLIC_SLACK_REDIRECT_URI=https://<ngrok>/oauth/slack/callback`
- `backend/.env` has `SLACK_REDIRECT_BASE_URL=https://<ngrok>`
- `backend/.env` `ALLOWED_HOSTS` includes `<ngrok-domain>`
