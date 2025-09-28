# Use Python 3.13 slim image as base
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cron \
    curl \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-latex-extra \
    dvipng \
    cm-super \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy Python configuration files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY main.py ./
COPY inputs/ ./inputs/

# Create log directory
RUN mkdir -p /var/log/lockscreen

# Create cron job script
RUN echo '#!/bin/bash\n\
cd /app\n\
echo "$(date): Starting lockscreen generation" >> /var/log/lockscreen/cron.log 2>&1\n\
uv run python main.py >> /var/log/lockscreen/cron.log 2>&1\n\
echo "$(date): Lockscreen generation completed" >> /var/log/lockscreen/cron.log 2>&1\n\
echo "----------------------------------------" >> /var/log/lockscreen/cron.log 2>&1' > /app/run_lockscreen.sh

# Make script executable
RUN chmod +x /app/run_lockscreen.sh

# Create crontab entry (every 30 minutes)
RUN echo "*/30 * * * * /app/run_lockscreen.sh" > /etc/cron.d/lockscreen-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/lockscreen-cron

# Apply cron job
RUN crontab /etc/cron.d/lockscreen-cron

# Create startup script that starts cron and keeps container running
RUN echo '#!/bin/bash\n\
echo "Starting iPhone Lockscreen Calendar Generator"\n\
echo "Cron job will run every 30 minutes"\n\
echo "Logs available at /var/log/lockscreen/cron.log"\n\
echo ""\n\
# Run once immediately on startup\n\
echo "Running initial lockscreen generation..."\n\
/app/run_lockscreen.sh\n\
echo ""\n\
# Start cron daemon\n\
echo "Starting cron daemon..."\n\
cron\n\
echo "Cron daemon started. Container will now run continuously."\n\
echo "Use: docker logs <container-id> to see this output"\n\
echo "Use: docker exec <container-id> tail -f /var/log/lockscreen/cron.log to see generation logs"\n\
echo ""\n\
# Keep container running by tailing the log file\n\
tail -f /var/log/lockscreen/cron.log' > /app/start.sh

RUN chmod +x /app/start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/tmp/uv-cache

# Expose port (not needed for this app, but good practice)
EXPOSE 8080

# Health check to ensure the application is working
HEALTHCHECK --interval=60m --timeout=30s --start-period=5m --retries=3 \
    CMD test -f /var/log/lockscreen/cron.log && \
        test $(find /var/log/lockscreen/cron.log -mmin -35 | wc -l) -gt 0 || exit 1

# Run the startup script
CMD ["/app/start.sh"]