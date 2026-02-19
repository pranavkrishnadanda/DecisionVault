# DecisionVault Slack Integration

Production-grade Slack OAuth + channel discovery + message history + test delivery for a multi-tenant SaaS app.

## Stack
- Backend: Django + httpx + cryptography (Fernet)
- Frontend: Next.js + React Query
- Storage: PostgreSQL
- Cache: Redis

## End-to-End Flow
1. User clicks `Add Slack` on `/integrations/slack`.
2. Frontend requests install URL via `GET /api/v1/integrations/{integration_id}/slack/install-url/`.
3. Slack OAuth consent screen opens.
4. Slack redirects to `/oauth/slack/callback` (frontend route).
5. Frontend completes OAuth by calling `POST /api/v1/integrations/{integration_id}/slack/oauth-callback/`.
6. Server exchanges code for token server-side, encrypts token at rest, stores integration.
7. Frontend returns to `/integrations/slack?status=success`, loads channels/messages, and can send test message.

No end user ever sees client secret or bot token.

## Slack App Setup (One-Time)
1. Go to https://api.slack.com/apps and create an app (From Scratch).
2. Choose a dev workspace.
3. OAuth & Permissions:
   - Redirect URL (dev): `https://<your-ngrok>/oauth/slack/callback`
   - Redirect URL (prod): `https://yourdomain.com/oauth/slack/callback`
4. Add bot scopes:
   - `channels:read`
   - `channels:history`
   - `groups:read`
   - `groups:history`
   - `chat:write`
   - `users:read`
5. Copy values from Basic Information:
   - Client ID
   - Client Secret
   - Signing Secret
6. Configure environment variables in `backend/.env`.

## Environment Variables
Copy `backend/.env.example` to `backend/.env`.

Required:
```bash
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_SIGNING_SECRET=
SLACK_REDIRECT_BASE_URL=https://xxxx.ngrok-free.app
TOKEN_ENCRYPTION_KEY=
```

Generate encryption key:
```bash
./scripts/generate-encryption-key.sh
```

## HTTPS Options

### Option 1 (Default Dev): ngrok
Slack OAuth redirect URIs and Events API require HTTPS.

Run:
```bash
./scripts/setup-tunnel.sh 3000
```

This script:
- installs ngrok if missing (via Homebrew)
- starts tunnel to localhost
- prints HTTPS URL
- writes `NEXT_PUBLIC_SLACK_REDIRECT_URI` into `frontend/.env.local`
- writes `SLACK_REDIRECT_BASE_URL` and updates `ALLOWED_HOSTS` in `backend/.env`

Important: free ngrok URLs rotate on restart.

### Option 2: Cloudflare Tunnel
Run:
```bash
./scripts/setup-cloudflare-tunnel.sh 3000
```

This is often more stable for longer-running demo/dev sessions.

### Option 3 (Recommended Production): Managed Deploy (Railway)
Included:
- `Dockerfile` (multi-stage build)
- `railway.toml`

Deploy on Railway and set env vars in Railway dashboard. TLS/HTTPS is automatic.

### Option 4: Self-host with Nginx + Let's Encrypt
Included:
- `deploy/nginx/decisionvault.conf`
- `scripts/setup-letsencrypt-nginx.sh`

Run on VPS:
```bash
./scripts/setup-letsencrypt-nginx.sh yourdomain.com admin@yourdomain.com
```

## Local Development (Redis/RabbitMQ Local, Not Docker)
1. Start Redis locally:
```bash
redis-server
```
2. Start RabbitMQ locally:
```bash
rabbitmq-server
```
3. Start PostgreSQL locally (your own installation/service), then backend:
```bash
cd backend
uv sync
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```
4. Start frontend:
```bash
cd frontend
npm ci
npm run dev
```
5. Start HTTPS tunnel for frontend callback:
```bash
cd ..
./scripts/setup-tunnel.sh 3000
```

## API Surface
- `GET /api/v1/integrations/{integration_id}/slack/install-url/`
- `POST /api/v1/integrations/{integration_id}/slack/oauth-callback/`
- `GET /api/v1/integrations/{integration_id}/slack/channels/`
- `POST /api/v1/integrations/{integration_id}/slack/test/`
- `GET /api/v1/integrations/{integration_id}/deliveries/`
- `GET /api/slack/integrations`
- `GET /api/slack/channels?integration_id=...`
- `GET /api/slack/messages?integration_id=...&channel_id=...&oldest=...&limit=100`
- `POST /api/slack/test`
- `POST /api/slack/events`

## Security Controls
- OAuth `state` with TTL (CSRF defense)
- `client_secret` used only server-to-server in `oauth.v2.access`
- Tokens encrypted at rest via Fernet (`TOKEN_ENCRYPTION_KEY`)
- Slack API calls server-side only
- Slack request signature verification for events endpoint
- Per-org integration access isolation
- Audit logging on install/channel/messages/test/events actions

## Tests (TDD)
Backend Slack tests:
```bash
backend/.venv/bin/pytest backend/tests/slack -q
```

Frontend Slack page tests:
```bash
cd frontend
npm test -- src/ui/features/slack/slack-integration-page-client.test.tsx
```
