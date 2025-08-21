# Use the Google Cloud SDK image as a base, as it includes all necessary dependencies
FROM google/cloud-sdk

# Set the working directory
WORKDIR /app

# The base image already has a working version of wget, gnupg, and Chrome.
# We just need to install Python and pip.
RUN apt-get update -y && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set the environment variable for Selenium
ENV CHROMIUM_EXECUTABLE_PATH="/usr/bin/google-chrome"

# Copy your application files
COPY . .

# Install Python dependencies using the flag to override the "externally managed environment" error
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]