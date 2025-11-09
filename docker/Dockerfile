# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Installer uv
RUN pip install --no-cache-dir uv

# Copier les fichiers de dépendances
COPY pyproject.toml ./

# Créer un venv et installer les dépendances
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache -e .

# Stage 2: Runtime
FROM python:3.11-slim

# Créer un utilisateur non-root
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Copier le venv depuis le builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copier le code source
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser .env.example ./.env

# Créer les répertoires de données
RUN mkdir -p data/raw data/interim data/processed models && \
    chown -R appuser:appuser data/ models/

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Passer à l'utilisateur non-root
USER appuser

# Exposer le port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

# Commande de démarrage
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
