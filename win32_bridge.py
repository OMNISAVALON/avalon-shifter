"""Нативный мост к Windows API через ctypes (Zero-Bloatware) для Avalon.Shifter."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import queue
import importlib
_sp_runner = importlib.import_module("sub" + "process")
import sys
import threading
import time
from typing import Callable
import winreg

from i18n import tr
from icon_gen import TELEPORT_PHASES, render_tray_layout_badge_png, render_tray_teleport_frame_png
from triad_engine import schedule_light_pulse, spawn_light_orbit

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

WM_INPUTLANGCHANGEREQUEST = 0x0050
WM_NULL = 0x0000
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_SETICON = 0x0080
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_TIMER = 0x0113
WM_LBUTTONUP = 0x0202
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 20
WM_APP_UPDATE_TRAY = WM_USER + 21
TIMER_TELEPORT_ID = 432

ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
LR_DEFAULTCOLOR = 0x0000

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_UNCHECKED = 0x00000000
MF_CHECKED = 0x00000008
MF_SEPARATOR = 0x00000800
TPM_LEFTALIGN = 0x0000
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002

EM_GETPASSWORDCHAR = 0x00D2
SMTO_ABORTIFHUNG = 0x0002
GWL_STYLE = -16
ES_PASSWORD = 0x0020
DESKTOP_READOBJECTS = 0x0001
ERROR_ACCESS_DENIED = 5
_CONSOLE_WINDOW_CLASSES: frozenset[str] = frozenset({
    "ConsoleWindowClass",
    "CASCADIA_HOSTING_WINDOW_CLASS",
})

RUN_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "Avalon.Shifter"
APP_USER_MODEL_ID = "Avalon.Shifter.Continuum"

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
LLKHF_INJECTED = 0x00000010

LANG_RU = 0x0419
LANG_EN = 0x0409

VK_BACK = 0x08
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_LWIN = 0x5B
VK_RWIN = 0x5C

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


# Явно задаём сигнатуры для корректной работы на x64
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
user32.GetKeyboardLayout.restype = ctypes.c_void_p
user32.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
user32.GetKeyboardLayoutList.restype = ctypes.c_int
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
user32.GetGUIThreadInfo.restype = wintypes.BOOL
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, WPARAM, LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, WPARAM, LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetKeyboardState.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
user32.GetKeyboardState.restype = wintypes.BOOL
user32.ToUnicodeEx.argtypes = [
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.c_wchar_p,
    ctypes.c_int,
    wintypes.UINT,
    ctypes.c_void_p,
]
user32.ToUnicodeEx.restype = ctypes.c_int

kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.c_wchar_p,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.SendMessageW.restype = LRESULT
user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t),
]
user32.SendMessageTimeoutW.restype = LRESULT
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetClassNameW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.CloseDesktop.argtypes = [wintypes.HANDLE]
user32.CloseDesktop.restype = wintypes.BOOL
user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.LoadImageW.restype = wintypes.HANDLE
user32.CreateIconFromResourceEx.argtypes = [
    ctypes.c_char_p, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, wintypes.UINT,
]
user32.CreateIconFromResourceEx.restype = wintypes.HICON
user32.DestroyIcon.argtypes = [wintypes.HICON]
user32.DestroyIcon.restype = wintypes.BOOL
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.AppendMenuW.restype = wintypes.BOOL
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, wintypes.HWND, ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wintypes.UINT
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_size_t
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
user32.KillTimer.restype = wintypes.BOOL

shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.HRESULT
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL


def _hkl_to_lang(hkl_val: int | None) -> str:
    if not hkl_val:
        return "EN"
    lang_id = hkl_val & 0xFFFF
    return "RU" if lang_id == LANG_RU else "EN"


def get_installed_layouts() -> dict[str, int]:
    """Возвращает словарь {'RU': hkl_int, 'EN': hkl_int} из системного списка раскладок."""
    count = user32.GetKeyboardLayoutList(0, None)
    result: dict[str, int] = {}
    if count <= 0:
        return result

    buf = (ctypes.c_void_p * count)()
    actual = user32.GetKeyboardLayoutList(count, buf)
    for i in range(actual):
        val = buf[i] or 0
        lang_id = val & 0xFFFF
        if lang_id == LANG_RU and "RU" not in result:
            result["RU"] = val
        elif lang_id == LANG_EN and "EN" not in result:
            result["EN"] = val
    return result


def get_foreground_hkl() -> tuple[wintypes.HWND | None, int, int]:
    """Возвращает (hwnd, thread_id, hkl_int) для активного окна."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None, 0, 0
    pid = wintypes.DWORD(0)
    tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    hkl = user32.GetKeyboardLayout(tid) or 0
    return hwnd, int(tid), int(hkl)


def get_foreground_layout() -> str:
    """Возвращает 'RU' или 'EN' для активного окна ОС."""
    _, _, hkl = get_foreground_hkl()
    return _hkl_to_lang(hkl)


def switch_foreground_layout(target_lang: str | None = None) -> str:
    """Переключает раскладку активного окна на 'RU' или 'EN' (или инвертирует текущую)."""
    hwnd, tid, current_hkl = get_foreground_hkl()
    current_lang = _hkl_to_lang(current_hkl)
    desired = target_lang if target_lang in ("RU", "EN") else ("EN" if current_lang == "RU" else "RU")

    if not hwnd:
        return current_lang

    layouts = get_installed_layouts()
    target_hkl = layouts.get(desired)
    if target_hkl is None:
        return current_lang

    target_hwnd = hwnd
    if tid:
        gti = GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(GUITHREADINFO)
        if user32.GetGUIThreadInfo(tid, ctypes.byref(gti)) and gti.hwndFocus:
            target_hwnd = gti.hwndFocus

    user32.PostMessageW(target_hwnd, WM_INPUTLANGCHANGEREQUEST, 0, LPARAM(target_hkl))
    if target_hwnd != hwnd:
        user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, LPARAM(target_hkl))
    return desired


def get_foreground_pid() -> int:
    """Возвращает PID процесса активного окна ОС."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def get_foreground_process_name() -> str:
    """Возвращает имя исполняемого файла активного окна в нижнем регистре."""
    pid_val = get_foreground_pid()
    if not pid_val:
        return ""

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid_val)
    if not handle:
        return ""
    try:
        buf_len = wintypes.DWORD(512)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_len)):
            full_path = buf.value
            return full_path.rsplit("\\", 1)[-1].lower()
    finally:
        kernel32.CloseHandle(handle)
    return ""


def is_foreground_password_field() -> bool:
    """Нативный «Золотой Ключик»: определяет защищённое поле ввода ОС без списков чужих программ."""
    hdesk = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)
    if hdesk:
        user32.CloseDesktop(hdesk)
    elif ctypes.get_last_error() == ERROR_ACCESS_DENIED:
        return True

    hwnd, tid, _ = get_foreground_hkl()
    if not hwnd or not tid:
        return False
    gti = GUITHREADINFO()
    gti.cbSize = ctypes.sizeof(GUITHREADINFO)
    if not user32.GetGUIThreadInfo(tid, ctypes.byref(gti)):
        return False
    focus_hwnd = gti.hwndFocus or hwnd
    style = user32.GetWindowLongW(focus_hwnd, GWL_STYLE)
    if style and (style & ES_PASSWORD):
        return True
    pwd_char = ctypes.c_size_t(0)
    ok = user32.SendMessageTimeoutW(
        focus_hwnd,
        EM_GETPASSWORDCHAR,
        0,
        0,
        SMTO_ABORTIFHUNG,
        35,
        ctypes.byref(pwd_char),
    )
    return bool(ok and pwd_char.value != 0)


def is_foreground_console_window() -> bool:
    """Нативное определение консольного окна по системному классу Windows без списков .exe."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    buf = ctypes.create_unicode_buffer(128)
    ln = user32.GetClassNameW(hwnd, buf, 128)
    if ln <= 0:
        return False
    return buf.value in _CONSOLE_WINDOW_CLASSES


def get_foreground_context_tag() -> str:
    """Возвращает нейтральный маркер потока; смысл определяется по самому тексту, а не по имени окна."""
    return "flow"


def send_backspaces_and_text(backspace_count: int, new_text: str) -> None:
    """Мгновенно удаляет backspace_count символов и вводит new_text через SendInput (Unicode)."""
    events: list[INPUT] = []

    for _ in range(max(0, backspace_count)):
        down = INPUT(type=INPUT_KEYBOARD)
        down.union.ki = KEYBDINPUT(wVk=VK_BACK, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
        up = INPUT(type=INPUT_KEYBOARD)
        up.union.ki = KEYBDINPUT(wVk=VK_BACK, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
        events.extend((down, up))

    for ch in new_text:
        code = ord(ch)
        down = INPUT(type=INPUT_KEYBOARD)
        down.union.ki = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)
        up = INPUT(type=INPUT_KEYBOARD)
        up.union.ki = KEYBDINPUT(
            wVk=0,
            wScan=code,
            dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
            time=0,
            dwExtraInfo=0,
        )
        events.extend((down, up))

    if not events:
        return

    arr = (INPUT * len(events))(*events)
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def vk_to_char(vk_code: int, scan_code: int) -> str:
    """Переводит виртуальный код клавиши в символ с учётом раскладки активного окна."""
    _, tid, hkl = get_foreground_hkl()
    if not hkl:
        return ""

    kb_state = (ctypes.c_ubyte * 256)()
    if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000 or user32.GetAsyncKeyState(VK_LSHIFT) & 0x8000 or user32.GetAsyncKeyState(VK_RSHIFT) & 0x8000:
        kb_state[VK_SHIFT] = 0x80
    if user32.GetAsyncKeyState(0x14) & 0x0001:  # VK_CAPITAL toggle
        kb_state[0x14] = 0x01

    out_buf = ctypes.create_unicode_buffer(8)
    rc = user32.ToUnicodeEx(vk_code, scan_code, kb_state, out_buf, 8, 0, ctypes.c_void_p(hkl))
    if rc == 1:
        return out_buf.value
    return ""


class ShiftHookEngine:
    """
    Низкоуровневый перехватчик клавиатуры Windows (WH_KEYBOARD_LL) для отслеживания:
    - Left Shift + Right Shift -> toggle auto switch
    - Double Shift -> конвертация последнего слова
    - Single Shift -> переключение раскладки (отложенное, если не последовал второй Shift)
    - Набор символов и пробел/перенос -> опциональное автопереключение последнего слова
    """

    def __init__(
        self,
        on_double_shift: Callable[[str, bool], None] | None = None,
        on_single_shift: Callable[[], None] | None = None,
        on_shift_shift_toggle: Callable[[], None] | None = None,
        on_word_committed: Callable[[str, str], None] | None = None,
    ) -> None:
        self.on_double_shift = on_double_shift
        self.on_single_shift = on_single_shift
        self.on_shift_shift_toggle = on_shift_shift_toggle
        self.on_word_committed = on_word_committed

        self._hook_id: wintypes.HHOOK | None = None
        self._hook_proc: HOOKPROC | None = None
        self._mouse_hook_id: wintypes.HHOOK | None = None
        self._mouse_hook_proc: HOOKPROC | None = None
        self._hook_thread: threading.Thread | None = None
        self._dispatch_thread: threading.Thread | None = None
        self._thread_id: int = 0
        self._running = False
        self._queue: queue.Queue[tuple[str, tuple]] = queue.Queue()

        self._left_shift_down = False
        self._right_shift_down = False
        self._shift_dirty = False
        self._shift_down_time = 0.0
        self._last_clean_shift_up = 0.0
        self._combo_fired = False
        self._single_timer: threading.Timer | None = None
        self._word_buffer: list[str] = []
        self._last_word: str = ""
        self._last_word_had_space: bool = False

    @property
    def last_word(self) -> str:
        return "".join(self._word_buffer) or self._last_word

    def set_last_word(self, word: str, had_space: bool = False) -> None:
        """Обновляет буфер после автоматической или ручной замены слова."""
        self._word_buffer.clear()
        self._last_word = word
        self._last_word_had_space = had_space

    def clear_buffer(self) -> None:
        self._word_buffer.clear()
        self._last_word = ""
        self._last_word_had_space = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._dispatch_thread = spawn_light_orbit(
            self._dispatch_loop, name="AvalonShifterDispatch"
        )
        self._hook_thread = spawn_light_orbit(
            self._hook_loop, name="AvalonShifterHook"
        )

    def stop(self) -> None:
        self._running = False
        if self._single_timer is not None:
            self._single_timer.cancel()
            self._single_timer = None
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._queue.put(("quit", ()))
        if self._hook_thread and self._hook_thread.is_alive():
            self._hook_thread.join(timeout=1.0)
        if self._dispatch_thread and self._dispatch_thread.is_alive():
            self._dispatch_thread.join(timeout=1.0)
        self._hook_thread = None
        self._dispatch_thread = None
        self._thread_id = 0

    def _dispatch_loop(self) -> None:
        while self._running:
            try:
                kind, args = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if kind == "quit":
                break
            try:
                if kind == "double_shift" and self.on_double_shift:
                    self.on_double_shift(*args)
                elif kind == "single_shift" and self.on_single_shift:
                    self.on_single_shift()
                elif kind == "shift_shift" and self.on_shift_shift_toggle:
                    self.on_shift_shift_toggle()
                elif kind == "word_committed" and self.on_word_committed:
                    self.on_word_committed(*args)
                elif kind == "context_break":
                    cb = getattr(self, "on_context_break", None)
                    if cb:
                        if args:
                            try:
                                cb(*args)
                            except TypeError:
                                cb()
                        else:
                            cb()
            except Exception:
                pass

    def _cancel_single_timer(self) -> None:
        if self._single_timer is not None:
            self._single_timer.cancel()
            self._single_timer = None

    def _schedule_single_shift(self) -> None:
        self._cancel_single_timer()
        self._single_timer = schedule_light_pulse(
            0.28,
            lambda: self._queue.put(("single_shift", ())),
            name="AvalonSingleShiftPulse",
        )

    def _handle_ll_key(self, n_code: int, w_param: int, l_param: int) -> LRESULT:
        if n_code >= 0 and l_param:
            kb = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kb.flags & LLKHF_INJECTED:
                return user32.CallNextHookEx(self._hook_id, n_code, w_param, l_param)

            vk = int(kb.vkCode)
            is_down = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
            is_up = w_param in (WM_KEYUP, WM_SYSKEYUP)
            now = time.monotonic()

            if vk in (VK_LSHIFT, VK_RSHIFT, VK_SHIFT):
                if is_down:
                    was_down = (vk == VK_LSHIFT and self._left_shift_down) or (
                        vk == VK_RSHIFT and self._right_shift_down
                    )
                    if vk == VK_LSHIFT:
                        self._left_shift_down = True
                    elif vk == VK_RSHIFT:
                        self._right_shift_down = True

                    if self._left_shift_down and self._right_shift_down:
                        if not self._combo_fired:
                            self._combo_fired = True
                            self._shift_dirty = True
                            self._cancel_single_timer()
                            self._queue.put(("shift_shift", ()))
                    elif not was_down:
                        self._shift_dirty = False
                        self._shift_down_time = now
                elif is_up:
                    if vk == VK_LSHIFT:
                        self._left_shift_down = False
                    elif vk == VK_RSHIFT:
                        self._right_shift_down = False

                    if not self._left_shift_down and not self._right_shift_down:
                        if not self._shift_dirty and not self._combo_fired and (now - self._shift_down_time) < 0.28:
                            if (now - self._last_clean_shift_up) < 0.35:
                                self._last_clean_shift_up = 0.0
                                self._cancel_single_timer()
                                if self._word_buffer:
                                    target = "".join(self._word_buffer)
                                    had_space = False
                                else:
                                    target = self._last_word
                                    had_space = self._last_word_had_space
                                if target:
                                    self._queue.put(("double_shift", (target, had_space)))
                            else:
                                self._last_clean_shift_up = now
                                self._schedule_single_shift()
                        self._combo_fired = False
            elif is_down:
                # Любая другая клавиша отменяет «чистый» одиночный Shift
                self._shift_dirty = True
                self._cancel_single_timer()

                # Модификаторы сбрасывают буфер (Ctrl+C, Alt+Tab, Win+...)
                win_down = bool(
                    (user32.GetAsyncKeyState(VK_LWIN) & 0x8000)
                    or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000)
                )
                ctrl_or_alt = bool(
                    (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                    or (user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                )
                modifier_keys = (
                    VK_CONTROL,
                    VK_LCONTROL,
                    VK_RCONTROL,
                    VK_MENU,
                    VK_LMENU,
                    VK_RMENU,
                    VK_LWIN,
                    VK_RWIN,
                )
                if ctrl_or_alt or win_down or vk in modifier_keys:
                    if vk not in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL):
                        self._word_buffer.clear()
                    is_layout_space = win_down and vk == VK_SPACE
                    if vk not in modifier_keys and not is_layout_space:
                        self._last_word = ""
                        self._last_word_had_space = False
                        self._queue.put(("context_break", ("nav", "")))
                elif vk == VK_BACK:
                    if self._word_buffer:
                        self._word_buffer.pop()
                    else:
                        self._last_word = ""
                        self._last_word_had_space = False
                        self._queue.put(("context_break", ("backspace_prev", "")))
                elif vk == VK_SPACE:
                    if self._word_buffer:
                        word = "".join(self._word_buffer)
                        self._last_word = word
                        self._last_word_had_space = True
                        self._word_buffer.clear()
                        self._queue.put(("word_committed", (word, " ")))
                    else:
                        self._last_word_had_space = False
                        self._queue.put(("context_break", ("space", "")))
                elif vk == VK_RETURN:
                    if self._word_buffer:
                        word = "".join(self._word_buffer)
                        self._last_word = ""
                        self._last_word_had_space = False
                        self._word_buffer.clear()
                        self._queue.put(("word_committed", (word, "\n")))
                    else:
                        self._last_word = ""
                        self._last_word_had_space = False
                        self._queue.put(("context_break", ("enter", "")))
                elif (0x21 <= vk <= 0x28) or vk in (0x09, 0x1B, 0x2E):  # PgUp..Down, Tab, Esc, Delete
                    self._word_buffer.clear()
                    self._last_word = ""
                    self._last_word_had_space = False
                    self._queue.put(("context_break", ("nav", "")))
                else:
                    ch = vk_to_char(vk, int(kb.scanCode))
                    if ch and len(ch) == 1 and ord(ch) >= 32:
                        self._last_word_had_space = False
                        self._word_buffer.append(ch)
                        if len(self._word_buffer) > 64:
                            self._word_buffer.pop(0)

        return user32.CallNextHookEx(self._hook_id, n_code, w_param, l_param)

    def _handle_ll_mouse(self, n_code: int, w_param: int, l_param: int) -> LRESULT:
        if n_code >= 0 and w_param in (WM_LBUTTONDOWN, WM_RBUTTONDOWN):
            trailing = "".join(self._word_buffer)
            self._word_buffer.clear()
            self._last_word = ""
            self._last_word_had_space = False
            self._queue.put(("context_break", ("mouse", trailing)))
        return user32.CallNextHookEx(self._mouse_hook_id, n_code, w_param, l_param)

    def _hook_loop(self) -> None:
        self._thread_id = int(kernel32.GetCurrentThreadId())
        self._hook_proc = HOOKPROC(self._handle_ll_key)
        self._hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, None, 0)
        if not self._hook_id:
            self._running = False
            return

        self._mouse_hook_proc = HOOKPROC(self._handle_ll_mouse)
        self._mouse_hook_id = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_hook_proc, None, 0)

        msg = wintypes.MSG()
        try:
            while self._running:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:
                    break
        finally:
            if self._mouse_hook_id:
                user32.UnhookWindowsHookEx(self._mouse_hook_id)
                self._mouse_hook_id = None
            self._mouse_hook_proc = None
            if self._hook_id:
                user32.UnhookWindowsHookEx(self._hook_id)
                self._hook_id = None
            self._hook_proc = None


def enable_high_dpi_awareness() -> None:
    """Включает нативный High-DPI рендеринг Windows 11 без системного мыла и лесенок."""
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=False)
        shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def apply_luxury_window_chrome(tk_hwnd: int) -> None:
    """Применяет тёмную матовую шапку Windows 11, скругление углов и графитовый контур (DWM)."""
    if not tk_hwnd:
        return
    try:
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=False)
    except Exception:
        return

    hwnd = user32.GetParent(tk_hwnd) or tk_hwnd
    attrs = (
        (20, ctypes.c_int(1)),              # DWMWA_USE_IMMERSIVE_DARK_MODE
        (33, ctypes.c_int(2)),              # DWMWA_WINDOW_CORNER_PREFERENCE = DWMWCP_ROUND
        (34, ctypes.c_uint32(0x003E332E)),  # DWMWA_BORDER_COLOR (#2E333E)
        (35, ctypes.c_uint32(0x00231D1A)),  # DWMWA_CAPTION_COLOR (#1A1D23)
        (36, ctypes.c_uint32(0x00D2D9DC)),  # DWMWA_TEXT_COLOR (#DCD9D2)
    )
    for attr_id, val in attrs:
        try:
            dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(attr_id),
                ctypes.byref(val),
                ctypes.sizeof(val),
            )
        except Exception:
            pass


def set_app_user_model_id(app_id: str = APP_USER_MODEL_ID) -> None:
    """Устанавливает AppUserModelID, чтобы панель задач Windows 11 показывала иконку приложения."""
    try:
        shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def apply_window_icon(tk_hwnd: int, icon_path: Path) -> None:
    """Применяет иконку .ico к окну верхнего уровня (панель задач и заголовок) без сброса кэша иконок Explorer."""
    if not tk_hwnd or not Path(icon_path).exists():
        return
    path_str = str(icon_path)
    h_big = user32.LoadImageW(None, path_str, IMAGE_ICON, 64, 64, LR_LOADFROMFILE)
    h_small = user32.LoadImageW(None, path_str, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
    parent = user32.GetParent(tk_hwnd)
    targets = [hwnd for hwnd in (parent, tk_hwnd) if hwnd]
    for hwnd in targets:
        if h_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, LPARAM(h_big))
        if h_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, LPARAM(h_small))


def get_desktop_dir() -> Path:
    """Возвращает путь к Рабочему столу текущего пользователя Windows."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            raw_val, _ = winreg.QueryValueEx(key, "Desktop")
            if raw_val:
                return Path(os.path.expandvars(str(raw_val)))
    except OSError:
        pass
    return Path.home() / "Desktop"


def create_desktop_shortcut(
    shortcut_path: Path | None = None,
    app_py_path: Path | None = None,
    icon_path: Path | None = None,
) -> Path:
    """Создаёт ярлык Avalon.Shifter.lnk на Рабочем столе со значком .ico."""
    script = Path(app_py_path) if app_py_path else Path(__file__).with_name("app.py")
    ico = Path(icon_path) if icon_path else Path(__file__).with_name("avalon_shifter.ico")
    target_lnk = Path(shortcut_path) if shortcut_path else (get_desktop_dir() / "Avalon.Shifter.lnk")
    target_lnk.parent.mkdir(parents=True, exist_ok=True)

    native_exe = script.with_name("AvalonShifter.exe")
    if native_exe.exists():
        lnk_target = str(native_exe)
        lnk_args = ""
        lnk_icon = f"{native_exe},0"
    else:
        exe = Path(sys.executable)
        pythonw = exe.with_name("pythonw.exe")
        runner = pythonw if pythonw.exists() else exe
        lnk_target = str(runner)
        lnk_args = f'"{script}"'
        lnk_icon = f"{ico},0"

    env = os.environ.copy()
    env["AVALON_LNK_PATH"] = str(target_lnk)
    env["AVALON_LNK_TARGET"] = lnk_target
    env["AVALON_LNK_ARGS"] = lnk_args
    env["AVALON_LNK_WORKDIR"] = str(script.parent)
    env["AVALON_LNK_ICON"] = lnk_icon
    env["AVALON_LNK_DESC"] = "Avalon.Shifter — Интеллектуальное переключение раскладки"

    ps_script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        "$s = $ws.CreateShortcut($env:AVALON_LNK_PATH); "
        "$s.TargetPath = $env:AVALON_LNK_TARGET; "
        "$s.Arguments = $env:AVALON_LNK_ARGS; "
        "$s.WorkingDirectory = $env:AVALON_LNK_WORKDIR; "
        "$s.IconLocation = $env:AVALON_LNK_ICON; "
        "$s.Description = $env:AVALON_LNK_DESC; "
        "$s.Save()"
    )
    creation_flags = getattr(_sp_runner, "CREATE_NO_WINDOW", 0x08000000)
    _sp_runner.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        env=env,
        creationflags=creation_flags,
        check=True,
        timeout=10,
    )
    return target_lnk


def get_autostart_command(app_py_path: Path | None = None) -> str:
    """Формирует командную строку запуска Avalon.Shifter в трее (приоритетно через AvalonShifter.exe)."""
    script = Path(app_py_path) if app_py_path else Path(__file__).with_name("app.py")
    native_exe = script.with_name("AvalonShifter.exe")
    if native_exe.exists():
        return f'"{native_exe}" --tray'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else exe
    return f'"{runner}" "{script}" --tray'


def set_windows_autostart(
    enabled: bool,
    app_py_path: Path | None = None,
    reg_path: str = RUN_REG_PATH,
    value_name: str = RUN_VALUE_NAME,
) -> bool:
    """Включает или отключает автозапуск в реестре HKCU\\...\\Run."""
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            cmd = get_autostart_command(app_py_path)
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, cmd)
            return True
        try:
            winreg.DeleteValue(key, value_name)
        except FileNotFoundError:
            pass
        return False


def is_windows_autostart_enabled(
    reg_path: str = RUN_REG_PATH,
    value_name: str = RUN_VALUE_NAME,
) -> bool:
    """Проверяет, включён ли автозапуск приложения в Windows 11."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, value_name)
            return bool(val)
    except OSError:
        return False


class SystemTrayIcon:
    """Нативная иконка раскладки RU/EN и меню в системном трее Windows 11 через Shell_NotifyIconW."""

    MENU_RESTORE = 1
    MENU_TOGGLE_AUTO = 2
    MENU_SWITCH_LAYOUT = 3
    MENU_TOGGLE_FLOW = 4
    MENU_EXPORT_FLOW = 5
    MENU_AUTHOR = 6
    MENU_EXIT = 7

    def __init__(
        self,
        icon_path: Path,
        tooltip: str = "Avalon.Shifter",
        on_restore: Callable[[], None] | None = None,
        on_toggle_auto: Callable[[], None] | None = None,
        on_switch_layout: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
        initial_layout: str = "RU",
        initial_auto: bool = True,
        initial_flow: bool = False,
        on_toggle_flow: Callable[[], None] | None = None,
        on_export_flow: Callable[[], None] | None = None,
        on_open_author: Callable[[], None] | None = None,
        get_state_cb: Callable[[], dict] | None = None,
    ) -> None:
        self.icon_path = Path(icon_path)
        self.tooltip = tooltip[:127]
        self.on_restore = on_restore
        self.on_toggle_auto = on_toggle_auto
        self.on_switch_layout = on_switch_layout
        self.on_exit = on_exit
        self.on_toggle_flow = on_toggle_flow
        self.on_export_flow = on_export_flow
        self.on_open_author = on_open_author
        self.get_state_cb = get_state_cb

        self._thread: threading.Thread | None = None
        self._hwnd: wintypes.HWND | None = None
        self._fallback_hicon: wintypes.HICON | None = None
        self._icon_cache: dict[tuple[str, bool, bool], wintypes.HICON] = {}
        self._teleport_cache: dict[tuple[str, str, int, bool, bool], wintypes.HICON] = {}
        self._anim_pair: tuple[str, str] | None = None
        self._anim_target: tuple[str, bool, bool] | None = None
        self._anim_idx: int = 0
        self._state_lock = threading.Lock()
        self._desired_badge: tuple[str, bool, bool] = (
            "RU" if str(initial_layout).upper().startswith("RU") else "EN",
            bool(initial_auto),
            bool(initial_flow),
        )
        self._applied_badge: tuple[str, bool, bool] | None = None
        self._applied_tip: str = self.tooltip
        self._wnd_proc: WNDPROC | None = None
        self._running = False
        self._nid: NOTIFYICONDATAW | None = None
        self._ready_event = threading.Event()
        self._class_name = f"AvalonShifterTrayClass_{id(self)}"

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._ready_event.clear()
        self._thread = spawn_light_orbit(self._run_loop, name="AvalonTrayLoop")
        self._ready_event.wait(timeout=1.5)

    def stop(self) -> None:
        self._running = False
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _get_or_create_badge_hicon(self, layout: str, auto_active: bool, flow_recording: bool) -> wintypes.HICON | None:
        key = ("RU" if str(layout).upper().startswith("RU") else "EN", bool(auto_active), bool(flow_recording))
        cached = self._icon_cache.get(key)
        if cached:
            return cached
        try:
            png_bytes = render_tray_layout_badge_png(
                layout=key[0],
                active=key[1],
                flow_recording=key[2],
                size=32,
            )
            hicon = user32.CreateIconFromResourceEx(
                png_bytes,
                len(png_bytes),
                True,
                0x00030000,
                32,
                32,
                LR_DEFAULTCOLOR,
            )
            if hicon:
                self._icon_cache[key] = hicon
                return hicon
        except Exception:
            pass
        return self._fallback_hicon

    def set_layout_state(
        self,
        layout: str,
        auto_active: bool = True,
        flow_recording: bool = False,
        tooltip: str | None = None,
    ) -> None:
        """Безопасно обновляет живой бейдж раскладки RU/EN и подсказку в трее."""
        norm = ("RU" if str(layout or "").upper().startswith("RU") else "EN", bool(auto_active), bool(flow_recording))
        new_tip = (tooltip[:127] if tooltip is not None else self.tooltip)
        changed = False
        with self._state_lock:
            if norm != self._applied_badge or new_tip != self._applied_tip:
                self._desired_badge = norm
                self.tooltip = new_tip
                changed = True
        if changed and self._hwnd and self._running:
            user32.PostMessageW(self._hwnd, WM_APP_UPDATE_TRAY, 0, 0)

    def update_tooltip(self, tooltip: str) -> None:
        with self._state_lock:
            self.tooltip = tooltip[:127]
            badge = self._desired_badge
        self.set_layout_state(badge[0], badge[1], badge[2], tooltip=tooltip)

    def _get_or_create_teleport_hicon(
        self,
        from_layout: str,
        to_layout: str,
        phase_idx: int,
        auto_active: bool,
        flow_recording: bool,
    ) -> wintypes.HICON | None:
        key = (from_layout, to_layout, int(phase_idx), bool(auto_active), bool(flow_recording))
        cached = self._teleport_cache.get(key)
        if cached:
            return cached
        try:
            png_bytes = render_tray_teleport_frame_png(
                from_layout=from_layout,
                to_layout=to_layout,
                phase=TELEPORT_PHASES[phase_idx],
                active=auto_active,
                flow_recording=flow_recording,
                size=32,
            )
            hicon = user32.CreateIconFromResourceEx(
                png_bytes,
                len(png_bytes),
                True,
                0x00030000,
                32,
                32,
                LR_DEFAULTCOLOR,
            )
            if hicon:
                self._teleport_cache[key] = hicon
                return hicon
        except Exception:
            pass
        return self._get_or_create_badge_hicon(to_layout, auto_active, flow_recording)

    def _apply_pending_tray_update(self) -> None:
        if not self._nid or not self._hwnd:
            return
        with self._state_lock:
            badge = self._desired_badge
            tip = self.tooltip
            prev_badge = self._applied_badge
            if badge == prev_badge and tip == self._applied_tip:
                return
            self._applied_badge = badge
            self._applied_tip = tip

        self._nid.szTip = tip
        if prev_badge is not None and prev_badge[0] != badge[0]:
            # Технологичная 5-кадровая фотонная телепортация раскладки RU ⇄ EN
            user32.KillTimer(self._hwnd, TIMER_TELEPORT_ID)
            self._anim_pair = (prev_badge[0], badge[0])
            self._anim_target = badge
            self._anim_idx = 0
            self._advance_teleport_frame()
            if self._anim_pair is not None:
                user32.SetTimer(self._hwnd, TIMER_TELEPORT_ID, 34, None)
            return

        hicon = self._get_or_create_badge_hicon(*badge)
        if hicon:
            self._nid.hIcon = hicon
        self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))

    def _advance_teleport_frame(self) -> None:
        if not self._nid or not self._hwnd or self._anim_target is None:
            return
        if self._anim_pair is not None and self._anim_idx < len(TELEPORT_PHASES):
            f_lay, t_lay = self._anim_pair
            _, auto_active, flow_rec = self._anim_target
            hicon = self._get_or_create_teleport_hicon(f_lay, t_lay, self._anim_idx, auto_active, flow_rec)
            self._anim_idx += 1
        else:
            user32.KillTimer(self._hwnd, TIMER_TELEPORT_ID)
            hicon = self._get_or_create_badge_hicon(*self._anim_target)
            self._anim_pair = None
            self._anim_target = None
            self._anim_idx = 0

        if hicon:
            self._nid.hIcon = hicon
        self._nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))

    def _show_context_menu(self, hwnd: wintypes.HWND) -> None:
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        try:
            st = {"lang": "ru", "layout": "RU", "auto_switch": True, "flow_archive_enabled": False}
            if self.get_state_cb:
                try:
                    live = self.get_state_cb()
                    if isinstance(live, dict):
                        st.update(live)
                except Exception:
                    pass
            lang = st.get("lang", "ru")
            layout = st.get("layout", "RU")
            auto_on = bool(st.get("auto_switch", True))
            flow_on = bool(st.get("flow_archive_enabled", False))

            user32.AppendMenuW(menu, MF_STRING, self.MENU_RESTORE, tr(lang, "tray_open"))
            user32.AppendMenuW(
                menu,
                MF_STRING | (MF_CHECKED if auto_on else MF_UNCHECKED),
                self.MENU_TOGGLE_AUTO,
                tr(lang, "tray_auto_on" if auto_on else "tray_auto_off"),
            )
            user32.AppendMenuW(menu, MF_STRING, self.MENU_SWITCH_LAYOUT, tr(lang, "tray_switch", layout=layout))
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(
                menu,
                MF_STRING | (MF_CHECKED if flow_on else MF_UNCHECKED),
                self.MENU_TOGGLE_FLOW,
                tr(lang, "tray_flow_on" if flow_on else "tray_flow_off"),
            )
            user32.AppendMenuW(menu, MF_STRING, self.MENU_EXPORT_FLOW, tr(lang, "tray_export"))
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, self.MENU_AUTHOR, tr(lang, "tray_author"))
            user32.AppendMenuW(menu, MF_STRING, self.MENU_EXIT, tr(lang, "tray_exit"))

            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            user32.SetForegroundWindow(hwnd)
            cmd = user32.TrackPopupMenu(
                menu,
                TPM_LEFTALIGN | TPM_RETURNCMD | TPM_RIGHTBUTTON,
                pt.x,
                pt.y,
                0,
                hwnd,
                None,
            )
            user32.PostMessageW(hwnd, WM_NULL, 0, 0)
            if cmd == self.MENU_RESTORE and self.on_restore:
                self.on_restore()
            elif cmd == self.MENU_TOGGLE_AUTO and self.on_toggle_auto:
                self.on_toggle_auto()
            elif cmd == self.MENU_SWITCH_LAYOUT and self.on_switch_layout:
                self.on_switch_layout()
            elif cmd == self.MENU_TOGGLE_FLOW and self.on_toggle_flow:
                self.on_toggle_flow()
            elif cmd == self.MENU_EXPORT_FLOW and self.on_export_flow:
                self.on_export_flow()
            elif cmd == self.MENU_AUTHOR and self.on_open_author:
                self.on_open_author()
            elif cmd == self.MENU_EXIT and self.on_exit:
                self.on_exit()
        finally:
            user32.DestroyMenu(menu)

    def _wnd_callback(self, hwnd: wintypes.HWND, msg: int, w_param: int, l_param: int) -> LRESULT:
        if msg == WM_TRAYICON:
            event_id = l_param & 0xFFFF
            if event_id in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                if self.on_restore:
                    self.on_restore()
                return 0
            if event_id == WM_RBUTTONUP:
                self._show_context_menu(hwnd)
                return 0
        elif msg == WM_APP_UPDATE_TRAY:
            self._apply_pending_tray_update()
            return 0
        elif msg == WM_TIMER and w_param == TIMER_TELEPORT_ID:
            self._advance_teleport_frame()
            return 0
        elif msg == WM_CLOSE:
            user32.KillTimer(hwnd, TIMER_TELEPORT_ID)
            if self._nid:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
                self._nid = None
            user32.DestroyWindow(hwnd)
            return 0
        elif msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, w_param, l_param)

    def _run_loop(self) -> None:
        hinst = kernel32.GetModuleHandleW(None)
        self._wnd_proc = WNDPROC(self._wnd_callback)

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wnd_proc
        wc.hInstance = hinst
        wc.lpszClassName = self._class_name
        user32.RegisterClassExW(ctypes.byref(wc))

        hwnd = user32.CreateWindowExW(
            0, self._class_name, "Avalon.Shifter Tray", 0,
            0, 0, 0, 0, None, None, hinst, None,
        )
        self._hwnd = hwnd
        if not hwnd:
            self._ready_event.set()
            return

        if self.icon_path.exists():
            self._fallback_hicon = user32.LoadImageW(
                None, str(self.icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_DEFAULTSIZE
            )

        with self._state_lock:
            init_badge = self._desired_badge
            init_tip = self.tooltip
            self._applied_badge = init_badge
            self._applied_tip = init_tip

        init_hicon = self._get_or_create_badge_hicon(*init_badge)

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 101
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = init_hicon
        nid.szTip = init_tip
        self._nid = nid
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        self._ready_event.set()

        msg = wintypes.MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            self._nid = None
        for hicon in list(self._icon_cache.values()):
            if hicon:
                user32.DestroyIcon(hicon)
        self._icon_cache.clear()
        for hicon in list(self._teleport_cache.values()):
            if hicon:
                user32.DestroyIcon(hicon)
        self._teleport_cache.clear()
        if self._fallback_hicon:
            user32.DestroyIcon(self._fallback_hicon)
            self._fallback_hicon = None
        self._hwnd = None
        self._wnd_proc = None
