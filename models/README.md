# Models Directory

Ce répertoire contient les modèles entraînés.

## Fichiers

- `rule.joblib` : Modèle à règles (seuils)
- `ml.joblib` : Modèle ML (LogisticRegression + IsolationForest)

## Entraînement

```bash
# 1. Générer les données d'abord (serveur doit tourner)
curl -X POST http://localhost:8080/v1/ingest -H "Content-Type: application/json" -d '{}'

# 2. Entraîner les modèles
python -m src.scripts.train_models
```

## Utilisation

Les modèles sont automatiquement chargés au démarrage selon le `MODEL_MODE` :

```bash
# Utiliser le modèle à règles (par défaut)
export MODEL_MODE=rule
make run

# Utiliser le modèle ML
export MODEL_MODE=ml
make run
```

## Nettoyage

```bash
rm -f models/*.joblib
```

---

**Note** : Les fichiers de modèles sont gitignorés.
