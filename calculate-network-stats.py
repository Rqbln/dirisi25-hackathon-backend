#!/usr/bin/env python3
"""
Script de calcul des statistiques réseau globales.
Analyse tous les fichiers raw logs pour calculer:
- 🌐 Nœuds: nombre d'IPs uniques (src + dst)
- 🔗 Liaisons: nombre de paires (src_ip, dst_ip) uniques
- 📋 Logs: nombre total de lignes
"""

import pandas as pd
from pathlib import Path

# Chemins possibles
paths = [
    Path("/workspace/results-team-9/raw-logs"),
    Path(__file__).parent.parent / "datasets",
]

print("=" * 70)
print("Calcul des statistiques réseau globales")
print("=" * 70)

# Trouver le dossier
raw_dir = None
for path in paths:
    if path.exists():
        raw_dir = path
        print(f"✓ Dossier trouvé: {raw_dir}")
        break

if not raw_dir:
    print("❌ Dossier non trouvé")
    exit(1)

# Liste des fichiers
files = [
    "firewall_logs_100mb_feb2025.csv",
    "firewall_logs_100mb_mar2025.csv",
    "firewall_logs_100mb_apr2025.csv",
    "firewall_logs_100mb_may2025.csv",
    "firewall_logs_100mb_jun2025.csv",
    "firewall_logs_100mb_jul2025.csv",
    "firewall_logs_100mb_aug2025.csv",
    "firewall_logs_100mb_nov2025.csv",
]

print(f"\nAnalyse de {len(files)} mois...\n")

# Sets pour les uniques
all_ips = set()
all_connections = set()
total_logs = 0

for filename in files:
    file_path = raw_dir / filename
    if not file_path.exists():
        print(f"⚠️  {filename}: non trouvé")
        continue
    
    try:
        # Charger le CSV
        df = pd.read_csv(file_path)
        month_logs = len(df)
        total_logs += month_logs
        
        # Extraire IPs
        src_ips = df['src_ip'].dropna().unique()
        dst_ips = df['dst_ip'].dropna().unique()
        all_ips.update(src_ips)
        all_ips.update(dst_ips)
        
        # Extraire connexions (paires src->dst)
        connections = df[['src_ip', 'dst_ip']].dropna()
        for _, row in connections.iterrows():
            all_connections.add((row['src_ip'], row['dst_ip']))
        
        print(f"✓ {filename:35s}: {month_logs:>8,} logs".replace(',', ' '))
        
    except Exception as e:
        print(f"❌ {filename}: erreur - {e}")

print("\n" + "=" * 70)
print("RÉSULTATS")
print("=" * 70)

nodes = len(all_ips)
liaisons = len(all_connections)

print(f"\n🌐 Nœuds (IPs uniques):      {nodes:>10,}".replace(',', ' '))
print(f"🔗 Liaisons (paires uniques): {liaisons:>10,}".replace(',', ' '))
print(f"📋 Logs (total):              {total_logs:>10,}".replace(',', ' '))

# Période
print(f"📅 Période:                   7 mois (Fév-Août, Nov 2025)")

print("\n" + "=" * 70)
print("Copie ces valeurs dans streamlit_app.py (section Statistiques Réseau)")
print("=" * 70)
