"""Génération de données synthétiques pour le réseau."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.config import settings
from app.schemas.topology import Link, Node, NodeRole
from app.utils.seed import set_seed


class DataSynthesizer:
    """Générateur de données synthétiques déterministes."""

    def __init__(self, seed: int = 42):
        """Initialise le générateur.

        Args:
            seed: Seed pour reproductibilité
        """
        self.seed = seed
        set_seed(seed)
        self.rng = np.random.default_rng(seed)

    def generate_topology(
        self, num_sites: int = 5, nodes_per_site: int = 3
    ) -> tuple[list[Node], list[Link]]:
        """Génère une topologie réseau connectée.

        Args:
            num_sites: Nombre de sites
            nodes_per_site: Nombre de nœuds par site

        Returns:
            Tuple (nodes, links)
        """
        nodes = []
        links = []

        # Créer les nœuds
        node_id = 0
        for site_idx in range(num_sites):
            site_name = f"SITE_{chr(65 + site_idx)}"  # SITE_A, SITE_B, ...

            for node_idx in range(nodes_per_site):
                # Premier nœud = CORE, dernier = EDGE, autres = AGG
                if node_idx == 0:
                    role = NodeRole.CORE
                    capacity = self.rng.integers(5000, 10000)
                elif node_idx == nodes_per_site - 1:
                    role = NodeRole.EDGE
                    capacity = self.rng.integers(500, 2000)
                else:
                    role = NodeRole.AGG
                    capacity = self.rng.integers(2000, 5000)

                nodes.append(
                    Node(
                        id=f"N{node_id}",
                        role=role,
                        site=site_name,
                        capacity_mbps=capacity,
                    )
                )
                node_id += 1

        # Créer les liens (topologie maillée partielle)
        link_id = 0

        # Liens intra-site (chaîne)
        for site_idx in range(num_sites):
            start_idx = site_idx * nodes_per_site
            for i in range(nodes_per_site - 1):
                src_idx = start_idx + i
                dst_idx = start_idx + i + 1

                latency = self.rng.uniform(1, 10)
                bandwidth = min(
                    nodes[src_idx].capacity_mbps,
                    nodes[dst_idx].capacity_mbps,
                )

                links.append(
                    Link(
                        id=f"L{link_id}",
                        src=nodes[src_idx].id,
                        dst=nodes[dst_idx].id,
                        latency_ms=round(latency, 2),
                        bandwidth_mbps=bandwidth,
                    )
                )
                link_id += 1

        # Liens inter-sites (CORE à CORE)
        core_nodes = [n for n in nodes if n.role == NodeRole.CORE]
        for i in range(len(core_nodes) - 1):
            src = core_nodes[i]
            dst = core_nodes[i + 1]

            latency = self.rng.uniform(10, 50)
            bandwidth = min(src.capacity_mbps, dst.capacity_mbps)

            links.append(
                Link(
                    id=f"L{link_id}",
                    src=src.id,
                    dst=dst.id,
                    latency_ms=round(latency, 2),
                    bandwidth_mbps=bandwidth,
                )
            )
            link_id += 1

        # Quelques liens redondants aléatoires
        for _ in range(max(1, num_sites // 2)):
            src = self.rng.choice(nodes)
            dst = self.rng.choice(nodes)

            if src.id != dst.id:
                # Vérifier que le lien n'existe pas déjà
                existing = any(
                    (l.src == src.id and l.dst == dst.id)
                    or (l.src == dst.id and l.dst == src.id)
                    for l in links
                )

                if not existing:
                    latency = self.rng.uniform(5, 30)
                    bandwidth = min(src.capacity_mbps, dst.capacity_mbps)

                    links.append(
                        Link(
                            id=f"L{link_id}",
                            src=src.id,
                            dst=dst.id,
                            latency_ms=round(latency, 2),
                            bandwidth_mbps=bandwidth,
                        )
                    )
                    link_id += 1

        return nodes, links

    def generate_metrics(
        self,
        nodes: list[Node],
        links: list[Link],
        duration_min: int = 1440,
        freq_min: int = 1,
        incident_rate: float = 0.01,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Génère les métriques temporelles et incidents.

        Args:
            nodes: Liste des nœuds
            links: Liste des liens
            duration_min: Durée de simulation (minutes)
            freq_min: Fréquence d'échantillonnage (minutes)
            incident_rate: Taux d'incidents par nœud/lien par période

        Returns:
            Tuple (metrics_df, incidents_df)
        """
        start_time = datetime.utcnow().replace(second=0, microsecond=0)
        timestamps = [
            start_time + timedelta(minutes=i * freq_min)
            for i in range(duration_min // freq_min)
        ]

        metrics_data = []
        incidents_data = []

        # Générer métriques pour chaque nœud
        for node in nodes:
            # Patterns de base selon le rôle
            if node.role == NodeRole.CORE:
                base_cpu = 0.60
                base_mem = 0.65
                base_if_util = 0.70
            elif node.role == NodeRole.AGG:
                base_cpu = 0.50
                base_mem = 0.55
                base_if_util = 0.60
            else:  # EDGE
                base_cpu = 0.40
                base_mem = 0.45
                base_if_util = 0.50

            # Incidents pour ce nœud
            incident_times = []
            for ts_idx, ts in enumerate(timestamps):
                if self.rng.random() < incident_rate:
                    incident_times.append(ts_idx)
                    incidents_data.append(
                        {
                            "timestamp": ts,
                            "node_id": node.id,
                            "link_id": None,
                            "type": "anomaly",
                            "severity": self.rng.choice(["low", "medium", "high"]),
                        }
                    )

            # Générer séries temporelles
            for ts_idx, ts in enumerate(timestamps):
                # Cycle jour/nuit (pic à mi-journée)
                hour = (ts.hour + ts.minute / 60) % 24
                daily_factor = 0.3 * np.sin(2 * np.pi * hour / 24)

                # Tendance lente
                trend = 0.05 * np.sin(2 * np.pi * ts_idx / len(timestamps))

                # Bruit
                noise_cpu = self.rng.normal(0, 0.05)
                noise_mem = self.rng.normal(0, 0.03)
                noise_if = self.rng.normal(0, 0.08)
                noise_pkt = self.rng.exponential(0.002)

                # Valeurs normales
                cpu = base_cpu + daily_factor + trend + noise_cpu
                mem = base_mem + trend + noise_mem
                if_util = base_if_util + daily_factor + noise_if
                pkt_err = 0.001 + noise_pkt

                # Anomalies
                if ts_idx in incident_times:
                    cpu += self.rng.uniform(0.15, 0.30)
                    mem += self.rng.uniform(0.10, 0.20)
                    if_util += self.rng.uniform(0.15, 0.25)
                    pkt_err += self.rng.uniform(0.02, 0.08)

                # Clipping [0, 1]
                cpu = np.clip(cpu, 0, 1)
                mem = np.clip(mem, 0, 1)
                if_util = np.clip(if_util, 0, 1)
                pkt_err = np.clip(pkt_err, 0, 1)

                metrics_data.append(
                    {
                        "ts": ts,
                        "node_id": node.id,
                        "link_id": None,
                        "cpu": round(cpu, 4),
                        "mem": round(mem, 4),
                        "if_util": round(if_util, 4),
                        "pkt_err": round(pkt_err, 4),
                        "latency_ms": None,
                    }
                )

        # Générer métriques pour chaque lien
        for link in links:
            # Incidents pour ce lien
            incident_times = []
            for ts_idx, ts in enumerate(timestamps):
                if self.rng.random() < incident_rate * 0.5:  # Moins d'incidents sur liens
                    incident_times.append(ts_idx)
                    incidents_data.append(
                        {
                            "timestamp": ts,
                            "node_id": None,
                            "link_id": link.id,
                            "type": "congestion",
                            "severity": self.rng.choice(["low", "medium", "high"]),
                        }
                    )

            base_latency = link.latency_ms
            base_if_util = 0.50

            for ts_idx, ts in enumerate(timestamps):
                hour = (ts.hour + ts.minute / 60) % 24
                daily_factor = 0.2 * np.sin(2 * np.pi * hour / 24)

                noise_latency = self.rng.normal(0, base_latency * 0.1)
                noise_if = self.rng.normal(0, 0.08)
                noise_pkt = self.rng.exponential(0.001)

                latency = base_latency + noise_latency
                if_util = base_if_util + daily_factor + noise_if
                pkt_err = 0.0005 + noise_pkt

                # Anomalies
                if ts_idx in incident_times:
                    latency += self.rng.uniform(20, 100)
                    if_util += self.rng.uniform(0.20, 0.40)
                    pkt_err += self.rng.uniform(0.01, 0.05)

                latency = max(0, latency)
                if_util = np.clip(if_util, 0, 1)
                pkt_err = np.clip(pkt_err, 0, 1)

                metrics_data.append(
                    {
                        "ts": ts,
                        "node_id": None,
                        "link_id": link.id,
                        "cpu": None,
                        "mem": None,
                        "if_util": round(if_util, 4),
                        "pkt_err": round(pkt_err, 4),
                        "latency_ms": round(latency, 2),
                    }
                )

        metrics_df = pd.DataFrame(metrics_data)
        incidents_df = pd.DataFrame(incidents_data)

        return metrics_df, incidents_df

    def save_data(
        self,
        nodes: list[Node],
        links: list[Link],
        metrics_df: pd.DataFrame,
        incidents_df: pd.DataFrame,
    ) -> dict[str, Any]:
        """Sauvegarde les données générées.

        Args:
            nodes: Liste des nœuds
            links: Liste des liens
            metrics_df: DataFrame des métriques
            incidents_df: DataFrame des incidents

        Returns:
            Dictionnaire avec les chemins et statistiques
        """
        # Assurer que les répertoires existent
        settings.ensure_directories()

        # Sauvegarder la topologie en JSON
        topology_path = settings.data_dir / "raw" / "topology.json"
        topology_data = {
            "nodes": [n.model_dump() for n in nodes],
            "links": [l.model_dump() for l in links],
        }
        with open(topology_path, "w") as f:
            json.dump(topology_data, f, indent=2)

        # Sauvegarder les métriques en parquet
        metrics_path = settings.data_dir / "interim" / "metrics.parquet"
        metrics_df.to_parquet(metrics_path, index=False, engine="pyarrow")

        # Sauvegarder les incidents en CSV
        incidents_path = settings.data_dir / "interim" / "incidents.csv"
        incidents_df.to_csv(incidents_path, index=False)

        return {
            "topology_path": str(topology_path),
            "metrics_path": str(metrics_path),
            "incidents_path": str(incidents_path),
            "num_nodes": len(nodes),
            "num_links": len(links),
            "num_metrics": len(metrics_df),
            "num_incidents": len(incidents_df),
        }
