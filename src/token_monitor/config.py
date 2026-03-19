from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import sys


if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.json"


class ConfigError(RuntimeError):
    """Raised when the config file cannot be loaded."""


@dataclass
class WindowConfig:
    x: int = 40
    y: int = 40
    width: int = 148
    height: int = 148
    alpha: float = 0.98
    always_on_top: bool = True


@dataclass
class AppConfig:
    base_url: str = "https://aixj.vip"
    api_key: str = ""
    organization_id: str = ""
    fallback_budget_usd: float = 100.0
    refresh_interval_seconds: int = 300
    window: WindowConfig = field(default_factory=WindowConfig)


def default_config() -> AppConfig:
    return AppConfig()


def _coerce_window(data: dict) -> WindowConfig:
    return WindowConfig(
        x=int(data.get("x", 40)),
        y=int(data.get("y", 40)),
        width=int(data.get("width", 340)),
        height=int(data.get("height", 220)),
        alpha=float(data.get("alpha", 0.97)),
        always_on_top=bool(data.get("always_on_top", True)),
    )


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        config = default_config()
        save_config(config)
        return config

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config.json 不是合法 JSON: {exc}") from exc

    window = _coerce_window(raw.get("window", {}))
    config = AppConfig(
        base_url=str(raw.get("base_url", "https://aixj.vip")).strip().rstrip("/"),
        api_key=str(raw.get("api_key", "")).strip(),
        organization_id=str(raw.get("organization_id", "")).strip(),
        fallback_budget_usd=float(raw.get("fallback_budget_usd", raw.get("monthly_budget_usd", 100.0))),
        refresh_interval_seconds=max(30, int(raw.get("refresh_interval_seconds", 300))),
        window=window,
    )
    if not config.base_url:
        config.base_url = "https://aixj.vip"
    config.window.width = max(140, config.window.width)
    config.window.height = max(140, config.window.height)
    config.window.alpha = min(1.0, max(0.75, config.window.alpha))
    return config


def save_config(config: AppConfig) -> None:
    payload = asdict(config)
    CONFIG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
