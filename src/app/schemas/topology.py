"""Schémas pour la topologie réseau."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class NodeRole(str, Enum):
    """Rôle d'un nœud dans le réseau."""

    CORE = "CORE"
    EDGE = "EDGE"
    AGG = "AGG"


class Node(BaseModel):
    """Nœud du réseau."""

    id: Annotated[str, Field(description="Identifiant unique du nœud")]
    role: Annotated[NodeRole, Field(description="Rôle du nœud (CORE/AGG/EDGE)")]
    site: Annotated[str, Field(description="Site d'appartenance")]
    capacity_mbps: Annotated[int, Field(ge=0, description="Capacité en Mbps")]


class Link(BaseModel):
    """Lien entre deux nœuds."""

    id: Annotated[str, Field(description="Identifiant unique du lien")]
    src: Annotated[str, Field(description="ID du nœud source")]
    dst: Annotated[str, Field(description="ID du nœud destination")]
    latency_ms: Annotated[float, Field(ge=0, description="Latence en ms")]
    bandwidth_mbps: Annotated[int, Field(ge=0, description="Bande passante en Mbps")]


class Topology(BaseModel):
    """Topologie complète du réseau."""

    nodes: Annotated[list[Node], Field(description="Liste des nœuds")]
    links: Annotated[list[Link], Field(description="Liste des liens")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "nodes": [
                    {"id": "N1", "role": "CORE", "site": "SITE_A", "capacity_mbps": 10000},
                    {"id": "N2", "role": "EDGE", "site": "SITE_A", "capacity_mbps": 1000},
                ],
                "links": [
                    {
                        "id": "L1",
                        "src": "N1",
                        "dst": "N2",
                        "latency_ms": 5.2,
                        "bandwidth_mbps": 1000,
                    }
                ],
            }
        }
