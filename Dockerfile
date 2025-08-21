# Use a pre-configured image that contains a headless browser
FROM zenika/alpine-chrome:latest

# Set the working directory for your application
WORKDIR /app

# Switch to the root user to install packages
USER root

# Install Python and pip
RUN apk update && apk add --no-cache python3 py3-pip

# Switch back to the default user for security
USER chrome

# Copy your application files
COPY . .

# Install Python dependencies (as the non-root user)
RUN pip3 install --no-cache-dir -r requirements.txt

# Set the environment variable for Selenium
ENV CHROMIUM_EXECUTABLE_PATH="/usr/bin/chromium"

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]