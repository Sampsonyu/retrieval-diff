"""Offline, stage-aware retrieval comparison."""

from .compare import compare
from .model import Hit, Snapshot, ValidationError
from .recorder import RunRecorder

__all__ = ["Hit", "RunRecorder", "Snapshot", "ValidationError", "compare"]
__version__ = "0.2.1"
