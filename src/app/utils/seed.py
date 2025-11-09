"""Utilitaires pour gestion de seed."""

import random

import numpy as np


def set_seed(seed: int) -> None:
    """Configure le seed pour reproductibilité."""
    random.seed(seed)
    np.random.seed(seed)
