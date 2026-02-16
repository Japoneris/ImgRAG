# Multi-stage build for Image Database application
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY app/ ./app/

# Create data directory
RUN mkdir -p /app/data

# Install the package in editable mode
RUN pip install -e .

# Set Python path
ENV PYTHONPATH=/app

# Expose port for Streamlit (default)
EXPOSE 8501

# Default command runs the Streamlit app
# Can be overridden in docker-compose or docker run
CMD ["streamlit", "run", "app/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
