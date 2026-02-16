# Docker Deployment

**Date:** 2026-02-16

## Overview

Added Docker support for the Image Database application with easy configuration for AI server and database file locations.

## Files Added

1. **Dockerfile**: Multi-stage Python 3.12 image with all dependencies
2. **docker-compose.yml**: Orchestration with environment variable configuration
3. **.env.docker**: Template for environment configuration
4. **.dockerignore**: Excludes unnecessary files from build
5. **README.docker.md**: Comprehensive deployment guide

## Key Features

### Environment Variables

- `EMBEDDING_API_URL`: Configure AI server endpoint
- `EMBEDDING_MODEL`: Select model (dinov2-small, dinov2-base, dinov2-large)
- `EMBEDDING_API_KEY`: Optional authentication
- `STREAMLIT_PORT`: Web interface port (default: 8501)

### Volume Mounts

- `DATA_DIR`: Database files (persistent storage)
- `IMAGES_DIR`: Source images (read-only)
- `CONFIG_DIR`: YAML configurations (read-only)

### Two Service Modes

1. **imgdb**: Web application (Streamlit) - runs by default
2. **imgdb-cli**: CLI commands - activated with `--profile cli`

## Quick Start

```bash
# Configure
cp .env.docker .env
# Edit .env with your settings

# Start web app
docker-compose up -d

# Access at http://localhost:8501
```

## CLI Usage

```bash
# Enable CLI service
docker-compose --profile cli up -d imgdb-cli

# Run commands
docker-compose exec imgdb-cli imgdb-full ingest /app/images
docker-compose exec imgdb-cli imgdb-full list
```

## Network Configuration

Supports multiple network configurations for connecting to the embedding API:
- Host network (Linux)
- Docker internal network
- host.docker.internal (Mac/Windows)

See README.docker.md for detailed configuration examples.
