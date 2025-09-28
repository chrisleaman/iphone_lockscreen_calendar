# Docker Deployment Guide

This guide explains how to run the iPhone Lockscreen Calendar Generator in a Docker container that automatically generates new lockscreen images every 30 minutes.

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository and navigate to the project directory**
   ```bash
   git clone <repository-url>
   cd iphone_lockscreen_calendar
   ```

2. **Configure your settings in `inputs/config.toml`**
   - Update AWS credentials
   - Set your calendar URLs
   - Adjust any layout or display preferences

3. **Add background images to `inputs/backgrounds/`**
   - Place your PNG background images in this directory

4. **Start the container**
   ```bash
   docker-compose up -d
   ```

5. **Monitor the logs**
   ```bash
   # View startup logs
   docker-compose logs -f

   # View generation logs
   docker exec iphone-lockscreen-calendar tail -f /var/log/lockscreen/cron.log
   ```

### Using Docker directly

1. **Build the image**
   ```bash
   docker build -t lockscreen-generator .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name iphone-lockscreen-calendar \
     --restart unless-stopped \
     -v $(pwd)/inputs/config.toml:/app/inputs/config.toml:ro \
     -v $(pwd)/inputs/backgrounds:/app/inputs/backgrounds:ro \
     -e TZ=Australia/Brisbane \
     lockscreen-generator
   ```

## How It Works

### Schedule
- The container runs `main.py` **every 30 minutes** using cron
- An initial run happens immediately when the container starts
- Logs are written to `/var/log/lockscreen/cron.log` inside the container

### Process Flow
1. **Container starts** → Initial lockscreen generation
2. **Every 30 minutes** → Cron triggers new generation
3. **For each run**:
   - Fetch today's calendar events
   - Select daily background image (deterministic by date)
   - Generate lockscreen with events overlay
   - Upload to AWS S3
   - Log results

### Generated Images
- Images are uploaded to your configured AWS S3 bucket
- Public URL: `https://{bucket-name}.s3.amazonaws.com/lockscreen.jpg`
- Each run overwrites the previous image with the latest events

## Configuration

### Environment Variables
You can override config.toml settings using environment variables:

```yaml
environment:
  - TZ=Australia/Brisbane           # Timezone for cron and events
  - PYTHONUNBUFFERED=1             # Ensure logs appear immediately
```

### Volume Mounts
- **Config**: `./inputs/config.toml:/app/inputs/config.toml:ro`
- **Backgrounds**: `./inputs/backgrounds:/app/inputs/backgrounds:ro`
- **Logs**: `lockscreen-logs:/var/log/lockscreen` (persistent volume)

## Monitoring

### View Logs
```bash
# Container startup and cron daemon logs
docker-compose logs -f lockscreen-generator

# Lockscreen generation logs (detailed)
docker exec iphone-lockscreen-calendar tail -f /var/log/lockscreen/cron.log

# View recent generations
docker exec iphone-lockscreen-calendar tail -50 /var/log/lockscreen/cron.log
```

### Health Checks
The container includes health checks that verify:
- Log file exists
- Recent generation activity (within 35 minutes)

Check health status:
```bash
docker-compose ps
# or
docker inspect iphone-lockscreen-calendar --format='{{.State.Health.Status}}'
```

### Manual Trigger
Force an immediate generation:
```bash
docker exec iphone-lockscreen-calendar /app/run_lockscreen.sh
```

## Troubleshooting

### Common Issues

1. **No images generated**
   - Check AWS credentials in config.toml
   - Verify calendar URLs are accessible
   - Check logs: `docker exec iphone-lockscreen-calendar tail -f /var/log/lockscreen/cron.log`

2. **Cron not running**
   - Verify container is running: `docker-compose ps`
   - Check cron daemon: `docker exec iphone-lockscreen-calendar ps aux | grep cron`

3. **Permission errors**
   - Ensure config and background files are readable
   - Check mounted volume permissions

4. **Timezone issues**
   - Set correct TZ environment variable
   - Verify timezone in logs matches expectations

### Debug Mode
Run container interactively for debugging:
```bash
docker run -it --rm \
  -v $(pwd)/inputs:/app/inputs:ro \
  lockscreen-generator \
  /bin/bash
```

Then manually run:
```bash
cd /app
python main.py
```

## Updating

### Update Application Code
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Update Configuration
```bash
# Edit config file
nano inputs/config.toml

# Restart container to reload config
docker-compose restart
```

### Update Background Images
```bash
# Add new images to inputs/backgrounds/
cp new-image.png inputs/backgrounds/

# No restart needed - images are read each time
```

## Production Deployment

### Resource Requirements
- **CPU**: Minimal (peaks during generation)
- **Memory**: ~200MB base + ~500MB during generation
- **Storage**: ~50MB application + logs
- **Network**: Outbound for calendar feeds and S3 upload

### Security Considerations
- Store AWS credentials securely (use Docker secrets or environment variables)
- Use read-only mounts for configuration and backgrounds
- Consider running as non-root user
- Monitor S3 bucket access and costs

### Scaling
- Single container is sufficient (generates one lockscreen per day)
- Multiple containers would generate identical images (deterministic by date)
- Consider backup strategies for generated images

## Example Production Setup

```yaml
version: '3.8'

services:
  lockscreen-generator:
    build: .
    container_name: iphone-lockscreen-calendar
    restart: unless-stopped

    volumes:
      - ./inputs/config.toml:/app/inputs/config.toml:ro
      - ./inputs/backgrounds:/app/inputs/backgrounds:ro
      - /var/log/lockscreen:/var/log/lockscreen

    environment:
      - PYTHONUNBUFFERED=1
      - TZ=Australia/Brisbane

    # Resource limits
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 200M
          cpus: '0.1'

    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
```