FROM python:3.11-slim

WORKDIR /app

# Copy dependency list
COPY requirements.txt /app/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and config folder
COPY src/ /app/src/
COPY config/ /app/config/

# Expose port for FastAPI (only used by control center, ignored by others)
EXPOSE 8000

# Default command (will be overridden by docker-compose)
CMD ["python"]
