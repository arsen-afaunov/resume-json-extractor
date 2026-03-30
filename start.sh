#!/bin/bash
set -e  # Exit on error

# Cleanup on exit (Ctrl+C or error)
trap 'docker compose down' EXIT

# Subshell for ollama initialization (with UID/GID hack)
(
  LOCAL_UID=$(id -u)
  export LOCAL_UID
  
  LOCAL_GID=$(id -g)
  export LOCAL_GID
  
  # Create .ollama directory if it doesn't exist
  if [ ! -d .ollama ]; then
    mkdir .ollama
    echo "Created .ollama directory"
  fi
  
  # Start ollama service
  echo "Starting Ollama..."
  docker compose up -d ollama
  
  # Wait for ollama readiness (from inside container)
  echo "Waiting for Ollama to be ready..."
  docker compose exec ollama bash -c '
    for i in $(seq 1 60); do
      if cat < /dev/null > /dev/tcp/localhost/11434 2>/dev/null; then
        exit 0
      fi
      sleep 1
    done
    echo "Timeout: Ollama failed to start" >&2
    exit 1
  '
  echo "Ollama is ready!"
  
  # Download model
  echo "Downloading model..."
  docker compose exec ollama sh -c 'ollama pull "$OLLAMA_MODEL"'
  
  # Fix permissions for .ollama directory
  echo "Fixing permissions..."
  docker compose exec ollama sh -c "chown -R $LOCAL_UID:$LOCAL_GID /root/.ollama"
)

# Start all remaining services (docker manages the rest)
echo "Starting all services..."
docker compose up
