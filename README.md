# Realynk

Realynk is a real-time communication backend built with Flask, PostgreSQL, SQLAlchemy, Flask-SocketIO, and Supabase Storage. It includes authentication, channels, conversations, messages, presence, reactions, read receipts, notifications, search, and secure file attachments.

## Stack and Requirements

- Python 3.11+
- Flask, Flask-CORS, Flask-SocketIO
- Flask-SQLAlchemy, SQLAlchemy, psycopg
- Flask-Migrate and Alembic
- PyJWT, Werkzeug, python-dotenv, pytest
- Supabase PostgreSQL and Supabase Storage

No SQLite, Redis, Docker, Kubernetes, external broker, S3 provider, Cloudinary, Firebase Storage, or background worker is required.

## Environment

Create `.env` from `.env.example`, set the Supabase PostgreSQL URL, and configure the private Storage bucket. Keep `.env` private; it is Git-ignored.

```text
APP_NAME=Realynk
APP_ENV=development
DEBUG=true
HOST=127.0.0.1
PORT=5000
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:PORT/DATABASE
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too
JWT_ACCESS_TOKEN_EXPIRES_MINUTES=60
CORS_ORIGINS=*
TYPING_TIMEOUT_SECONDS=5
NOTIFICATION_RETENTION_DAYS=90
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=replace-with-server-only-key
SUPABASE_STORAGE_BUCKET=realynk-attachments
MAX_ATTACHMENT_SIZE_MB=25
MAX_TOTAL_ATTACHMENT_SIZE_MB=50
MAX_ATTACHMENTS_PER_MESSAGE=10
ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS=600
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=120
RATE_LIMIT_DEFAULT_WINDOW_SECONDS=60
AUTH_RATE_LIMIT_REQUESTS=10
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
SOCKET_RATE_LIMIT_EVENTS=60
SOCKET_RATE_LIMIT_WINDOW_SECONDS=60
MAX_REQUEST_BODY_SIZE_BYTES=5242880
MAX_QUERY_PARAMS=50
MAX_HEADER_SIZE=8192
TRUST_PROXY=false
CORS_ALLOWED_ORIGINS=*
CORS_ALLOW_CREDENTIALS=false
JWT_ALGORITHM=HS256
SOCKETIO_MAX_HTTP_BUFFER_SIZE=5242880
HSTS_ENABLED=false
LOG_LEVEL=INFO
LOG_FORMAT=text
METRICS_ENABLED=true
METRICS_ENDPOINT_ENABLED=true
SLOW_REQUEST_THRESHOLD_MS=1000
DB_POOL_TIMEOUT=30
```

The Supabase service-role key is server-side only and must never be logged or returned. Use a private bucket named `realynk-attachments` or configure another bucket name.

## Installation and Startup

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

Migrations are explicit and never run during startup:

```text
flask --app main.py db upgrade
flask --app main.py db migrate -m "describe change"
```

The migration chain currently ends at `0009_security`.

For production, set `APP_ENV=production`, use a real Supabase PostgreSQL `DATABASE_URL`, provide distinct strong `SECRET_KEY` and `JWT_SECRET_KEY` values, set `DEBUG=false`, and configure explicit CORS origins. Configuration is validated before Flask is created; invalid production settings terminate startup without logging secrets or database credentials.

Both development and production use:

```text
python main.py
```

The supported deployment architecture is one application process. Presence state, metrics, and Socket.IO event coordination are process-local because no external message broker is used.

### Production checklist

- PostgreSQL configured
- Secrets configured and distinct
- `DEBUG` disabled
- CORS explicitly configured
- HTTPS deployment in place
- HSTS enabled only when HTTPS is guaranteed
- Rate limiting enabled
- Upload limits configured
- Structured logging enabled
- Health endpoints available
- Metrics endpoint protected by the deployment's access controls
- `.env` excluded from Git

## Observability and Health

Module 13 adds a lightweight observability layer without Redis, Prometheus, or external telemetry systems. The application emits structured JSON logs, attaches a request correlation ID to every response via `X-Request-ID`, exposes `/health`, `/health/live`, `/health/ready`, and `/metrics`, and keeps a small in-memory snapshot of request counts and latency.

### Logging

Logs are emitted as JSON by default and include the timestamp, log level, logger name, message, and safe observability fields such as `request_id`, `route`, `method`, `status_code`, and `duration_ms`. Secret values such as JWTs, passwords, bearer tokens, and connection strings are never logged.

### Health and readiness

`/health/live` returns a fast liveness check, while `/health/ready` validates critical dependencies such as PostgreSQL connectivity and returns HTTP 503 when the service is not ready. `/health` remains available for basic compatibility checks and includes a database connectivity result.

### In-memory metrics

The runtime metrics endpoint exposes aggregate request counts and recent latency samples in memory only. It is intended for lightweight operational visibility and is not a replacement for a centralized metrics platform.

### Socket.IO observability

Connection and disconnect events are annotated with the request correlation context where available, and socket lifecycle events continue to log safely without leaking sensitive connection metadata or tokens.

## Security Architecture

Module 12 adds a PostgreSQL-backed security layer that works without Redis or external services. The application uses centralized configuration, request correlation IDs, security headers, request sizing safeguards, and a lightweight PostgreSQL rate-limit bucket model. Security events are recorded in the database for important failures and abuse signals without storing secrets or tokens.

### Environment variables

```text
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=120
RATE_LIMIT_DEFAULT_WINDOW_SECONDS=60
AUTH_RATE_LIMIT_REQUESTS=10
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
SOCKET_RATE_LIMIT_EVENTS=60
SOCKET_RATE_LIMIT_WINDOW_SECONDS=60
MAX_REQUEST_BODY_SIZE_BYTES=5242880
MAX_QUERY_PARAMS=50
MAX_HEADER_SIZE=8192
TRUST_PROXY=false
```

### Proxy and IP handling

The application only uses forwarded IP headers when `TRUST_PROXY=true`. Otherwise, it uses the direct socket address and normalizes IPv4/IPv6 values consistently, stripping ports before rate-limit keys are generated. The system does not trust arbitrary client headers for identity or IP unless explicitly configured.

### Security headers and CORS

Every response includes `X-Request-ID`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a conservative CSP. CORS is restricted to explicit origins and required methods/headers. Credentials are not enabled in the default configuration, and wildcard origins are avoided in credentialed setups.

### Request protection

The app enforces a default request-body size cap, rejects oversized JSON bodies, caps query parameter counts, and validates malformed UUID and pagination inputs before service-layer processing. Secrets are never logged, and the centralized error handler avoids returning stack traces, SQL internals, or database connection strings.

### PostgreSQL-backed rate limiting

Rate-limit state is stored in `rate_limit_buckets` and updated with transactional bucket increments using the database as the coordination layer. Limits are enforced per scope (global, IP, user, route, socket), with stricter thresholds for authentication endpoints and higher-cost operations such as attachments and message sends. A rate-limit failure returns HTTP 429 with a standardized JSON error payload and `Retry-After`/`RateLimit-*` headers when appropriate.

### Socket.IO protection

Protected Socket.IO connections continue to use the existing JWT-based authentication flow. Event-level rate limiting applies to message, typing, presence, reaction, and connection-heavy traffic without affecting passive server events. Connection limits and authentication abuse protections are handled through the same PostgreSQL-backed infrastructure.

### Security event logging

The application records security-relevant events such as invalid requests, authentication failures, rate-limit violations, and suspicious actions in the `security_events` table. The `metadata` payload is bounded and limited to safe, explainable values; no passwords, JWTs, tokens, or secret keys are logged.

### Failure policy

For security-sensitive operations the application fails closed. Non-critical telemetry failures are isolated and never break the whole application. Database failures are returned as generic application errors rather than exposing internal details.

## API

Protected endpoints use `Authorization: Bearer <jwt>` and the shared `{ "success": true, "data": ... }` response format.

- `GET /health`
- Authentication and profiles under `/api/v1/auth` and `/api/v1/users`
- Channel and membership operations under `/api/v1/channels`
- Direct conversations under `/api/v1/conversations`
- Messages under `/api/v1/messages`
- Reactions under `/api/v1/messages/<message_id>/reactions`
- Read receipts under `/api/v1/messages/<message_id>/read`, `/reads`, and `/api/v1/messages/read`
- Presence under `/api/v1/presence`
- Notifications and preferences under `/api/v1/notifications`
- Upload attachments with `POST /api/v1/messages/<message_id>/attachments` using multipart field `file`
- Retrieve a signed attachment URL with `GET /api/v1/attachments/<attachment_id>`
- Soft-delete an attachment with `DELETE /api/v1/attachments/<attachment_id>`
- List active message attachments with `GET /api/v1/messages/<message_id>/attachments`

## Attachments

PostgreSQL stores attachment metadata only. Binary data is uploaded to private Supabase Storage. Uploads require message access, use server-generated UUID storage paths, calculate SHA-256 checksums, sanitize filenames, enforce MIME/extension allowlists, and reject executable/script files and SVG. Limits are 25 MB per file, 50 MB total per message, and 10 attachments per message. Image dimensions are optional metadata and are not trusted from clients.

Attachment access returns a short-lived signed URL valid for `ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS`. Message responses and history include active metadata but do not generate N signed URLs. Storage failures are translated into application errors, and database failure attempts storage cleanup. Cleanup of deleted objects is an explicit service operation, not a startup task.

Successful upload/delete operations emit `attachment_added` and `attachment_deleted` to the authorized `channel:<uuid>` or `conversation:<uuid>` room after database success. Module 9 search is not present in the current repository, so no separate search integration was added.

## Realtime and Security

Socket.IO authenticates connections with JWT and uses server-derived rooms: `channel:<uuid>`, `conversation:<uuid>`, and `user:<uuid>`. Existing message, reaction, read, presence, typing, and notification events remain available. Notification events and attachment events are emitted only after persistence succeeds. Presence remains process-local and does not use Redis.

## Structure

```text
realynk/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── migrations/versions/
│   ├── initial_users.py
│   ├── channels_and_memberships.py
│   ├── conversations.py
│   ├── messages.py
│   ├── last_seen.py
│   ├── reactions_reads.py
│   ├── notifications.py
│   ├── attachments.py
│   └── security.py
└── app/
    ├── models/
    │   ├── attachment.py
    │   ├── rate_limit_bucket.py
    │   └── security_event.py
    ├── middleware/security.py
    ├── security/
    │   ├── __init__.py
    │   ├── headers.py
    │   ├── rate_limiter.py
    │   ├── abuse_detector.py
    │   ├── security_events.py
    │   └── request_context.py
    ├── routes/attachments.py
    ├── services/attachment_service.py
    ├── repositories/attachment_repository.py
    ├── repositories/security_repository.py
    ├── validators/attachment_validator.py
    └── storage/supabase_storage.py
```

## License

Realynk is licensed under the Apache License 2.0. See `LICENSE` for the complete license text.
