"""Router pour l'ingestion de données synthétiques."""

from fastapi import APIRouter, HTTPException

from app.logging_conf import get_logger
from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.data_synth import DataSynthesizer

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_synthetic_data(request: IngestRequest):
    """Génère et ingère des données synthétiques.

    Args:
        request: Paramètres de génération

    Returns:
        Statistiques d'ingestion
    """
    try:
        logger.info(
            f"Ingesting synthetic data: {request.num_sites} sites, "
            f"{request.nodes_per_site} nodes/site"
        )

        # Créer le générateur
        synth = DataSynthesizer(seed=request.seed)

        # Générer la topologie
        nodes, links = synth.generate_topology(
            num_sites=request.num_sites,
            nodes_per_site=request.nodes_per_site,
        )

        # Générer les métriques et incidents
        metrics_df, incidents_df = synth.generate_metrics(
            nodes=nodes,
            links=links,
            duration_min=request.duration_min,
            freq_min=request.freq_min,
            incident_rate=request.incident_rate,
        )

        # Sauvegarder
        result = synth.save_data(nodes, links, metrics_df, incidents_df)

        logger.info(f"Ingestion complete: {result['num_metrics']} metrics generated")

        return IngestResponse(
            status="success",
            topology_path=result["topology_path"],
            metrics_path=result["metrics_path"],
            incidents_path=result["incidents_path"],
            num_nodes=result["num_nodes"],
            num_links=result["num_links"],
            num_metrics=result["num_metrics"],
            num_incidents=result["num_incidents"],
        )

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
