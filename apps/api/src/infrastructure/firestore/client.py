"""Firestore client bootstrap.

Honors the standard `FIRESTORE_EMULATOR_HOST` env var automatically (that's
built into `google.cloud.firestore.Client` itself) so local dev/tests point
at the Firestore emulator without any code here needing to know about it —
see infra/firebase/firestore.rules and the migration plan for the emulator
setup.
"""
from functools import lru_cache

from google.cloud import firestore

from src.config import get_settings


@lru_cache
def get_firestore_client() -> firestore.Client:
    settings = get_settings()
    return firestore.Client(project=settings.firestore_project_id)
