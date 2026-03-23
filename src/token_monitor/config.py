from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any


APP_NAME = "Token悬浮球"


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _config_path() -> Path:
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        home = Path(os.path.expanduser("~"))
        return home / "Library" / "Application Support" / APP_NAME / "config.json"
    return _runtime_root() / "config.json"


PROJECT_ROOT = _runtime_root()
CONFIG_PATH = _config_path()


class ConfigError(RuntimeError):
    """Raised when the config file cannot be loaded."""


@dataclass
class WindowConfig:
    x: int = 40
    y: int = 40
    width: int = 148
    height: int = 148
    settings_width: int = 640
    settings_height: int = 720
    alpha: float = 0.98
    always_on_top: bool = True


@dataclass
class ApiProfile:
    name: str = "主 API"
    base_url: str = "https://aixj.vip"
    api_key: str = ""
    organization_id: str = ""


@dataclass
class AppConfig:
    active_profile_index: int = 0
    profiles: list[ApiProfile] = field(default_factory=lambda: [ApiProfile()])
    fallback_budget_usd: float = 100.0
    refresh_interval_seconds: int = 300
    window: WindowConfig = field(default_factory=WindowConfig)

    @property
    def current_profile(self) -> ApiProfile:
        if not self.profiles:
            self.profiles.append(ApiProfile())
        self.active_profile_index = min(max(0, self.active_profile_index), len(self.profiles) - 1)
        return self.profiles[self.active_profile_index]

    @property
    def base_url(self) -> str:
        return self.current_profile.base_url

    @property
    def api_key(self) -> str:
        return self.current_profile.api_key

    @property
    def organization_id(self) -> str:
        return self.current_profile.organization_id


def _coerce_profile(data: dict[str, Any], *, fallback_name: str, fallback_base_url: str = "") -> ApiProfile:
    base_url = str(data.get("base_url", fallback_base_url)).strip().rstrip("/")
    return ApiProfile(
        name=str(data.get("name", fallback_name)).strip() or fallback_name,
        base_url=base_url,
        api_key=str(data.get("api_key", "")).strip(),
        organization_id=str(data.get("organization_id", "")).strip(),
    )


def _profile_has_content(profile: ApiProfile) -> bool:
    return any((profile.base_url, profile.api_key, profile.organization_id))


def default_config() -> AppConfig:
    return AppConfig()


def _coerce_window(data: dict) -> WindowConfig:
    return WindowConfig(
        x=int(data.get("x", 40)),
        y=int(data.get("y", 40)),
        width=int(data.get("width", 340)),
        height=int(data.get("height", 220)),
        settings_width=int(data.get("settings_width", 640)),
        settings_height=int(data.get("settings_height", 720)),
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
    profiles_raw = raw.get("profiles")
    primary_raw = raw.get("primary_profile")
    secondary_raw = raw.get("secondary_profile")
    legacy_base_url = str(raw.get("base_url", "https://aixj.vip")).strip().rstrip("/")
    legacy_api_key = str(raw.get("api_key", "")).strip()
    legacy_org = str(raw.get("organization_id", "")).strip()

    profiles: list[ApiProfile] = []
    if isinstance(profiles_raw, list):
        for index, item in enumerate(profiles_raw):
            if isinstance(item, dict):
                profiles.append(
                    _coerce_profile(
                        item,
                        fallback_name=f"API {index + 1}",
                        fallback_base_url="https://aixj.vip" if index == 0 else "",
                    )
                )
    else:
        if isinstance(primary_raw, dict):
            profiles.append(_coerce_profile(primary_raw, fallback_name="主 API", fallback_base_url="https://aixj.vip"))
        else:
            profiles.append(
                ApiProfile(
                    name="主 API",
                    base_url=legacy_base_url or "https://aixj.vip",
                    api_key=legacy_api_key,
                    organization_id=legacy_org,
                )
            )

        if isinstance(secondary_raw, dict):
            secondary = _coerce_profile(secondary_raw, fallback_name="备用 API")
            if _profile_has_content(secondary):
                profiles.append(secondary)

    profiles = [profile for profile in profiles if _profile_has_content(profile)]
    if not profiles:
        profiles = [ApiProfile()]

    config = AppConfig(
        active_profile_index=int(raw.get("active_profile_index", 0)),
        profiles=profiles,
        fallback_budget_usd=float(raw.get("fallback_budget_usd", raw.get("monthly_budget_usd", 100.0))),
        refresh_interval_seconds=max(30, int(raw.get("refresh_interval_seconds", 300))),
        window=window,
    )
    if "active_profile" in raw and "active_profile_index" not in raw:
        legacy_active = str(raw.get("active_profile", "primary")).strip()
        if legacy_active == "secondary" and len(config.profiles) > 1:
            config.active_profile_index = 1

    if not config.profiles[0].base_url:
        config.profiles[0].base_url = "https://aixj.vip"
    config.active_profile_index = min(max(0, config.active_profile_index), len(config.profiles) - 1)
    config.window.width = max(140, config.window.width)
    config.window.height = max(140, config.window.height)
    config.window.settings_width = max(520, config.window.settings_width)
    config.window.settings_height = max(620, config.window.settings_height)
    config.window.alpha = min(1.0, max(0.75, config.window.alpha))
    return config


def save_config(config: AppConfig) -> None:
    payload = asdict(config)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
