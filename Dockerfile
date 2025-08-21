# Use a standard, clean Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies for a headless browser
RUN apt-get update && apt-get install -y \
    gnupg \
    wget \
    libnss3 \
    libxss1 \
    libasound2 \
    libappindicator3-1 \
    libsecret-1-0 \
    libu2f-udev \
    libvulkan1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    -qq

# Install Chromium (the browser executable)
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable --no-install-recommends

# Set the environment variable for Selenium
ENV CHROMIUM_EXECUTABLE_PATH="/usr/bin/google-chrome"

# Copy your application files
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]