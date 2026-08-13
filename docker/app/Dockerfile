# Stage 1: Build Node assets
FROM node:22-alpine AS build-node

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY ui/ ./ui/
RUN npm run tailwind-build

# Stage 2: Build Python dependencies
FROM python:3.14-slim AS build-python

WORKDIR /app

# Install UV
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies with UV
ENV UV_NO_DEV=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ARG UV_EXTRAS=""
RUN uv sync --no-dev --locked --no-install-project $(for extra in $UV_EXTRAS; do printf ' --extra %s' "$extra"; done)

# Stage 3: Runtime
FROM python:3.14-slim AS runtime

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy Python environment from build stage
COPY --from=build-python /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy built assets from node stage
COPY --from=build-node /app/dist/bundles /app/dist/bundles

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY docker/app/start-prod.sh ./start-prod.sh

# Collect static files
RUN cd backend && python manage.py collectstatic --noinput

# Change ownership to non-root user
RUN chmod +x /app/start-prod.sh && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://localhost:8000/dashboard/login/').close()" || exit 1

# Default command
CMD ["/app/start-prod.sh"]
