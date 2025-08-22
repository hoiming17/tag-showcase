# Use a slim Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install necessary system dependencies for Chromium
# The 'slim' image doesn't have these by default
RUN apt-get update && apt-get install -y \
    chromium \
    # The following are required dependencies for running Chromium headless
    libnss3 \
    libgconf-2-4 \
    libasound2 \
    libatk1.0-0 \
    libgtk-3-0 \
    libcups2 \
    libfontconfig1 \
    libexpat1 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libxss1 \
    libxcomposite1 \
    libxext6 \
    libxfixes3 \
    libxtst6 \
    fonts-liberation \
    lsb-release \
    xdg-utils \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libdrm2 \
    libflac8 \
    libogg0 \
    libopus0 \
    libpulse0 \
    libsndfile1 \
    libvorbis0a \
    libvpx6 \
    libwebpdemux2 \
    libwebp7 \
    libwoff1 \
    libharfbuzz0b \
    libharfbuzz-icu7 \
    libicu-le-t67 \
    libjpeg-turbo8 \
    libpng16-16 \
    libwebp6 \
    libwebp-dev \
    libfreetype6 \
    libpng-dev \
    libjpeg-dev \
    libavahi-client3 \
    libavahi-common3 \
    libxtst-dev \
    libxdamage-dev \
    libxrandr-dev \
    libxrender-dev \
    libxi-dev \
    libxext-dev \
    libxfixes-dev \
    libxcomposite-dev \
    libxcursor-dev \
    libxinerama-dev \
    libxkbcommon-dev \
    libxkbcommon-x11-0 \
    libxcb1 \
    libxcb-dri3-0 \
    libxcb-shm0 \
    libxcb-render0 \
    libxcb-xfixes0 \
    libxcb-composite0 \
    libxcb-sync1 \
    libxcb-util1 \
    libxcb-keysyms1 \
    libxcb-image0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbfile1 \
    libgdk-pixbuf-2.0-0 \
    libgio-2.0-0 \
    libpangocairo-1.0-0 \
    libpangoxft-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libfontconfig1 \
    libpixman-1-0 \
    libxcb-shm0 \
    libxcb-render-util0 \
    libxcb-render0 \
    libxau6 \
    libxdmcp6 \
    libx11-6 \
    libx11-dev \
    libxi6 \
    libxrender1 \
    libxext6 \
    libxfixes3 \
    libxcomposite1 \
    libxcursor1 \
    libxinerama1 \
    libxkbcommon0 \
    libharfbuzz0b \
    libgdk-pixbuf2.0-dev \
    libgdk-pixbuf2.0-common \
    libglib2.0-0 \
    libglib2.0-dev \
    libglib2.0-data \
    libgtk-3-0 \
    libgtk-3-dev \
    libgtk-3-common \
    libatk-bridge2.0-0 \
    libatk-bridge2.0-dev \
    libatk1.0-0 \
    libatk1.0-dev \
    libatk-bridge2.0-dev \
    libatk-bridge2.0-0 \
    libxkbfile1 \
    libxkbcommon-x11-0 \
    libxkbcommon-dev \
    libxkbcommon0 \
    libxkbfile1 \
    libxkbcommon-x11-0 \
    libxkbcommon-dev \
    libxkbcommon0 \
    libxkbfile1 \
    libxkbcommon-x11-0 \
    libxkbcommon-dev \
    libxkbcommon0 \
    libgconf-2-4 \
    --no-install-recommends

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . /app/

# Expose the port the Flask app runs on
EXPOSE 8000

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app:app"]