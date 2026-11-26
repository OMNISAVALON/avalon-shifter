"""Двуязычный словарь интерфейса, стилизованных подсказок и философии Avalon.Shifter (RU / EN)."""

from __future__ import annotations

AUTHOR_FULL_NAME = "Ігор Дєточевський • Игорь Деточевский • Ihor Dietochevskyi"
AUTHOR_CANONICAL_ID = "Ігор Дєточевський (Ihor Dietochevskyi • OMNISAVALON • C1)"

AUTHOR_LINKS: tuple[dict[str, str], ...] = (
    {
        "id": "github_org",
        "label_ru": "GitHub • OMNISAVALON",
        "label_en": "GitHub • OMNISAVALON",
        "url": "https://github.com/OMNISAVALON",
    },
    {
        "id": "github_author",
        "label_ru": "GitHub • IhorDietochevskyi",
        "label_en": "GitHub • IhorDietochevskyi",
        "url": "https://github.com/IhorDietochevskyi",
    },
    {
        "id": "hf_org",
        "label_ru": "Hugging Face • OMNISAVALON",
        "label_en": "Hugging Face • OMNISAVALON",
        "url": "https://huggingface.co/OMNISAVALON",
    },
    {
        "id": "hf_author",
        "label_ru": "Hugging Face • IhorDietochevskyi",
        "label_en": "Hugging Face • IhorDietochevskyi",
        "url": "https://huggingface.co/IhorDietochevskyi",
    },
)

PHILOSOPHY_QUOTE_RU = (
    "Ты просто печатаешь поток своей мысли — на русском, английском или в их живой смеси.\n"
    "Утилита незаметно выравнивает раскладку без лишних переключений и искажений.\n"
    "Ноль телеметрии. Ноль сбора данных. Твой поток информации — твоя суверенная база."
)

PHILOSOPHY_QUOTE_EN = (
    "Just type your stream of thought naturally — in Russian, English, or a seamless mix of both.\n"
    "This featherweight tool silently aligns keyboard layouts with zero interruptions and zero distortion.\n"
    "Zero analytics. Zero tracking. Your flow of thought belongs strictly to you."
)

STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "subtitle": "Выравниватель потока мысли  •  0% телеметрии  •  432 Гц",
        "btn_tray": "В трей",
        "dial_auto": "Авто-поток",
        "dial_single": "Одиночный Shift",
        "dial_dev": "Защита кода",
        "dial_on": "Включено",
        "dial_off": "Ожидание",
        "sec_settings": "Настройки потока",
        "sw_double_shift": "Double Shift — исправить последнее слово и знак «?»",
        "sw_single_shift": "Single Shift — переключение раскладки одиночным нажатием",
        "sw_shift_toggle": "Shift + Shift — быстрая пауза и возврат автопотока",
        "sw_caps": "Автовыравнивание Caps Lock (пРИВЕТ → Привет)",
        "sw_empathy": "Эмпатическая память — тихое обучение из ваших поправок",
        "sw_autostart": "Запуск вместе с Windows в свернутом виде",
        "sw_flow_archive": "Личная База Потока (для своего ИИ • выкл. по умолчанию • фильтр паролей)",
        "flow_status_off": "База Потока: выключена (0 Б)",
        "flow_status_on": "База: {records} фр. • {size_kb:.1f} КБ • скр.: {secrets}",
        "btn_export_ai": "Экспорт для ИИ",
        "btn_clear_flow": "Очистить",
        "sec_sandbox": "Проверка выравнивания",
        "sandbox_hint": "Пробел — выравнивание на лету",
        "btn_convert": "Выровнять",
        "btn_switch_layout": "Раскладка ОС",
        "btn_clear_sandbox": "Очистить",
        "footer_clean": "Avalon.Shifter • Continuum • 432 Гц • 0% телеметрии",
        "link_under_hood": "Под капотом",
        "link_author": "Автор • OMNISAVALON",
        "stats_counter": "Выровнено: {converted}  •  Защищено: {protected}",
        "event_ready": "Поток готов — просто печатайте без прерываний",
        "event_layout_switched": "Раскладка ОС переключена → {lang}",
        "event_autostart_on": "Автозапуск Windows включён",
        "event_autostart_off": "Автозапуск Windows отключён",
        "event_autostart_err": "Не удалось обновить параметры автозапуска",
        "event_empathy_cleared": "Эмпатическая память очищена (правил удалено: {count})",
        "event_flow_toggled_on": "Личная База Потока включена (локально, с фильтром паролей)",
        "event_flow_toggled_off": "Личная База Потока приостановлена",
        "event_flow_exported": "Экспорт для ИИ готов: {count} фраз → {dir}",
        "event_flow_empty": "Личная База Потока пока пуста — напечатайте текст при включённой записи",
        "event_flow_cleared": "Личная База Потока полностью очищена (удалено файлов: {files})",
        "event_lang_changed": "Язык интерфейса: Русский",
        "tray_open": "Открыть Avalon.Shifter",
        "tray_auto_on": "✓ Авто-поток (Вкл)",
        "tray_auto_off": "   Авто-поток (Пауза)",
        "tray_flow_on": "✓ База Потока для ИИ (Запись)",
        "tray_flow_off": "   База Потока для ИИ (Выкл)",
        "tray_export": "Экспорт Базы Потока для ИИ...",
        "tray_switch": "Сменить раскладку ({layout})",
        "tray_author": "Автор и ссылки OMNISAVALON...",
        "tray_exit": "Выход",
        "tray_tip": "Avalon.Shifter ({layout}) — {auto_state} • База ИИ: {flow_state} • 0% телеметрии",
        "dlg_title": "Avalon.Shifter • OMNISAVALON",
        "tab_author": "Автор • OMNISAVALON",
        "tab_hood": "Под капотом • Прозрачность",
        "author_heading": "Экосистема OMNISAVALON • Выравниватель Потока Мысли",
        "author_creator_label": "Создатель и Архитектор:",
        "author_links_title": "Официальные каналы Создателя и Проекта:",
        "author_license_btn": "Открыть лицензию Continuum",
        "author_readme_btn": "Открыть руководство",
        "hood_heading": "Открытая суверенная архитектура (100% прозрачность)",
        "hood_arch_line": "Ядро: САБ-432 + Rust #![no_std] ({native}) + Язык INTENT (.avl AST) + ПЛАЗМА-432",
        "hood_crypto_line": "Печать и формат памяти: AGLS-432-Phi • .qholo (AVALON_QHOLO_V8) • Тороид ЗСВ-8192",
        "hood_privacy_line": "Сетевых вызовов: 0 • Телеметрии: 0 байт • Фильтр секретов и полей паролей: Активен",
        "hood_vector_line": "Последний 4D-вектор: R4 {vec}  •  Намерение (.avl): {intent}",
        "hood_otp_line": "Активность Триады: Надзиратель OTP (перезапусков: {restarts})  •  Резонанс: 432.0 Гц",
        "hood_empathy_line": "Эмпатическая память ({state}): {entries} слов (направл. {dirs}, исключ. {keeps})",
        "hood_flow_line": "Личная База Потока ({state}): {records} фраз • {size_kb:.1f} КБ • Отброшено секретов: {secrets}",
        "hood_btn_reset_empathy": "Сбросить эмпатию",
        "hood_btn_open_exports": "Открыть папку экспортов",
        "hood_btn_close": "Закрыть",
    },
    "en": {
        "subtitle": "Effortless Thought-Flow Aligner  •  0% Analytics  •  432 Hz",
        "btn_tray": "Tray",
        "dial_auto": "Auto Flow",
        "dial_single": "Single Shift",
        "dial_dev": "Code Guard",
        "dial_on": "Active",
        "dial_off": "Standby",
        "sec_settings": "Flow Settings",
        "sw_double_shift": "Double Shift — fix last word or contextual '&' → '?'",
        "sw_single_shift": "Single Shift — switch OS layout on single tap",
        "sw_shift_toggle": "Shift + Shift — quick pause & resume auto alignment",
        "sw_caps": "Fix accidental Caps Lock (hELLO → Hello)",
        "sw_empathy": "Empathic Memory — quiet local adaptation from manual fixes",
        "sw_autostart": "Launch quietly with Windows in tray",
        "sw_flow_archive": "Personal Flow Base (for your AI • off by default • password shield)",
        "flow_status_off": "Flow Base: disabled (0 B)",
        "flow_status_on": "Base: {records} lines • {size_kb:.1f} KB • blk: {secrets}",
        "btn_export_ai": "Export AI",
        "btn_clear_flow": "Clear",
        "sec_sandbox": "Live Alignment Sandbox",
        "sandbox_hint": "Spacebar triggers auto-align",
        "btn_convert": "Align Flow",
        "btn_switch_layout": "OS Layout",
        "btn_clear_sandbox": "Clear",
        "footer_clean": "Avalon.Shifter • Continuum • 432 Hz • 0% Analytics",
        "link_under_hood": "Under the Hood",
        "link_author": "Author • OMNISAVALON",
        "stats_counter": "Aligned: {converted}  •  Protected: {protected}",
        "event_ready": "Ready — type freely in RU, EN, or mixed flow",
        "event_layout_switched": "OS layout switched → {lang}",
        "event_autostart_on": "Windows autostart enabled",
        "event_autostart_off": "Windows autostart disabled",
        "event_autostart_err": "Could not update Windows autostart registry",
        "event_empathy_cleared": "Empathic memory cleared ({count} rules removed)",
        "event_flow_toggled_on": "Personal Flow Base enabled (local-only, secret filter armed)",
        "event_flow_toggled_off": "Personal Flow Base paused",
        "event_flow_exported": "AI export complete: {count} lines → {dir}",
        "event_flow_empty": "Flow Base is empty — enable recording and type naturally first",
        "event_flow_cleared": "Personal Flow Base wiped cleanly (files removed: {files})",
        "event_lang_changed": "Interface language: English",
        "tray_open": "Open Avalon.Shifter",
        "tray_auto_on": "✓ Auto Flow (Active)",
        "tray_auto_off": "   Auto Flow (Paused)",
        "tray_flow_on": "✓ AI Flow Base (Recording)",
        "tray_flow_off": "   AI Flow Base (Off)",
        "tray_export": "Export Flow Base for AI...",
        "tray_switch": "Switch Layout ({layout})",
        "tray_author": "Author & OMNISAVALON Links...",
        "tray_exit": "Exit",
        "tray_tip": "Avalon.Shifter ({layout}) — {auto_state} • AI Base: {flow_state} • 0% analytics",
        "dlg_title": "Avalon.Shifter • OMNISAVALON",
        "tab_author": "Author • OMNISAVALON",
        "tab_hood": "Under the Hood • Transparency",
        "author_heading": "OMNISAVALON Ecosystem • Thought-Flow Aligner",
        "author_creator_label": "Creator & Architect:",
        "author_links_title": "Official Creator & Project Repositories:",
        "author_license_btn": "Open Continuum License",
        "author_readme_btn": "Open Guide",
        "hood_heading": "Open Sovereign Architecture (100% Transparent)",
        "hood_arch_line": "Core: SAB-432 + Rust #![no_std] ({native}) + INTENT (.avl AST) + PLASMA-432",
        "hood_crypto_line": "Seal & Storage: AGLS-432-Phi • .qholo (AVALON_QHOLO_V8) • ZSV-8192 Toroid",
        "hood_privacy_line": "Network calls: 0 • Analytics: 0 bytes • Password field & secret guard: Armed",
        "hood_vector_line": "Last 4D Vector: R4 {vec}  •  Intent (.avl): {intent}",
        "hood_otp_line": "Triad Runtime: OTP Supervisor (restarts: {restarts})  •  Resonance: 432.0 Hz",
        "hood_empathy_line": "Empathic Memory ({state}): {entries} words (dirs: {dirs}, keeps: {keeps})",
        "hood_flow_line": "Personal Flow Base ({state}): {records} lines • {size_kb:.1f} KB • Secrets filtered: {secrets}",
        "hood_btn_reset_empathy": "Reset Empathic Memory",
        "hood_btn_open_exports": "Open Exports Folder",
        "hood_btn_close": "Close",
    },
}

TOOLTIPS: dict[str, dict[str, tuple[str, str]]] = {
    "ru": {
        "lang_toggle": (
            "Язык интерфейса (РУС / ENG)",
            "Мгновенно переключает все подписи, подсказки, окна и меню системного трея между русским и английским без перезапуска.",
        ),
        "layout_badge": (
            "Живой индикатор раскладки ОС",
            "Показывает текущую раскладку активного окна. Нажмите, чтобы переключить раскладку RU ⇄ EN с фотонной телепортацией значка.",
        ),
        "btn_tray": (
            "Свернуть в системный трей",
            "Скрывает окно с экрана. Утилита продолжит тихо выравнивать раскладку в фоне, отображая крупный значок RU / EN в трее.",
        ),
        "dial_auto": (
            "Авто-поток (Невидимое выравнивание)",
            "По мере ввода исправляет слова, набранные в ошибочной раскладке (ghbdtn → привет), сохраняя непрерывность мысли.",
        ),
        "dial_single": (
            "Одиночный Shift",
            "При включении быстрое одиночное нажатие Shift переключает раскладку клавиатуры RU ⇄ EN в любом окне.",
        ),
        "dial_dev": (
            "Защита кода (Developer Guard)",
            "Распознаёт команды терминала, пути файлов, расширения (.py, .avl, .rs) и идентификаторы кода, не искажая их при автозамене.",
        ),
        "sw_double_shift": (
            "Double Shift — ручная поправка",
            "Двойное нажатие Shift переводит только что напечатанное слово в другую раскладку или превращает '&' в '?' после английского слова.",
        ),
        "sw_single_shift": (
            "Single Shift — быстрая смена раскладки",
            "Одиночное короткое нажатие Shift без других клавиш меняет раскладку RU ⇄ EN, не затрагивая последний набранный текст.",
        ),
        "sw_shift_toggle": (
            "Shift + Shift — мгновенная пауза",
            "Одновременное нажатие Левый Shift + Правый Shift ставит автопереключение на паузу или возвращает его обратно в один жест.",
        ),
        "sw_caps": (
            "Автовыравнивание Caps Lock",
            "Исправляет случайно перевёрнутый регистр вроде «пРИВЕТ» → «Привет» или «hELLO» → «Hello» без ручного стирания.",
        ),
        "sw_empathy": (
            "Эмпатическая память (локально)",
            "Тихо запоминает слова, которые вы исправили через Double Shift, чтобы в будущем сразу попадать в ваш личный стиль ввода.",
        ),
        "sw_autostart": (
            "Автозапуск вместе с Windows",
            "Запускает AvalonShifter.exe тихо и свёрнуто в трей при входе в Windows — никаких всплывающих окон на старте.",
        ),
        "sw_flow_archive": (
            "Личная База Потока (для своего ИИ • Opt-In)",
            "Выключена по умолчанию (0 байт на диске). При включении локально сохраняет очищенные фразы с фильтром паролей, токенов, карт и OTP.\nАктивный файл: {corpus_path}\nПапка экспортов ИИ: {exports_path}",
        ),
        "flow_bar": (
            "Хранилище и защита Базы Потока",
            "Дедупликация AGLS-432-Phi + компактная авто-свёртка в .qholo (лимит <= 2 МБ / <= 16 МБ).\nБаза: {corpus_path}\nЭкспорты для ИИ: {exports_path}",
        ),
        "btn_export_ai": (
            "Экспорт для всех моделей ИИ",
            "Выгружает накопленную базу в 4 универсальных формата (Chat SFT JSONL, Pretrain JSONL, Markdown RAG, кристалл .qholo).\nПуть сохранения: {exports_path}",
        ),
        "btn_clear_flow": (
            "Полная очистка Базы Потока",
            "Мгновенно и безвозвратно удаляет локальный файл потока и все архивные сегменты .qholo из папки:\n{corpus_dir}",
        ),
        "btn_convert": (
            "Выровнять текст в полигоне",
            "Проверьте работу выравнивателя на фразе выше — преобразует выделенный фрагмент или весь текст, защищая код.",
        ),
        "btn_switch_layout": (
            "Сменить раскладку системы",
            "Программно переключает раскладку активного окна ОС между RU и EN и обновляет живой бейдж в трее.",
        ),
        "btn_clear_sandbox": (
            "Очистить поле проверки",
            "Очищает текстовую область полигона для нового тестового ввода.",
        ),
        "btn_author": (
            "Создатель и философия OMNISAVALON",
            "Открывает карточку Создателя с прямыми кнопками на GitHub и Hugging Face (OMNISAVALON и IhorDietochevskyi) и лицензию Continuum.",
        ),
        "btn_hood": (
            "Под капотом • Полная прозрачность",
            "Открывает живую телеметрию САБ-432, Rust #![no_std], INTENT (.avl), вектор R4, статус OTP и эмпатической памяти без загромождения главного экрана.",
        ),
    },
    "en": {
        "lang_toggle": (
            "Interface Language (РУС / ENG)",
            "Instantly switches all labels, tooltips, dialogs, and tray menus between Russian and English with zero restart.",
        ),
        "layout_badge": (
            "Live OS Keyboard Layout",
            "Reflects your current active window layout. Click to toggle RU ⇄ EN with photonic tray teleport animation.",
        ),
        "btn_tray": (
            "Minimize to System Tray",
            "Hides the main window cleanly while keeping instant thought-flow alignment active with a bold RU / EN badge in the tray.",
        ),
        "dial_auto": (
            "Auto Flow Alignment",
            "Silently converts mistyped wrong-layout words in real time (ghbdtn → привет) so your typing rhythm stays unbroken.",
        ),
        "dial_single": (
            "Single Shift",
            "When enabled, tapping Shift once cleanly switches your OS keyboard layout between RU and EN.",
        ),
        "dial_dev": (
            "Code Guard (Developer Guard)",
            "Detects terminal commands, file paths, extensions (.py, .avl, .rs), and code identifiers so technical tokens stay untouched.",
        ),
        "sw_double_shift": (
            "Double Shift — manual word & '?' fix",
            "Double-tap Shift to flip the last word into the opposite layout or convert trailing '&' to '?' after an English term.",
        ),
        "sw_single_shift": (
            "Single Shift — quick layout tap",
            "Tap Shift alone to switch OS layout RU ⇄ EN without altering the already typed text.",
        ),
        "sw_shift_toggle": (
            "Shift + Shift — instant pause/resume",
            "Press Left Shift + Right Shift together to toggle automatic flow alignment on or off anytime.",
        ),
        "sw_caps": (
            "Accidental Caps Lock Aligner",
            "Automatically normalizes inverted casing like 'hELLO' → 'Hello' or 'пРИВЕТ' → 'Привет' seamlessly.",
        ),
        "sw_empathy": (
            "Empathic Memory (Local Only)",
            "Quietly learns from your Double Shift fixes so your preferred mixed vocabulary aligns immediately next time.",
        ),
        "sw_autostart": (
            "Launch with Windows (Tray Mode)",
            "Starts AvalonShifter.exe quietly minimized to the system tray on Windows sign-in with zero startup flash.",
        ),
        "sw_flow_archive": (
            "Personal Flow Base (Opt-In AI Corpus)",
            "Off by default (0 bytes written). When enabled, stores cleaned phrases locally with password-field, token, card, and OTP filtering.\nActive file: {corpus_path}\nAI export folder: {exports_path}",
        ),
        "flow_bar": (
            "Flow Base Storage & Zero-Bloat Bounds",
            "AGLS-432-Phi deduplication + automatic origami .qholo compaction (<= 2 MB active / <= 16 MB FIFO ceiling).\nCorpus file: {corpus_path}\nExports folder: {exports_path}",
        ),
        "btn_export_ai": (
            "Export for Any AI Model",
            "Exports your local Flow Base into 4 formats (Chat SFT JSONL, Pretrain JSONL, Markdown RAG, sealed .qholo crystal).\nOutput folder: {exports_path}",
        ),
        "btn_clear_flow": (
            "Wipe Personal Flow Base",
            "Immediately deletes the active Flow Base file and all compressed .qholo archive segments from:\n{corpus_dir}",
        ),
        "btn_convert": (
            "Align Sandbox Text",
            "Test thought-flow alignment on the selected text or full phrase above while keeping code tokens protected.",
        ),
        "btn_switch_layout": (
            "Switch OS Layout",
            "Toggles active foreground OS keyboard layout RU ⇄ EN and animates the live tray indicator.",
        ),
        "btn_clear_sandbox": (
            "Clear Sandbox",
            "Clears the sandbox text box above for a fresh test phrase.",
        ),
        "btn_author": (
            "Creator & OMNISAVALON Philosophy",
            "Opens the Author dialog with direct buttons to GitHub & Hugging Face (OMNISAVALON and IhorDietochevskyi) and Continuum License.",
        ),
        "btn_hood": (
            "Under the Hood • Transparency",
            "Inspect live SAB-432, Rust #![no_std], INTENT (.avl), R4 vector, OTP supervisor, and Empathic Memory internals cleanly.",
        ),
    },
}


def normalize_lang(lang: str | None) -> str:
    return "en" if str(lang or "").strip().lower().startswith("en") else "ru"


def tr(lang: str | None, key: str, **kwargs: object) -> str:
    code = normalize_lang(lang)
    table = STRINGS.get(code, STRINGS["ru"])
    template = table.get(key) or STRINGS["ru"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def tr_tip(lang: str | None, key: str, **kwargs: object) -> tuple[str, str]:
    code = normalize_lang(lang)
    table = TOOLTIPS.get(code, TOOLTIPS["ru"])
    title, body = table.get(key) or TOOLTIPS["ru"].get(key) or (key, "")
    if kwargs:
        try:
            title = title.format(**kwargs)
        except Exception:
            pass
        try:
            body = body.format(**kwargs)
        except Exception:
            pass
    return title, body
