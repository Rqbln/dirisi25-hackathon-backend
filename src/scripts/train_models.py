"""Script pour entraîner les modèles."""

import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.logging_conf import get_logger, setup_logging
from app.services.feature_store import FeatureStore
from app.services.modeling import ModelManager

setup_logging()
logger = get_logger(__name__)


def main():
    """Entraîne les modèles baseline."""
    logger.info("Starting model training...")

    try:
        # Charger les données
        store = FeatureStore()
        metrics_df = store.load_metrics()
        logger.info(f"Loaded {len(metrics_df)} metrics")

        # Calculer les features
        features_df = store.compute_features(metrics_df)
        logger.info(f"Computed {len(features_df)} feature rows")

        # Sauvegarder les features
        store.save_features(features_df)

        # Créer les splits
        train_df, val_df, test_df = store.create_train_test_split(features_df)

        # Initialiser le gestionnaire de modèles
        model_manager = ModelManager()

        # Entraîner le modèle à règles (juste sauvegarder les seuils)
        logger.info("Training rule-based model...")
        rule_model = model_manager._load_or_create_rule_model()
        rule_model.save(settings.models_dir / "rule.joblib")
        logger.info("Rule-based model saved")

        # Entraîner le modèle ML
        logger.info("Training ML model...")
        ml_model = model_manager._load_or_create_ml_model()

        # Créer des pseudo-labels depuis les incidents
        # Pour simplifier, on utilise un seuil sur cpu_current
        if "cpu_current" in train_df.columns:
            labels = (train_df["cpu_current"] > settings.threshold_cpu_high).astype(int)
            metrics = ml_model.train(train_df, labels)
            logger.info(f"ML model trained: {metrics}")
        else:
            metrics = ml_model.train(train_df)
            logger.info(f"ML model trained (unsupervised): {metrics}")

        ml_model.save(settings.models_dir / "ml.joblib")
        logger.info("ML model saved")

        # Évaluer sur le test set
        logger.info("Evaluating models on test set...")
        test_results = evaluate_models(model_manager, test_df)
        logger.info(f"Test results: {test_results}")

        logger.info("Training complete!")

    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)


def evaluate_models(model_manager: ModelManager, test_df) -> dict:
    """Évalue les modèles sur le test set.

    Args:
        model_manager: Gestionnaire de modèles
        test_df: DataFrame de test

    Returns:
        Résultats d'évaluation
    """
    results = {}

    # Évaluer le modèle à règles
    rule_model = model_manager.get_model("rule")
    rule_scores = []
    for _, row in test_df.head(100).iterrows():
        features = row.to_dict()
        score, _, _ = rule_model.predict(features)
        rule_scores.append(score)

    results["rule_mean_score"] = sum(rule_scores) / len(rule_scores) if rule_scores else 0

    # Évaluer le modèle ML
    ml_model = model_manager.get_model("ml")
    if ml_model.is_trained:
        ml_scores = []
        for _, row in test_df.head(100).iterrows():
            features = row.to_dict()
            score, _, _ = ml_model.predict(features)
            ml_scores.append(score)

        results["ml_mean_score"] = sum(ml_scores) / len(ml_scores) if ml_scores else 0

    return results


if __name__ == "__main__":
    main()
