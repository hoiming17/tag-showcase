# Use a robust, flexible base image with common dependencies
FROM buildpack-deps:stable-curl

# Install a headless browser (Google Chrome) and its dependencies
USER root
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    lsb-release gnupg apt-transport-https ca-certificates && \
    wget -qO- https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Now that the repository is added, we can install the browser and other tools
RUN apt-get update -y && \
    apt-get install -y \
    google-chrome-stable \
    python3 \
    python3-pip \
    libnss3 \
    libxss1 \
    libappindicator1 \
    libindicator7 \
    fonts-liberation \
    libgbm1 \
    libgdk-pixbuf2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Add the user that our application will run as.
RUN addgroup --system app && adduser --system --group app

# Set the working directory
WORKDIR /app

# Set the Chromium path environment variable for your application
ENV CHROMIUM_EXECUTABLE_PATH="/usr/bin/google-chrome"

# Copy your application files
COPY . .

# Change ownership of the files to the app user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]