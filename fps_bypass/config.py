# Configuration management.
from __future__ import annotations

import json
import os
from dataclasses import dataclass

CONFIG_VERSION = 1
FPS_CONFIG_DIR = "gfps_bypass"


# NOTE: All future values (after `target_fps`) must have a default value.
@dataclass
class Configuration:
    genshin_path: str
    target_fps: int


def _get_config_path() -> str:
    app_data = os.getenv("APPDATA")

    if not app_data:
        raise RuntimeError("Failed to get APPDATA location.")

    return f"{app_data}\\{FPS_CONFIG_DIR}"


def _ensure_config_dir() -> None:
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        os.mkdir(config_path)


def config_as_json(config: Configuration) -> str:
    data = {
        # Separate the header in case we want to add more fields later.
        "version": CONFIG_VERSION,
        "data": {
            "genshin_path": config.genshin_path,
            "target_fps": config.target_fps,
        },
    }

    return json.dumps(data, indent=4)


def config_from_json(json_str: str) -> Configuration:
    data = json.loads(json_str)

    if data["version"] != CONFIG_VERSION:
        # TODO: When we need to a new config version, we can add a migration
        ...

    return Configuration(
        genshin_path=data["data"]["genshin_path"],
        target_fps=data["data"]["target_fps"],
    )


def write_config(config: Configuration) -> None:
    _ensure_config_dir()

    config_path = _get_config_path()
    with open(f"{config_path}\\config.json", "w") as f:
        f.write(config_as_json(config))


def read_config() -> Configuration | None:
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        return None

    if not os.path.exists(f"{config_path}\\config.json"):
        return None

    with open(f"{config_path}\\config.json") as f:
        return config_from_json(f.read())


def delete_config() -> None:
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        return

    os.remove(f"{config_path}\\config.json")
    os.rmdir(config_path)
