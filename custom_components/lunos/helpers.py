"""Helper functions for LUNOS Heat Recovery Ventilation integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

LOG = logging.getLogger(__name__)


def load_lunos_codings() -> dict[str, Any]:
    """Load LUNOS controller coding configurations from YAML file."""
    config_path = Path(__file__).parent / 'lunos-codings.yaml'
    try:
        with config_path.open() as file:
            return yaml.safe_load(file) or {}
    except Exception:
        LOG.exception('Failed to load LUNOS codings from %s', config_path)
        return {}


def get_coding_options(coding_config: dict[str, Any]) -> list[str]:
    """Get list of available controller coding options."""
    return list(coding_config.keys())


def get_coding_name(coding_config: dict[str, Any], coding_key: str) -> str:
    """Get human-readable name for a controller coding."""
    coding = coding_config.get(coding_key, {})
    return coding.get('name', coding_key)
