"""Application FastAPI principale."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_conf import setup_logging
from app.routers import health, logs
from app.routers.infer import router as infer_router
from app.routers.rag import router as rag_router
from app.security import setup_security_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events."""
    # Startup
    setup_logging()
    settings.ensure_directories()
    yield
    # Shutdown (rien pour l'instant)


# Créer l'application
app = FastAPI(
    title="DIRISI 2025 Hackathon Backend",
    description="Backend pour anticiper les pannes par l'IA - MVP offline-ready",
    version=settings.api_version,
    lifespan=lifespan,
)

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de la sécurité
setup_security_middleware(app)

# Enregistrer les routers
app.include_router(health.router)
app.include_router(infer_router)
app.include_router(logs.router)
app.include_router(rag_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "DIRISI 2025 Hackathon Backend",
        "version": settings.api_version,
        "status": "operational",
        "docs": "/docs",
    }
