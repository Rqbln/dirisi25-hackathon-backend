"""Router pour les prédictions."""

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.logging_conf import get_logger
from app.schemas.prediction import PredictRequest, PredictResponse, PredictionResult
from app.services.feature_store import FeatureStore
from app.services.modeling import ModelManager

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["prediction"])


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Prédit le risque de panne pour les cibles spécifiées.

    Args:
        request: Cibles et horizon

    Returns:
        Prédictions de risque
    """
    try:
        logger.info(f"Predicting risk for {len(request.targets)} targets")

        # Charger les données
        store = FeatureStore()
        topology = store.load_topology()
        metrics_df = store.load_metrics()

        # Calculer les features
        features_df = store.compute_features(metrics_df)

        # Charger le modèle
        model_manager = ModelManager()
        model = model_manager.get_model(mode=settings.model_mode)

        # Prédire pour chaque cible
        predictions = []
        for target in request.targets:
            target_id = target.node_id or target.link_id
            entity_type = "node" if target.node_id else "link"

            # Récupérer les features de la cible
            target_features = features_df[
                features_df["entity_id"] == target_id
            ]

            if len(target_features) == 0:
                logger.warning(f"No features found for {target_id}")
                predictions.append(
                    PredictionResult(
                        target=target_id,
                        risk_score=0.0,
                        risk_band="LOW",
                        eta_failure_min=None,
                        explanations=["No data available"],
                    )
                )
                continue

            # Prendre les dernières features
            latest_features = target_features.iloc[-1].to_dict()

            # Prédire
            risk_score, risk_band, explanations = model.predict(latest_features)

            # Estimer ETA (simple heuristique)
            eta_failure_min = None
            if risk_score > 0.7:
                # ETA proportionnel au risque
                eta_failure_min = int((1 - risk_score) * request.horizon_min)

            predictions.append(
                PredictionResult(
                    target=target_id,
                    risk_score=round(risk_score, 3),
                    risk_band=risk_band,
                    eta_failure_min=eta_failure_min,
                    explanations=explanations,
                )
            )

        logger.info(f"Predictions generated for {len(predictions)} targets")

        return PredictResponse(predictions=predictions)

    except FileNotFoundError as e:
        logger.error(f"Data not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="Data not found. Please run /v1/ingest first.",
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
