"""Router pour l'explicabilité."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.logging_conf import get_logger
from app.services.explainability import ExplainabilityService
from app.services.feature_store import FeatureStore
from app.services.modeling import ModelManager

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["explainability"])


@router.post("/explain")
async def explain_prediction(
    entity_id: str = Query(..., description="ID de l'entité (node ou link)"),
):
    """Explique la prédiction pour une entité.

    Args:
        entity_id: ID de l'entité

    Returns:
        Explications de la prédiction
    """
    try:
        logger.info(f"Explaining prediction for {entity_id}")

        # Charger les données
        store = FeatureStore()
        metrics_df = store.load_metrics()
        features_df = store.compute_features(metrics_df)

        # Récupérer les features de l'entité
        entity_features = features_df[features_df["entity_id"] == entity_id]

        if len(entity_features) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No features found for entity {entity_id}",
            )

        latest_features = entity_features.iloc[-1].to_dict()

        # Charger le modèle
        model_manager = ModelManager()
        model = model_manager.get_model(mode=settings.model_mode)

        # Générer les explications
        explainer = ExplainabilityService()
        explanations = explainer.explain_prediction(
            features=latest_features,
            model_type=settings.model_mode,
            model=model,
        )

        return {
            "entity_id": entity_id,
            "model_mode": settings.model_mode,
            **explanations,
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"Data not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="Data not found. Please run /v1/ingest first.",
        )
    except Exception as e:
        logger.error(f"Explanation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feature-importance")
async def get_feature_importance(top_n: int = Query(20, ge=1, le=100)):
    """Récupère les importances de features globales.

    Args:
        top_n: Nombre de top features

    Returns:
        Importances de features
    """
    try:
        # Charger le modèle ML
        model_manager = ModelManager()
        model = model_manager.get_model(mode="ml")

        if not model.is_trained:
            raise HTTPException(
                status_code=400,
                detail="ML model is not trained. Please train it first.",
            )

        # Récupérer les importances
        explainer = ExplainabilityService()
        importances = explainer.get_feature_importance(model, top_n=top_n)

        return {
            "model_type": "ml",
            "num_features": len(importances),
            "features": importances,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feature importance failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
