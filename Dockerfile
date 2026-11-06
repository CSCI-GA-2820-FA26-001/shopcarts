##################################################
# Shopcarts service image
##################################################
FROM python:3.12-slim

# Install the runtime dependencies only (no dev packages)
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN python -m pip install --no-cache-dir --upgrade pip pipenv && \
    pipenv install --system --deploy && \
    python -m pip uninstall -y pipenv

# Copy the application code
COPY wsgi.py .
COPY service/ ./service/

# Run as a non-root user
RUN useradd --uid 1001 --no-create-home --shell /usr/sbin/nologin flask && \
    chown -R flask /app
USER flask

# Run the service with gunicorn on $PORT, like the Procfile
ENV PORT=8080
EXPOSE $PORT
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:$PORT --log-level=info wsgi:app"]
