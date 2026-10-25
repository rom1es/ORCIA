#!/usr/bin/env bash
# ==============================================================================
# ORCIA — Script d'administration unifié (./manage.sh)
# Usage:
#   ./manage.sh status [all|infra|postgres|redis|minio|api|worker|web]
#   ./manage.sh start  [all|infra|postgres|redis|minio|api|worker|web]
#   ./manage.sh stop   [all|infra|postgres|redis|minio|api|worker|web]
#   ./manage.sh restart [all|infra|postgres|redis|minio|api|worker|web]
#   ./manage.sh logs   [all|infra|postgres|redis|minio|api|worker|web] [-n 50]
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/scripts/manage.py" "$@"
