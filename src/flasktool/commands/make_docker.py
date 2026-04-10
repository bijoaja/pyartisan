import click
import os


@click.command()
def make_docker():
    """Generate Production & Development Dockerfile + docker-compose.yml"""

    build_path = "Docker"
    os.makedirs(build_path, exist_ok=True)

    # ============================================================
    # PRODUCTION DOCKERFILE
    # ============================================================
    dockerfile_prod = """# Multi-stage build for production
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender-dev \\
    libgomp1 \\
    libgl1-mesa-glx \\
    ffmpeg \\
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p app/static/uploads exports

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')"

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "--worker-class", "gevent", "run:app"]
"""

    # ============================================================
    # DEVELOPMENT DOCKERFILE
    # ============================================================
    dockerfile_dev = """# Development Dockerfile with hot reload
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    FLASK_ENV=development \\
    FLASK_DEBUG=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender-dev \\
    libgomp1 \\
    libgl1 \\
    ffmpeg \\
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p app/static/uploads exports

# Expose port
EXPOSE 8080

# Run Flask development server with auto-reload
CMD ["flask", "run"]
"""

    # ============================================================
    # DOCKER COMPOSE
    # ============================================================
    compose = """services:
  flaskiq_web:
    build: .
    container_name: flaskiq_web
    image: bijoaja/flaskiq:latest
    ports:
      - "${FLASK_RUN_PORT:-8080}:8080"
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - flaskiq_db
      - flaskiq_ai
    networks:
      - app-network

  flaskiq_db:
    image: mysql:8.4
    container_name: flaskiq_db
    environment:
      MYSQL_DATABASE: template_db
      MYSQL_ROOT_PASSWORD: root123
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - app-network

  flaskiq_ai:
    image: ollama/ollama:latest
    container_name: flaskiq_ai
    ports:  
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    tty: true
    stdin_open: true
    networks:
      - app-network
    entrypoint: ["/bin/bash", "-c"]
    command: >
      "ollama serve & sleep 5 && ollama pull mistral && wait"

volumes:
  mysql_data: {}
  ollama_models: {}

networks:
  app-network:
    driver: bridge
"""

    # ============================================================
    # WRITE FILES
    # ============================================================
    with open(f"{build_path}/Dockerfile", "w") as f:
        f.write(dockerfile_prod)

    with open(f"{build_path}/Dockerfile.dev", "w") as f:
        f.write(dockerfile_dev)

    with open(f"docker-compose.yml", "w") as f:
        f.write(compose)

    click.echo("✔ Dockerfile (prod), Dockerfile.dev, and docker-compose.yml created in Docker/")