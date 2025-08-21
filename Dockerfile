# Use a standard, clean Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install all necessary system dependencies for a headless browser, including gnupg
RUN apt-get update -y && \
    apt-get install -y \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcurl4 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    libxss1 \
    lsb-release \
    wget \
    xdg-utils \
    gnupg && \
    rm -rf /var/lib/apt/lists/*

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