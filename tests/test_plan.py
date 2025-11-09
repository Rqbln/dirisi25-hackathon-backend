"""Tests pour la planification."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_plan_with_data():
    """Test de génération de plan."""
    # D'abord ingérer des données
    client.post(
        "/v1/ingest",
        json={
            "seed": 42,
            "num_sites": 2,
            "nodes_per_site": 3,
            "duration_min": 60,
            "freq_min": 5,
        },
    )

    # Générer un plan
    response = client.post(
        "/v1/plan",
        json={
            "objectives": ["minimize_risk", "preserve_critical_flows"],
            "constraints": {"max_latency_ms": 50, "reserve_pct": 20},
            "context": {
                "impacted": ["N0", "L0"],
                "critical_flows": ["FLOW_CRIT_1"],
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "actions" in data
    assert "rationale" in data
    assert "estimated_gain" in data
    assert isinstance(data["actions"], list)
    assert "risk_delta" in data["estimated_gain"]


def test_simulate_scenario():
    """Test de simulation what-if."""
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

    # Simuler un scénario
    response = client.post(
        "/v1/simulate",
        json={
            "scenario": "Panne N0 + congestion L1",
            "failures": ["N0"],
            "variations": {"L1": 0.95},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "scenario" in data
    assert "risk_scores" in data
    assert "recommended_plan" in data
    assert isinstance(data["risk_scores"], dict)
