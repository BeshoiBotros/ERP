#!/bin/bash
# =============================================================================
# wait-for-it.sh — Generic TCP Port Waiter
# =============================================================================
# Usage: wait-for-it.sh host:port [-t timeout] [-- command args]
#
# Waits for a TCP service to become available, then optionally runs a command.
# Used in Docker Compose to enforce service startup ordering.
# =============================================================================

set -e

TIMEOUT=30
QUIET=0
HOST=""
PORT=""
CHILD=0

echoerr() {
    if [ "$QUIET" -ne 1 ]; then
        echo "$@" 1>&2
    fi
}

usage() {
    cat << USAGE >&2
Usage:
    $0 host:port [-t timeout] [-- command args]
    -q | --quiet        Do not output any status messages
    -t TIMEOUT          Timeout in seconds (default: 30)
    -- COMMAND ARGS     Execute command with args after the test finishes
USAGE
    exit 1
}

wait_for() {
    local start_ts=$(date +%s)
    while :; do
        if [ "$(command -v nc)" != "" ]; then
            nc -z "$HOST" "$PORT" > /dev/null 2>&1
        else
            (echo -n > /dev/tcp/$HOST/$PORT) > /dev/null 2>&1
        fi
        local result=$?

        if [ $result -eq 0 ]; then
            local end_ts=$(date +%s)
            echoerr "$HOST:$PORT is available after $((end_ts - start_ts)) seconds"
            break
        fi

        local now_ts=$(date +%s)
        if [ $((now_ts - start_ts)) -ge $TIMEOUT ]; then
            echoerr "Timeout after waiting ${TIMEOUT}s for $HOST:$PORT"
            exit 1
        fi

        sleep 1
    done
    return $result
}

# --- Parse Arguments ---
while [ $# -gt 0 ]; do
    case "$1" in
        *:* )
            HOST=$(echo "$1" | cut -d: -f1)
            PORT=$(echo "$1" | cut -d: -f2)
            shift 1
            ;;
        -q | --quiet)
            QUIET=1
            shift 1
            ;;
        -t)
            TIMEOUT="$2"
            if [ -z "$TIMEOUT" ]; then break; fi
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echoerr "Unknown argument: $1"
            usage
            ;;
    esac
done

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    echoerr "Error: you must provide a host:port to wait for."
    usage
fi

wait_for

# Execute remaining command
if [ $# -gt 0 ]; then
    exec "$@"
fi
