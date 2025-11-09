"""Tests pour l'ingestion."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ingest_synthetic_data():
    """Test de l'ingestion de données synthétiques."""
    response = client.post(
        "/v1/ingest",
        json={
            "seed": 42,
            "num_sites": 2,
            "nodes_per_site": 2,
            "duration_min": 60,
            "freq_min": 5,
            "incident_rate": 0.01,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["num_nodes"] == 4
    assert data["num_links"] > 0
    assert data["num_metrics"] > 0


def test_ingest_with_defaults():
    """Test de l'ingestion avec paramètres par défaut."""
    response = client.post("/v1/ingest", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
