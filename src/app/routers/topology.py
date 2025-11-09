"""Router pour la topologie."""

from fastapi import APIRouter, HTTPException

from app.logging_conf import get_logger
from app.schemas.topology import Topology
from app.services.feature_store import FeatureStore

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["topology"])


@router.get("/topology", response_model=Topology)
async def get_topology():
    """Récupère la topologie du réseau.

    Returns:
        Topologie complète
    """
    try:
        store = FeatureStore()
        topology_data = store.load_topology()

        return Topology(
            nodes=topology_data["nodes"],
            links=topology_data["links"],
        )

    except FileNotFoundError as e:
        logger.error(f"Topology not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="Topology not found. Please run /v1/ingest first.",
        )
    except Exception as e:
        logger.error(f"Error loading topology: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
