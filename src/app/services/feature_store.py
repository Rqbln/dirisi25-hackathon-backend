"""Feature store local pour transformation et agrégation."""

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.logging_conf import get_logger

logger = get_logger(__name__)


class FeatureStore:
    """Gestionnaire du feature store local."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialise le feature store.

        Args:
            data_dir: Répertoire des données (par défaut depuis settings)
        """
        self.data_dir = data_dir or settings.data_dir

    def load_topology(self) -> dict:
        """Charge la topologie depuis JSON.

        Returns:
            Dictionnaire avec nodes et links
        """
        topology_path = self.data_dir / "raw" / "topology.json"
        if not topology_path.exists():
            raise FileNotFoundError(f"Topology not found: {topology_path}")

        with open(topology_path) as f:
            return json.load(f)

    def load_metrics(self) -> pd.DataFrame:
        """Charge les métriques depuis parquet.

        Returns:
            DataFrame des métriques
        """
        metrics_path = self.data_dir / "interim" / "metrics.parquet"
        if not metrics_path.exists():
            raise FileNotFoundError(f"Metrics not found: {metrics_path}")

        df = pd.read_parquet(metrics_path)
        df["ts"] = pd.to_datetime(df["ts"])
        return df.sort_values("ts")

    def load_incidents(self) -> pd.DataFrame:
        """Charge les incidents depuis CSV.

        Returns:
            DataFrame des incidents
        """
        incidents_path = self.data_dir / "interim" / "incidents.csv"
        if not incidents_path.exists():
            return pd.DataFrame()

        df = pd.read_csv(incidents_path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp") if len(df) > 0 else df

    def compute_features(
        self,
        metrics_df: pd.DataFrame,
        windows: list[int] = [5, 15, 30],
    ) -> pd.DataFrame:
        """Calcule les features agrégées sur fenêtres glissantes.

        Args:
            metrics_df: DataFrame des métriques brutes
            windows: Fenêtres en minutes

        Returns:
            DataFrame avec features calculées
        """
        logger.info(f"Computing features for {len(metrics_df)} metrics")

        # Séparer nœuds et liens
        node_metrics = metrics_df[metrics_df["node_id"].notna()].copy()
        link_metrics = metrics_df[metrics_df["link_id"].notna()].copy()

        features_list = []

        # Features pour les nœuds
        if len(node_metrics) > 0:
            for node_id in node_metrics["node_id"].unique():
                node_data = node_metrics[node_metrics["node_id"] == node_id].copy()
                node_data = node_data.sort_values("ts")

                features = self._compute_entity_features(
                    node_data, entity_id=node_id, entity_type="node", windows=windows
                )
                features_list.append(features)

        # Features pour les liens
        if len(link_metrics) > 0:
            for link_id in link_metrics["link_id"].unique():
                link_data = link_metrics[link_metrics["link_id"] == link_id].copy()
                link_data = link_data.sort_values("ts")

                features = self._compute_entity_features(
                    link_data, entity_id=link_id, entity_type="link", windows=windows
                )
                features_list.append(features)

        if not features_list:
            return pd.DataFrame()

        features_df = pd.concat(features_list, ignore_index=True)
        logger.info(f"Computed {len(features_df)} feature rows")

        return features_df

    def _compute_entity_features(
        self,
        data: pd.DataFrame,
        entity_id: str,
        entity_type: str,
        windows: list[int],
    ) -> pd.DataFrame:
        """Calcule les features pour une entité (nœud ou lien).

        Args:
            data: Données de l'entité
            entity_id: ID de l'entité
            entity_type: Type ('node' ou 'link')
            windows: Fenêtres en minutes

        Returns:
            DataFrame avec features
        """
        data = data.copy()
        data = data.set_index("ts")

        # Colonnes numériques à traiter
        numeric_cols = [c for c in data.columns if c not in ["node_id", "link_id"]]
        numeric_cols = [c for c in numeric_cols if data[c].notna().any()]

        features = []

        for ts in data.index:
            feature_row = {
                "ts": ts,
                "entity_id": entity_id,
                "entity_type": entity_type,
            }

            # Valeurs instantanées
            for col in numeric_cols:
                if pd.notna(data.loc[ts, col]):
                    feature_row[f"{col}_current"] = data.loc[ts, col]

            # Features sur fenêtres glissantes
            for window_min in windows:
                window_start = ts - pd.Timedelta(minutes=window_min)
                window_data = data.loc[window_start:ts]

                if len(window_data) == 0:
                    continue

                for col in numeric_cols:
                    col_data = window_data[col].dropna()
                    if len(col_data) == 0:
                        continue

                    # Agrégations
                    feature_row[f"{col}_mean_{window_min}m"] = col_data.mean()
                    feature_row[f"{col}_std_{window_min}m"] = col_data.std()
                    feature_row[f"{col}_min_{window_min}m"] = col_data.min()
                    feature_row[f"{col}_max_{window_min}m"] = col_data.max()

                    # Dérivée (changement)
                    if len(col_data) >= 2:
                        first_val = col_data.iloc[0]
                        last_val = col_data.iloc[-1]
                        if first_val != 0:
                            change = (last_val - first_val) / first_val
                            feature_row[f"{col}_change_{window_min}m"] = change

            features.append(feature_row)

        return pd.DataFrame(features)

    def save_features(self, features_df: pd.DataFrame, name: str = "features") -> Path:
        """Sauvegarde les features.

        Args:
            features_df: DataFrame des features
            name: Nom du fichier (sans extension)

        Returns:
            Chemin du fichier sauvegardé
        """
        output_path = self.data_dir / "processed" / f"{name}.parquet"
        features_df.to_parquet(output_path, index=False, engine="pyarrow")
        logger.info(f"Features saved to {output_path}")
        return output_path

    def create_train_test_split(
        self,
        features_df: pd.DataFrame,
        test_size: float = 0.2,
        val_size: float = 0.1,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Crée des splits train/val/test temporels.

        Args:
            features_df: DataFrame des features
            test_size: Proportion du test
            val_size: Proportion de validation

        Returns:
            Tuple (train_df, val_df, test_df)
        """
        features_df = features_df.sort_values("ts")

        n = len(features_df)
        test_idx = int(n * (1 - test_size))
        val_idx = int(test_idx * (1 - val_size))

        train_df = features_df.iloc[:val_idx]
        val_df = features_df.iloc[val_idx:test_idx]
        test_df = features_df.iloc[test_idx:]

        logger.info(
            f"Split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}"
        )

        return train_df, val_df, test_df

    def get_latest_metrics(
        self, entity_id: str, entity_type: str, n: int = 10
    ) -> pd.DataFrame:
        """Récupère les dernières métriques pour une entité.

        Args:
            entity_id: ID de l'entité
            entity_type: Type ('node' ou 'link')
            n: Nombre de points

        Returns:
            DataFrame des dernières métriques
        """
        metrics_df = self.load_metrics()

        if entity_type == "node":
            filtered = metrics_df[metrics_df["node_id"] == entity_id]
        else:
            filtered = metrics_df[metrics_df["link_id"] == entity_id]

        return filtered.sort_values("ts", ascending=False).head(n)
