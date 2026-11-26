"""Avalon.Shifter — интеллектуальный выравниватель потока мысли RU ↔ EN (Continuum • 432 Гц)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tkinter as tk
from tkinter import font as tkfont

from empathic_memory import EmpathicMemoryCrystal
from flow_corpus import SovereignFlowCorpus
from i18n import (
    AUTHOR_FULL_NAME,
    AUTHOR_LINKS,
    PHILOSOPHY_QUOTE_EN,
    PHILOSOPHY_QUOTE_RU,
    normalize_lang,
    tr,
    tr_tip,
)
from icon_gen import (
    BG_CARD_RGB,
    BG_VOID_RGB,
    PHOTONIC_WAVE_FRAMES,
    ensure_app_icon,
    render_emblem_png,
    render_mode_dial_png,
    render_photonic_wave_frame_png,
    render_pill_switch_png,
    render_rounded_button_png,
    render_rounded_card_png,
)
from platform_bridge import (
    PLATFORM_MODE,
    ShiftHookEngine,
    SystemTrayIcon,
    apply_luxury_window_chrome,
    apply_window_icon,
    enable_high_dpi_awareness,
    get_foreground_context_tag,
    get_foreground_hkl,
    get_foreground_layout,
    get_foreground_pid,
    get_foreground_process_name,
    is_foreground_console_window,
    is_foreground_password_field,
    open_external_url,
    read_clipboard_text,
    send_backspaces_and_text,
    set_app_user_model_id,
    set_windows_autostart,
    switch_foreground_layout,
    write_clipboard_text,
)
from shifter_core import (
    AMBIGUOUS_SINGLE_EN_TO_RU,
    AMBIGUOUS_SINGLE_RU_TO_EN,
    _has_cyrillic,
    _has_latin,
    compute_shift_vector,
    convert_word,
    detect_mistyped_direction,
    is_protected_token,
    should_retroactively_fix_prev_token,
    smart_convert_text,
)
from triad_engine import (
    DEFAULT_AVL_PATH,
    AvlModuleAST,
    OneForOneSupervisor,
    ShiftVector,
    ShifterTriadActor,
    evaluate_intent,
    load_avl_file,
)

APP_CONTINUUM = "Continuum • 432 Гц"
APP_VERSION = APP_CONTINUUM
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")

DEFAULT_CONFIG: dict = {
    "auto_switch": True,
    "single_shift": False,
    "double_shift": True,
    "shift_shift_toggle": True,
    "developer_guard": True,
    "fix_caps_lock": True,
    "empathic_learning": True,
    "flow_archive_enabled": False,
    "autostart_windows": True,
    "ui_language": "ru",
    "excluded_processes": [],
}

SAMPLE_SANDBOX_TEXT = "ну что как ты себя теперь чувствуешь avalon &"


def load_config(path: Path | None = None) -> dict:
    """Загружает конфигурацию из JSON, дополняя отсутствующие ключи значениями по умолчанию."""
    target = Path(path) if path else DEFAULT_CONFIG_PATH
    cfg = dict(DEFAULT_CONFIG)
    cfg["excluded_processes"] = list(DEFAULT_CONFIG["excluded_processes"])
    if target.exists():
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, default_val in DEFAULT_CONFIG.items():
                    if key in raw and isinstance(raw[key], type(default_val)):
                        cfg[key] = raw[key]
        except (OSError, json.JSONDecodeError):
            pass
    cfg["ui_language"] = normalize_lang(str(cfg.get("ui_language", "ru")))
    return cfg


def save_config(config: dict, path: Path | None = None) -> Path:
    """Сохраняет конфигурацию в JSON-файл."""
    target = Path(path) if path else DEFAULT_CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


class ShifterController:
    """Управляющий контроллер состояния, контекстной истории, горячих клавиш и Базы Потока."""

    def __init__(
        self,
        config_path: Path | None = None,
        enable_hook: bool = False,
        apply_autostart: bool = False,
        ui_notify: callable | None = None,
        local_double_shift_cb: callable | None = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = load_config(self.config_path)
        self.memory_path = self.config_path.with_name("empathic_memory.json")
        self.empathic_memory = EmpathicMemoryCrystal(self.memory_path)
        self.flow_corpus = SovereignFlowCorpus(self.config_path.with_name("flow_corpus"))
        self.apply_autostart = apply_autostart
        self.converted_count = 0
        self.protected_count = 0
        self.caps_fixed_count = 0
        self.last_event = tr(self.lang, "event_ready")
        self.ui_notify = ui_notify
        self.local_double_shift_cb = local_double_shift_cb
        self._own_pid = os.getpid()
        self._line_history: list[str] = []
        self._last_fg_hwnd: int = 0
        self._retro_armed: bool = False

        avl_res = load_avl_file(DEFAULT_AVL_PATH)
        self.avl_ast: AvlModuleAST | None = avl_res.unwrap() if avl_res.is_ok() else None
        self.supervisor = OneForOneSupervisor(lambda: ShifterTriadActor(self.avl_ast))
        self.last_vector = ShiftVector(0.0, 0.0, 0.0, 0.0)
        self.last_intent = "idle"

        self.hook: ShiftHookEngine | None = None
        if enable_hook:
            self.hook = ShiftHookEngine(
                on_double_shift=self.handle_global_double_shift,
                on_single_shift=self.handle_global_single_shift,
                on_shift_shift_toggle=self.handle_shift_shift_toggle,
                on_word_committed=self.handle_global_word_committed,
            )
            self.hook.on_context_break = self.handle_global_context_break

    @property
    def lang(self) -> str:
        return normalize_lang(str(self.config.get("ui_language", "ru")))

    def start(self) -> None:
        if not self.config_path.exists():
            save_config(self.config, self.config_path)
        if self.apply_autostart:
            try:
                set_windows_autostart(bool(self.config.get("autostart_windows", True)), Path(__file__))
            except OSError:
                pass
        if self.hook:
            self.hook.start()

    def _active_memory(self) -> EmpathicMemoryCrystal | None:
        return self.empathic_memory if self.config.get("empathic_learning", True) else None

    def _is_flow_recording(self) -> bool:
        return bool(self.config.get("flow_archive_enabled", False))

    def stop(self) -> None:
        if self.hook:
            self.hook.stop()
        if self._is_flow_recording():
            try:
                self.flow_corpus.flush_pending()
            except Exception:
                pass
        if hasattr(self, "supervisor"):
            self.supervisor.stop()
        if hasattr(self, "empathic_memory"):
            self.empathic_memory.flush()

    def _notify(self) -> None:
        if self.ui_notify:
            self.ui_notify()

    def _dispatch_triad(
        self,
        token: str,
        direction: str | None,
        vector: ShiftVector,
        trigger: str = "AUTO",
        converted_words: int = 0,
        protected_tokens: int = 0,
        caps_fixed: int = 0,
    ) -> None:
        self.last_vector = vector
        res = self.supervisor.call(
            "process_token",
            {
                "token": token,
                "direction": direction,
                "vector": vector,
                "trigger": trigger,
                "converted_words": converted_words,
                "protected_tokens": protected_tokens,
                "caps_fixed": caps_fixed,
            },
        )
        if res.is_ok():
            reply = res.unwrap()
            self.last_intent = str(reply.get("intent", "idle"))
        else:
            eval_fallback = evaluate_intent(self.avl_ast, token, direction, vector, trigger=trigger)
            if eval_fallback.is_ok():
                self.last_intent = eval_fallback.unwrap()[0]

    def set_ui_language(self, new_lang: str) -> str:
        norm = normalize_lang(new_lang)
        self.config["ui_language"] = norm
        save_config(self.config, self.config_path)
        self.last_event = tr(norm, "event_lang_changed")
        self._notify()
        return norm

    def toggle_option(self, key: str, value: bool | None = None) -> bool:
        if key not in DEFAULT_CONFIG or not isinstance(DEFAULT_CONFIG[key], bool):
            raise KeyError(f"Неизвестный булев параметр конфигурации: {key}")
        new_val = (not self.config[key]) if value is None else bool(value)
        self.config[key] = new_val
        save_config(self.config, self.config_path)
        if key == "autostart_windows" and self.apply_autostart:
            try:
                set_windows_autostart(new_val, Path(__file__))
                self.last_event = tr(self.lang, "event_autostart_on" if new_val else "event_autostart_off")
            except OSError:
                self.last_event = tr(self.lang, "event_autostart_err")
        elif key == "flow_archive_enabled":
            if not new_val:
                self.flow_corpus.flush_pending()
                self.last_event = tr(self.lang, "event_flow_toggled_off")
            else:
                self.last_event = tr(self.lang, "event_flow_toggled_on")
        self._notify()
        return new_val

    def clear_empathic_memory(self) -> int:
        cleared = self.empathic_memory.clear()
        self.last_event = tr(self.lang, "event_empathy_cleared", count=cleared)
        self._notify()
        return cleared

    def export_flow_corpus(self, output_dir: Path | str | None = None, fmt: str = "all") -> dict:
        target = Path(output_dir) if output_dir else (self.config_path.with_name("flow_exports"))
        res = self.flow_corpus.export_for_ai(output_dir=target, fmt=fmt)
        if res.get("success"):
            self.last_event = tr(
                self.lang,
                "event_flow_exported",
                count=res["records_count"],
                dir=Path(res["export_dir"]).name,
            )
        else:
            self.last_event = tr(self.lang, "event_flow_empty")
        self._notify()
        return res

    def clear_flow_corpus(self) -> int:
        removed = self.flow_corpus.clear()
        self.last_event = tr(self.lang, "event_flow_cleared", files=removed)
        self._notify()
        return removed

    def convert_phrase(self, text: str, force_single_fallback: bool = True) -> tuple[str, dict]:
        """Преобразует фразу с учётом текущих настроек, 4D-вектора и акторной телеметрии."""
        dev_guard = bool(self.config.get("developer_guard", True))
        fix_caps = bool(self.config.get("fix_caps_lock", True))

        converted, stats = smart_convert_text(
            text,
            developer_guard=dev_guard,
            fix_caps=fix_caps,
            empathic_memory=self._active_memory(),
        )

        if force_single_fallback and converted == text and text.strip() and len(text.split()) == 1:
            if not (dev_guard and is_protected_token(text.strip())):
                forced = convert_word(text, target_direction=None, fix_caps=fix_caps)
                if forced != text:
                    converted = forced
                    stats["converted_words"] = 1

        tokens = text.split()
        last_tok = tokens[-1] if tokens else text
        has_ru_ctx = any(
            ("а" <= ch.lower() <= "я") or ch in "ёЁ"
            for ch in " ".join(converted.split()[:-1])
        )
        vec = ShiftVector(
            *compute_shift_vector(
                last_tok,
                prev_lang="RU" if has_ru_ctx else None,
                has_ru_context=has_ru_ctx,
            )
        )
        directions = stats.get("directions", [])
        last_dir = directions[-1] if directions else detect_mistyped_direction(last_tok, has_ru_context=has_ru_ctx)
        self._dispatch_triad(
            token=last_tok,
            direction=last_dir,
            vector=vec,
            trigger="DOUBLE_SHIFT" if force_single_fallback else "AUTO",
            converted_words=stats.get("converted_words", 0),
            protected_tokens=stats.get("protected_tokens", 0),
            caps_fixed=stats.get("caps_fixed", 0),
        )

        self.converted_count += stats.get("converted_words", 0)
        self.protected_count += stats.get("protected_tokens", 0)
        self.caps_fixed_count += stats.get("caps_fixed", 0)
        self._notify()
        return converted, stats

    def _is_excluded_foreground(self) -> bool:
        if is_foreground_console_window():
            return True
        excluded = {p.lower() for p in self.config.get("excluded_processes", []) if p}
        if not excluded:
            return False
        proc = get_foreground_process_name()
        return bool(proc and proc in excluded)

    def _sync_window_context(self) -> None:
        hwnd, _, _ = get_foreground_hkl()
        hwnd_val = int(hwnd or 0)
        if hwnd_val != self._last_fg_hwnd:
            self._last_fg_hwnd = hwnd_val
            self._line_history.clear()
            self._retro_armed = False
            if self._is_flow_recording():
                self.flow_corpus.flush_pending()

    def _record_flow_word_if_opted_in(
        self,
        aligned_word: str,
        delim: str,
        retro_prev_fixed: str | None = None,
    ) -> None:
        if not self._is_flow_recording():
            return
        if is_foreground_password_field():
            self.flow_corpus._pending_words.clear()
            return
        if retro_prev_fixed is not None and self.flow_corpus._pending_words:
            self.flow_corpus._pending_words[-1] = retro_prev_fixed
        lang_hint = "ru" if _has_cyrillic(aligned_word) else "en"
        self.flow_corpus.push_word(aligned_word, delim, lang_hint=lang_hint, ctx_tag="flow")

    def handle_global_context_break(self, reason: str = "nav", trailing_word: str = "") -> None:
        """Сбрасывает готовность ретроактивной правки и бережно закрывает фрагмент потока при клике или навигации."""
        self._retro_armed = False
        self._line_history.clear()
        if not self._is_flow_recording():
            return
        if is_foreground_password_field():
            self.flow_corpus.discard_pending()
            return
        if reason == "backspace_prev":
            self.flow_corpus.pop_last_pending_word()
            return
        if reason == "enter":
            if self.flow_corpus.flush_pending(min_words=1):
                self._notify()
            return
        if reason == "mouse":
            if trailing_word and get_foreground_pid() != self._own_pid and not self._is_excluded_foreground():
                lang_hint = "ru" if _has_cyrillic(trailing_word) else "en"
                self.flow_corpus.push_word(
                    trailing_word,
                    "",
                    lang_hint=lang_hint,
                    ctx_tag="flow",
                )
            if self.flow_corpus.flush_pending(min_words=2):
                self._notify()
            return
        if self.flow_corpus.flush_pending(min_words=2):
            self._notify()

    def handle_global_word_committed(self, word: str, delim: str) -> None:
        self._sync_window_context()
        if get_foreground_pid() == self._own_pid:
            return
        if self._is_excluded_foreground():
            return

        if not self.config.get("auto_switch", True):
            self._record_flow_word_if_opted_in(word, delim)
            return

        dev_guard = bool(self.config.get("developer_guard", True))
        fix_caps = bool(self.config.get("fix_caps_lock", True))

        prev_word = self._line_history[-1] if self._line_history else ""
        before_prev = list(self._line_history[:-1]) if self._line_history else []
        can_retro = bool(self._retro_armed and delim == " " and prev_word)

        has_ru_ctx = any(
            ("а" <= ch.lower() <= "я") or ch in "ёЁ"
            for prev_w in self._line_history
            for ch in prev_w
        )
        mem = self._active_memory()
        context_str = " ".join([*self._line_history, word]) if self._line_history else word
        converted_ctx, stats = smart_convert_text(
            context_str,
            developer_guard=dev_guard,
            fix_caps=fix_caps,
            empathic_memory=mem,
        )
        converted_tokens = converted_ctx.split(" ")
        converted = converted_tokens[-1] if converted_tokens else word

        retro_prev_converted: str | None = None
        if can_retro and len(converted_tokens) == len(self._line_history) + 1:
            cand_prev = converted_tokens[-2]
            if should_retroactively_fix_prev_token(prev_word, cand_prev, converted, before_prev):
                retro_prev_converted = cand_prev

        directions = stats.get("directions", [])
        if converted == word and retro_prev_converted is not None:
            if _has_latin(retro_prev_converted) and not _has_cyrillic(retro_prev_converted):
                vec = ShiftVector(*compute_shift_vector(prev_word))
                last_dir = "RU_TO_EN"
            else:
                vec = ShiftVector(*compute_shift_vector(prev_word, has_ru_context=True))
                last_dir = "EN_TO_RU"
        else:
            vec = ShiftVector(
                *compute_shift_vector(
                    word,
                    prev_lang="RU" if has_ru_ctx else None,
                    has_ru_context=has_ru_ctx,
                )
            )
            last_dir = directions[-1] if directions else detect_mistyped_direction(word, has_ru_context=has_ru_ctx)

        if delim == "\n":
            self._line_history.clear()
            self._retro_armed = False
        else:
            if retro_prev_converted is not None and self._line_history:
                self._line_history[-1] = retro_prev_converted
            self._line_history.append(converted)
            if len(self._line_history) > 8:
                self._line_history.pop(0)
            self._retro_armed = (
                delim == " "
                and converted == word
                and retro_prev_converted is None
                and len(word) == 1
                and word.isalpha()
                and (word.lower() in AMBIGUOUS_SINGLE_EN_TO_RU or word in AMBIGUOUS_SINGLE_RU_TO_EN)
            )

        self._record_flow_word_if_opted_in(converted, delim, retro_prev_fixed=retro_prev_converted)

        if converted == word and retro_prev_converted is None:
            is_prot = stats.get("protected_tokens", 0) > 0 and is_protected_token(word)
            self._dispatch_triad(
                token=word,
                direction=None,
                vector=vec,
                trigger="AUTO",
                protected_tokens=1 if is_prot else 0,
            )
            if is_prot:
                self.protected_count += 1
                self.last_event = f"Developer Guard: {word}"
                self._notify()
            elif self._is_flow_recording():
                self._notify()
            return

        fixed_now = (1 if converted != word else 0) + (1 if retro_prev_converted is not None else 0)
        triad_token = f"{prev_word} {word}" if retro_prev_converted is not None else word
        self._dispatch_triad(
            token=triad_token,
            direction=last_dir,
            vector=vec,
            trigger="AUTO",
            converted_words=fixed_now,
            caps_fixed=stats.get("caps_fixed", 0),
        )

        self.converted_count += fixed_now
        self.caps_fixed_count += stats.get("caps_fixed", 0)

        target_lang = None
        if retro_prev_converted is not None and converted == word:
            target_lang = "EN" if (_has_latin(retro_prev_converted) and not _has_cyrillic(retro_prev_converted)) else "RU"
        elif directions:
            target_lang = "RU" if directions[-1] == "EN_TO_RU" else "EN"

        if target_lang:
            switch_foreground_layout(target_lang)

        if retro_prev_converted is not None:
            bs_count = len(prev_word) + 1 + len(word) + len(delim)
            send_text = f"{retro_prev_converted} {converted}{delim}"
            self.last_event = f"{prev_word} {word} → {retro_prev_converted} {converted}"
        else:
            bs_count = len(word) + len(delim)
            send_text = converted + delim
            self.last_event = f"{word} → {converted}"

        if mem is not None and converted != word:
            mem.record_auto_conversion(word, converted, last_dir)

        send_backspaces_and_text(bs_count, send_text)
        if self.hook:
            self.hook.set_last_word(converted, had_space=(delim == " "))

        self._notify()

    def handle_global_double_shift(self, word: str, had_space: bool) -> None:
        if not self.config.get("double_shift", True):
            return
        if get_foreground_pid() == self._own_pid:
            if self.local_double_shift_cb:
                self.local_double_shift_cb()
            return
        if not word:
            return

        fix_caps = bool(self.config.get("fix_caps_lock", True))
        if word == "&":
            converted = "?"
            stats = {"converted_words": 1}
        else:
            converted, stats = smart_convert_text(
                word,
                developer_guard=False,
                fix_caps=fix_caps,
            )
            if converted == word:
                converted = convert_word(word, target_direction=None, fix_caps=fix_caps)

        vec = ShiftVector(*compute_shift_vector(word))
        self._dispatch_triad(
            token=word,
            direction=None,
            vector=vec,
            trigger="DOUBLE_SHIFT",
            converted_words=max(1, stats.get("converted_words", 0)) if converted != word else 0,
        )

        if converted == word:
            return

        bs_count = len(word) + (1 if had_space else 0)
        suffix = " " if had_space else ""
        target_lang = switch_foreground_layout(None)
        send_backspaces_and_text(bs_count, converted + suffix)
        if self.hook:
            self.hook.set_last_word(converted, had_space=had_space)

        if self._line_history:
            self._line_history[-1] = converted
        if self._is_flow_recording() and self.flow_corpus._pending_words and not is_foreground_password_field():
            self.flow_corpus._pending_words[-1] = converted

        self.converted_count += max(1, stats.get("converted_words", 0))
        learn_note = ""
        mem = self._active_memory()
        if mem is not None and word != "&":
            dirs = stats.get("directions") or []
            if dirs:
                learned_dir = dirs[-1]
            elif _has_cyrillic(converted) and not _has_cyrillic(word):
                learned_dir = "EN_TO_RU"
            elif _has_latin(converted) and not _has_latin(word):
                learned_dir = "RU_TO_EN"
            else:
                learned_dir = "EN_TO_RU" if target_lang == "RU" else "RU_TO_EN"
            outcome = mem.learn_from_manual_shift(word, converted, learned_dir)
            if outcome == "LEARNED_DIRECTION":
                learn_note = " • память запомнила"
            elif outcome == "LEARNED_KEEP_ROLLBACK":
                learn_note = " • откат учтён"
        self.last_event = f"Double Shift ({target_lang}{learn_note}): {word} → {converted}"
        self._notify()

    def handle_global_single_shift(self) -> None:
        if not self.config.get("single_shift", False):
            return
        new_lang = switch_foreground_layout(None)
        self.last_event = tr(self.lang, "event_layout_switched", lang=new_lang)
        self._notify()

    def handle_shift_shift_toggle(self) -> None:
        if not self.config.get("shift_shift_toggle", True):
            return
        state = self.toggle_option("auto_switch")
        label = "ВКЛ" if state else "ПАУЗА"
        self.last_event = f"Shift+Shift: {label}"
        self._notify()


def resolve_tech_fonts(root: tk.Misc) -> dict[str, str]:
    """Подбирает системный геометрический технологичный шрифт (Bahnschrift / Segoe UI Variable / Inter)."""
    try:
        available = set(tkfont.families(root))
    except Exception:
        available = set()

    def _pick(candidates: tuple[str, ...], fallback: str) -> str:
        for name in candidates:
            if name in available:
                return name
        return fallback

    return {
        "display": _pick(
            (
                "Bahnschrift SemiBold",
                "Bahnschrift",
                "Segoe UI Variable Display Semib",
                "Segoe UI Variable Display",
                "Inter",
                "SF Pro Display",
                "Segoe UI Semibold",
                "Segoe UI",
            ),
            "Segoe UI",
        ),
        "heading": _pick(
            (
                "Bahnschrift",
                "Segoe UI Variable Display",
                "Inter",
                "SF Pro Display",
                "Segoe UI Semibold",
                "Segoe UI",
            ),
            "Segoe UI",
        ),
        "body": _pick(
            (
                "Bahnschrift SemiLight",
                "Bahnschrift",
                "Segoe UI Variable Text",
                "Inter",
                "SF Pro Text",
                "Ubuntu",
                "Segoe UI",
            ),
            "Segoe UI",
        ),
        "mono": _pick(
            (
                "Cascadia Mono",
                "JetBrains Mono",
                "Consolas",
                "SF Mono",
                "DejaVu Sans Mono",
                "Courier New",
            ),
            "Consolas",
        ),
    }


def _spawn_quantum_gold_ripple(
    canvas: tk.Canvas,
    x: int,
    y: int,
    *,
    primary: bool = False,
    radius: int = 9,
    shape: str = "rounded_box",
    raise_item: int | None = None,
    tag_prefix: str = "ripple",
) -> None:
    """Гладкий субпиксельный фотонный золотой импульс (без пиксельных кругов)."""
    try:
        w = max(8, int(float(canvas.cget("width"))))
        h = max(8, int(float(canvas.cget("height"))))
        top_root = canvas.winfo_toplevel()
    except tk.TclError:
        return

    cache = getattr(top_root, "_avalon_wave_cache", None)
    if cache is None:
        cache = {}
        try:
            setattr(top_root, "_avalon_wave_cache", cache)
        except Exception:
            pass

    if w >= 72:
        raw_nx = max(0.0, min(1.0, float(x) / float(w)))
        origin_nx = min((0.22, 0.50, 0.78), key=lambda c: abs(c - raw_nx))
    else:
        origin_nx = 0.50
    origin_ny = 0.50

    key = (w, h, origin_nx, origin_ny, bool(primary), int(radius), str(shape))
    frames = cache.get(key)
    if frames is None:
        frames = [None] * PHOTONIC_WAVE_FRAMES
        cache[key] = frames

    tag = f"{tag_prefix}_{id(canvas)}"
    try:
        canvas.delete(tag)
    except tk.TclError:
        return

    state: dict[str, int | None] = {"item_id": None}

    def _frame(idx: int) -> None:
        try:
            if idx >= PHOTONIC_WAVE_FRAMES:
                canvas.delete(tag)
                return
            img = frames[idx]
            if img is None:
                png_bytes = render_photonic_wave_frame_png(
                    w,
                    h,
                    float(idx + 1) / float(PHOTONIC_WAVE_FRAMES),
                    origin_nx=origin_nx,
                    origin_ny=origin_ny,
                    primary=primary,
                    radius=radius,
                    shape=shape,
                )
                img = tk.PhotoImage(master=canvas, data=png_bytes)
                frames[idx] = img

            if state["item_id"] is None:
                state["item_id"] = canvas.create_image(0, 0, anchor="nw", image=img, tags=(tag,))
            else:
                canvas.itemconfigure(state["item_id"], image=img)
            canvas.tag_raise(tag)
            if raise_item is not None:
                canvas.tag_raise(raise_item)
            if bool(canvas.winfo_exists()):
                canvas.after(17, lambda nxt=idx + 1: _frame(nxt))
        except tk.TclError:
            pass

    _frame(0)


class AvalonTooltip:
    """Стилизованная всплывающая подсказка: бархатистый шиферный фон + приглушённый золотой кант."""

    BG_OUTER = "#12151A"
    BORDER_GOLD = "#B59A6E"
    BG_INNER = "#262B35"
    FG_TITLE = "#DEC393"
    FG_BODY = "#DDDAD3"

    def __init__(
        self,
        widget: tk.Widget,
        text_provider: callable,
        delay_ms: int = 280,
        font_title: tuple[str, int] | tuple[str, int, str] = ("Bahnschrift", 8),
        font_body: tuple[str, int] | tuple[str, int, str] = ("Bahnschrift SemiLight", 8),
    ) -> None:
        self.widget = widget
        self.text_provider = text_provider
        self.delay_ms = delay_ms
        self.font_title = font_title
        self.font_body = font_body
        self._after_id: str | None = None
        self._win: tk.Toplevel | None = None
        self.bind_widget(widget)

    def bind_widget(self, w: tk.Widget) -> None:
        w.bind("<Enter>", self._on_enter, add="+")
        w.bind("<Leave>", self._on_leave, add="+")
        w.bind("<ButtonPress>", self._on_leave, add="+")
        w.bind("<Destroy>", self._on_leave, add="+")

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay_ms, self.show)
        except tk.TclError:
            pass

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._cancel()
        self.hide()

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def show(self) -> None:
        if self._win is not None:
            return
        try:
            if not self.widget.winfo_viewable():
                return
            title, body = self.text_provider()
        except Exception:
            return
        if not title and not body:
            return

        win = tk.Toplevel(self.widget)
        win.withdraw()
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        win.configure(bg=self.BG_OUTER)

        gold_box = tk.Frame(win, bg=self.BORDER_GOLD, padx=1, pady=1)
        gold_box.pack(padx=1, pady=1)
        inner = tk.Frame(gold_box, bg=self.BG_INNER, padx=10, pady=7)
        inner.pack()

        if title:
            tk.Label(
                inner,
                text=title,
                font=self.font_title,
                bg=self.BG_INNER,
                fg=self.FG_TITLE,
                justify="left",
                anchor="w",
            ).pack(fill="x")
        if body:
            tk.Label(
                inner,
                text=body,
                font=self.font_body,
                bg=self.BG_INNER,
                fg=self.FG_BODY,
                justify="left",
                anchor="w",
                wraplength=360,
            ).pack(fill="x", pady=(2, 0) if title else 0)

        win.update_idletasks()
        tw = win.winfo_reqwidth()
        th = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()

        wx = self.widget.winfo_rootx() + 12
        wy = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        if wx + tw > sw - 12:
            wx = max(8, sw - tw - 12)
        if wy + th > sh - 12:
            wy = max(8, self.widget.winfo_rooty() - th - 6)

        win.geometry(f"{tw}x{th}+{wx}+{wy}")
        win.deiconify()
        self._win = win

    def hide(self) -> None:
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
            self._win = None


class LuxuryButton(tk.Canvas):
    """Сглаженная кнопка с тактильным откликом нажатия и фотонным золотым импульсом Web8."""

    def __init__(
        self,
        parent: tk.Widget,
        width: int,
        height: int,
        text: str,
        command: callable,
        primary: bool = False,
        bg_hex: str = "#21252D",
        bg_rgb: tuple[int, int, int] = BG_CARD_RGB,
        text_fg: str = "#DCD9D2",
        font: tuple[str, int, str] | tuple[str, int] = ("Bahnschrift", 9),
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=bg_hex,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._width = width
        self._height = height
        self._primary = primary
        self._base_y = height // 2 - 1
        self._command = command
        self._inside = False
        self._pressed = False
        self._img_normal = tk.PhotoImage(
            master=self,
            data=render_rounded_button_png(width, height, primary=primary, hover=False, pressed=False, bg_rgb=bg_rgb),
        )
        self._img_hover = tk.PhotoImage(
            master=self,
            data=render_rounded_button_png(width, height, primary=primary, hover=True, pressed=False, bg_rgb=bg_rgb),
        )
        self._img_pressed = tk.PhotoImage(
            master=self,
            data=render_rounded_button_png(width, height, primary=primary, hover=False, pressed=True, bg_rgb=bg_rgb),
        )
        self._bg_item = self.create_image(0, 0, anchor="nw", image=self._img_normal)
        self._txt_item = self.create_text(
            width // 2,
            self._base_y,
            text=text,
            fill=text_fg,
            font=font,
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_text(self, text: str) -> None:
        self.itemconfigure(self._txt_item, text=text)

    def _on_enter(self, _event: tk.Event) -> None:
        self._inside = True
        if not self._pressed:
            self.itemconfigure(self._bg_item, image=self._img_hover)

    def _on_leave(self, _event: tk.Event) -> None:
        self._inside = False
        self._pressed = False
        self.itemconfigure(self._bg_item, image=self._img_normal)
        self.coords(self._txt_item, self._width // 2, self._base_y)

    def _on_press(self, event: tk.Event) -> None:
        self._pressed = True
        self.itemconfigure(self._bg_item, image=self._img_pressed)
        self.coords(self._txt_item, self._width // 2, self._base_y + 1)
        _spawn_quantum_gold_ripple(
            self,
            int(getattr(event, "x", self._width // 2)),
            int(getattr(event, "y", self._height // 2)),
            primary=self._primary,
            radius=9,
            shape="rounded_box",
            raise_item=self._txt_item,
            tag_prefix="btn_rip",
        )
        self.tag_raise(self._txt_item)

    def _on_release(self, _event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self.coords(self._txt_item, self._width // 2, self._base_y)
        self.itemconfigure(self._bg_item, image=self._img_hover if self._inside else self._img_normal)
        if was_pressed and self._inside and self._command:
            self._command()


class AvalonShifterApp:
    """Бархатисто-обсидиановый NF UI интерфейс Avalon.Shifter Continuum (432 Гц • RU/EN • База Потока)."""

    BG_VOID = "#1A1D23"
    BG_CARD = "#21252D"
    BG_ELEVATED = "#282D37"
    BG_SANDBOX = "#1C2027"
    BORDER_SUBTLE = "#2E333E"
    GOLD = "#D2B684"
    GOLD_SOFT = "#B59A6E"
    TEXT_PRIMARY = "#DCD9D2"
    TEXT_MUTED = "#A3A8B4"
    TEXT_QUIET = "#7C8290"

    def __init__(
        self,
        root: tk.Tk,
        config_path: Path | None = None,
        icon_path: Path | None = None,
        enable_tray: bool = True,
        apply_autostart: bool = True,
        start_in_tray: bool = False,
    ) -> None:
        self.root = root
        self.root.withdraw()
        self.icon_path = ensure_app_icon(icon_path)
        self.enable_tray = enable_tray
        self._closed = False
        self._hidden_to_tray = False
        self._suppress_unmap = False
        self._last_layout = ""
        self._after_ids: set[str] = set()
        self._img_refs: list[tk.PhotoImage] = []
        self._card_records: list[tuple[tk.Canvas, tk.Frame]] = []
        self._switch_rows: list[tk.Frame] = []
        self._about_dlg: tk.Toplevel | None = None
        self._about_refs: dict[str, tk.Widget] = {}
        self._tooltips: list[AvalonTooltip] = []
        self._badge_animating = False
        self._fonts = resolve_tech_fonts(self.root)

        try:
            tk_scale = float(self.root.tk.call("tk", "scaling"))
            self._dpi = max(1.0, tk_scale / 1.3333333333333333)
        except Exception:
            self._dpi = 1.0

        win_w = self._px(644)
        win_h = self._px(796)

        self.root.title("Avalon.Shifter")
        self._center_window(win_w, win_h)
        self.root.minsize(win_w, win_h)
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_VOID)

        self.controller = ShifterController(
            config_path=config_path,
            enable_hook=True,
            apply_autostart=apply_autostart,
            ui_notify=self._schedule_refresh,
            local_double_shift_cb=self._schedule_local_double_shift,
        )

        self._orbital_widgets: dict[str, dict] = {}
        self._switch_widgets: dict[str, dict] = {}
        self._dial_images: dict[str, dict[str, tk.PhotoImage]] = {}
        self.tray: SystemTrayIcon | None = None

        self._build_ui()
        self._refresh_ui()
        self.controller.start()

        if self.enable_tray:
            init_layout = get_foreground_layout()
            self._last_layout = init_layout
            self.tray = SystemTrayIcon(
                icon_path=self.icon_path,
                tooltip=self._build_tray_tooltip(init_layout),
                on_restore=lambda: self._dispatch_ui(self.restore_from_tray),
                on_toggle_auto=lambda: self._dispatch_ui(lambda: self.controller.toggle_option("auto_switch")),
                on_switch_layout=lambda: self._dispatch_ui(self._on_toggle_os_layout),
                on_exit=lambda: self._dispatch_ui(self._on_close),
                initial_layout=init_layout,
                initial_auto=bool(self.controller.config.get("auto_switch", True)),
                initial_flow=bool(self.controller.config.get("flow_archive_enabled", False)),
                on_toggle_flow=lambda: self._dispatch_ui(lambda: self.controller.toggle_option("flow_archive_enabled")),
                on_export_flow=lambda: self._dispatch_ui(self._on_export_flow),
                on_open_author=lambda: self._dispatch_ui(lambda: self._open_info_dialog_from_tray("author")),
                get_state_cb=self._get_tray_state_snapshot,
            )
            self.tray.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Unmap>", self._on_unmap)
        self.root.bind("<Destroy>", self._on_root_destroy)
        self._schedule_after(180, self._poll_layout)

        if start_in_tray and self.enable_tray:
            self._hidden_to_tray = True
            self.root.withdraw()
            self._apply_ico()
        else:
            self.root.update_idletasks()
            self._apply_ico()
            self.root.deiconify()
            self.root.lift()
            self._apply_ico()

    def _px(self, logical: int) -> int:
        return max(1, int(round(logical * self._dpi)))

    def _keep_img(self, png_bytes: bytes) -> tk.PhotoImage:
        img = tk.PhotoImage(master=self.root, data=png_bytes)
        self._img_refs.append(img)
        return img

    def _apply_ico(self, hwnd_override: int | None = None) -> None:
        if hwnd_override is None:
            try:
                self.root.iconbitmap(str(self.icon_path))
            except tk.TclError:
                pass
            self.root.update_idletasks()
            hwnd = self.root.winfo_id()
        else:
            hwnd = hwnd_override
        apply_window_icon(hwnd, self.icon_path)
        apply_luxury_window_chrome(hwnd)

    def _center_window(self, width: int, height: int) -> None:
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _center_child(self, child: tk.Toplevel, width: int, height: int) -> None:
        self.root.update_idletasks()
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        rw = max(self.root.winfo_width(), width)
        rh = max(self.root.winfo_height(), height)
        sw = child.winfo_screenwidth()
        sh = child.winfo_screenheight()
        x = max(0, min(sw - width, rx + (rw - width) // 2))
        y = max(0, min(sh - height, ry + (rh - height) // 2))
        child.geometry(f"{width}x{height}+{x}+{y}")

    def _begin_card(
        self,
        parent: tk.Widget,
        width: int,
        pady: tuple[int, int] = (0, 10),
    ) -> tuple[tk.Canvas, tk.Frame]:
        canvas = tk.Canvas(
            parent,
            width=width,
            height=self._px(100),
            bg=self.BG_VOID,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(pady=pady)

        pad_x = self._px(18)
        pad_y = self._px(12)
        inner = tk.Frame(canvas, bg=self.BG_CARD, width=width - pad_x * 2)
        canvas.create_window(
            pad_x,
            pad_y,
            anchor="nw",
            window=inner,
            width=width - pad_x * 2,
        )
        self._card_records.append((canvas, inner))
        return canvas, inner

    def _finalize_card(
        self,
        canvas: tk.Canvas,
        inner: tk.Frame,
        width: int,
        min_height: int = 0,
        gold_tint: bool = False,
    ) -> None:
        canvas.update_idletasks()
        pad_y = self._px(12)
        req_h = inner.winfo_reqheight()
        card_h = max(min_height, req_h + pad_y * 2 + self._px(6))
        canvas.configure(width=width, height=card_h)
        for item_id in canvas.find_all():
            if canvas.type(item_id) == "window":
                canvas.itemconfigure(item_id, height=card_h - pad_y * 2)

        card_img = self._keep_img(
            render_rounded_card_png(
                width,
                card_h,
                radius=self._px(14),
                gold_tint=gold_tint,
                bg_rgb=BG_VOID_RGB,
            )
        )
        bg_id = canvas.create_image(0, 0, anchor="nw", image=card_img)
        canvas.tag_lower(bg_id)

    def _build_tray_tooltip(self, layout: str) -> str:
        lang = self.controller.lang
        auto_on = bool(self.controller.config.get("auto_switch", True))
        flow_on = bool(self.controller.config.get("flow_archive_enabled", False))
        auto_txt = ("Вкл" if auto_on else "Пауза") if lang == "ru" else ("Active" if auto_on else "Paused")
        flow_txt = ("Запись" if flow_on else "Выкл") if lang == "ru" else ("On" if flow_on else "Off")
        return tr(lang, "tray_tip", layout=layout, auto_state=auto_txt, flow_state=flow_txt)

    def _get_tray_state_snapshot(self) -> dict:
        return {
            "lang": self.controller.lang,
            "layout": get_foreground_layout(),
            "auto_switch": bool(self.controller.config.get("auto_switch", True)),
            "flow_archive_enabled": bool(self.controller.config.get("flow_archive_enabled", False)),
        }

    def _build_ui(self) -> None:
        f_title = tkfont.Font(family=self._fonts["display"], size=15)
        f_sub = tkfont.Font(family=self._fonts["body"], size=9)
        f_section = tkfont.Font(family=self._fonts["heading"], size=9)
        f_body = tkfont.Font(family=self._fonts["body"], size=9)
        f_mono = tkfont.Font(family=self._fonts["mono"], size=10)
        f_small = tkfont.Font(family=self._fonts["body"], size=8)

        card_w = self._px(600)
        lang = self.controller.lang

        # 1. Лаконичная верхняя шапка
        header = tk.Frame(self.root, bg=self.BG_VOID)
        header.pack(fill="x", side="top")

        header_inner = tk.Frame(header, bg=self.BG_VOID, padx=self._px(22), pady=self._px(12))
        header_inner.pack(fill="both", expand=True)

        emblem_img = self._keep_img(render_emblem_png(size=self._px(44), bg_rgb=BG_VOID_RGB))
        tk.Label(header_inner, image=emblem_img, bg=self.BG_VOID, bd=0).pack(side="left")

        title_col = tk.Frame(header_inner, bg=self.BG_VOID)
        title_col.pack(side="left", padx=(self._px(12), 0))

        tk.Label(
            title_col,
            text="Avalon.Shifter",
            font=f_title,
            bg=self.BG_VOID,
            fg=self.TEXT_PRIMARY,
        ).pack(anchor="w")

        self.lbl_subtitle = tk.Label(
            title_col,
            text=tr(lang, "subtitle"),
            font=f_sub,
            bg=self.BG_VOID,
            fg=self.TEXT_MUTED,
        )
        self.lbl_subtitle.pack(anchor="w", pady=(self._px(1), 0))

        right_col = tk.Frame(header_inner, bg=self.BG_VOID)
        right_col.pack(side="right")

        # Кнопка языка интерфейса (РУС / ENG) с тактильным откликом
        lang_w = self._px(48)
        btn_h = self._px(30)
        lang_canvas = tk.Canvas(
            right_col,
            width=lang_w,
            height=btn_h,
            bg=self.BG_VOID,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        lang_canvas.pack(side="left", padx=(0, self._px(6)))
        self._lang_img_idle = self._keep_img(
            render_rounded_button_png(lang_w, btn_h, primary=False, hover=False, bg_rgb=BG_VOID_RGB)
        )
        self._lang_img_hover = self._keep_img(
            render_rounded_button_png(lang_w, btn_h, primary=False, hover=True, bg_rgb=BG_VOID_RGB)
        )
        self._lang_img_pressed = self._keep_img(
            render_rounded_button_png(lang_w, btn_h, primary=False, pressed=True, bg_rgb=BG_VOID_RGB)
        )
        self._lang_bg_item = lang_canvas.create_image(0, 0, anchor="nw", image=self._lang_img_idle)
        self._lang_text_id = lang_canvas.create_text(
            lang_w // 2,
            btn_h // 2 - 1,
            text="РУС" if lang == "ru" else "ENG",
            fill=self.TEXT_PRIMARY,
            font=(self._fonts["heading"], 8),
        )
        lang_canvas.bind("<Enter>", lambda _e: lang_canvas.itemconfigure(self._lang_bg_item, image=self._lang_img_hover))
        lang_canvas.bind("<Leave>", lambda _e: lang_canvas.itemconfigure(self._lang_bg_item, image=self._lang_img_idle))
        lang_canvas.bind("<ButtonPress-1>", lambda e: self._on_header_pill_press(lang_canvas, self._lang_bg_item, self._lang_img_pressed, e, raise_item=self._lang_text_id))
        lang_canvas.bind("<ButtonRelease-1>", lambda _e: self._on_header_pill_release(lang_canvas, self._lang_bg_item, self._lang_img_hover, self._on_toggle_ui_lang))
        self.btn_lang_badge = lang_canvas
        self._attach_tooltip(lang_canvas, "lang_toggle")

        # Индикатор текущей раскладки ОС с фотонной телепортацией
        badge_w = self._px(54)
        badge_canvas = tk.Canvas(
            right_col,
            width=badge_w,
            height=btn_h,
            bg=self.BG_VOID,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        badge_canvas.pack(side="left", padx=(0, self._px(6)))
        self._badge_img_idle = self._keep_img(
            render_rounded_button_png(badge_w, btn_h, primary=False, hover=False, bg_rgb=BG_VOID_RGB)
        )
        self._badge_img_hover = self._keep_img(
            render_rounded_button_png(badge_w, btn_h, primary=False, hover=True, bg_rgb=BG_VOID_RGB)
        )
        self._badge_img_pressed = self._keep_img(
            render_rounded_button_png(badge_w, btn_h, primary=False, pressed=True, bg_rgb=BG_VOID_RGB)
        )
        self._badge_bg_item = badge_canvas.create_image(0, 0, anchor="nw", image=self._badge_img_idle)
        self._badge_beam_item = badge_canvas.create_line(
            6, btn_h // 2, badge_w - 6, btn_h // 2,
            fill="#DEC393", width=2, state="hidden",
        )
        self._badge_text_id = badge_canvas.create_text(
            badge_w // 2,
            btn_h // 2 - 1,
            text="RU",
            fill=self.GOLD,
            font=(self._fonts["heading"], 9),
        )
        badge_canvas.bind("<Enter>", lambda _e: badge_canvas.itemconfigure(self._badge_bg_item, image=self._badge_img_hover))
        badge_canvas.bind("<Leave>", lambda _e: badge_canvas.itemconfigure(self._badge_bg_item, image=self._badge_img_idle))
        badge_canvas.bind("<ButtonPress-1>", lambda e: self._on_header_pill_press(badge_canvas, self._badge_bg_item, self._badge_img_pressed, e, raise_item=self._badge_text_id))
        badge_canvas.bind("<ButtonRelease-1>", lambda _e: self._on_header_pill_release(badge_canvas, self._badge_bg_item, self._badge_img_hover, self._on_toggle_os_layout))
        self.lbl_layout_badge = badge_canvas
        self._attach_tooltip(badge_canvas, "layout_badge")

        self.btn_tray = LuxuryButton(
            right_col,
            width=self._px(78),
            height=btn_h,
            text=tr(lang, "btn_tray"),
            command=self.hide_to_tray,
            primary=False,
            bg_hex=self.BG_VOID,
            bg_rgb=BG_VOID_RGB,
            text_fg=self.TEXT_PRIMARY,
            font=(self._fonts["body"], 9),
        )
        self.btn_tray.pack(side="left")
        self._attach_tooltip(self.btn_tray, "btn_tray")

        divider_wrap = tk.Frame(self.root, bg=self.BG_VOID, padx=self._px(22))
        divider_wrap.pack(fill="x")
        tk.Frame(divider_wrap, bg="#34302B", height=1).pack(fill="x")

        body = tk.Frame(self.root, bg=self.BG_VOID, padx=self._px(22), pady=self._px(8))
        body.pack(fill="both", expand=True)

        # 2. Карточка 3 ключевых режимов
        dial_canvas, dial_card = self._begin_card(body, card_w, pady=(0, self._px(9)))
        for col_idx in (0, 2, 4):
            dial_card.columnconfigure(col_idx, weight=1, uniform="modes")

        dial_sz = self._px(52)
        self._dial_images = {
            key: {
                "active": self._keep_img(
                    render_mode_dial_png(True, size=dial_sz, bg_rgb=BG_CARD_RGB, kind=key)
                ),
                "idle": self._keep_img(
                    render_mode_dial_png(False, size=dial_sz, bg_rgb=BG_CARD_RGB, kind=key)
                ),
            }
            for key in ("auto_switch", "single_shift", "developer_guard")
        }
        self._pill_on_img = self._keep_img(
            render_pill_switch_png(True, width=self._px(46), height=self._px(24), bg_rgb=BG_CARD_RGB)
        )
        self._pill_off_img = self._keep_img(
            render_pill_switch_png(False, width=self._px(46), height=self._px(24), bg_rgb=BG_CARD_RGB)
        )

        self._make_orbital_module(dial_card, 0, "auto_switch", "dial_auto")
        tk.Frame(dial_card, bg="#2B303A", width=1).grid(row=0, column=1, sticky="ns", pady=self._px(6))
        self._make_orbital_module(dial_card, 2, "single_shift", "dial_single")
        tk.Frame(dial_card, bg="#2B303A", width=1).grid(row=0, column=3, sticky="ns", pady=self._px(6))
        self._make_orbital_module(dial_card, 4, "developer_guard", "dial_dev")
        self._finalize_card(dial_canvas, dial_card, card_w, min_height=self._px(126), gold_tint=True)

        # 3. Карточка параметров и опциональной Базы Потока для ИИ
        sw_canvas, switches_card = self._begin_card(body, card_w, pady=(0, self._px(9)))
        self.lbl_settings_hdr = tk.Label(
            switches_card,
            text=tr(lang, "sec_settings"),
            font=f_section,
            bg=self.BG_CARD,
            fg=self.GOLD,
            anchor="w",
        )
        self.lbl_settings_hdr.pack(fill="x", pady=(0, self._px(4)))

        self._add_switch_row(switches_card, "double_shift", "sw_double_shift", f_body)
        self._add_switch_row(switches_card, "single_shift", "sw_single_shift", f_body)
        self._add_switch_row(switches_card, "shift_shift_toggle", "sw_shift_toggle", f_body)
        self._add_switch_row(switches_card, "fix_caps_lock", "sw_caps", f_body)
        self._add_switch_row(switches_card, "empathic_learning", "sw_empathy", f_body)
        self._add_switch_row(switches_card, "flow_archive_enabled", "sw_flow_archive", f_body)
        self._add_switch_row(switches_card, "autostart_windows", "sw_autostart", f_body)

        tk.Frame(switches_card, bg="#2E333E", height=1).pack(fill="x", pady=(self._px(6), self._px(6)))

        # СНАЧАЛА правые кнопки, ЗАТЕМ левый текст — нулевой шанс перекрытия!
        flow_bar = tk.Frame(switches_card, bg=self.BG_CARD)
        flow_bar.pack(fill="x")

        self.btn_flow_export = LuxuryButton(
            flow_bar,
            width=self._px(122),
            height=self._px(26),
            text=tr(lang, "btn_export_ai"),
            command=self._on_export_flow,
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.GOLD,
            font=(self._fonts["heading"], 8),
        )
        self.btn_flow_export.pack(side="right", padx=(self._px(6), 0))
        self._attach_tooltip(self.btn_flow_export, "btn_export_ai")

        self.btn_flow_clear = LuxuryButton(
            flow_bar,
            width=self._px(88),
            height=self._px(26),
            text=tr(lang, "btn_clear_flow"),
            command=self._on_clear_flow,
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.TEXT_MUTED,
            font=(self._fonts["body"], 8),
        )
        self.btn_flow_clear.pack(side="right")
        self._attach_tooltip(self.btn_flow_clear, "btn_clear_flow")

        self.lbl_flow_summary = tk.Label(
            flow_bar,
            text=tr(lang, "flow_status_off"),
            font=f_small,
            bg=self.BG_CARD,
            fg=self.TEXT_MUTED,
            anchor="w",
        )
        self.lbl_flow_summary.pack(side="left", fill="x", expand=True, padx=(0, self._px(8)))
        self._attach_tooltip(self.lbl_flow_summary, "flow_bar")

        self._finalize_card(sw_canvas, switches_card, card_w, min_height=self._px(286), gold_tint=False)

        # 4. Карточка проверки выравнивания
        sb_canvas, sandbox_card = self._begin_card(body, card_w, pady=(0, self._px(2)))

        top_sb = tk.Frame(sandbox_card, bg=self.BG_CARD)
        top_sb.pack(fill="x", pady=(0, self._px(5)))
        self.lbl_sandbox_hdr = tk.Label(
            top_sb,
            text=tr(lang, "sec_sandbox"),
            font=f_section,
            bg=self.BG_CARD,
            fg=self.TEXT_PRIMARY,
        )
        self.lbl_sandbox_hdr.pack(side="left")

        self.lbl_sandbox_hint = tk.Label(
            top_sb,
            text=tr(lang, "sandbox_hint"),
            font=f_small,
            bg=self.BG_CARD,
            fg=self.TEXT_QUIET,
        )
        self.lbl_sandbox_hint.pack(side="right")

        self.sandbox_text = tk.Text(
            sandbox_card,
            width=48,
            height=3,
            font=f_mono,
            wrap="word",
            bg=self.BG_SANDBOX,
            fg=self.TEXT_PRIMARY,
            insertbackground=self.GOLD,
            selectbackground="#433C31",
            selectforeground=self.TEXT_PRIMARY,
            relief="flat",
            highlightbackground="#2E333E",
            highlightcolor=self.GOLD_SOFT,
            highlightthickness=1,
            padx=self._px(10),
            pady=self._px(7),
        )
        self.sandbox_text.pack(fill="x")
        self.sandbox_text.insert("1.0", SAMPLE_SANDBOX_TEXT)
        self.sandbox_text.bind("<KeyRelease-space>", self._on_sandbox_space)

        btn_row = tk.Frame(sandbox_card, bg=self.BG_CARD)
        btn_row.pack(fill="x", pady=(self._px(8), self._px(6)))

        self.btn_convert = LuxuryButton(
            btn_row,
            width=self._px(140),
            height=self._px(32),
            text=tr(lang, "btn_convert"),
            command=self._on_sandbox_convert,
            primary=True,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg="#181B21",
            font=(self._fonts["heading"], 9),
        )
        self.btn_convert.pack(side="left", padx=(0, self._px(8)))
        self._attach_tooltip(self.btn_convert, "btn_convert")

        self.btn_switch_layout = LuxuryButton(
            btn_row,
            width=self._px(152),
            height=self._px(32),
            text=tr(lang, "btn_switch_layout"),
            command=self._on_toggle_os_layout,
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.TEXT_PRIMARY,
            font=(self._fonts["body"], 9),
        )
        self.btn_switch_layout.pack(side="left")
        self._attach_tooltip(self.btn_switch_layout, "btn_switch_layout")

        self.btn_clear_sandbox = LuxuryButton(
            btn_row,
            width=self._px(96),
            height=self._px(32),
            text=tr(lang, "btn_clear_sandbox"),
            command=lambda: self.sandbox_text.delete("1.0", "end"),
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.TEXT_MUTED,
            font=(self._fonts["body"], 9),
        )
        self.btn_clear_sandbox.pack(side="right")
        self._attach_tooltip(self.btn_clear_sandbox, "btn_clear_sandbox")

        self.lbl_event = tk.Label(
            sandbox_card,
            text=self.controller.last_event,
            font=f_small,
            bg=self.BG_CARD,
            fg=self.TEXT_MUTED,
            anchor="w",
        )
        self.lbl_event.pack(fill="x", pady=(self._px(2), 0))

        self._finalize_card(sb_canvas, sandbox_card, card_w, min_height=self._px(196), gold_tint=False)

        # 5. Двухстрочный чистый низ без перекрытий + кнопки Автор и Под капотом
        footer = tk.Frame(self.root, bg=self.BG_VOID, padx=self._px(22), pady=self._px(6))
        footer.pack(fill="x", side="bottom")

        footer_top = tk.Frame(footer, bg=self.BG_VOID)
        footer_top.pack(fill="x")

        self.btn_author = LuxuryButton(
            footer_top,
            width=self._px(176),
            height=self._px(28),
            text=tr(lang, "link_author"),
            command=lambda: self._open_info_dialog("author"),
            primary=False,
            bg_hex=self.BG_VOID,
            bg_rgb=BG_VOID_RGB,
            text_fg=self.GOLD,
            font=(self._fonts["heading"], 8),
        )
        self.btn_author.pack(side="left", padx=(0, self._px(8)))
        self._attach_tooltip(self.btn_author, "btn_author")

        self.btn_hood = LuxuryButton(
            footer_top,
            width=self._px(120),
            height=self._px(28),
            text=tr(lang, "link_under_hood"),
            command=lambda: self._open_info_dialog("hood"),
            primary=False,
            bg_hex=self.BG_VOID,
            bg_rgb=BG_VOID_RGB,
            text_fg=self.TEXT_PRIMARY,
            font=(self._fonts["body"], 8),
        )
        self.btn_hood.pack(side="left")
        self._attach_tooltip(self.btn_hood, "btn_hood")

        self.lbl_stats = tk.Label(
            footer_top,
            text="",
            font=f_small,
            bg=self.BG_VOID,
            fg=self.TEXT_MUTED,
            anchor="e",
        )
        self.lbl_stats.pack(side="right")

        footer_bottom = tk.Frame(footer, bg=self.BG_VOID)
        footer_bottom.pack(fill="x", pady=(self._px(4), 0))

        self.lbl_triad_status = tk.Label(
            footer_bottom,
            text=tr(lang, "footer_clean"),
            font=f_small,
            bg=self.BG_VOID,
            fg=self.TEXT_QUIET,
            anchor="w",
        )
        self.lbl_triad_status.pack(side="left")

        self.root.update_idletasks()
        fit_w = max(self._px(644), self.root.winfo_reqwidth())
        fit_h = max(self._px(792), self.root.winfo_reqheight() + self._px(10))
        self.root.minsize(fit_w, fit_h)
        self._center_window(fit_w, fit_h)

    def _tooltip_kwargs(self) -> dict[str, str]:
        return {
            "corpus_path": str(self.controller.flow_corpus.active_path),
            "corpus_dir": str(self.controller.flow_corpus.corpus_dir),
            "exports_path": str(self.controller.config_path.with_name("flow_exports")),
        }

    def _attach_tooltip(self, widget: tk.Widget | list[tk.Widget], tip_key: str) -> AvalonTooltip:
        widgets = widget if isinstance(widget, (list, tuple)) else [widget]
        tip = AvalonTooltip(
            widgets[0],
            text_provider=lambda k=tip_key: tr_tip(self.controller.lang, k, **self._tooltip_kwargs()),
            font_title=(self._fonts["heading"], 8),
            font_body=(self._fonts["body"], 8),
        )
        for extra in widgets[1:]:
            tip.bind_widget(extra)
        self._tooltips.append(tip)
        return tip

    def _hide_all_tooltips(self) -> None:
        for tip in self._tooltips:
            tip._cancel()
            tip.hide()

    def _on_header_pill_press(
        self,
        canvas: tk.Canvas,
        bg_id: int,
        pressed_img: tk.PhotoImage,
        event: tk.Event,
        *,
        raise_item: int | None = None,
    ) -> None:
        canvas.itemconfigure(bg_id, image=pressed_img)
        _spawn_quantum_gold_ripple(
            canvas,
            int(getattr(event, "x", canvas.winfo_width() // 2)),
            int(getattr(event, "y", canvas.winfo_height() // 2)),
            primary=False,
            radius=9,
            shape="rounded_box",
            raise_item=raise_item,
            tag_prefix="hdr_rip",
        )

    def _on_header_pill_release(self, canvas: tk.Canvas, bg_id: int, hover_img: tk.PhotoImage, cmd: callable) -> None:
        canvas.itemconfigure(bg_id, image=hover_img)
        cmd()

    def _animate_header_layout_teleport(self, target_layout: str) -> None:
        if self._closed or self._badge_animating:
            return
        self._badge_animating = True
        code = "RU" if target_layout == "RU" else "EN"
        fg_final = self.GOLD if code == "RU" else self.TEXT_PRIMARY

        steps = (
            ("compress_1", 1, "#D2B684"),
            ("beam_peak", 3, "#EFE4CE"),
            ("expand_1", 1, fg_final),
        )

        def _tick(i: int) -> None:
            if self._closed:
                return
            try:
                if i >= len(steps):
                    self.lbl_layout_badge.itemconfigure(self._badge_beam_item, state="hidden")
                    self.lbl_layout_badge.itemconfigure(self._badge_text_id, text=code, fill=fg_final, state="normal")
                    self._badge_animating = False
                    return
                stage, beam_w, col = steps[i]
                if stage == "beam_peak":
                    self.lbl_layout_badge.itemconfigure(self._badge_text_id, state="hidden")
                    self.lbl_layout_badge.itemconfigure(self._badge_beam_item, state="normal", width=beam_w, fill=col)
                else:
                    show_txt = code if stage == "expand_1" else self.lbl_layout_badge.itemcget(self._badge_text_id, "text")
                    self.lbl_layout_badge.itemconfigure(self._badge_beam_item, state="normal", width=beam_w, fill="#C2A574")
                    self.lbl_layout_badge.itemconfigure(self._badge_text_id, state="normal", text=show_txt, fill=col)
                self._schedule_after(42, lambda nxt=i + 1: _tick(nxt))
            except tk.TclError:
                self._badge_animating = False

        _tick(0)

    def _make_orbital_module(
        self,
        parent: tk.Widget,
        col: int,
        key: str,
        title_key: str,
    ) -> None:
        cell = tk.Frame(parent, bg=self.BG_CARD, cursor="hand2")
        cell.grid(row=0, column=col, sticky="nsew")

        dial_sz = self._px(52)
        canvas = tk.Canvas(
            cell,
            width=dial_sz,
            height=dial_sz,
            bg=self.BG_CARD,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(pady=(self._px(2), 0))
        img_id = canvas.create_image(0, 0, anchor="nw", image=self._dial_images[key]["idle"])

        title_lbl = tk.Label(
            cell,
            text=tr(self.controller.lang, title_key),
            font=(self._fonts["body"], 9),
            bg=self.BG_CARD,
            fg=self.TEXT_PRIMARY,
        )
        title_lbl.pack(pady=(self._px(5), self._px(1)))

        state_lbl = tk.Label(
            cell,
            text="",
            font=(self._fonts["body"], 8),
            bg=self.BG_CARD,
        )
        state_lbl.pack(pady=(0, self._px(2)))

        def _on_dial_press(event: tk.Event, c: tk.Canvas = canvas) -> None:
            _spawn_quantum_gold_ripple(
                c,
                int(getattr(event, "x", dial_sz // 2)),
                int(getattr(event, "y", dial_sz // 2)),
                primary=False,
                radius=dial_sz // 2,
                shape="circle",
                tag_prefix="dial_rip",
            )

        for w in (cell, canvas, title_lbl, state_lbl):
            w.bind("<ButtonPress-1>", _on_dial_press)
            w.bind("<ButtonRelease-1>", lambda _e, k=key: self.controller.toggle_option(k))

        self._orbital_widgets[key] = {
            "canvas": canvas,
            "img_id": img_id,
            "title_lbl": title_lbl,
            "title_key": title_key,
            "state_lbl": state_lbl,
        }
        self._attach_tooltip([cell, canvas, title_lbl, state_lbl], title_key)

    def _add_switch_row(
        self,
        parent: tk.Widget,
        key: str,
        label_key: str,
        font_body: tkfont.Font,
    ) -> None:
        row = tk.Frame(parent, bg=self.BG_CARD, cursor="hand2", pady=self._px(3))
        row.pack(fill="x")
        self._switch_rows.append(row)

        lbl = tk.Label(
            row,
            text=tr(self.controller.lang, label_key),
            font=font_body,
            bg=self.BG_CARD,
            fg=self.TEXT_PRIMARY,
            anchor="w",
        )
        lbl.pack(side="left", fill="x", expand=True, padx=(0, self._px(10)))

        pill_w = self._px(46)
        pill_h = self._px(24)
        pill = tk.Canvas(
            row,
            width=pill_w,
            height=pill_h,
            bg=self.BG_CARD,
            highlightthickness=0,
            bd=0,
        )
        pill.pack(side="right")
        img_id = pill.create_image(0, 0, anchor="nw", image=self._pill_off_img)

        def _on_row_press(_event: tk.Event, p_c: tk.Canvas = pill) -> None:
            _spawn_quantum_gold_ripple(
                p_c,
                pill_w // 2,
                pill_h // 2,
                primary=False,
                radius=pill_h // 2,
                shape="pill",
                tag_prefix="sw_rip",
            )

        for w in (row, lbl, pill):
            w.bind("<ButtonPress-1>", _on_row_press)
            w.bind("<ButtonRelease-1>", lambda _e, k=key: self.controller.toggle_option(k))

        self._switch_widgets[key] = {
            "pill": pill,
            "img_id": img_id,
            "lbl": lbl,
            "label_key": label_key,
        }
        self._attach_tooltip([row, lbl, pill], label_key)

    def _on_toggle_ui_lang(self) -> None:
        next_lang = "en" if self.controller.lang == "ru" else "ru"
        self.controller.set_ui_language(next_lang)
        self._refresh_ui()
        if self._about_dlg is not None and self._about_dlg.winfo_exists():
            active_tab = self._about_refs.get("active_tab", "author")
            self._close_about_dialog()
            self._open_info_dialog(str(active_tab))

    def _on_toggle_os_layout(self) -> None:
        new_lang = switch_foreground_layout(None)
        self.controller.last_event = tr(self.controller.lang, "event_layout_switched", lang=new_lang)
        self._refresh_ui()

    def _on_clear_empathy(self) -> None:
        self.controller.clear_empathic_memory()
        self._refresh_ui()

    def _on_export_flow(self) -> None:
        self.controller.export_flow_corpus()
        self._refresh_ui()

    def _on_clear_flow(self) -> None:
        self.controller.clear_flow_corpus()
        self._refresh_ui()

    def _open_info_dialog_from_tray(self, initial_tab: str = "author") -> None:
        if self._hidden_to_tray:
            self.restore_from_tray()
        self._open_info_dialog(initial_tab=initial_tab)

    def _close_about_dialog(self) -> None:
        if self._about_dlg is not None:
            try:
                self._about_dlg.destroy()
            except tk.TclError:
                pass
        self._about_dlg = None
        self._about_refs.clear()

    def _open_info_dialog(self, initial_tab: str = "author") -> None:
        if self._closed:
            return
        if self._about_dlg is not None and self._about_dlg.winfo_exists():
            self._about_dlg.lift()
            self._select_about_tab(initial_tab)
            return

        lang = self.controller.lang
        dlg = tk.Toplevel(self.root)
        dlg.withdraw()
        dlg.title(tr(lang, "dlg_title"))
        dlg.configure(bg=self.BG_VOID)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.protocol("WM_DELETE_WINDOW", self._close_about_dialog)

        dlg_w = self._px(540)
        dlg_h = self._px(440)
        self._center_child(dlg, dlg_w, dlg_h)
        self._about_dlg = dlg

        wrap = tk.Frame(dlg, bg=self.BG_VOID, padx=self._px(18), pady=self._px(14))
        wrap.pack(fill="both", expand=True)

        tab_bar = tk.Frame(wrap, bg=self.BG_VOID)
        tab_bar.pack(fill="x", pady=(0, self._px(10)))

        tab_author_btn = LuxuryButton(
            tab_bar,
            width=self._px(210),
            height=self._px(30),
            text=tr(lang, "tab_author"),
            command=lambda: self._select_about_tab("author"),
            primary=True,
            bg_hex=self.BG_VOID,
            bg_rgb=BG_VOID_RGB,
            text_fg="#181B21",
            font=(self._fonts["heading"], 9),
        )
        tab_author_btn.pack(side="left", padx=(0, self._px(8)))

        tab_hood_btn = LuxuryButton(
            tab_bar,
            width=self._px(230),
            height=self._px(30),
            text=tr(lang, "tab_hood"),
            command=lambda: self._select_about_tab("hood"),
            primary=False,
            bg_hex=self.BG_VOID,
            bg_rgb=BG_VOID_RGB,
            text_fg=self.TEXT_PRIMARY,
            font=(self._fonts["body"], 9),
        )
        tab_hood_btn.pack(side="left")

        content_box = tk.Frame(wrap, bg=self.BG_CARD, padx=self._px(16), pady=self._px(14), highlightbackground="#2E333E", highlightthickness=1)
        content_box.pack(fill="both", expand=True)

        # Панель "Автор • OMNISAVALON"
        author_frame = tk.Frame(content_box, bg=self.BG_CARD)
        tk.Label(
            author_frame,
            text=tr(lang, "author_heading"),
            font=(self._fonts["heading"], 10),
            bg=self.BG_CARD,
            fg=self.GOLD,
            anchor="w",
        ).pack(fill="x", pady=(0, self._px(8)))

        quote = PHILOSOPHY_QUOTE_EN if lang == "en" else PHILOSOPHY_QUOTE_RU
        tk.Label(
            author_frame,
            text=quote,
            font=(self._fonts["body"], 9),
            bg=self.BG_CARD,
            fg=self.TEXT_PRIMARY,
            justify="left",
            wraplength=self._px(460),
            anchor="w",
        ).pack(fill="x", pady=(0, self._px(10)))

        tk.Label(
            author_frame,
            text=f"{tr(lang, 'author_creator_label')} {AUTHOR_FULL_NAME}",
            font=(self._fonts["heading"], 8),
            bg=self.BG_CARD,
            fg=self.GOLD_SOFT,
            anchor="w",
            wraplength=self._px(460),
        ).pack(fill="x", pady=(0, self._px(8)))

        tk.Label(
            author_frame,
            text=tr(lang, "author_links_title"),
            font=(self._fonts["body"], 8),
            bg=self.BG_CARD,
            fg=self.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(0, self._px(6)))

        links_grid = tk.Frame(author_frame, bg=self.BG_CARD)
        links_grid.pack(fill="x", pady=(0, self._px(10)))
        for idx, item in enumerate(AUTHOR_LINKS):
            r_idx, c_idx = divmod(idx, 2)
            label_txt = item["label_en"] if lang == "en" else item["label_ru"]
            LuxuryButton(
                links_grid,
                width=self._px(220),
                height=self._px(30),
                text=label_txt,
                command=lambda u=item["url"]: open_external_url(u),
                primary=False,
                bg_hex=self.BG_CARD,
                bg_rgb=BG_CARD_RGB,
                text_fg=self.TEXT_PRIMARY,
                font=(self._fonts["body"], 8),
            ).grid(row=r_idx, column=c_idx, padx=(0, self._px(8)), pady=(0, self._px(6)), sticky="w")

        doc_row = tk.Frame(author_frame, bg=self.BG_CARD)
        doc_row.pack(fill="x", pady=(self._px(2), 0))
        readme_name = "README_EN.md" if lang == "en" else "README.md"
        LuxuryButton(
            doc_row,
            width=self._px(220),
            height=self._px(28),
            text=tr(lang, "author_license_btn"),
            command=lambda: self._open_local_doc("LICENSE.md"),
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.GOLD_SOFT,
            font=(self._fonts["body"], 8),
        ).pack(side="left", padx=(0, self._px(8)))
        LuxuryButton(
            doc_row,
            width=self._px(220),
            height=self._px(28),
            text=tr(lang, "author_readme_btn"),
            command=lambda rn=readme_name: self._open_local_doc(rn),
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.TEXT_MUTED,
            font=(self._fonts["body"], 8),
        ).pack(side="left")

        # Панель "Под капотом • Прозрачность"
        hood_frame = tk.Frame(content_box, bg=self.BG_CARD)
        tk.Label(
            hood_frame,
            text=tr(lang, "hood_heading"),
            font=(self._fonts["heading"], 10),
            bg=self.BG_CARD,
            fg=self.GOLD,
            anchor="w",
        ).pack(fill="x", pady=(0, self._px(8)))

        native_tag = "AvalonShifter.exe" if Path(__file__).with_name("AvalonShifter.exe").exists() else PLATFORM_MODE
        emp = self.controller.empathic_memory.stats()
        emp_state = ("активна" if self.controller.config.get("empathic_learning", True) else "пауза") if lang == "ru" else (
            "active" if self.controller.config.get("empathic_learning", True) else "paused"
        )
        flow_st = self.controller.flow_corpus.stats()
        flow_state = ("включена" if self.controller._is_flow_recording() else "выключена") if lang == "ru" else (
            "enabled" if self.controller._is_flow_recording() else "disabled"
        )
        restarts = getattr(self.controller.supervisor, "restart_count", 0)

        hood_lines = (
            tr(lang, "hood_arch_line", native=native_tag),
            tr(lang, "hood_crypto_line"),
            tr(lang, "hood_privacy_line"),
            tr(lang, "hood_vector_line", vec=self.controller.last_vector.format_short(), intent=self.controller.last_intent),
            tr(lang, "hood_otp_line", restarts=restarts),
            tr(
                lang,
                "hood_empathy_line",
                state=emp_state,
                entries=emp["entries_count"],
                dirs=emp["direction_rules_count"],
                keeps=emp["keep_rules_count"],
            ),
            tr(
                lang,
                "hood_flow_line",
                state=flow_state,
                records=flow_st["records_count"],
                size_kb=flow_st["size_kb"],
                secrets=flow_st["filtered_secrets_count"],
            ),
        )
        for line in hood_lines:
            tk.Label(
                hood_frame,
                text=line,
                font=(self._fonts["mono"], 8),
                bg=self.BG_CARD,
                fg=self.TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=self._px(460),
            ).pack(fill="x", pady=(0, self._px(5)))

        hood_btns = tk.Frame(hood_frame, bg=self.BG_CARD)
        hood_btns.pack(fill="x", pady=(self._px(10), 0))
        LuxuryButton(
            hood_btns,
            width=self._px(190),
            height=self._px(30),
            text=tr(lang, "hood_btn_reset_empathy"),
            command=self._on_clear_empathy,
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.GOLD_SOFT,
            font=(self._fonts["body"], 8),
        ).pack(side="left", padx=(0, self._px(8)))
        LuxuryButton(
            hood_btns,
            width=self._px(200),
            height=self._px(30),
            text=tr(lang, "hood_btn_open_exports"),
            command=self._open_flow_exports_folder,
            primary=False,
            bg_hex=self.BG_CARD,
            bg_rgb=BG_CARD_RGB,
            text_fg=self.TEXT_PRIMARY,
            font=(self._fonts["body"], 8),
        ).pack(side="left")

        bottom_bar = tk.Frame(wrap, bg=self.BG_VOID)
        bottom_bar.pack(fill="x", pady=(self._px(10), 0))
        LuxuryButton(
            bottom_bar,
            width=self._px(110),
            height=self._px(30),
            text=tr(lang, "hood_btn_close"),
            command=self._close_about_dialog,
            primary=True,
            bg_hex=self.BG_VOID,
            bg_rgb=BG_VOID_RGB,
            text_fg="#181B21",
            font=(self._fonts["heading"], 9),
        ).pack(side="right")

        self._about_refs = {
            "author_frame": author_frame,
            "hood_frame": hood_frame,
            "active_tab": initial_tab,
        }
        self._select_about_tab(initial_tab)

        dlg.update_idletasks()
        self._apply_ico(dlg.winfo_id())
        dlg.deiconify()
        dlg.lift()

    def _select_about_tab(self, tab_name: str) -> None:
        if not self._about_refs:
            return
        author_f = self._about_refs.get("author_frame")
        hood_f = self._about_refs.get("hood_frame")
        self._about_refs["active_tab"] = tab_name
        if isinstance(author_f, tk.Frame) and isinstance(hood_f, tk.Frame):
            author_f.pack_forget()
            hood_f.pack_forget()
            if tab_name == "hood":
                hood_f.pack(fill="both", expand=True)
            else:
                author_f.pack(fill="both", expand=True)

    def _open_local_doc(self, filename: str) -> None:
        doc_path = Path(__file__).with_name(filename)
        if not doc_path.exists():
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(doc_path))  # type: ignore[attr-defined]
            else:
                open_external_url(doc_path.as_uri())
        except Exception:
            pass

    def _open_flow_exports_folder(self) -> None:
        export_dir = self.controller.config_path.with_name("flow_exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(export_dir))  # type: ignore[attr-defined]
            else:
                open_external_url(export_dir.as_uri())
        except Exception:
            pass

    def _on_sandbox_space(self, _event: tk.Event) -> None:
        if not self.controller.config.get("auto_switch", True):
            return

        cursor_pos = self.sandbox_text.index("insert")
        line_no, _ = (int(x) for x in cursor_pos.split("."))
        line_start = f"{line_no}.0"
        before = self.sandbox_text.get(line_start, cursor_pos)
        if not before.endswith(" "):
            return

        prefix_text = before[:-1]
        match = re.search(r"(\S+)$", prefix_text)
        if not match:
            return

        raw_word = match.group(1)
        start_col = match.start(1)
        end_col = match.end(1)

        slice_start = max(0, start_col - 80)
        while slice_start > 0 and not prefix_text[slice_start - 1].isspace():
            slice_start -= 1
        ctx_slice = prefix_text[slice_start:end_col]
        converted_slice, stats = self.controller.convert_phrase(ctx_slice, force_single_fallback=False)
        new_tokens = converted_slice.split()
        if not new_tokens:
            return
        new_word = new_tokens[-1]

        pair_match = re.search(r"(?:^|(?<=\s))(\S+) (\S+)$", prefix_text)
        retro_prev: str | None = None
        if pair_match and len(new_tokens) >= 2 and len(new_tokens) == len(ctx_slice.split()):
            prev_start = pair_match.start(1)
            prev_word = pair_match.group(1)
            cand_prev = new_tokens[-2]
            before_prev = prefix_text[:prev_start].split()
            if should_retroactively_fix_prev_token(prev_word, cand_prev, new_word, before_prev):
                retro_prev = cand_prev

        if retro_prev is not None and pair_match is not None:
            prev_start = pair_match.start(1)
            prev_word = pair_match.group(1)
            replacement = f"{retro_prev} {new_word}"
            self.sandbox_text.delete(f"{line_no}.{prev_start}", f"{line_no}.{end_col}")
            self.sandbox_text.insert(f"{line_no}.{prev_start}", replacement)
            self.sandbox_text.mark_set("insert", f"{line_no}.{prev_start + len(replacement) + 1}")
            self.controller.last_event = f"{prev_word} {raw_word} → {replacement}"
            self._refresh_ui()
        elif new_word != raw_word:
            self.sandbox_text.delete(f"{line_no}.{start_col}", f"{line_no}.{end_col}")
            self.sandbox_text.insert(f"{line_no}.{start_col}", new_word)
            new_cursor_col = start_col + len(new_word) + 1
            self.sandbox_text.mark_set("insert", f"{line_no}.{new_cursor_col}")
            self.controller.last_event = f"{raw_word} → {new_word}"
            self._refresh_ui()
        elif stats.get("protected_tokens", 0) > 0 and is_protected_token(raw_word):
            self.controller.last_event = f"Developer Guard: {raw_word}"
            self._refresh_ui()

    def _on_sandbox_convert(self) -> None:
        try:
            sel_start = self.sandbox_text.index("sel.first")
            sel_end = self.sandbox_text.index("sel.last")
            source = self.sandbox_text.get(sel_start, sel_end)
        except tk.TclError:
            sel_start = "1.0"
            sel_end = "end-1c"
            source = self.sandbox_text.get(sel_start, sel_end)

        if not source.strip():
            return

        converted, stats = self.controller.convert_phrase(source, force_single_fallback=True)
        if converted != source:
            self.sandbox_text.delete(sel_start, sel_end)
            self.sandbox_text.insert(sel_start, converted)
            self.controller.last_event = f"✓ {stats.get('converted_words', 0)}"
        else:
            self.controller.last_event = f"• {stats.get('protected_tokens', 0)}"
        self._refresh_ui()

    def _schedule_after(self, delay_ms: int, callback: callable) -> str | None:
        if self._closed:
            return None
        holder: dict[str, str | None] = {"id": None}

        def _wrapped() -> None:
            aid = holder["id"]
            if aid is not None:
                self._after_ids.discard(aid)
            if self._closed:
                return
            try:
                if not bool(self.root.winfo_exists()):
                    return
                callback()
            except tk.TclError:
                pass

        try:
            if not bool(self.root.winfo_exists()):
                return None
            aid = self.root.after(delay_ms, _wrapped)
            holder["id"] = aid
            self._after_ids.add(aid)
            return aid
        except tk.TclError:
            return None

    def _cancel_all_after(self) -> None:
        self._closed = True
        pending = list(self._after_ids)
        self._after_ids.clear()
        for aid in pending:
            try:
                self.root.after_cancel(aid)
            except tk.TclError:
                pass

    def _on_root_destroy(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self._cancel_all_after()
            self._hide_all_tooltips()
            self.controller.stop()
            if self.tray:
                self.tray.stop()

    def _dispatch_ui(self, fn: callable) -> None:
        if not self._closed:
            self._schedule_after(0, fn)

    def _schedule_refresh(self) -> None:
        self._dispatch_ui(self._refresh_ui)

    def _schedule_local_double_shift(self) -> None:
        self._dispatch_ui(self._on_sandbox_convert)

    def _refresh_ui(self) -> None:
        if self._closed:
            return

        cfg = self.controller.config
        lang = self.controller.lang
        layout = get_foreground_layout()
        prev_layout = self._last_layout
        self._last_layout = layout
        auto_active = bool(cfg.get("auto_switch", True))
        flow_active = bool(cfg.get("flow_archive_enabled", False))

        self.lbl_subtitle.configure(text=tr(lang, "subtitle"))
        self.btn_lang_badge.itemconfigure(
            self._lang_text_id,
            text="РУС" if lang == "ru" else "ENG",
        )
        self.btn_tray.set_text(tr(lang, "btn_tray"))
        self.lbl_settings_hdr.configure(text=tr(lang, "sec_settings"))
        self.lbl_sandbox_hdr.configure(text=tr(lang, "sec_sandbox"))
        self.lbl_sandbox_hint.configure(text=tr(lang, "sandbox_hint"))
        self.btn_convert.set_text(tr(lang, "btn_convert"))
        self.btn_switch_layout.set_text(tr(lang, "btn_switch_layout"))
        self.btn_clear_sandbox.set_text(tr(lang, "btn_clear_sandbox"))
        self.btn_flow_export.set_text(tr(lang, "btn_export_ai"))
        self.btn_flow_clear.set_text(tr(lang, "btn_clear_flow"))
        self.lbl_triad_status.configure(text=tr(lang, "footer_clean"))
        self.btn_hood.set_text(tr(lang, "link_under_hood"))
        self.btn_author.set_text(tr(lang, "link_author"))

        for key, item in self._orbital_widgets.items():
            active = bool(cfg.get(key, False))
            canvas = item["canvas"]
            imgs = self._dial_images[key]
            canvas.itemconfigure(
                item["img_id"],
                image=imgs["active"] if active else imgs["idle"],
            )
            item["title_lbl"].configure(
                text=tr(lang, item["title_key"]),
                fg=self.TEXT_PRIMARY if active else self.TEXT_MUTED,
            )
            item["state_lbl"].configure(
                text=tr(lang, "dial_on" if active else "dial_off"),
                fg=self.GOLD if active else self.TEXT_QUIET,
            )

        for key, item in self._switch_widgets.items():
            active = bool(cfg.get(key, False))
            item["pill"].itemconfigure(
                item["img_id"],
                image=self._pill_on_img if active else self._pill_off_img,
            )
            item["lbl"].configure(
                text=tr(lang, item["label_key"]),
                fg=self.TEXT_PRIMARY if active else self.TEXT_MUTED,
            )

        if prev_layout and prev_layout != layout:
            self._animate_header_layout_teleport(layout)
        elif not self._badge_animating:
            self.lbl_layout_badge.itemconfigure(
                self._badge_text_id,
                text="RU" if layout == "RU" else "EN",
                fill=self.GOLD if layout == "RU" else self.TEXT_PRIMARY,
                state="normal",
            )

        flow_st = self.controller.flow_corpus.stats()
        if flow_active or flow_st["records_count"] > 0:
            self.lbl_flow_summary.configure(
                text=tr(
                    lang,
                    "flow_status_on",
                    records=flow_st["records_count"],
                    size_kb=flow_st["size_kb"],
                    segments=flow_st["segments_count"],
                    secrets=flow_st["filtered_secrets_count"],
                ),
                fg=self.GOLD if flow_active else self.TEXT_MUTED,
            )
        else:
            self.lbl_flow_summary.configure(text=tr(lang, "flow_status_off"), fg=self.TEXT_QUIET)

        self.lbl_event.configure(text=self.controller.last_event)
        self.lbl_stats.configure(
            text=tr(
                lang,
                "stats_counter",
                converted=self.controller.converted_count,
                protected=self.controller.protected_count,
            )
        )

        if self.tray is not None:
            self.tray.set_layout_state(
                layout,
                auto_active=auto_active,
                flow_recording=flow_active,
                tooltip=self._build_tray_tooltip(layout),
            )

    def _poll_layout(self) -> None:
        if self._closed:
            return
        layout = get_foreground_layout()
        if layout != self._last_layout:
            self._refresh_ui()
        self._schedule_after(180, self._poll_layout)

    def _on_unmap(self, event: tk.Event) -> None:
        if self._closed or self._suppress_unmap or not self.enable_tray:
            return
        if event.widget is self.root and self.root.state() == "iconic":
            self.hide_to_tray()

    def hide_to_tray(self) -> None:
        if self._closed:
            return
        self._hide_all_tooltips()
        self._suppress_unmap = True
        self._hidden_to_tray = True
        self.root.withdraw()
        self._schedule_after(50, lambda: setattr(self, "_suppress_unmap", False))

    def restore_from_tray(self) -> None:
        if self._closed:
            return
        self._suppress_unmap = True
        self._hidden_to_tray = False
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()
        self._apply_ico()
        self._refresh_ui()
        self._schedule_after(50, lambda: setattr(self, "_suppress_unmap", False))

    def _on_close(self) -> None:
        self._cancel_all_after()
        self._hide_all_tooltips()
        self._close_about_dialog()
        self.controller.stop()
        if self.tray:
            self.tray.stop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def run_self_test() -> int:
    """Быстрая самопроверка ядра, Базы Потока, иконок, платформенного моста и Tkinter."""
    enable_high_dpi_awareness()
    set_app_user_model_id()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        tmp_cfg = tmp_root / "config.json"
        tmp_ico = ensure_app_icon(tmp_root / "test_icon.ico")
        if not tmp_ico.exists() or not tmp_ico.read_bytes().startswith(b"\x00\x00\x01\x00"):
            raise AssertionError("Сгенерированный .ico имеет некорректный заголовок")

        ctrl = ShifterController(config_path=tmp_cfg, enable_hook=False, apply_autostart=False)
        try:
            save_config(ctrl.config, tmp_cfg)
            if ctrl.avl_ast is None or not ctrl.avl_ast.intents:
                raise AssertionError("Модуль shifter_intent.avl не был загружен в AST")

            sup_res = ctrl.supervisor.call("get_state")
            if sup_res.is_err():
                raise AssertionError(f"OTP Supervisor не ответил: {sup_res.error}")

            converted, stats = ctrl.convert_phrase(SAMPLE_SANDBOX_TEXT)
            expected = "ну что как ты себя теперь чувствуешь avalon ?"
            if converted != expected:
                raise AssertionError(f"Ожидалось {expected!r}, получено {converted!r}")
            if stats.get("converted_words", 0) < 1:
                raise AssertionError("Знак '?' из '&' не был конвертирован")

            chfpe_conv, _ = ctrl.convert_phrase("chfpe", force_single_fallback=False)
            if chfpe_conv != "сразу":
                raise AssertionError(f"Ожидалось 'сразу' для 'chfpe', получено {chfpe_conv!r}")
        finally:
            ctrl.stop()

        layout = get_foreground_layout()
        if layout not in ("RU", "EN"):
            raise AssertionError(f"Некорректная раскладка ОС: {layout!r}")

        root = tk.Tk()
        root.withdraw()
        root.iconbitmap(str(tmp_ico))
        root.update_idletasks()
        root.destroy()

    print("AVALON_SHIFTER_SELF_TEST_OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else list(sys.argv[1:])
    if "--self-test" in args:
        return run_self_test()

    if "--cli-convert" in args:
        idx = args.index("--cli-convert")
        tail = args[idx + 1 :]
        raw_text = " ".join(tail) if tail else sys.stdin.read()
        converted, _stats = smart_convert_text(raw_text)
        sys.stdout.write(converted)
        return 0

    if "--clipboard-convert" in args:
        raw_text = read_clipboard_text()
        if raw_text:
            converted, stats = smart_convert_text(raw_text)
            write_clipboard_text(converted)
            if stats.get("converted_words", 0) > 0:
                target = "RU" if _has_cyrillic(converted) and not _has_latin(converted) else None
                switch_foreground_layout(target)
        return 0

    enable_high_dpi_awareness()
    set_app_user_model_id()
    start_in_tray = "--tray" in args
    root = tk.Tk()
    root.withdraw()
    AvalonShifterApp(root, start_in_tray=start_in_tray)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
