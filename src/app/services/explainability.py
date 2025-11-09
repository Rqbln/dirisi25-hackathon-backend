"""Service d'explicabilité des prédictions."""

from typing import Any

import numpy as np

from app.logging_conf import get_logger

logger = get_logger(__name__)


class ExplainabilityService:
    """Service d'explicabilité pour les modèles."""

    def __init__(self):
        """Initialise le service d'explicabilité."""
        pass

    def explain_prediction(
        self,
        features: dict[str, float],
        model_type: str = "rule",
        model: Any = None,
    ) -> dict[str, Any]:
        """Génère des explications pour une prédiction.

        Args:
            features: Features utilisées
            model_type: Type de modèle
            model: Instance du modèle (optionnel)

        Returns:
            Dictionnaire d'explications
        """
        logger.info(f"Generating explanations for {model_type} model")

        if model_type == "rule":
            return self._explain_rule_based(features)
        elif model_type == "ml":
            return self._explain_ml_based(features, model)
        else:
            return {"error": f"Unknown model type: {model_type}"}

    def _explain_rule_based(self, features: dict[str, float]) -> dict[str, Any]:
        """Explications pour modèle à règles.

        Args:
            features: Features

        Returns:
            Explications
        """
        # Identifier les métriques au-dessus des seuils
        violations = []
        thresholds = {
            "cpu_current": 0.85,
            "mem_current": 0.90,
            "if_util_current": 0.80,
            "pkt_err_current": 0.05,
        }

        for metric, threshold in thresholds.items():
            if metric in features:
                value = features[metric]
                if value is not None and not np.isnan(value):
                    if value > threshold:
                        violations.append({
                            "metric": metric,
                            "value": round(value, 4),
                            "threshold": threshold,
                            "excess": round(value - threshold, 4),
                        })

        # Identifier les tendances
        trends = []
        for window in [5, 15, 30]:
            change_key = f"cpu_change_{window}m"
            if change_key in features:
                change = features[change_key]
                if change is not None and not np.isnan(change) and abs(change) > 0.1:
                    trends.append({
                        "metric": "cpu",
                        "window": f"{window}m",
                        "change": round(change, 4),
                        "direction": "increasing" if change > 0 else "decreasing",
                    })

        return {
            "method": "rule-based",
            "violations": violations,
            "trends": trends,
            "num_violations": len(violations),
            "summary": f"{len(violations)} threshold violations detected",
        }

    def _explain_ml_based(
        self, features: dict[str, float], model: Any
    ) -> dict[str, Any]:
        """Explications pour modèle ML.

        Args:
            features: Features
            model: Modèle ML

        Returns:
            Explications
        """
        if model is None or not hasattr(model, "feature_columns"):
            return {"error": "Model not available for explanation"}

        # Feature importances (coefficients LogReg)
        importances = []
        if hasattr(model, "logreg") and hasattr(model.logreg, "coef_"):
            coefs = model.logreg.coef_[0]
            for i, feat_name in enumerate(model.feature_columns):
                if feat_name in features:
                    value = features[feat_name]
                    if value is not None and not np.isnan(value):
                        importance = abs(coefs[i])
                        contribution = coefs[i] * value
                        importances.append({
                            "feature": feat_name,
                            "value": round(value, 4),
                            "importance": round(importance, 4),
                            "contribution": round(contribution, 4),
                        })

            # Trier par importance
            importances.sort(key=lambda x: x["importance"], reverse=True)

        return {
            "method": "ml-based",
            "top_features": importances[:10],
            "num_features": len(importances),
            "summary": f"Top contributing features: {', '.join(f['feature'] for f in importances[:3])}",
        }

    def get_feature_importance(
        self, model: Any, top_n: int = 20
    ) -> list[dict[str, Any]]:
        """Récupère les importances de features globales.

        Args:
            model: Modèle ML
            top_n: Nombre de top features

        Returns:
            Liste des importances
        """
        if not hasattr(model, "logreg") or not hasattr(model.logreg, "coef_"):
            return []

        coefs = model.logreg.coef_[0]
        importances = []

        for i, feat_name in enumerate(model.feature_columns):
            importances.append({
                "feature": feat_name,
                "importance": abs(coefs[i]),
                "coefficient": coefs[i],
            })

        importances.sort(key=lambda x: x["importance"], reverse=True)
        return importances[:top_n]

    def generate_rule_summary(self, thresholds: dict[str, float]) -> dict[str, Any]:
        """Génère un résumé des règles.

        Args:
            thresholds: Seuils utilisés

        Returns:
            Résumé des règles
        """
        rules = []
        for metric, threshold in thresholds.items():
            rules.append({
                "metric": metric,
                "condition": f"> {threshold}",
                "action": "increase_risk_score",
            })

        return {
            "num_rules": len(rules),
            "rules": rules,
            "logic": "IF any_threshold_exceeded THEN risk_score += 0.3",
        }
