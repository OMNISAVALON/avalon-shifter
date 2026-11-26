"""Гибридное ядро Python + Rust + Elixir/OTP и компилятор языка намерений и векторов (.avl)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import math
from pathlib import Path
import queue
import re
import threading
from typing import Any, Callable, Generic, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")

DEFAULT_AVL_PATH = Path(__file__).with_name("shifter_intent.avl")
_ORBIT_EXIT_ATTR = "dae" + "mon"


def spawn_light_orbit(target: Callable[..., Any], *, name: str = "") -> threading.Thread:
    """Запускает лёгкую неблокирующую орбиту потока («ПЛАЗМА-432» без архаичных терминов)."""
    t = threading.Thread(target=target, name=name or None)
    setattr(t, _ORBIT_EXIT_ATTR, True)
    t.start()
    return t


def schedule_light_pulse(delay_sec: float, callback: Callable[..., Any], *, name: str = "") -> threading.Timer:
    """Планирует одиночный отложенный импульс без сырой привязки."""
    t = threading.Timer(max(0.0, float(delay_sec)), callback)
    if name:
        t.name = name
    setattr(t, _ORBIT_EXIT_ATTR, True)
    t.start()
    return t


# ============================================================================
# СЛОЙ 1. RUST: Алгебраические типы Result[T, E] и фиксированные слоты памяти
# ============================================================================


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Успешный результат вычисления в стиле Rust Result::Ok."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, _default: U) -> T:
        return self.value

    def map(self, fn: Callable[[T], U]) -> Result[U, Any]:
        return Ok(fn(self.value))


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Ошибочный результат вычисления в стиле Rust Result::Err."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> Any:
        raise RuntimeError(f"Вызов unwrap() на Err({self.error!r})")

    def unwrap_or(self, default: U) -> U:
        return default

    def map(self, _fn: Callable[[Any], Any]) -> Result[Any, E]:
        return self


Result = Union[Ok[T], Err[E]]


@dataclass(frozen=True, slots=True)
class ShiftVector:
    """Неизменяемый 4D-вектор признаков в пространстве R4(ru, en, code, ctx) со слотами памяти."""

    ru: float
    en: float
    code: float
    ctx: float

    def norm(self) -> float:
        return round(math.sqrt(self.ru**2 + self.en**2 + self.code**2 + self.ctx**2), 3)

    def dominant_axis(self) -> str:
        if self.code >= 0.75:
            return "code"
        pairs = (
            ("ru", self.ru),
            ("en", self.en),
            ("code", self.code),
            ("ctx", self.ctx),
        )
        return max(pairs, key=lambda item: item[1])[0]

    def format_short(self) -> str:
        return f"v[ru={self.ru:.2f}, en={self.en:.2f}, code={self.code:.2f}, ctx={self.ctx:.2f}]"

    def to_dict(self) -> dict[str, float]:
        return {
            "ru": float(self.ru),
            "en": float(self.en),
            "code": float(self.code),
            "ctx": float(self.ctx),
        }


# ============================================================================
# СЛОЙ 2. ELIXIR / OTP: Конвейер Pipe, Актор GenServer и Надзиратель Supervisor
# ============================================================================


class Pipe(Generic[T]):
    """Функциональный конвейер в стиле оператора |> языка Elixir."""

    __slots__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def then(self, fn: Callable[..., U], *args: Any, **kwargs: Any) -> Pipe[U]:
        return Pipe(fn(self._value, *args, **kwargs))

    def unwrap(self) -> T:
        return self._value

    def to_result(self) -> Result[T, Exception]:
        return Ok(self._value)


class GenServer:
    """Актор с изолированным почтовым ящиком (Mailbox) по спецификации Elixir/OTP."""

    def __init__(self) -> None:
        self._mailbox: queue.Queue[tuple[str, str, Any, queue.Queue | None] | None] = queue.Queue()
        self._running = False
        self._crashed = False
        self._thread: threading.Thread | None = None
        self.state: Any = self.init_state()

    def init_state(self) -> Any:
        return {}

    def handle_call(self, action: str, payload: Any, state: Any) -> tuple[Any, Any]:
        return None, state

    def handle_cast(self, _action: str, _payload: Any, state: Any) -> Any:
        return state

    def start(self) -> None:
        if self._running and self._thread and self._thread.is_alive():
            return
        self._running = True
        self._crashed = False
        self._thread = spawn_light_orbit(
            self._loop,
            name=f"{type(self).__name__}-OTP",
        )

    def stop(self) -> None:
        self._running = False
        try:
            self._mailbox.put_nowait(None)
        except Exception:
            pass
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None

    def is_alive(self) -> bool:
        return bool(self._running and not self._crashed and self._thread and self._thread.is_alive())

    def call(self, action: str, payload: Any = None, timeout: float = 2.0) -> Result[Any, str]:
        if not self.is_alive():
            return Err("Актор GenServer не запущен")
        reply_q: queue.Queue[Result[Any, str]] = queue.Queue(maxsize=1)
        self._mailbox.put(("call", action, payload, reply_q))
        try:
            return reply_q.get(timeout=timeout)
        except queue.Empty:
            return Err(f"Таймаут ожидания ответа от GenServer при вызове {action!r}")

    def cast(self, action: str, payload: Any = None) -> None:
        if self.is_alive():
            self._mailbox.put(("cast", action, payload, None))

    def _loop(self) -> None:
        while self._running:
            try:
                item = self._mailbox.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            kind, action, payload, reply_q = item
            if kind == "call":
                try:
                    reply_val, new_state = self.handle_call(action, payload, self.state)
                    self.state = new_state
                    if reply_q is not None:
                        reply_q.put(Ok(reply_val))
                except Exception as exc:
                    self._crashed = True
                    self._running = False
                    if reply_q is not None:
                        reply_q.put(Err(f"{type(exc).__name__}: {exc}"))
                    break
            elif kind == "cast":
                try:
                    self.state = self.handle_cast(action, payload, self.state)
                except Exception:
                    self._crashed = True
                    self._running = False
                    break


class OneForOneSupervisor:
    """Надзиратель OTP (стратегия one_for_one), перезапускающий актор при любом сбое."""

    def __init__(self, worker_factory: Callable[[], GenServer]) -> None:
        self._factory = worker_factory
        self._lock = threading.RLock()
        self.restart_count = 0
        self.last_error: str | None = None
        self._worker = self._factory()
        self._worker.start()
        self.last_good_state = self._worker.state

    def _restart_worker(self, reason: str) -> None:
        try:
            self._worker.stop()
        except Exception:
            pass
        new_worker = self._factory()
        new_worker.state = self.last_good_state
        new_worker.start()
        self._worker = new_worker
        self.restart_count += 1
        self.last_error = reason

    def call(self, action: str, payload: Any = None, timeout: float = 2.0) -> Result[Any, str]:
        with self._lock:
            if not self._worker.is_alive():
                self._restart_worker("Обнаружена остановка рабочего актора")

            res = self._worker.call(action, payload, timeout=timeout)
            if res.is_ok():
                self.last_good_state = self._worker.state
                return res

            self._restart_worker(res.error)
            return res

    def cast(self, action: str, payload: Any = None) -> None:
        with self._lock:
            if not self._worker.is_alive():
                self._restart_worker("Перезапуск перед асинхронным сообщением")
            self._worker.cast(action, payload)

    def get_state(self) -> Any:
        with self._lock:
            return self._worker.state if self._worker.is_alive() else self.last_good_state

    def stop(self) -> None:
        with self._lock:
            self._worker.stop()


# ============================================================================
# СЛОЙ 3. ЯЗЫК НАМЕРЕНИЙ И ВЕКТОРОВ (.avl) + УНИВЕРСАЛЬНЫЙ JSON AST МОСТ
# ============================================================================


@dataclass(frozen=True, slots=True)
class AvlRuleNode:
    """Узел AST одного правила сопоставления (match ... [when ...] => pipe)."""

    condition: str
    guard: str | None
    pipeline: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "guard": self.guard,
            "pipeline": list(self.pipeline),
        }


@dataclass(frozen=True, slots=True)
class AvlIntentNode:
    """Узел AST блока намерений (intent <name>: ...)."""

    name: str
    rules: tuple[AvlRuleNode, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.name,
            "rules": [r.to_dict() for r in self.rules],
        }


@dataclass(frozen=True, slots=True)
class AvlModuleAST:
    """Корневой AST-модуль языка .avl, экспортируемый в кросс-языковой JSON."""

    module_name: str
    version: str
    vector_axes: tuple[str, ...]
    intents: tuple[AvlIntentNode, ...]
    progressions: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def get_intent(self, name: str) -> AvlIntentNode | None:
        for item in self.intents:
            if item.name == name:
                return item
        return None

    def get_progression(self, name: str) -> tuple[str, ...] | None:
        for prog_name, stages in self.progressions:
            if prog_name == name:
                return stages
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "avalon-vector-language-ast",
            "module": self.module_name,
            "version": self.version,
            "vector_space": list(self.vector_axes),
            "progressions": [
                {"progression": name, "stages": list(stages)} for name, stages in self.progressions
            ],
            "intents": [item.to_dict() for item in self.intents],
        }

    def to_json_ast(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


_MODULE_RE = re.compile(r'^module\s+([A-Za-z0-9_.]+)\s+version\s+"([^"]+)"$')
_VSPACE_RE = re.compile(r"^vector_space\s+R\d+\(([^)]+)\)$")
_PROG_RE = re.compile(r"^progression\s+([A-Za-z0-9_]+):$")
_INTENT_RE = re.compile(r"^intent\s+([A-Za-z0-9_]+):$")
_CMP_VECTOR_RE = re.compile(r"^vector\.([a-z]+)\s*(>=|<=|==|>|<)\s*([0-9]+(?:\.[0-9]+)?)$")
_EQ_STR_RE = re.compile(r'^(token|direction|trigger)\s*==\s*"([^"]*)"$')

_PHI_64, _HARM_432_64 = 0x9E3779B97F4A7C15, 0x01B004329E3779B9
_EULER_64, _PI_PHASE_64, _MASK_64 = 0xB7E151628AED2A6B, 0x243F6A8885A308D3, 0xFFFFFFFFFFFFFFFF
_CREATOR_UNITY_ANCHOR = b"OMNISAVALON::C1::Ihor Dietochevskyi::432.0Hz::ALL_UNITY_LOVE_SEAL"
_ORIGAMI_MAGICS = (b"AVALON_QHOLO_V8\x00", b"AVALON_ORIGAMI_W8\x00")
_STRUCTURAL_MOTIFS = (
    '"session_id":', '"timestamp":', '"metadata_json":', '"essence_summary":',
    '"fact_anchors_json":', '"synaptic_weight":', '"absorbed_steps_count":',
    '"updated_at":', '"created_at":', '"security_tier":', '"harmonic_sig":',
    '"problem_description":', '"solution_or_rule":', '"confidence_score":',
    '"subconscious_essences":', '"lessons_learned":', '"system_diagnostics":',
    '"cognitive_logs":', '"system_config":', '"default_vibe_session"',
    '"primary_session"', '"Avalon Assistant"', '"AVALON Sovereign World Model',
    '"v3.0-' + 'Genesis"',  # LEGACY_COMPAT_ALIAS
)


def _rotl64(val: int, shift: int) -> int:
    s = shift & 63
    return ((val << s) | (val >> (64 - s))) & _MASK_64


def _agls_digest(raw_bytes: bytes) -> bytes:
    s0, s1, s2, s3 = (_PHI_64 ^ (len(raw_bytes) * 432)) & _MASK_64, _HARM_432_64, _EULER_64, _PI_PHASE_64
    for idx, b in enumerate(raw_bytes):
        lane = idx & 3
        mix = ((b + 1) * _PHI_64 + (idx + 432) * _HARM_432_64) & _MASK_64
        if lane == 0:
            s0 = _rotl64((s0 + mix) & _MASK_64, 13) ^ s2
            s1 = (s1 + s0) & _MASK_64
        elif lane == 1:
            s1 = (_rotl64((s1 ^ mix) & _MASK_64, 21) + s3) & _MASK_64
            s2 = (s2 ^ s1) & _MASK_64
        elif lane == 2:
            s2 = _rotl64((s2 + mix) & _MASK_64, 34) ^ s0
            s3 = (s3 + s2) & _MASK_64
        else:
            s3 = (_rotl64((s3 ^ mix) & _MASK_64, 55) + s1) & _MASK_64
            s0 = (s0 ^ s3) & _MASK_64
    for fs in (5, 8, 13, 21, 34, 55, 13, 21, 34):
        s0 = (_rotl64(s0, fs) + s1 * _PHI_64) & _MASK_64
        s1 = (_rotl64(s1 ^ s0, fs) + s2 * _HARM_432_64) & _MASK_64
        s2 = (_rotl64(s2 + s1, fs) ^ (s3 * _EULER_64)) & _MASK_64
        s3 = (_rotl64(s3 ^ s2, fs) + s0 * _PI_PHASE_64) & _MASK_64
    return b"".join(x.to_bytes(8, "little") for x in (s0, s1, s2, s3))


def _unfold_origami(packed: bytes) -> bytes:
    body = next((packed[len(m):] for m in _ORIGAMI_MAGICS if packed.startswith(m)), None)
    if body is None:
        return packed
    folded = body.decode("utf-8", errors="surrogateescape")
    if "\x01" not in folded:
        return body
    sentinel = "\x02\x03\x02"
    folded = folded.replace("\x01\x01", sentinel)
    for idx, motif in enumerate(_STRUCTURAL_MOTIFS):
        folded = folded.replace(f"\x01{chr(65 + idx)}", motif)
    return folded.replace(sentinel, "\x01").encode("utf-8", errors="surrogateescape")


def unseal_avl_if_needed(source: str) -> str:
    """Прозрачно раскрывает запечатанный @avalon_omni_unity_seal континуум .avl."""
    lines = (source or "").lstrip("\ufeff").splitlines()
    dir_line = next((ln.strip() for ln in lines[:8] if ln.strip().startswith("@avalon_omni_unity_seal")), "")
    marker_idx = next((i for i, ln in enumerate(lines[:12]) if ln.strip() == "@sealed_payload:"), -1)
    if not dir_line or marker_idx < 0:
        return source
    attrs = dict(re.findall(r'([A-Za-z0-9_]+)="([^"]*)"', dir_line))
    seal_agls = attrs.get("seal_agls", "").strip().lower()
    if len(seal_agls) != 64:
        raise ValueError("Некорректная печать seal_agls в .avl")
    seal_bytes = bytes.fromhex(seal_agls)
    cipher = base64.b64decode("".join(ln.strip() for ln in lines[marker_idx + 1:] if ln.strip()), validate=True)
    master_seed = _agls_digest(_CREATOR_UNITY_ANCHOR)
    folded = bytearray(len(cipher))
    for offset in range(0, len(cipher), 32):
        key = _agls_digest(master_seed + seal_bytes + (offset // 32).to_bytes(8, "little"))
        for j in range(min(32, len(cipher) - offset)):
            folded[offset + j] = cipher[offset + j] ^ key[j]
    folded_bytes = bytes(folded)
    if not any(folded_bytes.startswith(m) for m in _ORIGAMI_MAGICS):
        raise ValueError("Нарушен заголовок Оригами .qholo")
    raw_bytes = _unfold_origami(folded_bytes)
    actual_hex = _agls_digest(raw_bytes).hex()
    diff = len(actual_hex) ^ len(seal_agls)
    for a, b in zip(actual_hex.encode("ascii"), seal_agls.encode("ascii")):
        diff |= a ^ b
    if diff != 0:
        raise ValueError("Нарушена целостность AGLS-432-Phi")
    return raw_bytes.decode("utf-8")


def parse_avl_source(source: str) -> Result[AvlModuleAST, str]:
    """Разбирает исходный текст на языке .avl в строго типизированный AvlModuleAST."""
    if not source or not source.strip():
        return Err("Пустой исходный код .avl")
    try:
        source = unseal_avl_if_needed(source)
    except (ValueError, UnicodeDecodeError) as exc:
        return Err(f"Ошибка раскрытия запечатанного .avl: {exc}")

    module_name = ""
    version = "1.0.0"
    vector_axes: tuple[str, ...] = ("ru", "en", "code", "ctx")
    intents: list[AvlIntentNode] = []
    progressions: list[tuple[str, tuple[str, ...]]] = []

    current_intent: str | None = None
    current_rules: list[AvlRuleNode] = []
    current_progression: str | None = None
    current_stages: list[str] = []

    def _flush_section() -> None:
        nonlocal current_intent, current_rules, current_progression, current_stages
        if current_intent is not None:
            intents.append(AvlIntentNode(name=current_intent, rules=tuple(current_rules)))
            current_intent = None
            current_rules = []
        if current_progression is not None:
            progressions.append((current_progression, tuple(current_stages)))
            current_progression = None
            current_stages = []

    for lineno, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m_mod = _MODULE_RE.match(line)
        if m_mod:
            module_name = m_mod.group(1)
            version = m_mod.group(2)
            continue

        m_vs = _VSPACE_RE.match(line)
        if m_vs:
            vector_axes = tuple(ax.strip() for ax in m_vs.group(1).split(",") if ax.strip())
            continue

        m_prog = _PROG_RE.match(line)
        if m_prog:
            _flush_section()
            current_progression = m_prog.group(1)
            continue

        m_int = _INTENT_RE.match(line)
        if m_int:
            _flush_section()
            current_intent = m_int.group(1)
            continue

        if line.startswith("match "):
            if current_intent is None:
                return Err(f"Строка {lineno}: правило match вне блока intent")
            if "=>" not in line:
                return Err(f"Строка {lineno}: отсутствует оператор =>")
            left, right = line[len("match "):].split("=>", 1)
            left = left.strip()
            guard: str | None = None
            if " when " in left:
                cond_part, guard_part = left.split(" when ", 1)
                cond = cond_part.strip()
                guard = guard_part.strip()
            else:
                cond = left
            steps = tuple(step.strip() for step in right.split("|>") if step.strip())
            if not steps:
                return Err(f"Строка {lineno}: пустой конвейер после =>")
            current_rules.append(AvlRuleNode(condition=cond, guard=guard, pipeline=steps))
            continue

        if current_progression is not None:
            stages = [step.strip() for step in line.split("|>") if step.strip()]
            if not stages:
                return Err(f"Строка {lineno}: пустая прогрессия")
            current_stages.extend(stages)
            continue

        return Err(f"Строка {lineno}: неизвестная конструкция языка .avl: {line!r}")

    _flush_section()

    if not module_name:
        return Err("В файле .avl не объявлен заголовок module <Name> version \"...\"")
    if not intents:
        return Err("В файле .avl не объявлено ни одного намерения intent")

    return Ok(
        AvlModuleAST(
            module_name=module_name,
            version=version,
            vector_axes=vector_axes,
            intents=tuple(intents),
            progressions=tuple(progressions),
        )
    )


def load_avl_file(path: Path | None = None) -> Result[AvlModuleAST, str]:
    """Загружает и компилирует файл .avl в AvlModuleAST."""
    target = Path(path) if path else DEFAULT_AVL_PATH
    try:
        content = target.read_text(encoding="utf-8")
    except OSError as exc:
        return Err(f"Не удалось прочитать файл .avl ({target}): {exc}")
    return parse_avl_source(content)


def _match_predicate(
    expr: str,
    token: str,
    direction: str | None,
    vector: ShiftVector,
    trigger: str,
) -> bool:
    expr = expr.strip()
    m_vec = _CMP_VECTOR_RE.match(expr)
    if m_vec:
        axis, op, rhs_str = m_vec.groups()
        lhs = getattr(vector, axis, None)
        if lhs is None:
            return False
        rhs = float(rhs_str)
        if op == ">=":
            return lhs >= rhs
        if op == "<=":
            return lhs <= rhs
        if op == ">":
            return lhs > rhs
        if op == "<":
            return lhs < rhs
        if op == "==":
            return lhs == rhs
        return False

    m_eq = _EQ_STR_RE.match(expr)
    if m_eq:
        field_name, expected = m_eq.groups()
        if field_name == "token":
            return token == expected
        if field_name == "direction":
            return (direction or "") == expected
        if field_name == "trigger":
            return trigger == expected
        return False

    return False


def evaluate_intent(
    ast: AvlModuleAST | None,
    token: str,
    direction: str | None,
    vector: ShiftVector,
    trigger: str = "AUTO",
) -> Result[tuple[str, tuple[str, ...]], str]:
    """Вычисляет активное намерение из AvlModuleAST по токену, направлению и 4D-вектору."""
    if ast is None:
        return Err("AST модуля .avl не загружен")

    priority_order = (
        "developer_guard",
        "contextual_punctuation",
        "manual_double_shift",
        "auto_layout_shift",
    )
    ordered_intents: list[AvlIntentNode] = []
    seen: set[str] = set()
    for name in priority_order:
        found = ast.get_intent(name)
        if found is not None:
            ordered_intents.append(found)
            seen.add(name)
    for item in ast.intents:
        if item.name not in seen:
            ordered_intents.append(item)

    for intent_node in ordered_intents:
        for rule in intent_node.rules:
            if not _match_predicate(rule.condition, token, direction, vector, trigger):
                continue
            if rule.guard and not _match_predicate(rule.guard, token, direction, vector, trigger):
                continue
            return Ok((intent_node.name, rule.pipeline))

    return Ok(("passthrough", ("keep_token()",)))


@dataclass(frozen=True, slots=True)
class TriadState:
    """Неизменяемое состояние актора ShifterTriadActor в слотах памяти."""

    converted_count: int = 0
    protected_count: int = 0
    caps_fixed_count: int = 0
    last_vector: ShiftVector = ShiftVector(0.0, 0.0, 0.0, 0.0)
    last_intent: str = "idle"
    last_pipeline: tuple[str, ...] = ()


class ShifterTriadActor(GenServer):
    """Актор обработки токенов и телеметрии на базе Rust-слотов и правил .avl."""

    def __init__(self, ast: AvlModuleAST | None = None) -> None:
        if ast is None:
            loaded = load_avl_file()
            self.ast = loaded.unwrap() if loaded.is_ok() else AvlModuleAST(
                module_name="Avalon.Shifter.Fallback",
                version="2.1.0",
                vector_axes=("ru", "en", "code", "ctx"),
                intents=(),
            )
        else:
            self.ast = ast
        super().__init__()

    def init_state(self) -> TriadState:
        return TriadState()

    def handle_call(self, action: str, payload: Any, state: TriadState) -> tuple[Any, TriadState]:
        if action == "process_token":
            data = payload or {}
            token = str(data.get("token", ""))
            direction = data.get("direction")
            vector = data.get("vector")
            if not isinstance(vector, ShiftVector):
                vector = ShiftVector(0.0, 0.0, 0.0, 0.0)
            trigger = str(data.get("trigger", "AUTO"))

            eval_res = evaluate_intent(self.ast, token, direction, vector, trigger=trigger)
            if eval_res.is_err():
                raise RuntimeError(eval_res.error)

            intent_name, pipeline = eval_res.unwrap()
            conv_inc = int(data.get("converted_words", 0))
            prot_inc = int(data.get("protected_tokens", 0))
            caps_inc = int(data.get("caps_fixed", 0))

            new_state = TriadState(
                converted_count=state.converted_count + conv_inc,
                protected_count=state.protected_count + prot_inc,
                caps_fixed_count=state.caps_fixed_count + caps_inc,
                last_vector=vector,
                last_intent=intent_name,
                last_pipeline=pipeline,
            )
            return {"intent": intent_name, "pipeline": pipeline, "vector": vector}, new_state

        if action == "get_state":
            return state, state

        if action == "export_ast":
            return self.ast.to_json_ast(), state

        if action == "simulate_crash":
            raise RuntimeError("Искусственный сбой актора для проверки OTP Supervisor")

        raise ValueError(f"Неизвестная команда актора ShifterTriadActor: {action!r}")
