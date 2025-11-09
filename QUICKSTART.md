# 🚀 Quick Start Guide - DIRISI 2025 Backend

## En 3 minutes chrono !

### 1. Installation (1 min)

```bash
# Installer uv si pas encore fait
pip install uv

# Installer les dépendances
make setup
```

### 2. Lancer le serveur (30 secondes)

```bash
make run
```

✅ Le serveur démarre sur http://localhost:8080

### 3. Tester (1 min 30)

**Option A - Script automatique** :
```bash
chmod +x test_api.sh
./test_api.sh
```

**Option B - Manuel** :
```bash
# 1. Health check
curl http://localhost:8080/health

# 2. Générer des données
curl -X POST http://localhost:8080/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"seed": 42, "num_sites": 3, "nodes_per_site": 3}'

# 3. Prédire
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"horizon_min": 30, "targets": [{"node_id": "N0"}]}'
```

### 4. Explorer l'API

Ouvrir dans un navigateur : **http://localhost:8080/docs**

---

## Commandes utiles

```bash
make help          # Voir toutes les commandes
make test          # Lancer les tests
make fmt           # Formater le code
make lint          # Vérifier le code
make docker-build  # Build Docker
make clean         # Nettoyer
```

---

## Troubleshooting

### Erreur "Port 8080 already in use"
```bash
lsof -ti:8080 | xargs kill -9
make run
```

### Erreur "No module named 'fastapi'"
```bash
make uv  # Réinstaller les dépendances
```

### Erreur "Data not found"
```bash
# Générer les données d'abord
curl -X POST http://localhost:8080/v1/ingest -H "Content-Type: application/json" -d '{}'
```

---

## Structure minimale

```
dirisi25-backend/
├── src/app/            # Code source
├── data/               # Données (auto-générées)
├── models/             # Modèles (auto-générés)
├── tests/              # Tests
├── Makefile            # Commandes
└── README.md           # Documentation complète
```

---

## Next Steps

1. ✅ Lire le [README complet](README.md)
2. ✅ Explorer la [doc API](http://localhost:8080/docs)
3. ✅ Modifier le [config](.env)
4. ✅ Lancer les [tests](tests/)

---

**Besoin d'aide ?** Voir le README principal ou les logs !
