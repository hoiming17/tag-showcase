# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies for Chromium, including core libraries
RUN apt-get update && apt-get install -y \
    chromium \
    libglib2.0-0 \
    libnss3 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file and install the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Tell Selenium where the Chromium executable is
ENV CHROMIUM_EXECUTABLE_PATH="/usr/bin/chromium"

# Expose the port the app runs on
EXPOSE 5000

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]