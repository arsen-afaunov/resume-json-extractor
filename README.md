# Resume Generator

A service for generating structured resumes from a form using LLM.

## Quick Start

Make the script executable (once):

```bash
chmod +x start.sh
```

Run the project:

```bash
./start.sh
```

Services will be available at http://localhost

## Environment Variables

Create a `.env` file for configuration:

```bash
OLLAMA_MODEL=qwen2.5:3b  # LLM model
```

## How It Works

The `start.sh` script manages the startup:
1. Starts Ollama in the background
2. Downloads the model (if needed)
3. Sets file permissions to the current user
4. Starts remaining services

This separation is necessary because Docker Compose cannot execute commands after container startup or manage host file permissions.

## Stopping

Press `Ctrl+C` in the terminal with the script, or run:

```bash
docker compose down
```
