# DecisionVault Slack Integration

Production-grade Slack OAuth + channel discovery + message history + test delivery for a multi-tenant SaaS app.

## Stack
- Backend: Django + httpx + cryptography (Fernet)
- Frontend: Next.js + React Query
- Storage: PostgreSQL
- Cache: Redis

## End-to-End Flow
1. User clicks `Add Slack` on `/integrations/slack`.
2. Browser is redirected to `GET /api/slack/install`.
3. Slack OAuth consent screen opens.
4. Slack redirects to `GET /api/slack/callback`.
5. Server exchanges code for token server-side, encrypts token at rest, stores integration.
6. Frontend returns to `/integrations/slack?status=success`, loads channels/messages, and can send test message.

No end user ever sees client secret or bot token.

## Slack App Setup (One-Time)
1. Go to https://api.slack.com/apps and create an app (From Scratch).
2. Choose a dev workspace.
3. OAuth & Permissions:
   - Redirect URL (dev): `https://<your-ngrok>/api/slack/callback`
   - Redirect URL (prod): `https://yourdomain.com/api/slack/callback`
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
./scripts/setup-tunnel.sh 8000
```

This script:
- installs ngrok if missing (via Homebrew)
- starts tunnel to localhost
- prints HTTPS URL
- reminds you to update Slack redirect URI

Important: free ngrok URLs rotate on restart.

### Option 2: Cloudflare Tunnel
Run:
```bash
./scripts/setup-cloudflare-tunnel.sh 8000
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

## Local Development
1. Start infra:
```bash
docker-compose up -d postgres redis
```
2. Backend:
```bash
cd backend
uv sync
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```
3. Frontend:
```bash
cd frontend
npm ci
npm run dev
```

## API Surface
- `GET /api/slack/install`
- `GET /api/slack/callback`
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
