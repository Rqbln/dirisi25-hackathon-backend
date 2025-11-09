"""Modèles baseline pour la prédiction de pannes."""

import joblib
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.config import settings
from app.logging_conf import get_logger
from app.schemas.prediction import RiskBand

logger = get_logger(__name__)


class RuleBasedModel:
    """Modèle basé sur des règles de seuils."""

    def __init__(self):
        """Initialise le modèle à règles."""
        self.thresholds = {
            "cpu": settings.threshold_cpu_high,
            "mem": settings.threshold_mem_high,
            "if_util": settings.threshold_if_util_high,
            "pkt_err": settings.threshold_pkt_err_high,
            "latency_ms": settings.threshold_latency_high_ms,
        }

    def predict(self, features: dict[str, float]) -> tuple[float, RiskBand, list[str]]:
        """Prédit le risque basé sur les règles.

        Args:
            features: Dictionnaire des features

        Returns:
            Tuple (risk_score, risk_band, explanations)
        """
        violations = []
        explanations = []

        # Vérifier chaque métrique
        for metric, threshold in self.thresholds.items():
            current_key = f"{metric}_current"
            if current_key in features:
                value = features[current_key]
                if value is not None and not np.isnan(value):
                    if metric == "latency_ms":
                        # Latence est en ms
                        if value > threshold:
                            violations.append(metric)
                            explanations.append(f"{metric}↑ ({value:.2f} > {threshold})")
                    else:
                        # Métriques normalisées [0, 1]
                        if value > threshold:
                            violations.append(metric)
                            explanations.append(f"{metric}↑ ({value:.2f})")

        # Calculer score de risque
        num_violations = len(violations)

        if num_violations == 0:
            risk_score = 0.1
            risk_band = RiskBand.LOW
        elif num_violations == 1:
            risk_score = 0.4
            risk_band = RiskBand.MEDIUM
        elif num_violations == 2:
            risk_score = 0.7
            risk_band = RiskBand.HIGH
        else:
            risk_score = 0.95
            risk_band = RiskBand.CRITICAL

        # Ajuster avec les tendances (si disponibles)
        for window in [5, 15, 30]:
            cpu_change_key = f"cpu_change_{window}m"
            if cpu_change_key in features and features[cpu_change_key] is not None:
                change = features[cpu_change_key]
                if not np.isnan(change) and change > 0.2:
                    risk_score = min(1.0, risk_score + 0.1)
                    if "tendance CPU↑" not in " ".join(explanations):
                        explanations.append(f"tendance CPU↑ (+{change:.1%})")
                    break

        if not explanations:
            explanations = ["Métriques nominales"]

        return risk_score, risk_band, explanations

    def save(self, path: Path) -> None:
        """Sauvegarde le modèle.

        Args:
            path: Chemin du fichier
        """
        joblib.dump(self.thresholds, path)
        logger.info(f"Rule-based model saved to {path}")

    @classmethod
    def load(cls, path: Path) -> "RuleBasedModel":
        """Charge le modèle.

        Args:
            path: Chemin du fichier

        Returns:
            Instance du modèle
        """
        model = cls()
        model.thresholds = joblib.load(path)
        logger.info(f"Rule-based model loaded from {path}")
        return model


class MLBasedModel:
    """Modèle ML (LogisticRegression + IsolationForest)."""

    def __init__(self):
        """Initialise le modèle ML."""
        self.scaler = StandardScaler()
        self.logreg = LogisticRegression(random_state=settings.seed, max_iter=1000)
        self.iforest = IsolationForest(
            random_state=settings.seed,
            contamination=0.1,
            n_estimators=100,
        )
        self.feature_columns: Optional[list[str]] = None
        self.is_trained = False

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prépare les features pour le ML.

        Args:
            df: DataFrame avec features

        Returns:
            DataFrame préparé
        """
        # Sélectionner les colonnes numériques
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # Exclure les colonnes non-features
        exclude = ["ts", "entity_id", "entity_type"]
        feature_cols = [c for c in numeric_cols if c not in exclude]

        # Remplir les NaN avec 0
        df_clean = df[feature_cols].fillna(0)

        return df_clean

    def train(
        self,
        train_df: pd.DataFrame,
        labels: Optional[pd.Series] = None,
    ) -> dict[str, Any]:
        """Entraîne le modèle.

        Args:
            train_df: DataFrame d'entraînement
            labels: Labels pour LogisticRegression (optionnel)

        Returns:
            Métriques d'entraînement
        """
        logger.info("Training ML model...")

        X_train = self._prepare_features(train_df)
        self.feature_columns = X_train.columns.tolist()

        # Normalisation
        X_scaled = self.scaler.fit_transform(X_train)

        # Entraîner IsolationForest (unsupervised)
        self.iforest.fit(X_scaled)

        # Entraîner LogisticRegression si labels fournis
        if labels is not None:
            self.logreg.fit(X_scaled, labels)
            train_score = self.logreg.score(X_scaled, labels)
        else:
            # Créer des pseudo-labels depuis IsolationForest
            anomaly_scores = self.iforest.score_samples(X_scaled)
            threshold = np.percentile(anomaly_scores, 20)
            pseudo_labels = (anomaly_scores < threshold).astype(int)

            self.logreg.fit(X_scaled, pseudo_labels)
            train_score = self.logreg.score(X_scaled, pseudo_labels)

        self.is_trained = True

        logger.info(f"ML model trained. Accuracy: {train_score:.3f}")

        return {
            "train_accuracy": train_score,
            "num_features": len(self.feature_columns),
            "num_samples": len(X_train),
        }

    def predict(
        self, features: dict[str, float]
    ) -> tuple[float, RiskBand, list[str]]:
        """Prédit le risque avec le modèle ML.

        Args:
            features: Dictionnaire des features

        Returns:
            Tuple (risk_score, risk_band, explanations)
        """
        if not self.is_trained:
            raise ValueError("Model is not trained")

        # Préparer les features
        feature_values = []
        for col in self.feature_columns:
            val = features.get(col, 0)
            if val is None or np.isnan(val):
                val = 0
            feature_values.append(val)

        X = np.array([feature_values])
        X_scaled = self.scaler.transform(X)

        # Prédiction LogisticRegression
        proba = self.logreg.predict_proba(X_scaled)[0]
        risk_score_lr = proba[1] if len(proba) > 1 else proba[0]

        # Score IsolationForest (anomaly)
        anomaly_score = self.iforest.score_samples(X_scaled)[0]
        # Normaliser [-0.5, 0.5] -> [0, 1]
        risk_score_if = 1 / (1 + np.exp(anomaly_score * 5))

        # Combiner les deux scores
        risk_score = 0.6 * risk_score_lr + 0.4 * risk_score_if

        # Déterminer la bande
        if risk_score < 0.3:
            risk_band = RiskBand.LOW
        elif risk_score < 0.6:
            risk_band = RiskBand.MEDIUM
        elif risk_score < 0.85:
            risk_band = RiskBand.HIGH
        else:
            risk_band = RiskBand.CRITICAL

        # Explications (top features)
        explanations = self._get_top_features(features, n=3)

        return risk_score, risk_band, explanations

    def _get_top_features(self, features: dict[str, float], n: int = 3) -> list[str]:
        """Extrait les top N features contribuant au risque.

        Args:
            features: Dictionnaire des features
            n: Nombre de top features

        Returns:
            Liste d'explications
        """
        # Coefficients du LogisticRegression
        if hasattr(self.logreg, "coef_"):
            coefs = self.logreg.coef_[0]
            feature_importance = list(zip(self.feature_columns, coefs))
            feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)

            explanations = []
            for feat_name, coef in feature_importance[:n]:
                if feat_name in features:
                    value = features[feat_name]
                    if value is not None and not np.isnan(value):
                        direction = "↑" if coef > 0 else "↓"
                        explanations.append(f"{feat_name} {direction}")

            return explanations or ["Facteurs multiples"]

        return ["ML prediction"]

    def save(self, path: Path) -> None:
        """Sauvegarde le modèle.

        Args:
            path: Chemin du fichier
        """
        model_data = {
            "scaler": self.scaler,
            "logreg": self.logreg,
            "iforest": self.iforest,
            "feature_columns": self.feature_columns,
            "is_trained": self.is_trained,
        }
        joblib.dump(model_data, path)
        logger.info(f"ML model saved to {path}")

    @classmethod
    def load(cls, path: Path) -> "MLBasedModel":
        """Charge le modèle.

        Args:
            path: Chemin du fichier

        Returns:
            Instance du modèle
        """
        model_data = joblib.load(path)
        model = cls()
        model.scaler = model_data["scaler"]
        model.logreg = model_data["logreg"]
        model.iforest = model_data["iforest"]
        model.feature_columns = model_data["feature_columns"]
        model.is_trained = model_data["is_trained"]
        logger.info(f"ML model loaded from {path}")
        return model


class ModelManager:
    """Gestionnaire de modèles."""

    def __init__(self, models_dir: Optional[Path] = None):
        """Initialise le gestionnaire.

        Args:
            models_dir: Répertoire des modèles
        """
        self.models_dir = models_dir or settings.models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.rule_model: Optional[RuleBasedModel] = None
        self.ml_model: Optional[MLBasedModel] = None

    def get_model(self, mode: str = "rule"):
        """Récupère le modèle selon le mode.

        Args:
            mode: 'rule', 'ml', ou 'hybrid'

        Returns:
            Modèle approprié
        """
        if mode == "rule":
            if self.rule_model is None:
                self.rule_model = self._load_or_create_rule_model()
            return self.rule_model
        elif mode == "ml":
            if self.ml_model is None:
                self.ml_model = self._load_or_create_ml_model()
            return self.ml_model
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _load_or_create_rule_model(self) -> RuleBasedModel:
        """Charge ou crée le modèle à règles."""
        model_path = self.models_dir / "rule.joblib"
        if model_path.exists():
            return RuleBasedModel.load(model_path)
        return RuleBasedModel()

    def _load_or_create_ml_model(self) -> MLBasedModel:
        """Charge ou crée le modèle ML."""
        model_path = self.models_dir / "ml.joblib"
        if model_path.exists():
            return MLBasedModel.load(model_path)
        return MLBasedModel()

    def save_models(self) -> None:
        """Sauvegarde tous les modèles."""
        if self.rule_model:
            self.rule_model.save(self.models_dir / "rule.joblib")
        if self.ml_model:
            self.ml_model.save(self.models_dir / "ml.joblib")
