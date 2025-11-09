"""Schémas pour la planification et l'allocation de ressources."""

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Type d'action de planification."""

    REROUTE = "REROUTE"
    SHIFT_RESERVE = "SHIFT_RESERVE"
    SCALE_UP = "SCALE_UP"
    ISOLATE = "ISOLATE"


class Objective(str, Enum):
    """Objectifs de planification."""

    MINIMIZE_RISK = "minimize_risk"
    PRESERVE_CRITICAL_FLOWS = "preserve_critical_flows"
    BALANCE_LOAD = "balance_load"
    MINIMIZE_LATENCY = "minimize_latency"


class PlanConstraints(BaseModel):
    """Contraintes pour la planification."""

    max_latency_ms: Annotated[Optional[float], Field(None, ge=0, description="Latence max (ms)")]
    reserve_pct: Annotated[
        Optional[float], Field(None, ge=0, le=100, description="Pourcentage de réserve")
    ]
    min_bandwidth_mbps: Annotated[
        Optional[int], Field(None, ge=0, description="Bande passante min (Mbps)")
    ]


class PlanContext(BaseModel):
    """Contexte pour la planification."""

    impacted: Annotated[list[str], Field(default_factory=list, description="IDs impactés")]
    critical_flows: Annotated[
        list[str], Field(default_factory=list, description="IDs flows critiques")
    ]


class PlanRequest(BaseModel):
    """Requête de planification."""

    objectives: Annotated[list[Objective], Field(description="Objectifs de planification")]
    constraints: Annotated[PlanConstraints, Field(description="Contraintes")]
    context: Annotated[PlanContext, Field(description="Contexte")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "objectives": ["minimize_risk", "preserve_critical_flows"],
                "constraints": {"max_latency_ms": 50, "reserve_pct": 20},
                "context": {"impacted": ["N1", "L3"], "critical_flows": ["FTS-CRIT-12"]},
            }
        }


class PlanAction(BaseModel):
    """Action de planification."""

    type: Annotated[ActionType, Field(description="Type d'action")]
    flow: Annotated[Optional[str], Field(None, description="ID du flow concerné")]
    via: Annotated[Optional[list[str]], Field(None, description="Chemin alternatif (IDs)")]
    node: Annotated[Optional[str], Field(None, description="Nœud concerné")]
    delta_mbps: Annotated[Optional[int], Field(None, description="Delta de capacité (Mbps)")]


class EstimatedGain(BaseModel):
    """Gains estimés du plan."""

    risk_delta: Annotated[
        float, Field(description="Variation du risque (négatif = amélioration)")
    ]
    sla_violations_avoided: Annotated[
        int, Field(ge=0, description="Violations SLA évitées estimées")
    ]


class PlanResponse(BaseModel):
    """Réponse de planification."""

    actions: Annotated[list[PlanAction], Field(description="Actions recommandées")]
    rationale: Annotated[list[str], Field(description="Justifications")]
    estimated_gain: Annotated[EstimatedGain, Field(description="Gains estimés")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "actions": [
                    {"type": "REROUTE", "flow": "FTS-CRIT-12", "via": ["L7", "L8"]},
                    {"type": "SHIFT_RESERVE", "node": "N2", "delta_mbps": 150},
                ],
                "rationale": ["Bypass L3 congestion", "Protect critical flow FTS-CRIT-12"],
                "estimated_gain": {"risk_delta": -0.21, "sla_violations_avoided": 2},
            }
        }


class SimulateRequest(BaseModel):
    """Requête de simulation what-if."""

    scenario: Annotated[str, Field(description="Description du scénario")]
    failures: Annotated[list[str], Field(description="IDs des éléments en panne simulée")]
    variations: Annotated[
        dict[str, float], Field(default_factory=dict, description="Variations métriques")
    ]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "scenario": "Panne simultanée N1 + surcharge L3",
                "failures": ["N1"],
                "variations": {"L3.if_util": 0.95},
            }
        }


class SimulateResponse(BaseModel):
    """Réponse de simulation."""

    scenario: Annotated[str, Field(description="Scénario simulé")]
    risk_scores: Annotated[dict[str, float], Field(description="Scores de risque par cible")]
    recommended_plan: Annotated[Optional[PlanResponse], Field(None, description="Plan recommandé")]
