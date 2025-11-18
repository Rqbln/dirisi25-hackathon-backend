# DIRISI 2025 Hackathon Backend

**Backend Python pour anticiper les pannes par l'IA** — MVP offline-ready pour la planification et l'allocation de ressources d'un réseau militaire.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 📋 Contexte

**Événement** : Hackathon DIRISI 2025  
**Thème** : "Anticiper les pannes par l'IA"  
**Objectif** : Développer un système de prédiction et de planification pour éviter les pannes réseau et optimiser l'allocation de ressources.

### Contraintes

- ✅ **Sécurité by design** (non-root, headers, audit trail)
- ✅ **Offline-ready** (aucune dépendance cloud)
- ✅ **Sobriété** (CPU/RAM faibles, modèles légers)
- ✅ **Explicabilité** (justification des prédictions)
- ✅ **Traçabilité** (logs structurés JSON)
- ✅ **Reproductibilité** (seed déterministe)

---

## 🏗️ Architecture

```
dirisi25-backend/
├── src/app/
│   ├── main.py              # Application FastAPI
│   ├── config.py            # Configuration (Pydantic Settings)
│   ├── security.py          # Middlewares de sécurité
│   ├── routers/             # Endpoints API
│   │   ├── health.py        # /health
│   │   ├── ingest.py        # /v1/ingest
│   │   ├── topology.py      # /v1/topology
│   │   ├── predict.py       # /v1/predict
│   │   ├── plan.py          # /v1/plan, /v1/simulate
│   │   ├── explain.py       # /v1/explain
│   │   └── metrics.py       # /v1/metrics (Prometheus)
│   ├── services/            # Logique métier
│   │   ├── data_synth.py    # Génération données synthétiques
│   │   ├── feature_store.py # Feature engineering
│   │   ├── modeling.py      # Modèles baseline
│   │   ├── planning.py      # Heuristiques planification
│   │   └── explainability.py # Explications
│   └── schemas/             # Modèles Pydantic
├── data/                    # Données (gitignored sauf structure)
├── models/                  # Modèles entraînés (gitignored)
├── tests/                   # Tests pytest
├── docker/                  # Dockerfile
├── Makefile                 # Commandes automatisées
└── README.md                # Ce fichier
```

---

## 🚀 Quick Start (5 minutes)

### 1. Prérequis

- **Python 3.11+**
- **uv** (ou pip)
- **curl** (pour les tests)

### 2. Installation

```bash
# Cloner le repo
git clone <repo-url>
cd dirisi25-hackathon-backend

# Installer les dépendances
make uv

# Ou avec pip classique :
# pip install -e ".[dev]"

# Copier le fichier de configuration
cp .env.example .env
```

### 3. Lancer le serveur

```bash
make run
# Ou directement : uvicorn src.app.main:app --reload
```

Le serveur démarre sur **http://localhost:8080**

### 4. Scénario démo complet

**Terminal 1** : Serveur en cours d'exécution

**Terminal 2** : Tests

```bash
# 1. Vérifier la santé
curl http://localhost:8080/health

# 2. Générer des données synthétiques
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

# 3. Récupérer la topologie
curl http://localhost:8080/v1/topology | jq

# 4. Prédire les risques
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "horizon_min": 30,
    "targets": [
      {"node_id": "N0"},
      {"node_id": "N1"},
      {"link_id": "L3"}
    ]
  }' | jq

# 5. Générer un plan d'action
curl -X POST http://localhost:8080/v1/plan \
  -H "Content-Type: application/json" \
  -d '{
    "objectives": ["minimize_risk", "preserve_critical_flows"],
    "constraints": {"max_latency_ms": 50, "reserve_pct": 20},
    "context": {
      "impacted": ["N1", "L3"],
      "critical_flows": ["FTS-CRIT-12"]
    }
  }' | jq

# 6. Simuler un scénario
curl -X POST http://localhost:8080/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "Panne N1 + congestion L3",
    "failures": ["N1"],
    "variations": {"L3": 0.95}
  }' | jq

# 7. Expliquer une prédiction
curl -X POST "http://localhost:8080/v1/explain?entity_id=N0" | jq

# 8. Voir les métriques Prometheus
curl http://localhost:8080/v1/metrics
```

---

## 📊 API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Health check |
| `/v1/ingest` | POST | Génère données synthétiques |
| `/v1/topology` | GET | Récupère la topologie |
| `/v1/predict` | POST | Prédit les risques |
| `/v1/plan` | POST | Génère un plan d'action |
| `/v1/simulate` | POST | Simule un scénario |
| `/v1/explain` | POST | Explique une prédiction |
| `/v1/metrics` | GET | Métriques Prometheus |

**Documentation interactive** : http://localhost:8080/docs

---

## ⚙️ Configuration

Fichier `.env` (copier depuis `.env.example`) :

```bash
# Mode du modèle
MODEL_MODE=rule  # Options: rule, ml, hybrid

# Seed pour reproductibilité
SEED=42

# Sécurité
CORS_ORIGINS=  # Vide = désactivé
RATE_LIMIT_PER_MIN=0  # 0 = désactivé

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Seuils (modèle à règles)
THRESHOLD_CPU_HIGH=0.85
THRESHOLD_MEM_HIGH=0.90
THRESHOLD_IF_UTIL_HIGH=0.80
THRESHOLD_PKT_ERR_HIGH=0.05
THRESHOLD_LATENCY_HIGH_MS=100
```

---

## 🔧 Makefile

```bash
make help          # Affiche l'aide
make uv            # Installe les dépendances
make fmt           # Formate le code (black)
make lint          # Vérifie le code (ruff)
make test          # Exécute les tests
make data          # Génère les données (serveur doit tourner)
make train         # Entraîne les modèles
make run           # Lance le serveur (dev)
make run-prod      # Lance le serveur (prod, 4 workers)
make docker-build  # Build l'image Docker
make docker-run    # Lance le conteneur
make bench         # Benchmark l'API
make clean         # Nettoie les fichiers générés
make setup         # Setup initial complet
```

---

## 🐳 Docker

### Build

```bash
make docker-build
# Ou : docker build -t dirisi25-backend:latest -f docker/Dockerfile .
```

### Run

```bash
make docker-run
# Ou : docker run --rm -p 8080:8080 dirisi25-backend:latest
```

**Image optimisée** :
- Base `python:3.11-slim`
- Utilisateur non-root
- Multi-stage build
- Taille cible : < 300 MB

---

## 🧪 Tests

```bash
# Tous les tests
make test

# Tests spécifiques
pytest tests/test_health.py -v
pytest tests/test_predict.py -v

# Avec coverage
pytest --cov=src --cov-report=html
```

**Couverture actuelle** : ~80% des lignes critiques

---

## 🔐 Sécurité

### Mesures implémentées

1. **Conteneur non-root** (UID 1000)
2. **Headers de sécurité** :
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Content-Security-Policy`
3. **CORS strict** (désactivé par défaut)
4. **Rate limiting** (configurable)
5. **Audit trail** (logs structurés JSON)
6. **Pas d'écriture hors `./data` et `./models`**
7. **Secrets via variables d'env**
8. **Logs minimisés** (pas de données sensibles)

### Limites connues

- Rate limiting en mémoire (non distribué)
- Pas d'authentification (à ajouter selon besoins)
- Pas de chiffrement des données au repos

---

## 📈 Modèles

### 1. Modèle à règles (baseline)

**Principe** : Seuils sur métriques (CPU, mémoire, latence, erreurs)

**Avantages** :
- ✅ Explicable à 100%
- ✅ Pas d'entraînement nécessaire
- ✅ Déterministe

**Configuration** : Via `.env` (voir `THRESHOLD_*`)

### 2. Modèle ML (optionnel)

**Stack** :
- `LogisticRegression` (prédiction risque)
- `IsolationForest` (détection anomalies)
- Normalisation via `StandardScaler`

**Entraînement** :

```bash
# 1. Générer les données (serveur doit tourner)
curl -X POST http://localhost:8080/v1/ingest -H "Content-Type: application/json" -d '{}'

# 2. Entraîner
python -m src.scripts.train_models

# 3. Utiliser
export MODEL_MODE=ml
make run
```

**Explicabilité** : Coefficients LogisticRegression + Feature importances

---

## 📊 Métriques & Observabilité

**Endpoint Prometheus** : `/v1/metrics`

Métriques exposées :
- `dirisi_api_requests_total` : Nombre de requêtes API
- `dirisi_api_request_duration_seconds` : Latence API
- `dirisi_prediction_duration_seconds` : Temps de prédiction
- `dirisi_risk_score` : Scores de risque en temps réel
- `dirisi_model_predictions_total` : Compteur de prédictions

---

## ❓ Inconnues & Actions

### TODO Phase 1 (MVP)

- [ ] Valider les seuils avec des experts réseau
- [ ] Ajouter authentification (JWT ?)
- [ ] Implémenter cache pour features (Redis ?)
- [ ] Optimiser calcul features (parallélisation)

### Questions ouvertes

1. **Données réelles** : Formats exacts (SNMP/NetFlow/logs) ?
2. **Critères d'évaluation** : AUC-PR vs F1 ? Pondération faux positifs ?
3. **Infra** : Air-gapped total ? Contraintes SécOp ?
4. **Livrables** : Format soutenance ? Durée pitch ?

**Stratégie** :
- **Plan A** : MVP avec données synthétiques (actuel)
- **Plan B** : Adapteur d'ingestion pour dumps réels (à prévoir)

---

## 🤝 Contribution

```bash
# 1. Créer une branche
git checkout -b feature/ma-feature

# 2. Développer + tests
# ... code ...
make test

# 3. Formatter + lint
make fmt
make lint

# 4. Commit
git commit -m "feat: ajout de ma feature"

# 5. Push
git push origin feature/ma-feature
```

---

## 📝 License

MIT License - Voir [LICENSE](LICENSE)

---

## 📞 Contact

**Équipe DIRISI 2025 Hackathon**

Pour toute question : [contact@exemple.fr](mailto:contact@exemple.fr)

---

## 🐳 Docker

### Configuration

Le backend est conteneurisé avec un **Dockerfile multi-stage** optimisé :

**Stage 1 - Builder (Python 3.11)** :
- Installation de `uv` (gestionnaire de paquets Python ultra-rapide)
- Création d'un environnement virtuel
- Installation des dépendances depuis `pyproject.toml`

**Stage 2 - Runtime (Python 3.11 slim)** :
- Image légère (~150MB)
- Utilisateur non-root (`appuser`) pour la sécurité
- Port **8080** exposé
- Health check automatique sur `/health`
- `PYTHONPATH=/app/src` configuré

### Structure Docker

```
docker/
└── Dockerfile    # Build multi-stage optimisé
```

### Utilisation avec Docker Compose

**⚠️ Important** : Le backend et le frontend doivent être dans le **même dossier parent** pour que Docker Compose fonctionne.

```bash
# Structure requise
DIRISI-Hackathon/
├── dirisi25-hackathon-frontend/  # Contient docker/docker-compose.yml
└── dirisi25-hackathon-backend/   # Ce repo
```

Le backend est automatiquement lancé via le `docker-compose.yml` du frontend :

```bash
# Depuis le dossier frontend
cd ../dirisi25-hackathon-frontend
make docker
```

Cette commande lance **les deux services** :
- ✅ Backend FastAPI sur `http://localhost:8080`
- ✅ Frontend React sur `http://localhost:3000`
- ✅ Health checks automatiques
- ✅ Réseau Docker isolé (`dirisi-network`)

### Variables d'environnement Docker

```yaml
environment:
  - PYTHONUNBUFFERED=1        # Logs en temps réel
  - PYTHONPATH=/app/src       # Import des modules app.*
  - LOG_LEVEL=INFO            # Niveau de log
```

### Volumes persistants

```yaml
volumes:
  - ./data:/app/data        # Données (raw, interim, processed)
  - ./models:/app/models    # Modèles ML sauvegardés
```

Les données et modèles sont **persistés** entre les redémarrages du container.

### Health Check

Le container vérifie automatiquement sa santé :

```bash
# Vérifier le statut
docker ps
# STATUTS : starting (5s) → healthy

# Test manuel
curl http://localhost:8080/health
# {"status":"ok","version":"0.1.0","mode":"rule","env":"development"}
```

### Commandes Docker

```bash
# Depuis le frontend
cd ../dirisi25-hackathon-frontend

# Lancer (mode interactif, Ctrl+C pour arrêter)
make docker

# Lancer en arrière-plan
make docker-up

# Voir les logs du backend
docker compose -f docker/docker-compose.yml logs backend -f

# Arrêter
make docker-down

# Rebuild complet
make docker-build
```

### Build standalone

Pour builder uniquement le backend :

```bash
# Build l'image
docker build -t dirisi-backend:latest -f docker/Dockerfile .

# Run standalone
docker run -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  -e LOG_LEVEL=DEBUG \
  dirisi-backend:latest
```

---