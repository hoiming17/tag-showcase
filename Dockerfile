# Use a slim Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install a more minimal and correct set of dependencies for Chromium
RUN apt-get update && apt-get install -y \
    chromium \
    libnss3 \
    libgbm1 \
    libasound2 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . /app/

# Expose the port the Flask app runs on
EXPOSE 8000

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "app:app"]