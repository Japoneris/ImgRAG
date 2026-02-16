# Docker Setup for Image Database

This document explains how to run the Image Database application using Docker.

## Quick Start

1. **Configure environment variables:**
   ```bash
   cp .env.docker .env
   # Edit .env to set your configuration
   ```

2. **Build and start the web application:**
   ```bash
   docker-compose up -d
   ```

3. **Access the web interface:**
   Open your browser to http://localhost:8501

## Configuration

### Environment Variables

Edit the `.env` file to configure:

- **AI Server:**
  - `EMBEDDING_API_URL`: URL of your embedding API server
  - `EMBEDDING_MODEL`: Model to use (dinov2-small, dinov2-base, dinov2-large)
  - `EMBEDDING_API_KEY`: Optional API key

- **Application:**
  - `STREAMLIT_PORT`: Port for web interface (default: 8501)

- **Data Directories:**
  - `DATA_DIR`: Directory for database files (default: ./data)
  - `IMAGES_DIR`: Directory with images to process (default: ./test_images)
  - `CONFIG_DIR`: Directory with YAML configs (default: ./configs)

### Docker Network

If your embedding API server runs in Docker, use one of these options:

**Option 1: Host network (Linux only)**
```yaml
# In docker-compose.yml, add to imgdb service:
network_mode: "host"
```
Then set `EMBEDDING_API_URL=http://localhost:8000`

**Option 2: Docker internal network**
```yaml
# In docker-compose.yml, add both services to same network:
services:
  embedding-api:
    # your embedding server config
    networks:
      - imgdb-network

  imgdb:
    # existing config
    networks:
      - imgdb-network

networks:
  imgdb-network:
```
Then set `EMBEDDING_API_URL=http://embedding-api:8000`

**Option 3: Host.docker.internal (Mac/Windows)**
Set `EMBEDDING_API_URL=http://host.docker.internal:8000`

## Usage

### Running the Web Application

Start the Streamlit web interface:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f imgdb
```

Stop the application:
```bash
docker-compose down
```

### Running CLI Commands

The CLI service is disabled by default. To use it:

1. **Start the CLI container:**
   ```bash
   docker-compose --profile cli up -d imgdb-cli
   ```

2. **Run commands:**
   ```bash
   # Ingest images
   docker-compose exec imgdb-cli imgdb-full ingest /app/images

   # Search for an image
   docker-compose exec imgdb-cli imgdb-full search <hash>

   # Find similar images
   docker-compose exec imgdb-cli imgdb-full similar <hash>

   # List all images
   docker-compose exec imgdb-cli imgdb-full list

   # Check API health
   docker-compose exec imgdb-cli imgdb-full health

   # Analyze embeddings
   docker-compose exec imgdb-cli imgdb-full analyze

   # Visualize analysis
   docker-compose exec imgdb-cli imgdb-full visualize /app/data/analysis.json
   ```

3. **Interactive shell:**
   ```bash
   docker-compose exec imgdb-cli bash
   ```

### One-off CLI Commands

Run a single command without keeping the CLI container running:

```bash
# Using the main imgdb service
docker-compose run --rm imgdb imgdb-full --help

# Ingest images
docker-compose run --rm imgdb imgdb-full ingest /app/images

# List images
docker-compose run --rm imgdb imgdb-full list
```

## Volume Mounts

The following directories are mounted as volumes:

- `./data` → `/app/data` (read-write): Database files
- `./test_images` → `/app/images` (read-only): Source images
- `./configs` → `/app/configs` (read-only): Configuration files

## Database Persistence

All database files are stored in the `./data` directory on your host machine:
- `images.db`: SQLite database with image metadata
- `embeddings/`: ChromaDB vector database
- `index.json`: File path index

These files persist even when containers are removed.

## Troubleshooting

### Cannot connect to embedding API

1. Check the API is running:
   ```bash
   curl $EMBEDDING_API_URL/health
   ```

2. Verify the URL in `.env` is correct for your Docker setup

3. Check container logs:
   ```bash
   docker-compose logs imgdb
   ```

### Database permissions

If you get permission errors, ensure the `./data` directory has correct permissions:
```bash
chmod -R 755 ./data
```

### Port already in use

If port 8501 is already in use, change `STREAMLIT_PORT` in `.env`:
```
STREAMLIT_PORT=8502
```

Then restart:
```bash
docker-compose down && docker-compose up -d
```

## Building from Scratch

To rebuild the Docker image after code changes:
```bash
docker-compose build
docker-compose up -d
```

## Production Considerations

For production deployment:

1. **Set resource limits** in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

2. **Use secrets** for sensitive data instead of environment variables

3. **Enable HTTPS** using a reverse proxy (nginx, traefik, caddy)

4. **Set up backups** for the `./data` directory

5. **Monitor health** using the built-in healthcheck
