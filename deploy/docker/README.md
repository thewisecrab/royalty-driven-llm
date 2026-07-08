# Docker Deployment

Build and run the RDLLM service locally:

```bash
cp .env.example .env
# Set RDLLM_SERVICE_TOKEN_SHA256 to a SHA-256 hash of your bearer token.
docker compose up --build
```

The container exposes `8765`, runs as a non-root user, drops Linux
capabilities, uses a read-only filesystem, stores audit logs in the
`rdllm_audit` volume, and reports readiness through `/readyz`.

The raw bearer token must never be written to `.env`, the image, or the service
config. Store only the SHA-256 hash in `RDLLM_SERVICE_TOKEN_SHA256`.
