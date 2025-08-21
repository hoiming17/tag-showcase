# Use an official Python runtime as a parent image
FROM python:3.9-slim-bullseye

# Install core dependencies for a headless environment
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libglib2.0-0 \
    libnss3 \
    libxkbcommon-x11-0 \
    libxtst6 \
    libxrender1 \
    libfontconfig1 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium separately
RUN apt-get update && apt-get install -y chromium --no-install-recommends

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