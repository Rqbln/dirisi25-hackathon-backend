"""Router pour les métriques Prometheus."""

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.logging_conf import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["metrics"])

# Métriques Prometheus
REQUEST_COUNT = Counter(
    "dirisi_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "dirisi_api_request_duration_seconds",
    "API request latency",
    ["method", "endpoint"],
)

PREDICTION_LATENCY = Histogram(
    "dirisi_prediction_duration_seconds",
    "Prediction computation latency",
)

RISK_SCORE_GAUGE = Gauge(
    "dirisi_risk_score",
    "Current risk score",
    ["entity_id", "entity_type"],
)

FEATURE_COMPUTATION_LATENCY = Histogram(
    "dirisi_feature_computation_duration_seconds",
    "Feature computation latency",
)

MODEL_PREDICTIONS = Counter(
    "dirisi_model_predictions_total",
    "Total model predictions",
    ["model_type", "risk_band"],
)


@router.get("/metrics")
async def metrics():
    """Expose les métriques Prometheus.

    Returns:
        Métriques au format Prometheus
    """
    # Générer les métriques
    metrics_data = generate_latest()

    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
    )


def record_request(method: str, endpoint: str, status: int) -> None:
    """Enregistre une requête.

    Args:
        method: Méthode HTTP
        endpoint: Endpoint
        status: Code de statut
    """
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()


def record_latency(method: str, endpoint: str, duration: float) -> None:
    """Enregistre la latence d'une requête.

    Args:
        method: Méthode HTTP
        endpoint: Endpoint
        duration: Durée en secondes
    """
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def record_prediction_latency(duration: float) -> None:
    """Enregistre la latence de prédiction.

    Args:
        duration: Durée en secondes
    """
    PREDICTION_LATENCY.observe(duration)


def update_risk_score(entity_id: str, entity_type: str, score: float) -> None:
    """Met à jour le score de risque.

    Args:
        entity_id: ID de l'entité
        entity_type: Type d'entité
        score: Score de risque
    """
    RISK_SCORE_GAUGE.labels(entity_id=entity_id, entity_type=entity_type).set(score)


def record_prediction(model_type: str, risk_band: str) -> None:
    """Enregistre une prédiction.

    Args:
        model_type: Type de modèle
        risk_band: Bande de risque
    """
    MODEL_PREDICTIONS.labels(model_type=model_type, risk_band=risk_band).inc()
