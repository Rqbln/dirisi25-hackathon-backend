#!/usr/bin/env python3
"""Script de test pour l'API d'inférence."""

import requests
import json
import time

# Configuration
BACKEND_URL = "http://localhost:8000"

def test_health():
    """Test du endpoint health."""
    print("\n=== Test Health ===")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_check_files():
    """Test du endpoint de vérification des fichiers."""
    print("\n=== Test Check Files ===")
    try:
        response = requests.get(f"{BACKEND_URL}/v1/infer/check", timeout=10)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Dossier classifié: {data.get('classified_directory')}")
        print(f"Fichiers existants: {len(data.get('existing_files', {}))}")
        print(f"Mois manquants: {data.get('missing_months')}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_inference(months=["04"]):
    """Test de l'inférence pour un ou plusieurs mois."""
    print(f"\n=== Test Inference pour {months} ===")
    try:
        start = time.time()
        response = requests.post(
            f"{BACKEND_URL}/v1/infer/classify",
            json={"months": months},
            timeout=600
        )
        duration = time.time() - start
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Succès: {data.get('message')}")
            print(f"✓ Fichiers créés: {data.get('files_created')}")
            print(f"✓ Total anomalies: {data.get('total_anomalies')}")
            print(f"✓ Durée backend: {data.get('duration_seconds')}s")
            print(f"✓ Durée totale: {duration:.2f}s")
            return True
        else:
            print(f"❌ Erreur: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    """Exécuter tous les tests."""
    print("=" * 60)
    print("Test de l'API d'inférence")
    print("=" * 60)
    
    # Test 1: Health check
    if not test_health():
        print("\n❌ Backend non accessible, arrêt des tests")
        return
    
    # Test 2: Vérification des fichiers avant inférence
    test_check_files()
    
    # Test 3: Inférence pour avril
    print("\n⏳ Lancement de l'inférence (cela peut prendre plusieurs secondes)...")
    test_inference(["04"])
    
    # Test 4: Re-vérification après inférence
    test_check_files()
    
    print("\n" + "=" * 60)
    print("Tests terminés")
    print("=" * 60)


if __name__ == "__main__":
    main()
