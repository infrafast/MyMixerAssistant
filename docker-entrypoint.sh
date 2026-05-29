#!/bin/sh
set -eu

env_file="${ASSISTANT_ENV_FILE:-/config/.env.infrafast}"

if [ ! -f "$env_file" ]; then
    detected_env_file="$(find /config -maxdepth 1 -type f -name '.env*' ! -name '*.example' 2>/dev/null | sort | head -n 1 || true)"
    if [ -n "$detected_env_file" ]; then
        env_file="$detected_env_file"
    fi
fi

exec python voice_assistant/agent.py --env-file "$env_file" "$@"
