# Use official Python base image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better for Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining project files
COPY . .

# Expose port (Render will override with $PORT)
EXPOSE 10000

# Start the server using gunicorn + Flask app
CMD exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 main:app
