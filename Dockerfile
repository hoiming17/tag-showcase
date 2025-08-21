# Use a pre-built Selenium image that includes Chrome and ChromeDriver
FROM selenium/standalone-chrome

# Set the working directory
WORKDIR /app

# The Selenium image comes with Python, so we just need to install pip.
# The executable path for Chrome is already correctly set within the image's environment.
RUN apt-get update -y && \
    apt-get install -y python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Copy your application files
COPY . .

# Install Python dependencies
# We still need the "--break-system-packages" flag to install packages on this Debian-based image.
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]