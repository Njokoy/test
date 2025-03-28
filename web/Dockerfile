# Use Python 3.9 image
FROM python:3.9

# Create app directory
RUN mkdir /app
WORKDIR /app

# Copy application files
COPY server.py requirements.txt index.html /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 80
EXPOSE 80

# Run the application
CMD ["python", "server.py"]