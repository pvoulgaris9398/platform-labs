"""Config-repository payload validation and cache mapping."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


@dataclass(frozen=True)
class ConfigEntry:
    """One validated cache entry."""

    config_type: str
    config_key: str
    config_value: Any
    source_path: str
    source_commit: str


DIRECTORY_TYPES = {
    "guardrails": "guardrail",
    "dropdowns": "dropdown",
    "quotas": "quota",
    "budgets": "budget",
    "rate_limits": "rate_limit",
    "lifecycle": "lifecycle",
    "security": "security",
}


def map_config_file(path: str, value: Any, commit: str) -> ConfigEntry:
    """Map an allowed config-repository path to a cache namespace."""

    parsed = PurePosixPath(path)
    if len(parsed.parts) != 2 or parsed.parts[0] not in DIRECTORY_TYPES:
        raise ValueError(f"unsupported config path: {path}")
    if parsed.suffix not in {".yaml", ".yml", ".json"}:
        raise ValueError("config files must be YAML or JSON")
    return ConfigEntry(
        config_type=DIRECTORY_TYPES[parsed.parts[0]],
        config_key=parsed.stem,
        config_value=value,
        source_path=path,
        source_commit=commit,
    )
