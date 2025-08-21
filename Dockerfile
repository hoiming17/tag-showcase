# Use a pre-built Selenium image that includes Chrome and ChromeDriver
FROM selenium/standalone-chrome

# Switch to the root user to perform system updates and package installations
USER root

# Install Python and pip
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set the correct executable path for your application
# The path to the Chrome binary in this image is /usr/bin/google-chrome
ENV CHROMIUM_EXECUTABLE_PATH="/usr/bin/google-chrome"

# Set the working directory
WORKDIR /app

# Copy your application files
COPY . .

# Change ownership of the application directory to the non-root user
# This is crucial for the "Permission denied" error
RUN chown -R seluser:seluser /app

# Switch back to the default non-root user for security
USER seluser

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]