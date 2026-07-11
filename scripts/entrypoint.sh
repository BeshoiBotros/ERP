#!/bin/bash
# =============================================================================
# Custom Entrypoint for Odoo 17 Enterprise SaaS Container
# =============================================================================
# This script:
#   1. Waits for the database backend to be ready
#   2. Ensures filestore permissions are correct
#   3. Delegates to the official Odoo entrypoint
# =============================================================================

set -e

# --- Color Codes ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[ENTRYPOINT]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[ENTRYPOINT]${NC} $1"; }
log_error() { echo -e "${RED}[ENTRYPOINT]${NC} $1"; }

# --- Wait for Database ---
wait_for_db() {
    local host="${DB_HOST:-postgres}"
    local port="${DB_PORT:-5432}"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for database at ${host}:${port}..."

    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h "$host" -p "$port" -U "${DB_USER:-odoo}" > /dev/null 2>&1; then
            log_info "Database is ready! (attempt ${attempt}/${max_attempts})"
            return 0
        fi

        log_warn "Database not ready yet (attempt ${attempt}/${max_attempts}). Retrying in 2s..."
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "Database at ${host}:${port} did not become ready in time!"
    exit 1
}

# --- Wait for Redis ---
wait_for_redis() {
    local host="${REDIS_HOST:-redis}"
    local port="${REDIS_PORT:-6379}"
    local max_attempts=15
    local attempt=1

    log_info "Waiting for Redis at ${host}:${port}..."

    while [ $attempt -le $max_attempts ]; do
        if redis-cli -h "$host" -p "$port" ping > /dev/null 2>&1; then
            log_info "Redis is ready!"
            return 0
        fi

        # If redis-cli is not available, try nc/netcat
        if command -v nc > /dev/null 2>&1; then
            if nc -z "$host" "$port" > /dev/null 2>&1; then
                log_info "Redis port is open (redis-cli not available for PING)."
                return 0
            fi
        fi

        log_warn "Redis not ready yet (attempt ${attempt}/${max_attempts}). Retrying in 2s..."
        sleep 2
        attempt=$((attempt + 1))
    done

    log_warn "Redis did not respond — continuing without Redis session store."
    return 0
}

# --- Ensure Filestore Permissions ---
fix_permissions() {
    local data_dir="/var/lib/odoo"

    if [ -d "$data_dir" ]; then
        # Only fix if running as root (during init)
        if [ "$(id -u)" = "0" ]; then
            log_info "Fixing filestore permissions..."
            chown -R odoo:odoo "$data_dir" 2>/dev/null || true
        fi
    fi
}

# --- Main ---
main() {
    log_info "=== Odoo 17 Enterprise SaaS - Starting ==="
    log_info "Container role: ${ODOO_ROLE:-web}"

    # Wait for dependencies
    wait_for_db

    if [ "${ODOO_ROLE}" != "worker" ]; then
        wait_for_redis
    fi

    # Fix permissions
    fix_permissions

    log_info "Handing off to Odoo entrypoint..."
    log_info "============================================="

    # Delegate to the official Odoo entrypoint
    exec /entrypoint.sh "$@"
}

main "$@"
