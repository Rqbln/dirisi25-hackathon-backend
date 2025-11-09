"""Tests pour les prédictions."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_predict_without_data():
    """Test de prédiction sans données."""
    response = client.post(
        "/v1/predict",
        json={
            "horizon_min": 30,
            "targets": [{"node_id": "N0"}],
        },
    )

    # Devrait retourner 404 car pas de données
    assert response.status_code == 404


def test_predict_with_data():
    """Test de prédiction avec données."""
    # D'abord ingérer des données
    client.post(
        "/v1/ingest",
        json={
            "seed": 42,
            "num_sites": 2,
            "nodes_per_site": 2,
            "duration_min": 60,
            "freq_min": 5,
        },
    )

    # Puis prédire
    response = client.post(
        "/v1/predict",
        json={
            "horizon_min": 30,
            "targets": [{"node_id": "N0"}, {"node_id": "N1"}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 2

    # Vérifier la structure d'une prédiction
    pred = data["predictions"][0]
    assert "target" in pred
    assert "risk_score" in pred
    assert "risk_band" in pred
    assert "explanations" in pred
    assert 0 <= pred["risk_score"] <= 1
