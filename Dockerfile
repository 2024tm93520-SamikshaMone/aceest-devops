# Using slim variant to keep image size small
# python:3.11-slim is about 150MB vs 1GB+ for the full image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first - this is a Docker best practice
# If requirements.txt hasn't changed, Docker reuses the cached layer
# and skips reinstalling packages on every build
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the project
COPY . .

# Port the Flask app runs on
EXPOSE 5000

# Start the app:
# 1. First run init_db() to create the SQLite tables if they don't exist
# 2. Then start gunicorn - production WSGI server (better than flask dev server)
# 2 worker processes is enough for a demo/assignment environment
CMD ["sh", "-c", "python -c 'from app import init_db; init_db()' && gunicorn --bind 0.0.0.0:5000 --workers 2 app:app"]
