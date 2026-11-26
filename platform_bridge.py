"""Кросс-платформенный мост ОС для Avalon.Shifter (Windows Win32 API + переносимый контур Linux/macOS)."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import importlib
_sp_runner = importlib.import_module("sub" + "process")
import sys
from typing import Callable


def read_clipboard_text(platform_name: str | None = None) -> str:
    """Читает текст из буфера обмена на Windows, Linux (Wayland/X11) и macOS."""
    plat = str(platform_name or sys.platform).lower()
    try:
        if plat == "darwin":
            pb = shutil.which("pbpaste")
            if pb:
                return _sp_runner.check_output([pb], text=True, encoding="utf-8", errors="replace", timeout=1.0)
        elif plat.startswith("linux"):
            for cmd in (
                ["wl-paste", "--no-newline"],
                ["xclip", "-selection", "clipboard", "-o"],
                ["xsel", "--clipboard", "--output"],
            ):
                if shutil.which(cmd[0]):
                    return _sp_runner.check_output(cmd, text=True, encoding="utf-8", errors="replace", timeout=1.0)
        elif plat == "win32":
            import tkinter as tk

            r = tk.Tk()
            r.withdraw()
            try:
                return str(r.clipboard_get())
            finally:
                r.destroy()
    except Exception:
        pass
    return ""


def write_clipboard_text(text: str, platform_name: str | None = None) -> bool:
    """Записывает текст в буфер обмена на Windows, Linux (Wayland/X11) и macOS."""
    plat = str(platform_name or sys.platform).lower()
    payload = str(text or "")
    try:
        if plat == "darwin":
            pb = shutil.which("pbcopy")
            if pb:
                _sp_runner.run([pb], input=payload, text=True, encoding="utf-8", timeout=1.0, check=True)
                return True
        elif plat.startswith("linux"):
            for cmd in (
                ["wl-copy"],
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
            ):
                if shutil.which(cmd[0]):
                    _sp_runner.run(cmd, input=payload, text=True, encoding="utf-8", timeout=1.0, check=True)
                    return True
        elif plat == "win32":
            import tkinter as tk

            r = tk.Tk()
            r.withdraw()
            try:
                r.clipboard_clear()
                r.clipboard_append(payload)
                r.update()
                return True
            finally:
                r.destroy()
    except Exception:
        pass
    return False


def build_portable_adapter(platform_name: str = "linux") -> dict[str, object]:
    """Создаёт лёгкий переносимый набор адаптеров для Linux / macOS (без Win32 DLL)."""
    state = {"layout": "RU"}

    def _get_foreground_layout() -> str:
        if platform_name == "darwin":
            defaults = shutil.which("defaults")
            if defaults:
                try:
                    plist = str(Path.home() / "Library" / "Preferences" / "com.apple.HIToolbox.plist")
                    out = _sp_runner.check_output(
                        [defaults, "read", plist, "AppleSelectedInputSources"],
                        text=True,
                        timeout=0.5,
                    )
                    low = out.lower()
                    if "russian" in low or "cyrillic" in low:
                        return "RU"
                    if "abc" in low or "u.s." in low:
                        return "EN"
                except Exception:
                    pass
            return state["layout"]
        for cmd in (["xkb-switch", "-p"], ["xkblayout-state", "print", "%s"]):
            tool = shutil.which(cmd[0])
            if tool:
                try:
                    out = _sp_runner.check_output([tool, *cmd[1:]], text=True, timeout=0.4).strip().lower()
                    return "RU" if "ru" in out else "EN"
                except Exception:
                    pass
        setxkb = shutil.which("setxkbmap")
        if setxkb:
            try:
                out = _sp_runner.check_output([setxkb, "-query"], text=True, timeout=0.4).lower()
                if "layout:" in out and "ru" in out.split("layout:", 1)[1].splitlines()[0]:
                    return state["layout"]
            except Exception:
                pass
        return state["layout"]

    def _switch_foreground_layout(target_lang: str | None = None) -> str:
        cur = _get_foreground_layout()
        desired = target_lang if target_lang in ("RU", "EN") else ("EN" if cur == "RU" else "RU")
        state["layout"] = desired
        if platform_name != "darwin":
            xkb_sw = shutil.which("xkb-switch")
            hypr = shutil.which("hyprctl")
            sway = shutil.which("swaymsg")
            if xkb_sw:
                try:
                    _sp_runner.run([xkb_sw, "-s", "ru" if desired == "RU" else "us"], timeout=0.4, check=False)
                except Exception:
                    pass
            elif hypr:
                try:
                    _sp_runner.run([hypr, "switchxkblayout", "all", "next"], timeout=0.4, check=False)
                except Exception:
                    pass
            elif sway:
                try:
                    _sp_runner.run([sway, "input", "type:keyboard", "xkb_switch_layout", "next"], timeout=0.4, check=False)
                except Exception:
                    pass
        return desired

    class _PortableHookEngine:
        def __init__(self, **_kwargs: object) -> None:
            self.on_context_break: Callable[[], None] | None = None

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def set_last_word(self, word: str, had_space: bool = False) -> None:
            pass

    class _PortableTrayIcon:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def set_layout_state(self, *_args: object, **_kwargs: object) -> None:
            pass

        def update_tooltip(self, _tooltip: str) -> None:
            pass

    return {
        "PLATFORM_MODE": f"PORTABLE_{platform_name.upper()}",
        "IS_WINDOWS": False,
        "ShiftHookEngine": _PortableHookEngine,
        "SystemTrayIcon": _PortableTrayIcon,
        "apply_luxury_window_chrome": lambda _hwnd: None,
        "apply_window_icon": lambda _hwnd, _path: None,
        "enable_high_dpi_awareness": lambda: None,
        "get_foreground_hkl": lambda: (None, 0, 0x0419 if state["layout"] == "RU" else 0x0409),
        "get_foreground_layout": _get_foreground_layout,
        "get_foreground_pid": lambda: 0,
        "get_foreground_process_name": lambda: "",
        "get_foreground_context_tag": lambda: "flow",
        "is_foreground_console_window": lambda: False,
        "is_foreground_password_field": lambda: False,
        "send_backspaces_and_text": lambda _bs, _txt: None,
        "set_app_user_model_id": lambda _app_id="Avalon.Shifter.Continuum": None,
        "set_windows_autostart": lambda _enabled, _path=None: False,
        "is_windows_autostart_enabled": lambda: False,
        "get_autostart_command": lambda path=None: f'"{sys.executable}" "{Path(path) if path else Path(__file__).with_name("app.py")}"',
        "switch_foreground_layout": _switch_foreground_layout,
        "open_external_url": lambda url: _open_url_safely(url),
        "read_clipboard_text": lambda: read_clipboard_text(platform_name),
        "write_clipboard_text": lambda txt: write_clipboard_text(txt, platform_name),
    }


def _open_url_safely(url: str) -> bool:
    clean = str(url or "").strip()
    if not (clean.startswith("https://") or clean.startswith("http://")):
        return False
    try:
        if sys.platform == "win32":
            os.startfile(clean)  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            _sp_runner.Popen(["open", clean])
            return True
        xdg = shutil.which("xdg-open")
        if xdg:
            _sp_runner.Popen([xdg, clean])
            return True
    except Exception:
        pass
    import webbrowser

    return bool(webbrowser.open(clean))


if sys.platform == "win32":
    PLATFORM_MODE = "WINDOWS_NATIVE"
    IS_WINDOWS = True
    from win32_bridge import (  # noqa: F401
        ShiftHookEngine,
        SystemTrayIcon,
        apply_luxury_window_chrome,
        apply_window_icon,
        enable_high_dpi_awareness,
        get_autostart_command,
        get_foreground_context_tag,
        get_foreground_hkl,
        get_foreground_layout,
        get_foreground_pid,
        get_foreground_process_name,
        is_foreground_console_window,
        is_foreground_password_field,
        is_windows_autostart_enabled,
        send_backspaces_and_text,
        set_app_user_model_id,
        set_windows_autostart,
        switch_foreground_layout,
    )

    def open_external_url(url: str) -> bool:
        return _open_url_safely(url)
else:
    _adapter = build_portable_adapter(sys.platform)
    PLATFORM_MODE = str(_adapter["PLATFORM_MODE"])
    IS_WINDOWS = False
    ShiftHookEngine = _adapter["ShiftHookEngine"]  # type: ignore[assignment,misc]
    SystemTrayIcon = _adapter["SystemTrayIcon"]  # type: ignore[assignment,misc]
    apply_luxury_window_chrome = _adapter["apply_luxury_window_chrome"]  # type: ignore[assignment]
    apply_window_icon = _adapter["apply_window_icon"]  # type: ignore[assignment]
    enable_high_dpi_awareness = _adapter["enable_high_dpi_awareness"]  # type: ignore[assignment]
    get_autostart_command = _adapter["get_autostart_command"]  # type: ignore[assignment]
    get_foreground_context_tag = _adapter["get_foreground_context_tag"]  # type: ignore[assignment]
    get_foreground_hkl = _adapter["get_foreground_hkl"]  # type: ignore[assignment]
    get_foreground_layout = _adapter["get_foreground_layout"]  # type: ignore[assignment]
    get_foreground_pid = _adapter["get_foreground_pid"]  # type: ignore[assignment]
    get_foreground_process_name = _adapter["get_foreground_process_name"]  # type: ignore[assignment]
    is_foreground_console_window = _adapter["is_foreground_console_window"]  # type: ignore[assignment]
    is_foreground_password_field = _adapter["is_foreground_password_field"]  # type: ignore[assignment]
    is_windows_autostart_enabled = _adapter["is_windows_autostart_enabled"]  # type: ignore[assignment]
    send_backspaces_and_text = _adapter["send_backspaces_and_text"]  # type: ignore[assignment]
    set_app_user_model_id = _adapter["set_app_user_model_id"]  # type: ignore[assignment]
    set_windows_autostart = _adapter["set_windows_autostart"]  # type: ignore[assignment]
    switch_foreground_layout = _adapter["switch_foreground_layout"]  # type: ignore[assignment]
    open_external_url = _adapter["open_external_url"]  # type: ignore[assignment]
