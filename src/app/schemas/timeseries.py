"""Schémas pour les séries temporelles et métriques."""

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class MetricPoint(BaseModel):
    """Point de métrique pour un nœud ou lien."""

    ts: Annotated[datetime, Field(description="Timestamp ISO-8601")]
    node_id: Annotated[Optional[str], Field(None, description="ID du nœud (si métrique nœud)")]
    link_id: Annotated[Optional[str], Field(None, description="ID du lien (si métrique lien)")]
    cpu: Annotated[Optional[float], Field(None, ge=0, le=1, description="CPU usage (0-1)")]
    mem: Annotated[Optional[float], Field(None, ge=0, le=1, description="Memory usage (0-1)")]
    if_util: Annotated[
        Optional[float], Field(None, ge=0, le=1, description="Interface utilization (0-1)")
    ]
    pkt_err: Annotated[
        Optional[float], Field(None, ge=0, le=1, description="Packet error rate (0-1)")
    ]
    latency_ms: Annotated[Optional[float], Field(None, ge=0, description="Latency en ms")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "ts": "2025-11-09T10:30:00Z",
                "node_id": "N1",
                "cpu": 0.75,
                "mem": 0.68,
                "if_util": 0.82,
                "pkt_err": 0.02,
            }
        }


class MetricsBatch(BaseModel):
    """Batch de métriques."""

    metrics: Annotated[list[MetricPoint], Field(description="Liste des points de métrique")]
