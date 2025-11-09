"""Utilitaires pour mesure de temps."""

import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def timer(name: str) -> Generator[None, None, None]:
    """Context manager pour mesurer le temps d'exécution."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"[TIMER] {name}: {elapsed:.4f}s")
