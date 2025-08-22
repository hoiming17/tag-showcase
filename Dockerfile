# Use a simple, official Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy application files and requirements
COPY . .

# Install your Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 5000

# Run your application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]