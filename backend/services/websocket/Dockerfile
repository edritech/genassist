FROM python:3.10-slim
WORKDIR /src

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install shared module dependencies first
# Note: Build context should be backend/ directory for shared module access
COPY ./shared/requirements.txt /src/shared-requirements.txt
RUN pip install --no-cache-dir -r /src/shared-requirements.txt

# Install service-specific dependencies
COPY ./services/websocket/requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

# Copy shared module
COPY ./shared /src/shared

# Copy application code
COPY ./services/websocket/app /src/app

# Copy configuration files (optional - use .dockerignore if file doesn't exist)
# Note: COPY will fail if file doesn't exist, so ensure .env.example exists or remove this line
# COPY ./services/websocket/.env.example /src/.env.example

EXPOSE 8002

CMD ["python", "-m", "app.main"]
