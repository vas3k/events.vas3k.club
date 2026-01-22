FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    cron \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Configure Poetry: Don't create virtual environment, don't ask questions
RUN poetry config virtualenvs.create false \
    && poetry config cache-dir /tmp/poetry-cache

# Copy dependency files first for better layer caching
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN poetry install --no-interaction --no-ansi --no-root \
    && rm -rf /tmp/poetry-cache

# Copy project files
COPY . .

# Install the project itself
RUN poetry install --no-interaction --no-ansi

# Expose ports (8000 for dev, 8815 for production)
EXPOSE 8000 8815

# Default command (can be overridden in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
