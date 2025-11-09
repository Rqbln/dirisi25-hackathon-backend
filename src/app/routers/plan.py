"""Router pour la planification."""

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.logging_conf import get_logger
from app.schemas.planning import PlanRequest, PlanResponse, SimulateRequest, SimulateResponse
from app.services.feature_store import FeatureStore
from app.services.modeling import ModelManager
from app.services.planning import PlanningService

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["planning"])


@router.post("/plan", response_model=PlanResponse)
async def generate_plan(request: PlanRequest):
    """Génère un plan d'action pour la planification de ressources.

    Args:
        request: Objectifs, contraintes et contexte

    Returns:
        Plan d'action recommandé
    """
    try:
        logger.info(f"Generating plan with objectives: {request.objectives}")

        # Charger les données
        store = FeatureStore()
        topology = store.load_topology()
        metrics_df = store.load_metrics()

        # Calculer les features
        features_df = store.compute_features(metrics_df)

        # Calculer les scores de risque pour toutes les entités
        model_manager = ModelManager()
        model = model_manager.get_model(mode=settings.model_mode)

        risk_scores = {}
        for entity_id in features_df["entity_id"].unique():
            entity_features = features_df[features_df["entity_id"] == entity_id]
            if len(entity_features) > 0:
                latest = entity_features.iloc[-1].to_dict()
                risk_score, _, _ = model.predict(latest)
                risk_scores[entity_id] = risk_score

        # Générer le plan
        planner = PlanningService()
        plan = planner.generate_plan(request, topology, risk_scores)

        logger.info(f"Plan generated with {len(plan.actions)} actions")

        return plan

    except FileNotFoundError as e:
        logger.error(f"Data not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="Data not found. Please run /v1/ingest first.",
        )
    except Exception as e:
        logger.error(f"Planning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_scenario(request: SimulateRequest):
    """Simule un scénario what-if.

    Args:
        request: Scénario à simuler

    Returns:
        Résultats de simulation
    """
    try:
        logger.info(f"Simulating scenario: {request.scenario}")

        # Charger les données
        store = FeatureStore()
        topology = store.load_topology()
        metrics_df = store.load_metrics()

        # Calculer les features
        features_df = store.compute_features(metrics_df)

        # Simuler les pannes en modifiant les métriques
        simulated_features = features_df.copy()

        # Appliquer les variations
        for entity_id, variation in request.variations.items():
            mask = simulated_features["entity_id"] == entity_id
            # Appliquer la variation sur les métriques actuelles
            for col in simulated_features.columns:
                if "_current" in col:
                    if mask.any():
                        simulated_features.loc[mask, col] = variation

        # Calculer les scores de risque avec les données simulées
        model_manager = ModelManager()
        model = model_manager.get_model(mode=settings.model_mode)

        risk_scores = {}
        for entity_id in simulated_features["entity_id"].unique():
            # Marquer comme en panne si dans failures
            if entity_id in request.failures:
                risk_scores[entity_id] = 1.0
            else:
                entity_features = simulated_features[
                    simulated_features["entity_id"] == entity_id
                ]
                if len(entity_features) > 0:
                    latest = entity_features.iloc[-1].to_dict()
                    risk_score, _, _ = model.predict(latest)
                    risk_scores[entity_id] = risk_score

        # Générer un plan recommandé
        planner = PlanningService()
        # Créer une requête de plan par défaut
        from app.schemas.planning import Objective, PlanConstraints, PlanContext, PlanRequest

        plan_request = PlanRequest(
            objectives=[Objective.MINIMIZE_RISK, Objective.PRESERVE_CRITICAL_FLOWS],
            constraints=PlanConstraints(),
            context=PlanContext(impacted=request.failures),
        )

        recommended_plan = planner.generate_plan(plan_request, topology, risk_scores)

        logger.info(f"Simulation complete: {len(risk_scores)} entities evaluated")

        return SimulateResponse(
            scenario=request.scenario,
            risk_scores=risk_scores,
            recommended_plan=recommended_plan,
        )

    except FileNotFoundError as e:
        logger.error(f"Data not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="Data not found. Please run /v1/ingest first.",
        )
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
