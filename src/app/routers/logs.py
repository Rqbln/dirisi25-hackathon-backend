"""Router pour la recherche et l'analyse des logs firewall."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/v1/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Modèle pour une entrée de log."""
    timestamp: str
    firewall_id: str
    src_ip: str
    dst_ip: str
    protocol: str
    action: str
    incident_type: str
    bug_type: Optional[str] = None
    attack_type: Optional[str] = None


class LogSearchRequest(BaseModel):
    """Requête de recherche de logs."""
    start_timestamp: str
    end_timestamp: str
    incident_types: Optional[List[str]] = None  # ["OK", "Bug", "Attack"]


class LogSearchResponse(BaseModel):
    """Réponse de recherche de logs."""
    total: int
    ok_count: int
    bug_count: int
    attack_count: int
    logs: List[LogEntry]
    start_timestamp: str
    end_timestamp: str


def get_logs_directory() -> Path:
    """Retourne le chemin vers le dossier des logs analysés."""
    # En Docker, les logs sont montés dans /app/data/results
    docker_path = Path("/app/data/results")
    if docker_path.exists():
        return docker_path
    
    # En local: depuis src/app/routers/logs.py, remonter 5 fois puis aller dans datasets/results
    # logs.py -> routers -> app -> src -> dirisi25-hackathon-backend -> DIRISI-Hackathon -> datasets/results
    local_path = Path(__file__).parent.parent.parent.parent.parent / "datasets" / "results"
    if local_path.exists():
        return local_path
    
    raise HTTPException(
        status_code=500,
        detail=f"Impossible de trouver le dossier des logs analysés. Chemin testé: {local_path.absolute()}"
    )


def load_logs_for_month(month: str, year: int = 2025) -> Optional[pd.DataFrame]:
    """Charge les logs pour un mois donné."""
    logs_dir = get_logs_directory()
    
    # Mapping des mois
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
    
    filename = month_files.get(month)
    if not filename:
        return None
    
    filepath = logs_dir / filename
    if not filepath.exists():
        return None
    
    try:
        df = pd.read_csv(filepath)
        # Nettoyer les lignes corrompues
        df = df[df['timestamp'].notna()]
        df = df[~df['timestamp'].str.startswith('CORRUPTED_LINE', na=False)]
        return df
    except Exception as e:
        print(f"Erreur lors du chargement de {filename}: {e}")
        return None


@router.post("/search", response_model=LogSearchResponse)
async def search_logs(request: LogSearchRequest) -> LogSearchResponse:
    """
    Rechercher les logs entre deux timestamps.
    
    Les logs analysés sont stockés dans datasets/results/classified_*.csv
    Format: timestamp,firewall_id,src_ip,dst_ip,protocol,action,incident_type,bug_type,attack_type
    """
    try:
        # Parser les timestamps avec timezone UTC
        start_dt = datetime.fromisoformat(request.start_timestamp.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(request.end_timestamp.replace('Z', '+00:00'))
        
        # S'assurer que les timestamps ont une timezone UTC
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        
        # Identifier les mois à charger
        months_to_load = set()
        current_dt = start_dt
        while current_dt <= end_dt:
            month_str = f"{current_dt.month:02d}"
            if month_str in ["02", "03", "04", "05", "06", "07", "08", "11"]:
                months_to_load.add(month_str)
            # Passer au mois suivant
            if current_dt.month == 12:
                current_dt = current_dt.replace(year=current_dt.year + 1, month=1, day=1)
            else:
                current_dt = current_dt.replace(month=current_dt.month + 1, day=1)
        
        # Charger tous les logs des mois concernés
        all_logs = []
        for month in sorted(months_to_load):
            df = load_logs_for_month(month)
            if df is not None:
                all_logs.append(df)
        
        if not all_logs:
            return LogSearchResponse(
                total=0,
                ok_count=0,
                bug_count=0,
                attack_count=0,
                logs=[],
                start_timestamp=request.start_timestamp,
                end_timestamp=request.end_timestamp
            )
        
        # Concaténer tous les DataFrames
        df_all = pd.concat(all_logs, ignore_index=True)
        
        # Convertir les timestamps et filtrer (avec timezone UTC)
        df_all['timestamp_dt'] = pd.to_datetime(df_all['timestamp'], errors='coerce', utc=True)
        df_all = df_all[df_all['timestamp_dt'].notna()]
        
        # Convertir les datetime Python en Timestamp pandas pour la comparaison
        start_ts = pd.Timestamp(start_dt)
        end_ts = pd.Timestamp(end_dt)
        
        # Filtrer par plage de dates
        mask = (df_all['timestamp_dt'] >= start_ts) & (df_all['timestamp_dt'] <= end_ts)
        df_filtered = df_all[mask]
        
        # Filtrer par type d'incident si spécifié
        if request.incident_types:
            df_filtered = df_filtered[df_filtered['incident_type'].isin(request.incident_types)]
        
        # Compter les types d'incidents
        ok_count = len(df_filtered[df_filtered['incident_type'] == 'OK'])
        bug_count = len(df_filtered[df_filtered['incident_type'] == 'Bug'])
        attack_count = len(df_filtered[df_filtered['incident_type'] == 'Attack'])
        
        # Convertir en liste de LogEntry (limiter à 1000 pour la performance)
        df_result = df_filtered.head(1000)
        logs = []
        for _, row in df_result.iterrows():
            logs.append(LogEntry(
                timestamp=str(row['timestamp']),
                firewall_id=str(row['firewall_id']) if pd.notna(row['firewall_id']) else '',
                src_ip=str(row['src_ip']) if pd.notna(row['src_ip']) else '',
                dst_ip=str(row['dst_ip']) if pd.notna(row['dst_ip']) else '',
                protocol=str(row['protocol']) if pd.notna(row['protocol']) else '',
                action=str(row['action']) if pd.notna(row['action']) else '',
                incident_type=str(row['incident_type']) if pd.notna(row['incident_type']) else '',
                bug_type=str(row['bug_type']) if pd.notna(row['bug_type']) and row['bug_type'] else None,
                attack_type=str(row['attack_type']) if pd.notna(row['attack_type']) and row['attack_type'] else None
            ))
        
        return LogSearchResponse(
            total=len(df_filtered),
            ok_count=ok_count,
            bug_count=bug_count,
            attack_count=attack_count,
            logs=logs,
            start_timestamp=request.start_timestamp,
            end_timestamp=request.end_timestamp
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche de logs: {str(e)}"
        )


@router.get("/stats")
async def get_logs_stats():
    """Obtenir les statistiques globales des logs."""
    try:
        logs_dir = get_logs_directory()
        
        total_logs = 0
        total_ok = 0
        total_bugs = 0
        total_attacks = 0
        
        # Charger tous les fichiers disponibles
        for month in ["02", "03", "04", "05", "06", "07", "08", "11"]:
            df = load_logs_for_month(month)
            if df is not None:
                total_logs += len(df)
                total_ok += len(df[df['incident_type'] == 'OK'])
                total_bugs += len(df[df['incident_type'] == 'Bug'])
                total_attacks += len(df[df['incident_type'] == 'Attack'])
        
        return {
            "total_logs": total_logs,
            "ok_count": total_ok,
            "bug_count": total_bugs,
            "attack_count": total_attacks,
            "months_available": ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Nov"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du calcul des statistiques: {str(e)}"
        )
