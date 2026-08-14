# =============================================================================
# MULTI-STAGE DOCKERFILE — Odoo 17 Enterprise SaaS Platform
# =============================================================================
# Stage 1 (builder):  Fetches all open-source modules with retry logic
# Stage 2 (runtime):  Clean, minimal production image
#
# Modules Included:
#   - Odoo-Mates: Full Accounting Kit (om_account_accountant + dependencies)
#   - OCA: MIS Builder (financial reports), report_xlsx, web_responsive
#   - OCA: session_redis (Redis session store)
#
# Security: Final image runs as non-root 'odoo' user
# =============================================================================


# ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# STAGE 1: Builder — Fetch & Prepare Modules
# ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
FROM odoo:17.0 AS builder

USER root

# Install git and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Retry helper function
# Usage: git_clone_retry <url> <branch> <dest> [attempts]
# Retries git clone with exponential backoff to handle network timeouts
# ---------------------------------------------------------------------------
SHELL ["/bin/bash", "-c"]

# --- Odoo-Mates: Full Accounting Kit ---
# Branch MUST match base image version (17.0)
RUN attempts=0; max=3; delay=5; \
    until git clone --depth 1 -b 17.0 \
        https://github.com/odoomates/odooapps.git /tmp/odoomates; do \
        attempts=$((attempts + 1)); \
        if [ $attempts -ge $max ]; then \
            echo "ERROR: Failed to clone odoomates after ${max} attempts"; \
            exit 1; \
        fi; \
        echo "Retry ${attempts}/${max} — waiting ${delay}s..."; \
        sleep $delay; \
        delay=$((delay * 2)); \
    done

# --- OCA: MIS Builder (Financial Reporting Engine) ---
RUN attempts=0; max=3; delay=5; \
    until git clone --depth 1 -b 17.0 \
        https://github.com/OCA/mis-builder.git /tmp/oca-mis-builder; do \
        attempts=$((attempts + 1)); \
        if [ $attempts -ge $max ]; then \
            echo "ERROR: Failed to clone OCA/mis-builder after ${max} attempts"; \
            exit 1; \
        fi; \
        echo "Retry ${attempts}/${max} — waiting ${delay}s..."; \
        sleep $delay; \
        delay=$((delay * 2)); \
    done

# --- OCA: Report Engine (XLSX report generation) ---
RUN attempts=0; max=3; delay=5; \
    until git clone --depth 1 -b 17.0 \
        https://github.com/OCA/reporting-engine.git /tmp/oca-reporting-engine; do \
        attempts=$((attempts + 1)); \
        if [ $attempts -ge $max ]; then \
            echo "ERROR: Failed to clone OCA/reporting-engine after ${max} attempts"; \
            exit 1; \
        fi; \
        echo "Retry ${attempts}/${max} — waiting ${delay}s..."; \
        sleep $delay; \
        delay=$((delay * 2)); \
    done

# --- OCA: Web Enhancements (Responsive UI) ---
RUN attempts=0; max=3; delay=5; \
    until git clone --depth 1 -b 17.0 \
        https://github.com/OCA/web.git /tmp/oca-web; do \
        attempts=$((attempts + 1)); \
        if [ $attempts -ge $max ]; then \
            echo "ERROR: Failed to clone OCA/web after ${max} attempts"; \
            exit 1; \
        fi; \
        echo "Retry ${attempts}/${max} — waiting ${delay}s..."; \
        sleep $delay; \
        delay=$((delay * 2)); \
    done

# --- OCA: Server Tools (session_redis, etc.) ---
RUN attempts=0; max=3; delay=5; \
    until git clone --depth 1 -b 17.0 \
        https://github.com/OCA/server-tools.git /tmp/oca-server-tools; do \
        attempts=$((attempts + 1)); \
        if [ $attempts -ge $max ]; then \
            echo "ERROR: Failed to clone OCA/server-tools after ${max} attempts"; \
            exit 1; \
        fi; \
        echo "Retry ${attempts}/${max} — waiting ${delay}s..."; \
        sleep $delay; \
        delay=$((delay * 2)); \
    done

# --- OCA: Server UX (base_technical_features) ---
RUN attempts=0; max=3; delay=5; \
    until git clone --depth 1 -b 17.0 \
        https://github.com/OCA/server-ux.git /tmp/oca-server-ux; do \
        attempts=$((attempts + 1)); \
        if [ $attempts -ge $max ]; then \
            echo "ERROR: Failed to clone OCA/server-ux after ${max} attempts"; \
            exit 1; \
        fi; \
        echo "Retry ${attempts}/${max} — waiting ${delay}s..."; \
        sleep $delay; \
        delay=$((delay * 2)); \
    done

# ---------------------------------------------------------------------------
# Organize modules into clean directories
# ---------------------------------------------------------------------------
RUN mkdir -p /tmp/addons/extra-addons /tmp/addons/oca-addons && \
    # ── Odoo-Mates: ALL modules from 17.0 branch ──
    cp -r /tmp/odoomates/accounting_pdf_reports             /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_account_accountant              /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_account_asset                   /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_account_bank_statement_import   /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_account_budget                  /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_account_daily_reports            /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_account_followup                /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_data_remove                     /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_fiscal_year                     /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_hr_payroll                      /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_hr_payroll_account              /tmp/addons/extra-addons/ && \
    cp -r /tmp/odoomates/om_recurring_payments              /tmp/addons/extra-addons/ && \
    # ── OCA: MIS Builder ──
    cp -r /tmp/oca-mis-builder/mis_builder         /tmp/addons/oca-addons/ && \
    cp -r /tmp/oca-mis-builder/mis_builder_budget  /tmp/addons/oca-addons/ 2>/dev/null || true && \
    # ── OCA: Report Engine ──
    cp -r /tmp/oca-reporting-engine/report_xlsx    /tmp/addons/oca-addons/ 2>/dev/null || true && \
    # ── OCA: Web ──
    cp -r /tmp/oca-web/web_responsive              /tmp/addons/oca-addons/ 2>/dev/null || true && \
    # ── OCA: Server Tools ──
    cp -r /tmp/oca-server-tools/session_redis      /tmp/addons/oca-addons/ 2>/dev/null || true && \
    cp -r /tmp/oca-server-tools/base_sparse_field  /tmp/addons/oca-addons/ 2>/dev/null || true && \
    # ── OCA: Server UX ──
    cp -r /tmp/oca-server-ux/base_technical_features /tmp/addons/oca-addons/ 2>/dev/null || true && \
    # ── Cleanup ──
    rm -rf /tmp/odoomates /tmp/oca-*


# ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# STAGE 2: Runtime — Clean Production Image
# ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
FROM odoo:17.0

USER root

# Install runtime dependencies only (no git, no build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-client \
        netcat-openbsd \
        redis-tools \
        curl && \
    # Install Python packages needed by OCA modules
    pip3 install --no-cache-dir \
        redis \
        xlsxwriter \
        num2words \
        python-stdnum && \
        openpyxl \
    # Cleanup
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# --- Copy Modules from Builder Stage ---
# NOTE: We use /opt/odoo/ instead of /mnt/extra-addons/ because the official
# Odoo image declares /mnt/extra-addons as a VOLUME, which causes Docker to
# create anonymous volumes that override our image content on container restart.
COPY --from=builder /tmp/addons/extra-addons/ /opt/odoo/extra-addons/
COPY --from=builder /tmp/addons/oca-addons/   /opt/odoo/oca-addons/

# --- Copy Custom Scripts ---
COPY scripts/entrypoint.sh /custom-entrypoint.sh
COPY scripts/wait-for-it.sh /usr/local/bin/wait-for-it

# --- Fix Permissions ---
RUN chown -R odoo:odoo /opt/odoo/extra-addons /opt/odoo/oca-addons /var/lib/odoo && \
    chmod +x /custom-entrypoint.sh /usr/local/bin/wait-for-it && \
    # Create directory for Odoo sessions
    mkdir -p /var/lib/odoo/sessions && \
    chown -R odoo:odoo /var/lib/odoo/sessions

# --- Switch to Non-Root User ---
USER odoo

# --- Health Check ---
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1

# --- Ports ---
# 8069: HTTP (web interface + JSON-RPC)
# 8072: Longpolling / WebSocket (Discuss, live notifications)
EXPOSE 8069 8072

# --- Entrypoint ---
ENTRYPOINT ["/custom-entrypoint.sh"]
CMD ["odoo"]
