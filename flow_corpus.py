"""Суверенная локальная База Потока Мысли и Информации для обучения ИИ (SovereignFlowCorpus).

Построена полностью на Суверенном Базисе (без sqlite3, pickle, zlib, hashlib и сторонних пакетов):
- По умолчанию ОТКЛЮЧЕНА (строгий opt-in: пока пользователь сам не включит, 0 байт на диске).
- Многослойный щит приватности отбрасывает пароли, API-токены, карты, OTP-коды и секретные URL.
- 64-битная дедупликация AGLS-432-Phi + компактный JSONL-слой (<= 2 МБ) + суверенная словарная
  оригами-свёртка холодных сегментов (.qholo) с лимитом общего объёма (<= 16 МБ, FIFO).
- Экспорт в 4 универсальных формата для любых моделей ИИ (локальных и облачных).
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from datetime import date
import json
from pathlib import Path
import re
import struct
from typing import Any, Iterator


PHI_64 = 0x9E3779B97F4A7C15
HARM_432_64 = 0x01B004329E3779B9
EULER_64 = 0xB7E151628AED2A6B
PI_PHASE_64 = 0x243F6A8885A308D3
MASK_64 = 0xFFFFFFFFFFFFFFFF

QHOLO_MAGIC = b"AVALON_QHOLO_V8\x00"
FLOW_PACK_MAGIC = b"AVALON_FLOW_PACK_V1\x00"

MAX_ACTIVE_BYTES_DEFAULT = 2 * 1024 * 1024     # 2 МБ на активный слой
MAX_TOTAL_BYTES_DEFAULT = 16 * 1024 * 1024     # 16 МБ на всю локальную базу
MAX_LINE_CHARS = 1200
DEDUP_CACHE_LIMIT = 2048

_SECRET_PREFIXES = (
    "ghp_",
    "gho_",
    "ghs_",
    "ghu_",
    "github_pat_",
    "hf_",
    "sk-",
    "sk_live_",
    "pk_live_",
    "rk_live_",
    "aiza",
    "akia",
    "asia",
    "xoxb-",
    "xoxp-",
    "xoxa-",
    "eyj",
    "-----begin",
    "bearer ",
)

_SECRET_ASSIGN_RE = re.compile(
    r"(?i)(?:password|passwd|pwd|secret|api_key|apikey|access_token|private_key|парол[ья])\s*[:=]\s*\S+"
)
_URL_CRED_RE = re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://[^\s:@]+:[^\s@]+@|[?&](?:token|api_key|apikey|key|secret|password)=)")
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_HEX_SECRET_RE = re.compile(r"\b[0-9a-fA-F]{32,}\b")
_OTP_ONLY_RE = re.compile(r"^\s*[\d\- ]{4,9}\s*$")
_WORD_OR_SPACE_RE = re.compile(r"[^\s]+")

_PACK_SENTINEL = 0xFF
_PACK_ESCAPE = 0xFE


def _rotl64(val: int, shift: int) -> int:
    shift &= 63
    return ((val << shift) | (val >> (64 - shift))) & MASK_64


def agls_432_bytes(data: bytes | str) -> bytes:
    """Суверенная 256-битная гармоническая решётка AGLS-432-Phi (побитовый паритет с AVALON.OS)."""
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    s0, s1, s2, s3 = PHI_64, HARM_432_64, EULER_64, PI_PHASE_64
    s0 = (s0 ^ (len(raw) * 432)) & MASK_64

    for idx, b in enumerate(raw):
        lane = idx & 3
        mix = ((b + 1) * PHI_64 + (idx + 432) * HARM_432_64) & MASK_64
        if lane == 0:
            s0 = _rotl64((s0 + mix) & MASK_64, 13) ^ s2
            s1 = (s1 + s0) & MASK_64
        elif lane == 1:
            s1 = _rotl64((s1 ^ mix) & MASK_64, 21) + s3
            s1 &= MASK_64
            s2 = (s2 ^ s1) & MASK_64
        elif lane == 2:
            s2 = _rotl64((s2 + mix) & MASK_64, 34) ^ s0
            s3 = (s3 + s2) & MASK_64
        else:
            s3 = _rotl64((s3 ^ mix) & MASK_64, 55) + s1
            s3 &= MASK_64
            s0 = (s0 ^ s3) & MASK_64

    for fib_shift in (5, 8, 13, 21, 34, 55, 13, 21, 34):
        s0 = (_rotl64(s0, fib_shift) + s1 * PHI_64) & MASK_64
        s1 = (_rotl64(s1 ^ s0, fib_shift) + s2 * HARM_432_64) & MASK_64
        s2 = (_rotl64(s2 + s1, fib_shift) ^ (s3 * EULER_64)) & MASK_64
        s3 = (_rotl64(s3 ^ s2, fib_shift) + s0 * PI_PHASE_64) & MASK_64

    return (
        s0.to_bytes(8, "little")
        + s1.to_bytes(8, "little")
        + s2.to_bytes(8, "little")
        + s3.to_bytes(8, "little")
    )


def agls_432_hex(data: bytes | str) -> str:
    """Возвращает 64-символьную печать AGLS-432-Phi."""
    return agls_432_bytes(data).hex()


def fold_qholo_bytes(raw_utf8: bytes) -> bytes:
    """Упаковывает UTF-8 JSON/текст в совместимый с AVALON.OS / Avalon.Veritas формат AVALON_QHOLO_V8."""
    text = raw_utf8.decode("utf-8", errors="surrogateescape")
    escaped = text.replace("\x01", "\x01\x01").encode("utf-8", errors="surrogateescape")
    return QHOLO_MAGIC + escaped


def pack_flow_segment(raw_utf8: bytes) -> bytes:
    """Суверенное словарно-мотивное сжатие холодного сегмента (без zlib).

    Формат AVALON_FLOW_PACK_V1:
      magic (20 B) + count (uint8, <= 128) + [len (uint8) + motif bytes]* + encoded stream
    где байт 0xFF + idx (uint8) разворачивается в motif[idx], а 0xFE + byte -> буквальный byte.
    """
    text = raw_utf8.decode("utf-8", errors="surrogateescape")
    freq: Counter[str] = Counter()
    for match in re.finditer(r'[^\s\x00-\x1f]{4,24}', text):
        tok = match.group(0)
        freq[tok] += 1

    # Фиксированные структурные мотивы JSONL + самые частые токены потока
    base_motifs = ['{"d":"', '","l":"', '","c":"', '","t":"', '"}', 'ru', 'en']
    candidates: list[str] = []
    seen: set[str] = set()
    for bm in base_motifs:
        if bm in text and bm not in seen:
            candidates.append(bm)
            seen.add(bm)

    for tok, cnt in freq.most_common(128):
        if len(candidates) >= 120:
            break
        if tok not in seen and cnt >= 2 and (cnt * (len(tok) - 2)) > (len(tok.encode("utf-8")) + 2):
            candidates.append(tok)
            seen.add(tok)

    motif_bytes = [m.encode("utf-8", errors="surrogateescape")[:250] for m in candidates]
    motif_strs = [b.decode("utf-8", errors="surrogateescape") for b in motif_bytes]
    # Длинные мотивы подставляем раньше коротких
    ordered = sorted(enumerate(motif_strs), key=lambda pair: -len(pair[1]))

    # Заменяем в тексте через нейтральные маркеры PUA (U+E000..U+E07F)
    work = text
    for idx, m_str in ordered:
        if m_str:
            work = work.replace(m_str, chr(0xE000 + idx))

    out = bytearray()
    out.extend(FLOW_PACK_MAGIC)
    out.append(len(motif_bytes))
    for mb in motif_bytes:
        out.append(len(mb))
        out.extend(mb)

    for ch in work:
        o = ord(ch)
        if 0xE000 <= o < 0xE000 + len(motif_bytes):
            out.append(_PACK_SENTINEL)
            out.append(o - 0xE000)
        else:
            for b in ch.encode("utf-8", errors="surrogateescape"):
                if b in (_PACK_SENTINEL, _PACK_ESCAPE):
                    out.append(_PACK_ESCAPE)
                out.append(b)

    packed = bytes(out)
    # Если файл совсем крошечный и словарь не дал выигрыша, сохраняем как чистый AVALON_QHOLO_V8
    if len(packed) >= len(raw_utf8):
        return fold_qholo_bytes(raw_utf8)
    return packed


def unpack_flow_segment(blob: bytes) -> bytes:
    """Обратимо распаковывает AVALON_FLOW_PACK_V1 или AVALON_QHOLO_V8."""
    if blob.startswith(QHOLO_MAGIC):
        body = blob[len(QHOLO_MAGIC):]
        return body.replace(b"\x01\x01", b"\x01")
    if not blob.startswith(FLOW_PACK_MAGIC):
        return blob

    pos = len(FLOW_PACK_MAGIC)
    if pos >= len(blob):
        return b""
    count = blob[pos]
    pos += 1
    motifs: list[bytes] = []
    for _ in range(count):
        if pos >= len(blob):
            break
        ln = blob[pos]
        pos += 1
        motifs.append(blob[pos : pos + ln])
        pos += ln

    out = bytearray()
    n = len(blob)
    while pos < n:
        b = blob[pos]
        pos += 1
        if b == _PACK_SENTINEL and pos < n:
            idx = blob[pos]
            pos += 1
            if idx < len(motifs):
                out.extend(motifs[idx])
        elif b == _PACK_ESCAPE and pos < n:
            out.append(blob[pos])
            pos += 1
        else:
            out.append(b)
    return bytes(out)


def _looks_like_password_token(tok: str) -> bool:
    low = tok.lower()
    if any(low.startswith(pref) for pref in _SECRET_PREFIXES):
        return True
    if _HEX_SECRET_RE.search(tok):
        return True
    if len(tok) < 8:
        return False
    has_cyr = any(("а" <= c.lower() <= "я") or c in "ёЁ" for c in tok)
    if has_cyr:
        return False
    classes = (
        any("a" <= c <= "z" for c in tok),
        any("A" <= c <= "Z" for c in tok),
        any(c.isdigit() for c in tok),
        any(not c.isalnum() for c in tok),
    )
    if sum(1 for c in classes if c) >= 3:
        # Исключаем обычные домены/пути с точками без спецсимволов пароля
        special_only = set("!@#$%^&*+=~?")
        if any(c in special_only for c in tok) or (sum(c.isdigit() for c in tok) >= 2 and any("A" <= c <= "Z" for c in tok)):
            return True
    return False


def sanitize_flow_line(raw_line: str) -> str | None:
    """Проверяет строку щитом приватности и очищает артефакты пунктуации."""
    text = re.sub(r"\s+", " ", (raw_line or "").replace("\x00", "")).strip()
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = re.sub(r"(?:\s*-\s*)+([,;:])", r"\1", text)
    text = re.sub(r"([,;:])(?:\s*\1)+", r"\1", text)
    text = re.sub(r"^[,;:\-\s]+", "", text).strip()
    text = re.sub(r"\s+-\s*$", "", text).strip()
    if len(text) < 3:
        return None
    if len(text) > MAX_LINE_CHARS:
        text = text[:MAX_LINE_CHARS].rstrip()

    if _OTP_ONLY_RE.match(text):
        return None
    if _SECRET_ASSIGN_RE.search(text):
        return None
    if _URL_CRED_RE.search(text):
        return None
    if _CARD_RE.search(text):
        return None
    if _HEX_SECRET_RE.search(text):
        return None

    low = text.lower()
    if any(pref in low for pref in ("github_pat_", "bearer ", "-----begin")):
        return None

    for tok in _WORD_OR_SPACE_RE.findall(text):
        if _looks_like_password_token(tok):
            return None

    alpha_count = sum(1 for ch in text if ch.isalpha())
    if alpha_count < 2:
        return None
    return text


def _detect_line_lang(text: str, hint: str | None = None) -> str:
    cyr = sum(1 for ch in text if ("а" <= ch.lower() <= "я") or ch in "ёЁ")
    lat = sum(1 for ch in text if "a" <= ch.lower() <= "z")
    if cyr > 0 and lat > 0:
        return "mix"
    if cyr > 0:
        return "ru"
    if lat > 0:
        return "en"
    h = (hint or "").lower()
    return h if h in ("ru", "en", "mix") else "ru"


_CODE_TOKEN_RE = re.compile(
    r"(?:[A-Za-z]:\\|/[A-Za-z0-9_.\-]+/|--[a-z0-9\-]+|\b[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z]{1,6}\b|"
    r"\b[a-z]+[A-Z][A-Za-z0-9]*\b|[A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]+|[A-Za-z_][A-Za-z0-9_]*\([^)]*\))"
)
_IMPERATIVE_STARTS: frozenset[str] = frozenset({
    "сделай", "добавь", "убери", "проверь", "создай", "воплоти", "запусти", "удали", "исправь",
    "покажи", "открой", "закрой", "найди", "перезапусти", "собери",
    "build", "run", "fix", "add", "check", "create", "remove", "make", "show", "open", "test",
})


def classify_flow_context(text: str) -> str:
    """«Золотой Ключик»: определяет смысловой контекст по содержанию текста (без имён программ)."""
    s = (text or "").strip()
    if not s:
        return "thought"

    if any(op in s for op in ("->", "::", "=>", ":=", "==", "!=", "</")):
        return "code"
    if re.search(r"\b(?:def|class|import|from|fn|func|const|let)\s+[A-Za-z_]", s):
        return "code"
    if "{" in s and "}" in s and (":" in s or ";" in s):
        return "code"

    words = s.split()
    code_hits = len(_CODE_TOKEN_RE.findall(s))
    if code_hits >= 2 and (code_hits / max(1, len(words))) >= 0.30:
        return "code"

    if "?" in s:
        return "question"

    first_word = words[0].lower().strip(".,!?:;\"'") if words else ""
    if s.startswith("/") or (len(words) <= 10 and first_word in _IMPERATIVE_STARTS):
        return "command"

    return "thought"


class SovereignFlowCorpus:
    """Суверенная локальная База Потока Мысли с анти-раздуванием и экспортом для любых ИИ."""

    def __init__(
        self,
        corpus_dir: Path | str,
        *,
        max_active_bytes: int = MAX_ACTIVE_BYTES_DEFAULT,
        max_total_bytes: int = MAX_TOTAL_BYTES_DEFAULT,
    ) -> None:
        self.corpus_dir = Path(corpus_dir)
        self.active_path = self.corpus_dir / "flow_corpus.jsonl"
        self.archive_dir = self.corpus_dir / "flow_archive"
        self.max_active_bytes = max(4096, int(max_active_bytes))
        self.max_total_bytes = max(self.max_active_bytes * 2, int(max_total_bytes))

        self._pending_words: list[str] = []
        self._pending_lang: str = "ru"
        self._pending_ctx: str = "flow"
        self._dedup_lru: OrderedDict[str, None] = OrderedDict()
        self._filtered_secrets_count: int = 0
        self._dedup_skipped_count: int = 0
        self._session_records_added: int = 0
        self._segment_seq: int = 0

    def pop_last_pending_word(self) -> str | None:
        """Удаляет последнее накопленное слово при Backspace через границу слова."""
        if not self._pending_words:
            return None
        return self._pending_words.pop()

    def discard_pending(self) -> None:
        """Сбрасывает незавершённый буфер текущей фразы."""
        self._pending_words.clear()

    def push_word(self, word: str, delim: str, lang_hint: str | None = None, ctx_tag: str = "flow") -> bool:
        """Накапливает выровненное слово в оперативном буфере; при переносе строки фиксирует мысль."""
        clean_word = (word or "").strip()
        if clean_word:
            if not self._pending_words:
                self._pending_ctx = ctx_tag or "flow"
                self._pending_lang = (lang_hint or "ru").lower()
            elif ctx_tag and self._pending_ctx != ctx_tag:
                self.flush_pending(min_words=1)
                self._pending_ctx = ctx_tag or "flow"
            self._pending_words.append(clean_word)
            if len(self._pending_words) >= 48:
                return self.flush_pending(min_words=1)

        if delim == "\n":
            alpha_total = sum(1 for w in self._pending_words for c in w if c.isalpha())
            return self.flush_pending(min_words=2 if alpha_total < 10 else 1)
        return False

    def flush_pending(self, min_words: int = 1) -> bool:
        """Пропускает накопленную фразу через щит приватности, дедупликатор и записывает на диск."""
        if not self._pending_words:
            return False
        alpha_words = [w for w in self._pending_words if any(ch.isalpha() for ch in w)]
        if len(alpha_words) < max(1, int(min_words)):
            self._pending_words.clear()
            return False
        raw_line = " ".join(self._pending_words)
        lang_hint = self._pending_lang
        ctx_tag = self._pending_ctx
        self._pending_words.clear()
        return self.record_line(raw_line, lang_hint=lang_hint, ctx_tag=ctx_tag)

    def record_line(self, raw_line: str, *, lang_hint: str | None = None, ctx_tag: str = "flow") -> bool:
        """Записывает очищенную и уникальную фразу в локальный JSONL-слой с контролем объёма."""
        if not raw_line or not raw_line.strip():
            return False
        sanitized = sanitize_flow_line(raw_line)
        if sanitized is None:
            self._filtered_secrets_count += 1
            return False

        sig = agls_432_hex(sanitized.lower().encode("utf-8"))[:16]
        if sig in self._dedup_lru:
            self._dedup_lru.move_to_end(sig)
            self._dedup_skipped_count += 1
            return False

        self._dedup_lru[sig] = None
        if len(self._dedup_lru) > DEDUP_CACHE_LIMIT:
            self._dedup_lru.popitem(last=False)

        if ctx_tag in ("", "app", "flow", "auto", None):
            effective_ctx = classify_flow_context(sanitized)
        else:
            effective_ctx = str(ctx_tag)[:24]

        rec = {
            "d": date.today().isoformat(),
            "l": _detect_line_lang(sanitized, hint=lang_hint),
            "c": effective_ctx[:24],
            "t": sanitized,
        }
        line_bytes = (json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        with self.active_path.open("ab") as fh:
            fh.write(line_bytes)

        self._session_records_added += 1
        self._enforce_size_limits()
        return True

    def _enforce_size_limits(self) -> None:
        if self.active_path.exists() and self.active_path.stat().st_size >= self.max_active_bytes:
            self._rotate_active_to_qholo()

        total_bytes = self._compute_sizes()[2]
        if total_bytes > self.max_total_bytes and self.archive_dir.exists():
            segments = sorted(self.archive_dir.glob("seg_*.qholo"))
            while total_bytes > self.max_total_bytes and segments:
                oldest = segments.pop(0)
                sz = oldest.stat().st_size
                oldest.unlink(missing_ok=True)
                total_bytes -= sz

    def _rotate_active_to_qholo(self) -> Path | None:
        if not self.active_path.exists():
            return None
        raw = self.active_path.read_bytes()
        if not raw:
            return None
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._segment_seq += 1
        existing = len(list(self.archive_dir.glob("seg_*.qholo")))
        seg_name = f"seg_{date.today().strftime('%Y%m%d')}_{existing + self._segment_seq:04d}.qholo"
        seg_path = self.archive_dir / seg_name
        seg_path.write_bytes(pack_flow_segment(raw))
        self.active_path.write_bytes(b"")
        return seg_path

    def _compute_sizes(self) -> tuple[int, int, int, int]:
        active_sz = self.active_path.stat().st_size if self.active_path.exists() else 0
        archived_sz = 0
        seg_count = 0
        if self.archive_dir.exists():
            for seg in self.archive_dir.glob("seg_*.qholo"):
                if seg.is_file():
                    archived_sz += seg.stat().st_size
                    seg_count += 1
        return active_sz, archived_sz, active_sz + archived_sz, seg_count

    def iter_all_records(self) -> Iterator[dict[str, str]]:
        """Возвращает все записи из холодных .qholo-сегментов и активного слоя в хронологическом порядке."""
        if self.archive_dir.exists():
            for seg in sorted(self.archive_dir.glob("seg_*.qholo")):
                try:
                    raw = unpack_flow_segment(seg.read_bytes()).decode("utf-8", errors="replace")
                    for line in raw.splitlines():
                        line = line.strip()
                        if line:
                            obj = json.loads(line)
                            if isinstance(obj, dict) and obj.get("t"):
                                yield obj
                except (OSError, ValueError):
                    continue

        if self.active_path.exists():
            try:
                raw = self.active_path.read_text(encoding="utf-8", errors="replace")
                for line in raw.splitlines():
                    line = line.strip()
                    if line:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and obj.get("t"):
                            yield obj
            except (OSError, ValueError):
                pass

    def stats(self) -> dict[str, Any]:
        active_sz, archived_sz, total_sz, seg_count = self._compute_sizes()
        records_count = sum(1 for _ in self.iter_all_records())
        return {
            "records_count": records_count,
            "pending_words": len(self._pending_words),
            "active_bytes": active_sz,
            "archived_bytes": archived_sz,
            "total_bytes": total_sz,
            "size_kb": round(total_sz / 1024.0, 2),
            "segments_count": seg_count,
            "filtered_secrets_count": self._filtered_secrets_count,
            "dedup_skipped_count": self._dedup_skipped_count,
            "session_records_added": self._session_records_added,
            "corpus_dir": str(self.corpus_dir),
        }

    def clear(self) -> int:
        """Полностью удаляет всю накопленную локальную Базу Потока и очищает буфер."""
        self._pending_words.clear()
        self._dedup_lru.clear()
        removed = 0
        if self.active_path.exists():
            self.active_path.unlink(missing_ok=True)
            removed += 1
        if self.archive_dir.exists():
            for seg in list(self.archive_dir.glob("seg_*.qholo")):
                seg.unlink(missing_ok=True)
                removed += 1
            try:
                self.archive_dir.rmdir()
            except OSError:
                pass
        if self.corpus_dir.exists():
            try:
                if not any(self.corpus_dir.iterdir()):
                    self.corpus_dir.rmdir()
            except OSError:
                pass
        return removed

    def export_for_ai(self, output_dir: Path | str | None = None, fmt: str = "all") -> dict[str, Any]:
        """Экспортирует локальную Базу Потока в универсальные форматы для любых моделей ИИ."""
        self.flush_pending()
        records = list(self.iter_all_records())
        target_dir = Path(output_dir) if output_dir else (self.corpus_dir / "exports")

        if not records:
            return {
                "success": False,
                "reason": "EMPTY_CORPUS",
                "records_count": 0,
                "export_dir": str(target_dir),
                "files": {},
            }

        target_dir.mkdir(parents=True, exist_ok=True)
        requested = {"chat_jsonl", "pretrain_jsonl", "markdown_rag", "qholo_crystal"} if fmt == "all" else {fmt}
        written: dict[str, str] = {}

        if "chat_jsonl" in requested:
            chat_path = target_dir / "avalon_flow_chat_sft.jsonl"
            lines_out: list[str] = []
            for rec in records:
                lang = str(rec.get("l", "ru"))
                ctx = str(rec.get("c", "app"))
                dt = str(rec.get("d", ""))
                if lang == "en":
                    prompt = f"Express the author's thought naturally (context: {ctx}, language: en)."
                else:
                    prompt = f"Сформулируй мысль в естественном стиле автора (контекст: {ctx}, язык: {lang})."
                dialogue = {
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": rec["t"]},
                    ],
                    "meta": {"date": dt, "context": ctx, "lang": lang},
                }
                lines_out.append(json.dumps(dialogue, ensure_ascii=False))
            chat_path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
            written["chat_jsonl"] = str(chat_path)

        if "pretrain_jsonl" in requested:
            pre_path = target_dir / "avalon_flow_pretrain.jsonl"
            pre_lines = [
                json.dumps(
                    {
                        "text": r["t"],
                        "lang": r.get("l", "ru"),
                        "date": r.get("d", ""),
                        "context": r.get("c", "app"),
                    },
                    ensure_ascii=False,
                )
                for r in records
            ]
            pre_path.write_text("\n".join(pre_lines) + "\n", encoding="utf-8")
            written["pretrain_jsonl"] = str(pre_path)

        if "markdown_rag" in requested:
            md_path = target_dir / "avalon_flow_knowledge.md"
            md_lines = [
                "# Личная База Потока • Avalon.Shifter Knowledge Export",
                "",
                f"> **Хроно-Паспорт документа:** Создан: `{date.today().isoformat()}` • Всего записей: `{len(records)}` • Источник: `SovereignFlowCorpus (0% Analytics)`",
                "",
                "| Дата | Контекст | Язык | Фраза потока |",
                "| :--- | :--- | :---: | :--- |",
            ]
            for r in records:
                safe_t = str(r.get("t", "")).replace("|", "\\|")
                md_lines.append(f"| `{r.get('d', '')}` | `{r.get('c', 'app')}` | `{r.get('l', 'ru')}` | {safe_t} |")
            md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
            written["markdown_rag"] = str(md_path)

        if "qholo_crystal" in requested:
            qholo_path = target_dir / "avalon_flow_sovereign.qholo"
            payload = {
                "format": "AVALON_SHIFTER_FLOW_CRYSTAL",
                "exported_at": date.today().isoformat(),
                "resonance_hz": 432.0,
                "zero_analytics": True,
                "sovereign_basis": "SAB-432",
                "records_count": len(records),
                "records": records,
            }
            unsigned_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            payload["integrity_seal"] = {
                "algorithm": "AGLS-432-Phi",
                "digest_hex": agls_432_hex(unsigned_bytes),
            }
            sealed_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            qholo_path.write_bytes(fold_qholo_bytes(sealed_bytes))
            written["qholo_crystal"] = str(qholo_path)

        bundle_seal = agls_432_hex(json.dumps(written, sort_keys=True).encode("utf-8"))[:24]
        return {
            "success": True,
            "records_count": len(records),
            "export_dir": str(target_dir),
            "files": written,
            "agls_seal": bundle_seal,
        }


def verify_qholo_crystal(raw_or_path: bytes | Path | str) -> dict[str, Any]:
    """Проверяет заголовок AVALON_QHOLO_V8 и подпись AGLS-432-Phi кристалла .qholo."""
    try:
        if isinstance(raw_or_path, (bytes, bytearray)):
            raw = bytes(raw_or_path)
        else:
            raw = Path(raw_or_path).read_bytes()
    except OSError:
        return {"valid": False, "records_count": 0, "digest_hex": "", "resonance_hz": 0.0}

    if not raw.startswith(QHOLO_MAGIC):
        return {"valid": False, "records_count": 0, "digest_hex": "", "resonance_hz": 0.0}

    try:
        unfolded = unpack_flow_segment(raw)
        payload = json.loads(unfolded.decode("utf-8"))
        if not isinstance(payload, dict):
            return {"valid": False, "records_count": 0, "digest_hex": "", "resonance_hz": 0.0}
        seal_obj = payload.pop("integrity_seal", None)
        if not isinstance(seal_obj, dict):
            return {"valid": False, "records_count": 0, "digest_hex": "", "resonance_hz": 0.0}
        stored_hex = str(seal_obj.get("digest_hex", "")).lower()
        unsigned_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        computed_hex = agls_432_hex(unsigned_bytes)
        valid = len(stored_hex) == 64 and stored_hex == computed_hex
        return {
            "valid": valid,
            "records_count": int(payload.get("records_count", 0)),
            "digest_hex": computed_hex,
            "resonance_hz": float(payload.get("resonance_hz", 432.0)),
        }
    except (UnicodeDecodeError, ValueError, TypeError):
        return {"valid": False, "records_count": 0, "digest_hex": "", "resonance_hz": 0.0}
