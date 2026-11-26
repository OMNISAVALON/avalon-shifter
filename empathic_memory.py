"""
Эмпатическая самообучающаяся память предвосхищения Avalon.Shifter:
- Учится ТОЛЬКО из реальных ручных поправок и бережных откатов (Double Shift),
  без слежки, без хранения паролей/чисел/URL/секретов.
- Предвосхищает нужную раскладку на лету (< 0.1 мс из RAM-индекса).
- Самоочищается и жёстко ограничена по объёму (`<= 512` записей, `<= 32 КБ`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Optional


MAX_ENTRIES: int = 512
MAX_FILE_BYTES: int = 32768
MAX_TOKEN_LEN: int = 28
MIN_TOKEN_LEN: int = 2
ROLLBACK_WINDOW_SEC: float = 15.0

_FORBIDDEN_CHARS: frozenset[str] = frozenset("@$%/\\=*:#!^~+(){}<>|")
_INTERNAL_LAYOUT_CHARS: frozenset[str] = frozenset(";',.[]`\"")


def _split_word_core(token: str) -> tuple[str, str, str]:
    """Локально выделяет буквенную/раскладочную основу слова без циклического импорта."""
    if not token:
        return ("", "", "")
    lead_chars = "\"'([{«"
    trail_chars = "\"')]}»?!:,.;"
    i = 0
    j = len(token)
    while i < j and token[i] in lead_chars and not (token[i] in ("'", "[") and i + 1 < j and token[i + 1].isalpha()):
        i += 1
    while j > i and token[j - 1] in trail_chars:
        if token[j - 1] in (",", ".") and j - 1 > i and token[j - 2].isalpha():
            break
        j -= 1
    return (token[:i], token[i:j], token[j:])


def _default_is_safe(token: str, protected_fn: Optional[Callable[[str], bool]] = None) -> bool:
    """
    Фильтр «Любовь, а не Слежка»: допускает только чистые одиночные слова,
    исключая пароли, цифры, URL, пути, токены кода и смешанно-регистровые секреты.
    """
    if not token or any(ch.isspace() for ch in token):
        return False
    _, core, _ = _split_word_core(token)
    if len(core) < MIN_TOKEN_LEN or len(core) > MAX_TOKEN_LEN:
        return False
    if any(ch.isdigit() for ch in core):
        return False
    if any(ch in _FORBIDDEN_CHARS for ch in token):
        return False
    if "://" in token or "\\" in token or "/" in token:
        return False
    if protected_fn is not None and protected_fn(token):
        return False
    # Смешанный регистр внутри слова (camelCase / пароль вида MyPassWord) не сохраняем
    if len(core) >= 2 and any(c.isupper() for c in core[1:]) and not core.isupper():
        return False
    alpha_cnt = sum(1 for c in core if c.isalpha())
    if alpha_cnt < 2:
        return False
    for c in core:
        if not (c.isalpha() or c == "-" or c in _INTERNAL_LAYOUT_CHARS):
            return False
    return True


def _normalize_key(token: str) -> str:
    _, core, _ = _split_word_core(token.strip())
    return core.lower()


class EmpathicMemoryCrystal:
    """
    Компактная самообучающаяся память привычек ввода с самоочисткой и нулевым трением.
    """

    LEARN_DIR_THRESHOLD: float = 1.2
    LEARN_KEEP_THRESHOLD: float = 1.5

    def __init__(
        self,
        memory_path: Optional[Path] = None,
        protected_fn: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.memory_path: Optional[Path] = Path(memory_path) if memory_path else None
        if protected_fn is not None:
            self._protected_fn = protected_fn
        else:
            from shifter_core import is_protected_token

            self._protected_fn = is_protected_token

        self._entries: dict[str, dict[str, Any]] = {}
        self._tick: int = 0
        self._dirty: bool = False
        self.pruned_count: int = 0
        # Хранится только в RAM для распознавания бережного отката автозамены
        self._last_auto: Optional[tuple[str, str, str, float]] = None

        if self.memory_path is not None and self.memory_path.exists():
            self.load()

    def is_safe_to_remember(self, token: str) -> bool:
        return _default_is_safe(token, self._protected_fn)

    def load(self) -> None:
        if self.memory_path is None or not self.memory_path.exists():
            return
        try:
            raw_text = self.memory_path.read_text(encoding="utf-8")
            raw = json.loads(raw_text)
            if not isinstance(raw, dict):
                return
            self._tick = int(raw.get("tick", 0))
            entries = raw.get("entries") or {}
            if isinstance(entries, dict):
                loaded: dict[str, dict[str, Any]] = {}
                for k, v in entries.items():
                    if not isinstance(k, str) or not isinstance(v, dict):
                        continue
                    d = str(v.get("d", ""))
                    if d not in ("EN_TO_RU", "RU_TO_EN", "KEEP"):
                        continue
                    if not self.is_safe_to_remember(k):
                        continue
                    loaded[k.lower()] = {
                        "d": d,
                        "w": round(float(v.get("w", 1.5)), 3),
                        "h": int(v.get("h", 1)),
                        "t": int(v.get("t", self._tick)),
                    }
                self._entries = loaded
                self._prune_entries_only()
        except (OSError, ValueError, TypeError):
            pass

    def _serialize_compact(self) -> bytes:
        payload = {
            "v": 1,
            "tick": self._tick,
            "pruned": self.pruned_count,
            "entries": self._entries,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def _entry_priority(self, item: tuple[str, dict[str, Any]]) -> float:
        meta = item[1]
        age = max(0, self._tick - int(meta.get("t", 0)))
        return float(meta.get("w", 1.0)) * 100.0 + float(meta.get("h", 1)) * 10.0 - float(age) * 0.25

    def _prune_entries_only(self) -> None:
        if len(self._entries) > MAX_ENTRIES:
            ordered = sorted(self._entries.items(), key=self._entry_priority, reverse=True)
            removed = len(ordered) - MAX_ENTRIES
            self._entries = dict(ordered[:MAX_ENTRIES])
            self.pruned_count += removed

    def _prune_if_needed(self) -> bytes:
        self._prune_entries_only()
        raw = self._serialize_compact()
        while len(raw) > MAX_FILE_BYTES and len(self._entries) > 1:
            ordered = sorted(self._entries.items(), key=self._entry_priority, reverse=True)
            keep_n = max(1, int(len(ordered) * 0.9))
            removed = len(ordered) - keep_n
            self._entries = dict(ordered[:keep_n])
            self.pruned_count += max(1, removed)
            raw = self._serialize_compact()
        return raw

    def flush(self) -> bool:
        """Атомарно сохраняет эмпатическую память на диск, соблюдая жёсткий лимит 32 КБ."""
        if not self._dirty or self.memory_path is None:
            return False
        raw_bytes = self._prune_if_needed()
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.memory_path.with_name(f".{self.memory_path.name}.{os.getpid()}.tmp")
        try:
            tmp_path.write_bytes(raw_bytes)
            os.replace(tmp_path, self.memory_path)
            self._dirty = False
            return True
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def record_auto_conversion(self, orig_word: str, converted_word: str, direction: Optional[str]) -> None:
        """Фиксирует в RAM недавнюю автозамену для бережного распознавания отката."""
        if not orig_word or not converted_word or orig_word == converted_word:
            return
        orig_key = _normalize_key(orig_word)
        conv_key = _normalize_key(converted_word)
        if not orig_key or not conv_key:
            return
        self._last_auto = (orig_key, conv_key, str(direction or ""), time.monotonic())
        existing = self._entries.get(orig_key)
        if existing is not None and existing.get("d") == direction:
            self._tick += 1
            existing["h"] = int(existing.get("h", 0)) + 1
            existing["t"] = self._tick
            self._dirty = True

    def learn_from_user_keep(self, word: str) -> bool:
        """Явно закрепляет слово как не требующее автоперевода ('KEEP')."""
        if not self.is_safe_to_remember(word):
            return False
        key = _normalize_key(word)
        if not key:
            return False
        self._tick += 1
        cur = self._entries.get(key)
        if cur is None or cur.get("d") != "KEEP":
            self._entries[key] = {"d": "KEEP", "w": 2.5, "h": 1, "t": self._tick}
        else:
            cur["w"] = round(min(20.0, float(cur.get("w", 2.5)) + 1.5), 3)
            cur["h"] = int(cur.get("h", 1)) + 1
            cur["t"] = self._tick
        self._dirty = True
        self.flush()
        return True

    def learn_from_manual_shift(
        self,
        raw_word: str,
        converted_word: str,
        direction: Optional[str],
    ) -> str:
        """
        Обучается от осознанного действия человека (Double Shift):
        - Если человек откатил недавнюю автозамену -> учит `KEEP` для исходного токена;
        - Иначе -> учит направление (`EN_TO_RU` / `RU_TO_EN`), чтобы в следующий раз
          предвосхитить слово автоматически.
        """
        raw_key = _normalize_key(raw_word)
        conv_key = _normalize_key(converted_word)
        now = time.monotonic()

        # 1. Детекция отката недавней автозамены в пределах окна 15 сек
        if self._last_auto is not None:
            last_orig, last_conv, _last_dir, last_ts = self._last_auto
            if (now - last_ts) <= ROLLBACK_WINDOW_SEC and raw_key == last_conv and conv_key == last_orig:
                self._last_auto = None
                if self.learn_from_user_keep(last_orig):
                    return "LEARNED_KEEP_ROLLBACK"
                return "IGNORED_UNSAFE_TOKEN"

        if direction not in ("EN_TO_RU", "RU_TO_EN"):
            return "NO_OP"
        if not self.is_safe_to_remember(raw_word):
            return "IGNORED_UNSAFE_TOKEN"
        if not raw_key or raw_key == conv_key:
            return "NO_OP"

        self._tick += 1
        cur = self._entries.get(raw_key)
        if cur is None:
            self._entries[raw_key] = {"d": direction, "w": 1.5, "h": 1, "t": self._tick}
        elif cur.get("d") == direction:
            cur["w"] = round(min(20.0, float(cur.get("w", 1.5)) + 1.0), 3)
            cur["h"] = int(cur.get("h", 1)) + 1
            cur["t"] = self._tick
        else:
            # Смена полярности: снижаем старый вес или мягко переводим на выбор человека
            new_w = float(cur.get("w", 1.5)) - 1.5
            if new_w <= 0.5:
                self._entries[raw_key] = {"d": direction, "w": 1.5, "h": 1, "t": self._tick}
            else:
                cur["w"] = round(new_w, 3)
                cur["t"] = self._tick

        self._dirty = True
        self.flush()
        return "LEARNED_DIRECTION"

    def anticipate_direction(
        self,
        word: str,
        prev_lang: Optional[str] = None,
        has_ru_context: bool = False,
    ) -> Optional[str]:
        """
        Предвосхищает направление по выученным привычкам (< 0.1 мс):
        возвращает `'KEEP'`, `'EN_TO_RU'`, `'RU_TO_EN'` или `None` (отдать базовой эвристике).
        """
        if not self._entries or not word:
            return None
        key = _normalize_key(word)
        if not key or len(key) < MIN_TOKEN_LEN:
            return None
        entry = self._entries.get(key)
        if entry is None:
            return None
        d = entry.get("d")
        w = float(entry.get("w", 0.0))
        if d == "KEEP" and w >= self.LEARN_KEEP_THRESHOLD:
            return "KEEP"
        if d in ("EN_TO_RU", "RU_TO_EN") and w >= self.LEARN_DIR_THRESHOLD:
            return str(d)
        return None

    def clear(self) -> int:
        """Безопасно очищает накопленную эмпатическую память на диске и в RAM."""
        count = len(self._entries)
        self._entries.clear()
        self._last_auto = None
        self._tick = 0
        self._dirty = True
        self.flush()
        return count

    def stats(self) -> dict[str, Any]:
        size_bytes = 0
        if self.memory_path is not None and self.memory_path.exists():
            try:
                size_bytes = self.memory_path.stat().st_size
            except OSError:
                size_bytes = 0
        dir_cnt = sum(1 for v in self._entries.values() if v.get("d") in ("EN_TO_RU", "RU_TO_EN"))
        keep_cnt = sum(1 for v in self._entries.values() if v.get("d") == "KEEP")
        return {
            "entries_count": len(self._entries),
            "max_entries": MAX_ENTRIES,
            "direction_rules_count": dir_cnt,
            "keep_rules_count": keep_cnt,
            "file_size_bytes": size_bytes,
            "max_file_bytes": MAX_FILE_BYTES,
            "pruned_count": self.pruned_count,
        }
