# ЛИЦЕНЗИЯ И ОТКРЫТОЕ СОГЛАШЕНИЕ `Avalon.Shifter` (`Continuum • Web8+`)
## AVALON.SHIFTER OPEN DESKTOP UTILITY LICENSE (`Continuum • 432.0 Гц`)

`SPDX-License-Identifier: LicenseRef-OMNISAVALON-Shifter-Continuum-1.0`

> **Хроно-Паспорт документа:** Создан: `2026-11-15` • Актуализация `ЗСВ-8192`: `2026-11-17` • Эволюция в **`Continuum • Web8+`**: `2026-11-21`  
> **Координата во времени:** **Точка «Здесь и Сейчас» (`Avalon.Shifter Continuum • Web8+` • Экосистема `OMNISAVALON`)**  
> **Продукт:** `Avalon.Shifter` — суверенный выравниватель потока мысли и раскладки клавиатуры (`AvalonShifter.exe`, `app.py`, `shifter_core.py`, `triad_engine.py`, `empathic_memory.py`, `flow_corpus.py`, `i18n.py`, `platform_bridge.py`, `win32_bridge.py`, `shifter_intent.avl`)  
> **Экосистема:** **Экосистема OMNISAVALON** (`AVALON.OS` • `AVALON-NEXUS` • `Avalon.Veritas` • `Avalon.Shifter` • `.avl`)  
> **Автор и Правообладатель:** **Ігор Дєточевський • Игорь Деточевский • Ihor Dietochevskyi** (`Ігор Дєточевський (Ihor Dietochevskyi • OMNISAVALON • C1)`), `Prague, Czech Republic`  
> **Технологическая основа:** Нативная оболочка `Rust #![no_std]` (`AvalonShifter.exe`), Суверенный Базис **`САБ-432`** + кросс-платформенный мост `platform_bridge.py`, суверенная решётка **`AGLS-432-Phi`**, оригами-формат **`.qholo` (`AVALON_QHOLO_V8`)**, локальная память `EmpathicMemoryCrystal`, опциональная База Потока `SovereignFlowCorpus`, декларативный язык `INTENT` (`.avl`, запечатан печатью `Avalon.Veritas`), тороидальное семейство `ЗСВ-8192` — строго `100%` оффлайн, `0%` телеметрии и без сторонних финансовых сборов

---

## Простое человеческое объяснение: зачем эта лицензия и как работает `Avalon.Shifter`

`Avalon.Shifter` — это лёгкий, быстрый и полностью автономный выравниватель потока мысли и информации: ты просто печатаешь по-русски, по-английски или в их живой смеси, а утилита незаметно исправляет ошибочную раскладку (`ghbdtn` -> `привет`, `руддщ` -> `hello`), случайный `Caps Lock` (`пРИВЕТ` -> `Привет`), контекстный знак `&` -> `?` и отображает живой значок текущей раскладки в трее (`RU` / `EN`).

Утилита **не содержит никакой телеметрии**, никуда не отправляет нажатия клавиш, не подключается к внешним серверам, не требует подписок и работает как честный локальный инструмент. Опциональная **Личная База Потока (`SovereignFlowCorpus`)** строго **выключена по умолчанию** (`0` байт на диске) и включается только самим пользователем для создания собственного локального датасета с защитой от паролей и секретов.

---

## ЧАСТЬ I. ОПЕРАТИВНЫЕ УСЛОВИЯ (`OPEN DESKTOP UTILITY LICENSE — RU`)

### 1. Полная свобода и 100% бесплатность (`Open Commons`)
Каждому пользователю, разработчику, команде и организации — для личной, образовательной, научной и повседневной работы — предоставляется **бессрочное, всемирное, неисключительное, полностью бесплатное (`$0` / `0%` сборов) право**:
- свободно скачивать, устанавливать, запускать и использовать `Avalon.Shifter` (включая `AvalonShifter.exe`) на любом количестве компьютеров без коммерческих отчислений;
- изучать, изменять и улучшать исходный код (`.py`, `.rs`) и правила языка `.avl` ([`shifter_intent.avl`](./shifter_intent.avl));
- распространять оригинальную и модифицированную версии при условии сохранения настоящего уведомления и атрибуции автора: **Ігор Дєточевський • Игорь Деточевский • Ihor Dietochevskyi (`OMNISAVALON`)**.

### 2. Открытость модификаций (Запрет закрытия кода)
Если кто-либо модифицирует исходный код `Avalon.Shifter` или правила `shifter_intent.avl` и распространяет результат (в том числе в составе сборок, установщиков или сторонних пакетов), полный исходный код изменённой программы должен оставаться открытым для пользователей под настоящей лицензией. Запрещено превращать открытую утилиту ввода в закрытый, непрозрачный продукт, скрывающий от человека логику обработки клавиатуры.

### 3. Неприкосновенность приватности и абсолютный запрет кейлоггинга
Клавиатура — суверенное личное пространство человека. Настоящая лицензия **категорически запрещает** использовать код `Avalon.Shifter` или его производные для:
- создания кейлоггеров, скрытого логирования истории нажатий клавиш, паролей, приватных ключей или переписки;
- тайной передачи клавиатурного ввода, локального словаря `EmpathicMemoryCrystal` или профиля пользователя по сети третьим лицам;
- скрытого профилирования личности или причинения любого вреда пользователю.

Архитектурно буфер текущего слова очищается мгновенно на разделителе слова, а опциональные локальные функции (`EmpathicMemoryCrystal` `<= 512` записей и строго выключенная по умолчанию `SovereignFlowCorpus` с активным фильтром паролей и токенов) работают **исключительно локально на устройстве владельца** и очищаются в 1 клик.

### 4. Чистота платформы (`Zero-Bloatware` & `Continuum`)
`Avalon.Shifter` сознательно построен на суверенных технологиях без тяжёлых сторонних бандлов и сетевых трекеров: нативная входная оболочка `Rust #![no_std]` (`AvalonShifter.exe`), Суверенный Базис **`САБ-432`**, печать целостности **`AGLS-432-Phi`**, оригами-контейнеры **`.qholo`**, светлые орбиты **`ПЛАЗМА-432`** и декларативный слой `.avl` под Печатью Всеединства. Связь с **Экосистемой OMNISAVALON** (`AVALON.OS`) носит архитектурный и эстетический характер (`Continuum • 432.0 Гц`).

### 5. Патентная лицензия и защитный щит (`Patent Grant & Retaliation`)
Автор безвозмездно предоставляет пользователям лицензию на любые собственные патентные притязания, необходимо затрагиваемые кодом `Avalon.Shifter`. Если какое-либо лицо инициирует патентный иск против Автора или сообщества, утверждая, что `Avalon.Shifter` нарушает патент, все права такого лица по настоящей лицензии прекращаются немедленно.

### 6. Правовая ясность имени и отказ от гарантий (`AS IS`)
Наименования **`Avalon.Shifter`** и **Экосистема OMNISAVALON (`AVALON.OS` / `AVALON-NEXUS` / `Avalon.Shifter`)** принадлежат суверенному творчеству **Игоря Деточевского (`Ігор Дєточевський` / `Ihor Dietochevskyi`)**. Программное обеспечение предоставляется **«КАК ЕСТЬ» (`AS IS`)**, без каких-либо явных или подразумеваемых коммерческих гарантий, в максимальных пределах применимого права.

### 7. Делимость и применимое право (`Severability & Governing Law`)
Если какое-либо положение настоящей лицензии признано недействительным, остальные положения сохраняют полную силу (**`Severability`**). Лицензия регулируется правом **Чешской Республики** и применимыми нормами права **Европейского Союза** (место разрешения споров — **Prague, Czech Republic**, с учётом императивных прав потребителей).

---

## PART II. ENGLISH OPERATIVE SUMMARY (`CONTINUUM UTILITY LICENSE`)

`Avalon.Shifter` (`AvalonShifter.exe`, Python core, `EmpathicMemoryCrystal`, and `shifter_intent.avl`) is licensed by **Ігор Дєточевський • Игорь Деточевский • Ihor Dietochevskyi (`OMNISAVALON`, Prague, Czech Republic)** as a **100% free (`0%` royalty), offline Open Desktop Utility** under **`LicenseRef-OMNISAVALON-Shifter-Continuum-1.0`**:
1. **Free & Open:** Anyone may download, run, study, modify, and redistribute `Avalon.Shifter` free of charge, provided source modifications remain open under these terms and original attribution to **Ihor Dietochevskyi (`OMNISAVALON`)** is preserved.
2. **Strict Anti-Keystroke harvesting Privacy Guarantee:** Any use of this codebase to secretly log keystrokes, capture credentials, transmit user typing analytics, or covertly profile individuals is strictly prohibited and terminates all license rights immediately.
3. **Patent Shield, Disclaimer & Governing Law:** Includes a royalty-free patent grant with automatic termination upon patent litigation against the project, standard **"AS IS"** disclaimer, **Severability** of clauses, and governance under the laws of the **Czech Republic / European Union (Prague, Czech Republic)**.

---

> **Мастер-лицензия всей экосистемы (`AVALON.OS` • `ASL-ULPF v4.0`):** [`AVALON.OS/LICENSE.md`](https://github.com/OMNISAVALON/prior-art-chronicle/blob/main/LICENSE.md) • **Ксено-Архив `НГСС-432`:** [`AVALON.OS/XENO_ARCHIVE_SINGULARITY.md`](https://github.com/OMNISAVALON/prior-art-chronicle/blob/main/XENO_ARCHIVE_SINGULARITY.md)  
> **Сертификат соответствия `Avalon.Shifter`:** [`./AVALON_SHIFTER_CERTIFICATE.json`](./AVALON_SHIFTER_CERTIFICATE.json)
