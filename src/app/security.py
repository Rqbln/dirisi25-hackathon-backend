"""Configuration de sécurité."""

import time
from collections import defaultdict
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.logging_conf import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware pour ajouter les headers de sécurité."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Ajoute les headers de sécurité."""
        response = await call_next(request)

        # Headers de sécurité
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # CSP adapté selon le path
        if request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            # CSP permissif pour la documentation (Swagger UI/ReDoc)
            response.headers[
                "Content-Security-Policy"
            ] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https: blob:; "
                "font-src 'self' data: https:; "
                "connect-src 'self' https://cdn.jsdelivr.net"
            )
        else:
            # CSP strict pour les endpoints API
            response.headers["X-Frame-Options"] = "DENY"
            response.headers[
                "Content-Security-Policy"
            ] = "default-src 'self'; script-src 'self'; style-src 'self'"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware pour rate limiting (simple, en mémoire)."""

    def __init__(self, app, limit_per_min: int = 60):
        """Initialise le middleware.

        Args:
            app: Application FastAPI
            limit_per_min: Limite de requêtes par minute
        """
        super().__init__(app)
        self.limit_per_min = limit_per_min
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Vérifie le rate limit."""
        if self.limit_per_min <= 0:
            return await call_next(request)

        # Identifier le client (IP)
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Nettoyer les anciennes requêtes (>1 min)
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if current_time - t < 60
        ]

        # Vérifier la limite
        if len(self.requests[client_ip]) >= self.limit_per_min:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"},
            )

        # Ajouter la requête actuelle
        self.requests[client_ip].append(current_time)

        return await call_next(request)


class AuditTrailMiddleware(BaseHTTPMiddleware):
    """Middleware pour l'audit trail."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enregistre les requêtes importantes."""
        start_time = time.time()

        # Ne tracer que certaines routes
        trace_routes = ["/v1/ingest", "/v1/predict", "/v1/plan", "/v1/simulate"]
        should_trace = any(request.url.path.startswith(route) for route in trace_routes)

        if should_trace:
            logger.info(
                "audit_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client": request.client.host if request.client else "unknown",
                    "timestamp": datetime.utcnow().isoformat(),
                    "origin": "local",
                },
            )

        response = await call_next(request)

        if should_trace:
            duration = time.time() - start_time
            logger.info(
                "audit_response",
                extra={
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

        return response


def setup_cors(app):
    """Configure CORS si activé.

    Args:
        app: Application FastAPI
    """
    origins = settings.cors_origins_list

    if origins:
        logger.info(f"CORS enabled for origins: {origins}")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
            max_age=3600,
        )
    else:
        logger.info("CORS disabled")


def setup_security_middleware(app):
    """Configure tous les middlewares de sécurité.

    Args:
        app: Application FastAPI
    """
    # Headers de sécurité
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting
    if settings.rate_limit_per_min > 0:
        logger.info(f"Rate limiting enabled: {settings.rate_limit_per_min}/min")
        app.add_middleware(RateLimitMiddleware, limit_per_min=settings.rate_limit_per_min)

    # Audit trail
    app.add_middleware(AuditTrailMiddleware)

    # CORS
    setup_cors(app)
