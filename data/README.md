# Data Directory

Ce répertoire contient les données utilisées par le backend.

## Structure

- `raw/` : Données brutes (topologie JSON)
- `interim/` : Données intermédiaires (métriques parquet, incidents CSV)
- `processed/` : Features calculées (parquet)

## Génération

Les données sont générées via l'endpoint `/v1/ingest` :

```bash
curl -X POST http://localhost:8080/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "seed": 42,
    "num_sites": 5,
    "nodes_per_site": 3,
    "duration_min": 1440,
    "freq_min": 1,
    "incident_rate": 0.01
  }'
```

## Fichiers générés

- `raw/topology.json` : Topologie du réseau (nœuds + liens)
- `interim/metrics.parquet` : Séries temporelles des métriques
- `interim/incidents.csv` : Incidents simulés
- `processed/features.parquet` : Features calculées (après training)

## Nettoyage

```bash
make clean
# Ou manuellement :
rm -rf raw/*.json interim/*.parquet interim/*.csv processed/*.parquet
```

---

**Note** : Les fichiers de données sont gitignorés pour éviter de versionner de gros fichiers.
