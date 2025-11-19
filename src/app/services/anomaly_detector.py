"""Service de détection d'anomalies pour l'inférence en temps réel."""

import pandas as pd
import numpy as np
from datetime import timedelta
from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path


class AnomalyDetector(ABC):
    """Classe mère abstraite pour tous les détecteurs d'anomalies."""
    
    @abstractmethod
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Détecte les anomalies dans le DataFrame.
        
        Returns:
            DataFrame avec colonnes 'timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action', 'bug_type'
        """
        pass


class NaTDetector(AnomalyDetector):
    """Détecte les valeurs NaT dans la colonne timestamp."""
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_temp = df.copy()
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], errors='coerce')
        
        lignes_nat = df_temp[df_temp['timestamp'].isnull()].copy()
        
        if lignes_nat.empty:
            return pd.DataFrame(columns=['timestamp','firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action', 'bug_type'])
        
        autres_colonnes = [col for col in lignes_nat.columns if col != 'timestamp']
        lignes_nat['bug_type'] = 'corrupt_line'
        
        for index_n in lignes_nat.index:
            nb_valeurs_valides = lignes_nat.loc[index_n, autres_colonnes].count()
            if nb_valeurs_valides > 0:
                lignes_nat.loc[index_n, 'bug_type'] = 'malformed_timestamp'
        
        # Imputation du timestamp
        for index_n in lignes_nat.index:
            if index_n > df_temp.index.min():
                timestamp_precedent = df_temp.loc[index_n - 1, 'timestamp']
                if pd.notna(timestamp_precedent):
                    lignes_nat.loc[index_n, 'timestamp'] = timestamp_precedent + timedelta(seconds=1)
        
        return lignes_nat[['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type']]


class NonNumericPortDetector(AnomalyDetector):
    """Détecte les ports non numériques."""
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_temp = df.copy()
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], errors='coerce')
        
        src_port_numeric = pd.to_numeric(df_temp['src_port'], errors='coerce')
        dst_port_numeric = pd.to_numeric(df_temp['dst_port'], errors='coerce')
        
        condition_bug = src_port_numeric.isna() | dst_port_numeric.isna()
        lignes_bug = df_temp[condition_bug].copy()
        
        if lignes_bug.empty:
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type'])
        
        result = lignes_bug[['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action']].copy()
        result['bug_type'] = 'nonnumeric_port'
        return result


class NegativeBytesDetector(AnomalyDetector):
    """Détecte les octets négatifs."""
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_temp = df.copy()
        df_temp['bytes'] = pd.to_numeric(df_temp['bytes'], errors='coerce')
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], errors='coerce')
        
        condition_bug = df_temp['bytes'] < 0
        lignes_bug = df_temp[condition_bug].copy()
        
        if lignes_bug.empty:
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type'])
        
        result = lignes_bug[['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action']].copy()
        result['bug_type'] = 'negative_bytes'
        return result


class InvalidIPDetector(AnomalyDetector):
    """Détecte les IPs invalides spécifiques."""
    
    def __init__(self, ip_target: str = '999.999.999.999'):
        self.ip_target = ip_target
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_temp = df.copy()
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], errors='coerce')
        
        anomalies = []
        for col in ['src_ip', 'dst_ip']:
            if col in df_temp.columns:
                condition = df_temp[col].astype(str) == self.ip_target
                anomalies.append(df_temp[condition][['timestamp','firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action']].copy())
        
        if not anomalies or all(df.empty for df in anomalies):
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type'])
        
        result = pd.concat(anomalies, ignore_index=True).drop_duplicates()
        result['bug_type'] = 'invalid_ip'
        return result


class DuplicateFieldDetector(AnomalyDetector):
    """Détecte les symboles pipe dans session_id."""
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_temp = df.copy()
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], errors='coerce')
        
        if 'session_id' not in df_temp.columns:
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type'])
        
        condition = df_temp['session_id'].astype(str).str.contains(r'\|', regex=True, na=False)
        lignes_bug = df_temp[condition].copy()
        
        if lignes_bug.empty:
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type'])
        
        result = lignes_bug[['timestamp','firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action']].copy()
        result['bug_type'] = 'duplicate_field'
        return result


class MissingFieldDetector(AnomalyDetector):
    """Détecte les champs manquants."""
    
    REQUIRED_FIELDS = [
        "firewall_id", "src_ip", "dst_ip", "protocol", "action",
        "bytes", "duration_ms", "rule_id", "status", "session_id", "reason"
    ]
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_temp = df.copy()
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], errors='coerce')
        
        # Vérifier uniquement les colonnes qui existent
        fields_to_check = [f for f in self.REQUIRED_FIELDS if f in df_temp.columns]
        if not fields_to_check:
            return pd.DataFrame(columns=['timestamp','firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action', 'bug_type'])
        
        condition = df_temp[fields_to_check].isnull().any(axis=1)
        lignes_bug = df_temp[condition].copy()
        
        if lignes_bug.empty:
            return pd.DataFrame(columns=['timestamp','firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action', 'bug_type'])
        
        result = lignes_bug[['timestamp','firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action']].copy()
        result['bug_type'] = 'missing_field'
        return result


class ThreatDetector(AnomalyDetector):
    """Détecte et mappe les menaces spécifiques."""
    
    THREAT_MAPPING = {
        "Potential DDoS - high rate": "ddos",
        "Port scan detected": "port_scan",
        "Multiple auth failures": "brut_force",
        "XSS attempt": "xss",
        "Known malicious domain contacted": "malware_download",
        "Suspicious SQL payload": "sql_injection"
    }
    
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_temp = df.copy()
        df_temp['timestamp'] = pd.to_datetime(df_temp['timestamp'], errors='coerce')
        
        if 'reason' not in df_temp.columns:
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type'])
        
        condition = df_temp['reason'].astype(str).isin(self.THREAT_MAPPING.keys())
        lignes_bug = df_temp[condition].copy()
        
        if lignes_bug.empty:
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action','bug_type'])
        
        result = lignes_bug[['timestamp','firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action']].copy()
        result['bug_type'] = lignes_bug['reason'].map(self.THREAT_MAPPING)
        return result


class AnomalyClassifier:
    """Classifie les anomalies en severity et type."""
    
    CLASSIFICATION = {
        'malformed_timestamp': {'severity': 'High', 'type': 'Bug'},
        'corrupt_line': {'severity': 'High', 'type': 'Bug'},
        'nonnumeric_port': {'severity': 'Medium', 'type': 'Bug'},
        'missing_field': {'severity': 'Low', 'type': 'Bug'},
        'negative_bytes': {'severity': 'Medium', 'type': 'Bug'},
        'invalid_ip': {'severity': 'High', 'type': 'Bug'},
        'duplicate_field': {'severity': 'Low', 'type': 'Bug'},
        'port_scan': {'severity': 'Medium', 'type': 'Attack'},
        'brut_force': {'severity': 'High', 'type': 'Attack'},
        'xss': {'severity': 'Medium', 'type': 'Attack'},
        'malware_download': {'severity': 'High', 'type': 'Attack'},
        'ddos': {'severity': 'High', 'type': 'Attack'},
        'sql_injection': {'severity': 'High', 'type': 'Attack'}
    }
    
    @staticmethod
    def classify(bug_type: str) -> Dict[str, str]:
        """Retourne severity et type pour un bug_type donné."""
        return AnomalyClassifier.CLASSIFICATION.get(
            bug_type,
            {'severity': 'Unknown', 'type': 'Unknown'}
        )
    
    @staticmethod
    def enrich(df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute les colonnes severity et type au DataFrame."""
        df = df.copy()
        df['severity'] = df['bug_type'].apply(
            lambda x: AnomalyClassifier.classify(x)['severity']
        )
        df['type'] = df['bug_type'].apply(
            lambda x: AnomalyClassifier.classify(x)['type']
        )
        return df


class AnomalyPipeline:
    """Orchestre le pipeline complet de détection d'anomalies."""
    
    def __init__(self):
        self.detectors: List[AnomalyDetector] = []
        self._init_detectors()
    
    def _init_detectors(self):
        """Initialise tous les détecteurs."""
        self.detectors = [
            NaTDetector(),
            NonNumericPortDetector(),
            NegativeBytesDetector(),
            InvalidIPDetector(),
            DuplicateFieldDetector(),
            MissingFieldDetector(),
            ThreatDetector()
        ]
    
    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Exécute le pipeline complet.
        
        Args:
            df: DataFrame d'entrée (logs bruts)
        
        Returns:
            DataFrame enrichi avec timestamp, firewall_id, src_ip, dst_ip, protocol, action, bug_type, severity, type
        """
        all_anomalies = []
        
        # Exécuter chaque détecteur
        for detector in self.detectors:
            anomalies = detector.detect(df)
            if not anomalies.empty:
                all_anomalies.append(anomalies)
        
        if not all_anomalies:
            return pd.DataFrame(columns=['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action', 'bug_type', 'severity', 'type'])
        
        # Fusionner tous les résultats
        df_final = pd.concat(all_anomalies, ignore_index=True).drop_duplicates()
        df_final['timestamp'] = pd.to_datetime(df_final['timestamp'], errors='coerce', utc=True)
        df_final = df_final.sort_values(by='timestamp').reset_index(drop=True)
        
        # Enrichir avec severity et type
        df_final = AnomalyClassifier.enrich(df_final)
        
        return df_final[['timestamp', 'firewall_id', 'src_ip', 'dst_ip', 'protocol', 'action', 'bug_type', 'severity', 'type']]
