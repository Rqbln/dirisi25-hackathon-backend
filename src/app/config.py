"""Configuration de l'application via Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application DIRISI 2025 Backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Environnement ===
    env: Literal["development", "production", "test"] = Field(
        default="development", description="Environnement d'exécution"
    )
    debug: bool = Field(default=False, description="Mode debug")

    # === Modèle ===
    model_mode: Literal["rule", "ml", "hybrid"] = Field(
        default="rule", description="Mode du modèle de prédiction"
    )
    seed: int = Field(default=42, description="Seed pour reproductibilité")

    # === API ===
    api_host: str = Field(default="0.0.0.0", description="Host de l'API")
    api_port: int = Field(default=8080, description="Port de l'API")
    api_reload: bool = Field(default=False, description="Rechargement auto en dev")
    api_version: str = Field(default="0.1.0", description="Version de l'API")

    # === Sécurité ===
    cors_origins: str = Field(default="", description="CORS origins (séparés par virgule)")
    rate_limit_per_min: int = Field(
        default=0, description="Rate limit par minute (0 = désactivé)"
    )

    # === Logging ===
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Niveau de log"
    )
    log_format: Literal["json", "text"] = Field(default="json", description="Format de log")

    # === Data Generation ===
    default_num_sites: int = Field(default=5, description="Nombre de sites par défaut")
    default_nodes_per_site: int = Field(
        default=3, description="Nombre de nœuds par site par défaut"
    )
    default_duration_min: int = Field(
        default=1440, description="Durée de simulation par défaut (minutes)"
    )
    default_freq_min: int = Field(
        default=1, description="Fréquence des métriques par défaut (minutes)"
    )
    default_incident_rate: float = Field(
        default=0.01, description="Taux d'incidents par défaut"
    )

    # === Seuils (règles) ===
    threshold_cpu_high: float = Field(default=0.85, description="Seuil CPU haut")
    threshold_mem_high: float = Field(default=0.90, description="Seuil mémoire haut")
    threshold_if_util_high: float = Field(
        default=0.80, description="Seuil utilisation interface haut"
    )
    threshold_pkt_err_high: float = Field(
        default=0.05, description="Seuil taux erreur paquets haut"
    )
    threshold_latency_high_ms: float = Field(
        default=100.0, description="Seuil latence haute (ms)"
    )

    # === Chemins ===
    data_dir: Path = Field(default=Path("./data"), description="Répertoire des données")
    models_dir: Path = Field(default=Path("./models"), description="Répertoire des modèles")

    @property
    def cors_origins_list(self) -> list[str]:
        """Retourne la liste des origines CORS."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_directories(self) -> None:
        """Crée les répertoires nécessaires s'ils n'existent pas."""
        for directory in [
            self.data_dir / "raw",
            self.data_dir / "interim",
            self.data_dir / "processed",
            self.models_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Instance globale
settings = Settings()
