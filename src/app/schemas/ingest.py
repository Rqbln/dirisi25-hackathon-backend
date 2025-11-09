"""Schémas pour l'ingestion de données."""

from typing import Annotated

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Requête pour générer et ingérer des données synthétiques."""

    seed: Annotated[int, Field(default=42, description="Seed pour reproductibilité")]
    num_sites: Annotated[int, Field(default=5, ge=1, le=50, description="Nombre de sites")]
    nodes_per_site: Annotated[
        int, Field(default=3, ge=1, le=20, description="Nœuds par site")
    ]
    duration_min: Annotated[
        int, Field(default=1440, ge=60, le=10080, description="Durée simulation (minutes)")
    ]
    freq_min: Annotated[int, Field(default=1, ge=1, le=60, description="Fréquence (minutes)")]
    incident_rate: Annotated[
        float, Field(default=0.01, ge=0, le=1, description="Taux d'incidents")
    ]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "seed": 42,
                "num_sites": 5,
                "nodes_per_site": 3,
                "duration_min": 1440,
                "freq_min": 1,
                "incident_rate": 0.01,
            }
        }


class IngestResponse(BaseModel):
    """Réponse d'ingestion."""

    status: Annotated[str, Field(description="Statut de l'ingestion")]
    topology_path: Annotated[str, Field(description="Chemin du fichier topologie")]
    metrics_path: Annotated[str, Field(description="Chemin du fichier métriques")]
    incidents_path: Annotated[str, Field(description="Chemin du fichier incidents")]
    num_nodes: Annotated[int, Field(description="Nombre de nœuds générés")]
    num_links: Annotated[int, Field(description="Nombre de liens générés")]
    num_metrics: Annotated[int, Field(description="Nombre de points de métrique générés")]
    num_incidents: Annotated[int, Field(description="Nombre d'incidents générés")]

    class Config:
        """Configuration Pydantic."""

        json_schema_extra = {
            "example": {
                "status": "success",
                "topology_path": "data/raw/topology.json",
                "metrics_path": "data/interim/metrics.parquet",
                "incidents_path": "data/interim/incidents.csv",
                "num_nodes": 15,
                "num_links": 28,
                "num_metrics": 21600,
                "num_incidents": 12,
            }
        }
