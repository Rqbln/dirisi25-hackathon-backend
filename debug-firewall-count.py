#!/usr/bin/env python3
"""Script de debug pour compter les logs par firewall."""

import pandas as pd
from pathlib import Path
from collections import Counter

# Chemins possibles
paths = [
    Path("/workspace/dataset-team-9/classified_apr_2025.csv"),
    Path("/workspace/results-team-9/data/results/classified_apr_2025.csv"),
    Path(__file__).parent.parent / "datasets/results/classified_apr_2025.csv",
]

print("=" * 60)
print("Debug - Comptage des logs par firewall (avril 2025)")
print("=" * 60)

# Trouver le fichier
file_path = None
for path in paths:
    if path.exists():
        file_path = path
        print(f"✓ Fichier trouvé: {file_path}")
        break

if not file_path:
    print("❌ Fichier non trouvé dans les chemins testés:")
    for path in paths:
        print(f"  - {path}")
    exit(1)

# Charger les données
print(f"\n📂 Chargement du fichier...")
df = pd.read_csv(file_path)

print(f"✓ {len(df)} lignes chargées")
print(f"\nColonnes: {', '.join(df.columns)}")

# Comptage par firewall_id
print("\n" + "=" * 60)
print("Comptage par firewall_id")
print("=" * 60)

firewall_counts = df['firewall_id'].value_counts()
print(f"\nTotal unique firewalls: {len(firewall_counts)}")
print(f"\nRépartition:")
for fw, count in firewall_counts.items():
    pct = (count / len(df)) * 100
    print(f"  {fw:15s}: {count:6d} logs ({pct:5.2f}%)")

# Vérifier les valeurs manquantes
missing = df['firewall_id'].isna().sum()
empty = (df['firewall_id'] == '').sum()
print(f"\nValeurs manquantes: {missing}")
print(f"Valeurs vides: {empty}")

# Statistiques par type
print("\n" + "=" * 60)
print("Répartition par type")
print("=" * 60)
type_counts = df['type'].value_counts()
for typ, count in type_counts.items():
    pct = (count / len(df)) * 100
    print(f"  {typ:10s}: {count:6d} ({pct:5.2f}%)")

# Statistiques par sévérité
print("\n" + "=" * 60)
print("Répartition par sévérité")
print("=" * 60)
severity_counts = df['severity'].value_counts()
for sev, count in severity_counts.items():
    pct = (count / len(df)) * 100
    print(f"  {sev:10s}: {count:6d} ({pct:5.2f}%)")

# Top 10 bug_types
print("\n" + "=" * 60)
print("Top 10 types d'anomalies")
print("=" * 60)
bug_counts = df['bug_type'].value_counts().head(10)
for bug, count in bug_counts.items():
    pct = (count / len(df)) * 100
    print(f"  {bug:25s}: {count:6d} ({pct:5.2f}%)")

# Test de simulation backend
print("\n" + "=" * 60)
print("Simulation du code frontend")
print("=" * 60)

# Convertir en dict comme le fait le backend
all_logs = df.to_dict('records')

# Compter comme dans le frontend
firewall_totals = {}
for log in all_logs:
    fw = log.get('firewall_id', 'Unknown')
    # Gérer les NaN
    if pd.isna(fw) or fw == '':
        fw = 'Unknown'
    firewall_totals[fw] = firewall_totals.get(fw, 0) + 1

print(f"\nRésultat du comptage frontend:")
for fw, count in sorted(firewall_totals.items(), key=lambda x: x[1], reverse=True):
    print(f"  {fw:15s}: {count:6d} logs")

print("\n" + "=" * 60)
