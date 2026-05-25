#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${1:-local}"

load_env_file() {
  local service_dir="$1"
  local env_file="$ROOT_DIR/$service_dir/.env"
  local example_file="$ROOT_DIR/$service_dir/.env.example"

  set -a
  if [[ -f "$env_file" ]]; then
    # shellcheck disable=SC1090
    source "$env_file"
  else
    # shellcheck disable=SC1090
    source "$example_file"
  fi
  set +a
}

retry_until_ok() {
  local description="$1"
  local command="$2"
  local attempts="${3:-30}"
  local sleep_seconds="${4:-2}"

  for ((i = 1; i <= attempts; i += 1)); do
    if eval "$command" >/dev/null 2>&1; then
      printf 'PASS %s\n' "$description"
      return 0
    fi
    sleep "$sleep_seconds"
  done

  printf 'FAIL %s\n' "$description" >&2
  eval "$command"
  return 1
}

load_env_file "app"
APP_URL="${NEXT_PUBLIC_APP_URL:-http://localhost:3021}"
APP_PRODUCT_NAME="${NEXT_PUBLIC_PRODUCT_NAME:-Project X}"
API_URL="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8020/api/v1}"

load_env_file "site"
SITE_URL="${NEXT_PUBLIC_SITE_URL:-http://localhost:3020}"
SITE_PRODUCT_NAME="${NEXT_PUBLIC_PRODUCT_NAME:-Project X}"

load_env_file "backend"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-continuum}"
BACKEND_SERVICE_NAME="${CONTINUUM_PROJECT_NAME:-Project X API}"

cd "$ROOT_DIR"

printf 'Running smoke test for compose profile: %s\n' "$PROFILE"

retry_until_ok "database connectivity" \
  "docker compose --profile '$PROFILE' exec -T db pg_isready -U '$POSTGRES_USER' -d '$POSTGRES_DB'"

retry_until_ok "backend health endpoint" \
  "curl --fail --silent --show-error '$API_URL/system/health' | python3 -c \"import json, sys; payload=json.load(sys.stdin); assert payload['status'] == 'ok'; assert payload['service'] == '$BACKEND_SERVICE_NAME'\""

retry_until_ok "backend readiness endpoint" \
  "curl --fail --silent --show-error '$API_URL/system/readiness' | python3 -c \"import json, sys; payload=json.load(sys.stdin); assert 'PRIMARY' in payload['profile_types']; assert payload['modules']\""

retry_until_ok "site homepage" \
  "curl --fail --silent --show-error '$SITE_URL' | grep -F '$SITE_PRODUCT_NAME'"

retry_until_ok "app login page" \
  "curl --fail --silent --show-error '$APP_URL/login' | grep -F 'Welcome back to $APP_PRODUCT_NAME'"

printf 'Smoke test passed for profile: %s\n' "$PROFILE"
