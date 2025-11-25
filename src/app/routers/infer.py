"""Router pour l'inférence en temps réel des anomalies."""

from pathlib import Path
from typing import List
import time

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.anomaly_detector import AnomalyPipeline

router = APIRouter(prefix="/v1/infer", tags=["inference"])


class InferRequest(BaseModel):
    """Requête d'inférence."""
    months: List[str]  # ["02", "03", "04", etc.]


class InferResponse(BaseModel):
    """Réponse d'inférence."""
    success: bool
    message: str
    files_created: List[str]
    duration_seconds: float
    total_anomalies: int


def get_raw_logs_directory() -> Path:
    """Retourne le chemin vers les logs bruts."""
    # Sur Jupyter Lab
    jupyter_path = Path("/workspace/results-team-9/raw-logs")
    if jupyter_path.exists():
        return jupyter_path

    # En Docker
    docker_path = Path("/app/data/raw")
    if docker_path.exists():
        return docker_path

    # En local
    # infer.py -> routers -> app -> src -> dirisi25-hackathon-backend -> datasets

    print(f"Current file path: {Path(__file__)}")

    local_path = Path(__file__).parent.parent.parent.parent / "datasets" / "raw"
    print(f"Local raw path: {local_path}")
    if local_path.exists():
        return local_path

    raise HTTPException(
        status_code=500,
        detail=f"Impossible de trouver le dossier des logs bruts. Chemins testés: {jupyter_path}, {docker_path}, {local_path}"
    )


def get_classified_directory() -> Path:
    """Retourne le chemin vers les logs classifiés."""
    # Sur Jupyter Lab
    jupyter_path = Path("/workspace/dataset-team-9")
    if jupyter_path.exists():
        return jupyter_path

    # En Docker
    docker_path = Path("/app/data/classified")
    if docker_path.exists():
        return docker_path

    # En local

    print(f"Current file path: {Path(__file__)}")

    local_path = Path(__file__).parent.parent.parent.parent / "datasets" / "results"
    print(f"Local classified path: {local_path}")
    if local_path.exists():
        return local_path

    raise HTTPException(
        status_code=500,
        detail=f"Impossible de trouver le dossier des logs classifiés. Chemins testés: {jupyter_path}, {docker_path}, {local_path}"
    )


@router.post("/classify", response_model=InferResponse)
async def classify_months(request: InferRequest) -> InferResponse:
    """
    Infère les anomalies pour les mois spécifiés et crée les fichiers classifiés.

    Pour chaque mois, charge firewall_logs_100mb_{month}2025.csv,
    détecte les anomalies et sauvegarde classified_{month}_2025.csv
    """
    start_time = time.time()

    raw_dir = get_raw_logs_directory()
    classified_dir = get_classified_directory()

    # Mapping des mois
    month_mapping = {
        "02": ("firewall_logs_100mb_feb2025.csv", "classified_feb_2025.csv"),
        "03": ("firewall_logs_100mb_mar2025.csv", "classified_mar_2025.csv"),
        "04": ("firewall_logs_100mb_apr2025.csv", "classified_apr_2025.csv"),
        "05": ("firewall_logs_100mb_may2025.csv", "classified_may_2025.csv"),
        "06": ("firewall_logs_100mb_jun2025.csv", "classified_jun_2025.csv"),
        "07": ("firewall_logs_100mb_jul2025.csv", "classified_jul_2025.csv"),
        "08": ("firewall_logs_100mb_aug2025.csv", "classified_aug_2025.csv"),
        "11": ("firewall_logs_100mb_nov2025.csv", "classified_nov_2025.csv"),
    }

    files_created = []
    total_anomalies = 0
    pipeline = AnomalyPipeline()

    for month in request.months:
        if month not in month_mapping:
            continue

        raw_filename, classified_filename = month_mapping[month]
        raw_path = raw_dir / raw_filename
        classified_path = classified_dir / classified_filename

        # Vérifier si le fichier brut existe
        if not raw_path.exists():
            continue

        try:
            # Charger les logs bruts
            print(f"  ├─ Chargement {raw_filename}...", flush=True)
            df_raw = pd.read_csv(raw_path)

            # Exécuter la détection d'anomalies
            print(f"  ├─ Détection d'anomalies pour {month}/2025...", flush=True)
            df_classified = pipeline.run(df_raw)

            # Sauvegarder
            df_classified.to_csv(classified_path, index=False)

            files_created.append(classified_filename)
            total_anomalies += len(df_classified)

            print(f"  ├─ ✓ {len(df_classified)} anomalies détectées", flush=True)

        except Exception as e:
            print(f"  ├─ ✗ Erreur pour {month}: {e}", flush=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erreur lors du traitement du mois {month}: {str(e)}"
            )

    duration = time.time() - start_time

    return InferResponse(
        success=True,
        message=f"Inférence terminée pour {len(files_created)} mois",
        files_created=files_created,
        duration_seconds=round(duration, 2),
        total_anomalies=total_anomalies
    )


@router.get("/check")
async def check_classified_files():
    """Vérifie quels fichiers classifiés existent déjà."""
    classified_dir = get_classified_directory()

    month_files = {
        "02": "classified_feb_2025.csv",
        "03": "classified_mar_2025.csv",
        "04": "classified_apr_2025.csv",
        "05": "classified_may_2025.csv",
        "06": "classified_jun_2025.csv",
        "07": "classified_jul_2025.csv",
        "08": "classified_aug_2025.csv",
        "11": "classified_nov_2025.csv",
    }

    existing_files = {}
    missing_months = []

    for month, filename in month_files.items():
        file_path = classified_dir / filename
        if file_path.exists():
            # Lire quelques stats
            try:
                df = pd.read_csv(file_path)
                existing_files[month] = {
                    "filename": filename,
                    "count": len(df),
                    "path": str(file_path)
                }
            except:
                existing_files[month] = {
                    "filename": filename,
                    "count": 0,
                    "path": str(file_path)
                }
        else:
            missing_months.append(month)

    return {
        "classified_directory": str(classified_dir),
        "existing_files": existing_files,
        "missing_months": missing_months
    }
