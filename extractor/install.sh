#!/bin/bash
set -e

if [ -f "/.dockerenv" ]; then
    IN_CONTAINER=true
else
    IN_CONTAINER=false
fi

if [ "$IN_CONTAINER" = false ]; then
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    PIP=".venv/bin/pip"
    PIP_COMPILE=".venv/bin/pip-compile"
    PIP_SYNC=".venv/bin/pip-sync"
else
    PIP="pip"
    PIP_COMPILE="pip-compile"
    PIP_SYNC="pip-sync"
fi

if ! $PIP show pip-tools > /dev/null 2>&1; then
    $PIP install pip-tools
fi

$PIP_COMPILE requirements.txt -o requirements.lock --no-header --quiet
$PIP_SYNC requirements.lock --quiet

echo "✅ Dependencies installed and synced!"
