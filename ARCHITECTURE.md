# Enterprise Odoo 17 SaaS Platform — Architecture Guide

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Why These Components?](#why-these-components)
- [Service Breakdown](#service-breakdown)
- [Network Isolation](#network-isolation)
- [Quick Start](#quick-start)
- [Tenant Provisioning](#tenant-provisioning)
- [Scaling Strategy](#scaling-strategy)
- [Backup & Recovery](#backup--recovery)
- [Monitoring](#monitoring)
- [Security Hardening](#security-hardening)

---

## Architecture Overview

```
                    ┌──────────────────────────────────────────────────┐
                    │                   INTERNET                       │
                    │     tenant1.domain.com  tenant2.domain.com       │
                    └─────────────────────┬────────────────────────────┘
                                          │ HTTPS :443
                    ┌─────────────────────▼────────────────────────────┐
                    │              TRAEFIK v3.1                         │
                    │   ┌─────────────────────────────────────────┐    │
                    │   │  • Wildcard SSL (*.domain.com)          │    │
                    │   │  • Dynamic subdomain routing            │    │
                    │   │  • Rate limiting & security headers     │    │
                    │   │  • WebSocket proxy (/websocket → 8072)  │    │
                    │   │  • Gzip compression                     │    │
                    │   └─────────────────────────────────────────┘    │
                    └────────┬──────────────────────┬──────────────────┘
                             │ :8069               │ :8072
    ┌────────────────────────▼──────────────────────▼──────────────────┐
    │                    FRONTEND NETWORK                               │
    │  ┌──────────────────────────────────────────────────────────┐    │
    │  │                   ODOO-WEB                                │    │
    │  │   • 4 HTTP workers (multiprocessing)                     │    │
    │  │   • Cron DISABLED (max_cron_threads=0)                   │    │
    │  │   • Serves UI, API, longpolling                          │    │
    │  │   • dbfilter=^%d$ (tenant isolation via subdomain)       │    │
    │  └──────────────────┬───────────────────────────────────────┘    │
    └─────────────────────┼────────────────────────────────────────────┘
                          │
    ┌─────────────────────▼────────────────────────────────────────────┐
    │                    BACKEND NETWORK (internal)                     │
    │                                                                   │
    │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
    │  │   PGBOUNCER   │  │    REDIS 7    │  │    ODOO-WORKER      │    │
    │  │   :6432       │  │    :6379      │  │                     │    │
    │  │   Transaction │  │   Sessions    │  │  • Cron jobs (×2)   │    │
    │  │   mode pool   │  │   ORM Cache   │  │  • Heavy reports    │    │
    │  └──────┬───────┘  └──────────────┘  │  • 1.5GB RAM limit  │    │
    │         │                             │  • 10min timeout     │    │
    │         │                             └────────┬────────────┘    │
    │  ┌──────▼────────────────────────────────────────▼──────────┐    │
    │  │                   POSTGRESQL 15                           │    │
    │  │   • Optimized for Odoo (shared_buffers, WAL, etc.)      │    │
    │  │   • One database per tenant                              │    │
    │  │   • MD5 auth (PgBouncer compatible)                      │    │
    │  └──────────────────────────────────────────────────────────┘    │
    └──────────────────────────────────────────────────────────────────┘
```

---

## Why These Components?

### Why PgBouncer?
Odoo opens a new PostgreSQL connection for every HTTP request. With 4 workers and 50 concurrent tenants, that's **200+ connections** competing for PostgreSQL's default 100-connection limit. PgBouncer in **transaction mode** pools these connections, allowing 200 client connections to share just 25 actual database connections. This prevents `FATAL: too many connections` errors that kill multi-tenant deployments.

### Why Redis?
PostgreSQL is designed for durable, transactional data — not ephemeral session tokens. By offloading sessions and ORM cache to Redis (an in-memory store), you:
- Reduce PostgreSQL load by ~30%
- Get sub-millisecond session lookups (vs. 5-10ms from PostgreSQL)
- Enable horizontal scaling (shared session store across multiple Odoo containers)

### Why Separate Web & Worker Containers?
A single Odoo instance running both web requests AND cron jobs creates resource contention. A heavy PDF report generation (cron) can consume 1GB+ RAM and block web workers for 5+ minutes. By splitting into:
- **odoo-web**: Only serves UI (fast, responsive)
- **odoo-worker**: Only runs cron/reports (high memory, long timeouts)

Users never experience "the page froze because someone ran a report."

### Why Traefik?
Unlike Nginx, Traefik natively integrates with Docker — it auto-discovers services via container labels. When you add a new tenant, Traefik automatically routes their subdomain without reloading config files. This is essential for a SaaS platform where tenants are provisioned dynamically.

### Why Multi-Stage Dockerfile?
The builder stage installs git and clones repositories (~500MB of .git data). The runtime stage copies only the needed module directories (~50MB). This results in a **70% smaller** production image, faster deployments, and a smaller attack surface.

---

## Service Breakdown

| Service | Image | CPU | Memory | Purpose |
|---------|-------|-----|--------|---------|
| `traefik` | `traefik:v3.1` | 0.5 | 256MB | SSL, routing, load balancing |
| `odoo-web` | Custom | 2.0 | 4GB | Web UI, API, longpolling |
| `odoo-worker` | Custom | 2.0 | 4GB | Cron jobs, report generation |
| `postgres` | `postgres:15-alpine` | 2.0 | 4GB | Primary database |
| `pgbouncer` | `edoburu/pgbouncer` | 0.5 | 128MB | Connection pooling |
| `redis` | `redis:7-alpine` | 0.5 | 512MB | Sessions, caching |

**Total minimum resources: 7.5 CPU cores, ~13GB RAM**

---

## Network Isolation

```
┌────────────────────────┐     ┌────────────────────────────────┐
│    frontend network     │     │       backend network           │
│   (internet-facing)     │     │      (internal only)            │
│                         │     │                                 │
│   • traefik       ◄────┼─────┼──► traefik (bridge)             │
│   • odoo-web      ◄────┼─────┼──► odoo-web                     │
│                         │     │   • odoo-worker                 │
│   ✗ postgres            │     │   • postgres                    │
│   ✗ pgbouncer           │     │   • pgbouncer                   │
│   ✗ redis               │     │   • redis                       │
└────────────────────────┘     └────────────────────────────────┘
```

The `backend` network is configured as `internal: true`, meaning Docker will not create any host-accessible ports. Database, cache, and pooler are **physically unreachable** from the internet.

---

## Quick Start

### Prerequisites
- Docker Engine 24+ with Docker Compose v2
- A domain name with DNS pointed to your server
- Cloudflare account (for DNS-01 wildcard SSL)

### 1. Configure Environment
```bash
cd /home/beshoy/Desktop/ERP

# Edit the .env file with your production values
nano .env
```

**Minimum required changes in `.env`:**
- `POSTGRES_PASSWORD` — strong database password
- `ODOO_ADMIN_PASSWORD` — Odoo master admin password
- `DOMAIN` — your production domain (e.g., `myerp.com`)
- `ACME_EMAIL` — email for Let's Encrypt notifications
- `CF_DNS_API_TOKEN` — Cloudflare API token

### 2. Update Traefik Domain
```bash
# Replace placeholder domain in Traefik config
sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' config/traefik/traefik.yml
sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' config/traefik/dynamic.yml
```

### 3. Build & Deploy
```bash
# Build the Odoo image (fetches all modules)
docker compose build --no-cache

# Start all services
docker compose up -d

# Watch logs
docker compose logs -f
```

### 4. Verify
```bash
# Check all services are running
docker compose ps

# Test Odoo is responding
curl -I https://yourdomain.com/web/login

# Check PgBouncer pools
docker compose exec pgbouncer psql -p 6432 -U odoo pgbouncer -c "SHOW POOLS;"

# Check Redis
docker compose exec redis redis-cli ping
```

---

## Tenant Provisioning

### Creating a New Tenant

1. **Create DNS record**: Add a CNAME/A record for `newtenant.yourdomain.com` → your server IP
2. **Create database**: Access `https://yourdomain.com/web/database/create` (if enabled) or:
   ```bash
   docker compose exec odoo-web odoo --db_host=pgbouncer --db_port=6432 \
       -d newtenant --init=base --stop-after-init --without-demo=all
   ```
3. **Traefik auto-routes**: No config change needed — Traefik's wildcard rule catches `newtenant.yourdomain.com` automatically
4. **SSL auto-provisions**: The wildcard certificate covers all subdomains

---

## Scaling Strategy

### Horizontal Scaling (Odoo-Web)
```yaml
# docker-compose.override.yml
services:
  odoo-web:
    deploy:
      replicas: 3
```
Traefik automatically load-balances across all replicas with sticky sessions.

### Vertical Scaling (Workers)
Increase worker count in `config/odoo-web.conf`:
```ini
workers = 8  # Formula: (CPU cores × 2) + 1
```

### Database Scaling
For 100+ tenants, consider:
- PostgreSQL read replicas for reporting
- Separate PostgreSQL instances per tenant group
- Migrate to Kubernetes with StatefulSets

---

## Backup & Recovery

### Automated Database Backup
```bash
#!/bin/bash
# backup.sh — Run daily via cron
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"

# List all tenant databases
DATABASES=$(docker compose exec -T postgres psql -U odoo -t -c \
    "SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';")

for DB in $DATABASES; do
    DB=$(echo $DB | tr -d ' ')
    docker compose exec -T postgres pg_dump -U odoo -Fc "$DB" > \
        "${BACKUP_DIR}/${DB}_${TIMESTAMP}.dump"
done

# Cleanup backups older than 30 days
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete
```

### Filestore Backup
```bash
# Backup Odoo filestore volume
docker run --rm -v erp_odoo_filestore:/data -v /backups:/backup \
    alpine tar czf /backup/filestore_$(date +%Y%m%d).tar.gz -C /data .
```

### Recovery
```bash
# Restore a specific tenant database
docker compose exec -T postgres pg_restore -U odoo -d tenant_name \
    /backups/postgres/tenant_name_20260524.dump
```

---

## Monitoring

### Recommended Stack
- **Prometheus + Grafana**: System metrics (CPU, RAM, disk)
- **Loki**: Centralized log aggregation from all containers
- **Uptime Kuma**: Health endpoint monitoring

### Key Metrics to Watch
| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| PgBouncer `cl_waiting` | > 10 | Increase `default_pool_size` |
| Odoo worker memory | > `limit_memory_soft` | Check for memory leaks |
| PostgreSQL connections | > 150 | Scale PgBouncer or optimize queries |
| Redis memory usage | > 200MB | Check for session leaks |
| Traefik request latency | > 2s P95 | Add more Odoo-web replicas |

---

## Security Hardening

### Implemented
- ✅ Non-root Odoo container (`USER odoo`)
- ✅ Network isolation (backend internal, no exposed ports)
- ✅ Database manager disabled (`list_db = False`)
- ✅ HSTS, XSS protection, clickjacking prevention headers
- ✅ Rate limiting (100 req/s average, 200 burst)
- ✅ Docker socket read-only mount

### Recommended Additions
- 🔒 Set up fail2ban on the host for SSH protection
- 🔒 Enable PostgreSQL SSL (`sslmode=require`)
- 🔒 Rotate `POSTGRES_PASSWORD` and `ODOO_ADMIN_PASSWORD` regularly
- 🔒 Use Docker secrets instead of environment variables in production
- 🔒 Enable Odoo's 2FA for admin users
- 🔒 Set up WAF rules in Cloudflare

---

## File Reference

```
ERP/
├── Dockerfile                          # Multi-stage build for Odoo 17
├── docker-compose.yml                  # 6-service production stack
├── .env                                # Environment variables (SECRETS)
├── config/
│   ├── odoo-web.conf                   # UI worker configuration
│   ├── odoo-worker.conf                # Background worker configuration
│   ├── pgbouncer/
│   │   ├── pgbouncer.ini               # Connection pooler settings
│   │   └── userlist.txt                # PgBouncer auth credentials
│   └── traefik/
│       ├── traefik.yml                 # Static: entrypoints, ACME, providers
│       └── dynamic.yml                 # Dynamic: middlewares, security headers
├── scripts/
│   ├── entrypoint.sh                   # Custom entrypoint with health waits
│   └── wait-for-it.sh                  # TCP port wait utility
└── ARCHITECTURE.md                     # This file
```
