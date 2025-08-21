# Use a pre-built Selenium image that includes Chrome and ChromeDriver
FROM selenium/standalone-chrome

# Switch to the root user to perform system updates and package installations
USER root

# Install Python and pip
# The base image comes with Python, but we need pip to install our requirements.
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Switch back to the default non-root user for security
USER seluser

# Set the working directory
WORKDIR /app

# Copy your application files
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]