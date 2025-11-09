"""Schémas pour les prédictions et scoring de risque."""

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    """Bande de risque."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PredictionTarget(BaseModel):
    """Cible pour une prédiction."""

    node_id: Annotated[Optional[str], Field(None, description="ID du nœud à prédire")]
    link_id: Annotated[Optional[str], Field(None, description="ID du lien à prédire")]


class PredictRequest(BaseModel):
    """Requête de prédiction."""

    horizon_min: Annotated[int, Field(ge=1, le=1440, description="Horizon de prédiction (min)")]
    targets: Annotated[list[PredictionTarget], Field(description="Cibles à prédire")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "horizon_min": 30,
                "targets": [{"node_id": "N1"}, {"link_id": "L3"}],
            }
        }


class PredictionResult(BaseModel):
    """Résultat de prédiction pour une cible."""

    target: Annotated[str, Field(description="ID de la cible (node_id ou link_id)")]
    risk_score: Annotated[float, Field(ge=0, le=1, description="Score de risque (0-1)")]
    risk_band: Annotated[RiskBand, Field(description="Bande de risque")]
    eta_failure_min: Annotated[
        Optional[int], Field(None, ge=0, description="ETA avant panne estimée (min)")
    ]
    explanations: Annotated[list[str], Field(description="Explications lisibles")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "target": "N1",
                "risk_score": 0.72,
                "risk_band": "HIGH",
                "eta_failure_min": 45,
                "explanations": ["cpu↑ (0.92)", "pkt_err↑ (0.08)"],
            }
        }


class PredictResponse(BaseModel):
    """Réponse de prédiction."""

    predictions: Annotated[list[PredictionResult], Field(description="Résultats de prédiction")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "predictions": [
                    {
                        "target": "N1",
                        "risk_score": 0.72,
                        "risk_band": "HIGH",
                        "eta_failure_min": 45,
                        "explanations": ["cpu↑ (0.92)", "pkt_err↑ (0.08)"],
                    }
                ]
            }
        }


class ScoreRequest(BaseModel):
    """Requête de scoring (alias simplifié sans ETA)."""

    targets: Annotated[list[PredictionTarget], Field(description="Cibles à scorer")]


class ScoreResult(BaseModel):
    """Résultat de scoring."""

    target: Annotated[str, Field(description="ID de la cible")]
    risk_score: Annotated[float, Field(ge=0, le=1, description="Score de risque (0-1)")]
    risk_band: Annotated[RiskBand, Field(description="Bande de risque")]


class ScoreResponse(BaseModel):
    """Réponse de scoring."""

    scores: Annotated[list[ScoreResult], Field(description="Scores calculés")]
