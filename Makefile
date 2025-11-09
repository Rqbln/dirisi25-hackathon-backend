.PHONY: help uv fmt lint test data train run docker-build docker-run bench clean

help:  ## Afficher cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

uv:  ## Installer les dépendances avec uv
	@echo "Installing dependencies with uv..."
	uv pip install -e ".[dev]"

fmt:  ## Formater le code avec black
	@echo "Formatting code with black..."
	black src/ tests/

lint:  ## Vérifier le code avec ruff
	@echo "Linting with ruff..."
	ruff check src/ tests/

test:  ## Exécuter les tests
	@echo "Running tests..."
	pytest tests/ -v --cov=src --cov-report=term-missing

data:  ## Générer les données synthétiques
	@echo "Generating synthetic data..."
	@curl -s -X POST http://localhost:8080/v1/ingest \
		-H "Content-Type: application/json" \
		-d '{"seed": 42, "num_sites": 5, "nodes_per_site": 3, "duration_min": 1440, "freq_min": 1, "incident_rate": 0.01}' \
		| python -m json.tool

train:  ## Entraîner les modèles
	@echo "Training models..."
	@python -m src.scripts.train_models

run:  ## Lancer le serveur en mode dev
	@echo "Starting server..."
	uvicorn src.app.main:app --host 0.0.0.0 --port 8080 --reload

run-prod:  ## Lancer le serveur en mode production
	@echo "Starting server (production)..."
	uvicorn src.app.main:app --host 0.0.0.0 --port 8080 --workers 4

docker-build:  ## Construire l'image Docker
	@echo "Building Docker image..."
	docker build -t dirisi25-backend:latest -f docker/Dockerfile .

docker-run:  ## Lancer le conteneur Docker
	@echo "Running Docker container..."
	docker run --rm -p 8080:8080 --name dirisi25-backend dirisi25-backend:latest

bench:  ## Mesurer les performances de l'API
	@echo "Benchmarking API..."
	@echo "\n=== Health Check ==="
	@time curl -s http://localhost:8080/health > /dev/null
	@echo "\n=== Topology ==="
	@time curl -s http://localhost:8080/v1/topology > /dev/null
	@echo "\n=== Predict ==="
	@time curl -s -X POST http://localhost:8080/v1/predict \
		-H "Content-Type: application/json" \
		-d '{"horizon_min": 30, "targets": [{"node_id": "N0"}, {"node_id": "N1"}]}' > /dev/null

clean:  ## Nettoyer les fichiers générés
	@echo "Cleaning up..."
	@rm -rf data/raw/*.json data/interim/*.parquet data/interim/*.csv data/processed/*.parquet
	@rm -rf models/*.joblib
	@rm -rf .pytest_cache __pycache__ src/**/__pycache__ tests/__pycache__
	@rm -rf .coverage htmlcov
	@echo "Cleanup complete."

setup:  ## Setup initial complet
	@echo "=== Initial Setup ==="
	@make uv
	@echo "\n=== Creating .env file ==="
	@cp .env.example .env || true
	@echo "\n=== Setup complete! ==="
	@echo "Next steps:"
	@echo "  1. make run      # Start the server"
	@echo "  2. make data     # Generate synthetic data (in another terminal)"
	@echo "  3. Open http://localhost:8080/docs"
