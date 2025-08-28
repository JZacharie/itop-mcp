# Multi-stage build pour un container sécurisé
FROM  python:3.11-slim AS builder
# Métadonnées
LABEL maintainer="itop-mcp"
LABEL architecture="amd64"
LABEL platform="linux/amd64"
LABEL aws.fargate.compatible="true"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
# Créer un utilisateur non-root pour la construction
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Installer les dépendances de build
RUN apt-get update && apt-get install -y --no-install-recommends \
curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Créer le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances et README (requis par pyproject.toml)
COPY pyproject.toml ./
COPY README.md ./
COPY main.py ./

# Installer les dépendances Python (installation normale, pas éditable)
#RUN pip install --no-cache-dir --user .
RUN pip install fastmcp

# Stage final - image de production minimale
#FROM --platform=linux/amd64 python:3.11-slim

RUN pip install fastmcp

# Métadonnées de sécurité
LABEL maintainer="security@company.com" \
      version="1.2.0" \
      description="iTop MCP Server - Secure Container" \
      security.scan="enabled"

# Créer un utilisateur non-root
#RUN groupadd -r -g 1001 appgroup && \
#    useradd -r -u 1001 -g appgroup -d /app -s /sbin/nologin appuser

# Installer uniquement les packages système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer les répertoires nécessaires
RUN mkdir -p /app /app/logs && \
    chown -R appuser:appgroup /app

# Copier les dépendances Python depuis le builder
#COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copier le code de l'application
COPY --chown=appuser:appgroup main.py /app/
COPY --chown=appuser:appgroup pyproject.toml /app/
COPY --chown=appuser:appgroup README.md /app/

# Définir les variables d'environnement de sécurité
ENV PYTHONPATH=/home/appuser/.local/lib/python3.11/site-packages \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Variables d'environnement pour l'application (seront surchargées par ECS)
ENV ITOP_BASE_URL="" \
    ITOP_USER="" \
    ITOP_PASSWORD="" \
    ITOP_VERSION="1.4" \
    LOG_LEVEL="INFO"

# Passer à l'utilisateur non-root
USER appuser

# Définir le répertoire de travail
WORKDIR /app

# Exposer le port (bien que MCP utilise stdio, utile pour health checks)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import main; print('OK')" || exit 1

# Point d'entrée sécurisé
ENTRYPOINT ["python", "-m", "main"]

# Commande par défaut
CMD []