from __future__ import annotations

from pathlib import Path
import subprocess
import sys


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "TokenMonitor"


class StartupError(RuntimeError):
    """Raised when the application cannot update the login startup setting."""


def startup_supported() -> bool:
    return sys.platform == "win32"


def _launcher_command() -> str:
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([str(Path(sys.executable).resolve())])

    interpreter = Path(sys.executable).resolve()
    if interpreter.name.lower() == "python.exe":
        pythonw = interpreter.with_name("pythonw.exe")
        if pythonw.exists():
            interpreter = pythonw

    project_root = Path(__file__).resolve().parents[2]
    entrypoint = project_root / "main.py"
    return subprocess.list2cmdline([str(interpreter), str(entrypoint)])


def sync_launch_at_startup(enabled: bool) -> None:
    if not startup_supported():
        return

    try:
        import winreg

        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, _launcher_command())
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE_NAME)
                except FileNotFoundError:
                    pass
    except OSError as exc:
        raise StartupError(f"无法更新开机启动设置: {exc}") from exc
