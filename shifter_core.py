"""Ядро позиционного перекодировщика и контекстного анализатора Avalon.Shifter."""

from __future__ import annotations

import re
from typing import Any

EN_CHARS = "`qwertyuiop[]asdfghjkl;'zxcvbnm,./~QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?@#$^&"
RU_CHARS = "ёйцукенгшщзхъфывапролджэячсмитьбю.ЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,\"№;:?"

EN_TO_RU_MAP: dict[str, str] = dict(zip(EN_CHARS, RU_CHARS))
RU_TO_EN_MAP: dict[str, str] = dict(zip(RU_CHARS, EN_CHARS))

EN_VOWELS = frozenset("aeiouyAEIOUY")
RU_VOWELS = frozenset("аеёиоуыэюяАЕЁИОУЫЭЮЯ")

# Русские буквы, которым на QWERTY соответствуют символы пунктуации (в т.ч. в начале слова: Б, б, Ж, ж, Ю, ю, Х, х, Ъ, ъ, Э, э, Ё, ё)
EN_INTERNAL_LAYOUT_CHARS = frozenset("`[];',.~{}:\"<>")
EN_LEADING_LETTER_KEYS = frozenset("`~[{;:'\",<.>")

COMMON_EN_WORDS = frozenset({
    "a", "i", "an", "am", "as", "at", "be", "by", "do", "go", "he", "if",
    "in", "is", "it", "me", "my", "no", "of", "ok", "on", "or", "so", "to", "up",
    "us", "we", "all", "and", "are", "but", "can", "day", "did", "for", "get",
    "got", "had", "has", "her", "him", "his", "how", "man", "new", "not", "now",
    "old", "one", "our", "out", "put", "run", "say", "see", "she", "the", "too",
    "two", "use", "was", "way", "who", "why", "you", "back", "been", "call",
    "code", "come", "data", "down", "even", "file", "find", "from", "give",
    "good", "have", "help", "here", "home", "into", "just", "know", "last",
    "like", "line", "list", "look", "love", "made", "make", "many", "more",
    "most", "much", "must", "name", "need", "next", "only", "open", "over",
    "part", "play", "read", "real", "same", "save", "show", "side", "some",
    "song", "soon", "stop", "such", "take", "tell", "test", "text", "than",
    "that", "them", "then", "they", "this", "time", "turn", "user", "very",
    "want", "well", "were", "what", "when", "will", "with", "word", "work",
    "year", "your", "about", "after", "again", "could", "every", "first",
    "great", "hello", "house", "music", "never", "other", "place", "right",
    "sound", "start", "still", "study", "thank", "their", "there", "these",
    "thing", "think", "those", "three", "under", "water", "where", "which",
    "while", "world", "would", "write", "python", "windows", "shifter", "avalon",
    "plan", "model", "mirror", "system", "update", "script", "engine", "search",
    "folder", "button", "window", "screen", "design", "future", "matrix", "vector",
    "canvas", "space", "light", "flow", "unity", "core", "notes", "draft", "clean", "smart",
    "web", "app", "net", "dev", "pro", "bot", "hub", "win", "sha", "ver",
})

COMMON_RU_WORDS = frozenset({
    "а", "в", "и", "к", "о", "с", "у", "я",
    "бы", "во", "вы", "да", "до", "её", "ее", "же", "за", "из", "им", "их",
    "ко", "ли", "мы", "на", "не", "ни", "но", "ну", "об", "он", "от", "по",
    "со", "то", "ту", "ты", "уж", "уф", "эй",
    "без", "был", "вам", "вас", "ваш", "вот", "все", "всё", "вся", "где",
    "дал", "два", "две", "для", "дня", "дом", "его", "ему", "есть", "еще",
    "ещё", "жил", "или", "имя", "как", "кем", "кто", "куда", "лет", "лишь",
    "мне", "мог", "мои", "мой", "моя", "над", "нам", "нас", "наш", "него",
    "нее", "неё", "ней", "нет", "них", "ночь", "один", "одна", "одно", "она",
    "они", "оно", "под", "при", "про", "раз", "сам", "свой", "себя", "сейчас",
    "так", "там", "твой", "твоя", "тебе", "тебя", "тем", "тех", "того", "тоже",
    "только", "тому", "тот", "тут", "уже", "чем", "что", "это", "эта", "эти",
    "этот", "этом", "эту", "ясно", "привет", "дела", "пока", "спасибо",
    "хорошо", "отлично", "люблю", "будут", "будет", "проект", "проекте",
    "работает", "репозитории", "долгом", "пути", "слово", "слова", "текст",
    "звук", "музыка", "жизнь", "время", "человек", "люди", "день", "ночь",
    "сразу", "снова", "скоро", "столько", "сколько", "сначала", "совсем",
    "сегодня", "конечно", "почему", "потому", "поэтому", "всегда", "иногда",
    "вместе", "благодарю", "поблагодарю", "говорю", "смотрю", "верю",
    "творю", "храню", "помню", "ценю", "звоню", "позволю", "сохраню",
    "проверю", "повторю", "юг", "удар", "главное", "главный", "главная", "главной",
})

# Однобуквенные русские предлоги/союзы, набранные в QWERTY
AMBIGUOUS_SINGLE_EN_TO_RU = frozenset({"d", "c", "b", "r", "e", "z", "f", "j"})

# Однобуквенные английские слова ('a', 'A', 'I'), набранные в ЙЦУКЕН
AMBIGUOUS_SINGLE_RU_TO_EN = frozenset({"ф", "Ф", "Ш"})

# Английские слова-омографы, совпадающие по QWERTY с русскими словами в RU-контексте ('her' -> 'рук', 'here' -> 'руку')
CONTEXTUAL_EN_TO_RU_HOMOGRAPHS = frozenset({"her", "here"})

CLAUSE_BREAK_PUNCT = frozenset(",.;:!?—–()[]\"'«»")

# Короткие однозначные русские слова в QWERTY (не являющиеся словами в EN)
EXACT_EN_TO_RU_WORDS = frozenset({
    "yf", "yj", "yt", "lf", "jn", "gj", "pf", "bp", "lj", "ns", "ds", "jy",
    "jyb", "jnf", "jyj", "vyt", "rnj", "ult", "nen", "nfv", "djn", "nfr",
    "xnj", "rfr", "e;t", "bkb", "lkz", "yfl", "gjl", "ghb", "ghj", "tot",
    "dyt", "dct", "dc.", "dfv", "dfc", "vjq", "ndjq", "cdjq", "nt,z", "nt,t",
    "ct,z", "ct,t", "njkmrj", "ctqxfc", "dlheu", "ghbdtn", "cgfcb,j",
    "nj;t", "tcnm", "rulf", "rjulf", "reLf", "rekf", "pfxtv", "gjxtve",
    "crjkmrj", "rfre.", "nfre.", "k.,k.", "k.,jdm", "cjdctv", "'nj", "'njn",
    "'nf", "'nb", "'njv", "'ne", ",elen", ",eltn", ",tp", "[jhjij",
    "ye", "ntgthm", "xedcndetim", "xedcndetn", "gthtrk.xfntkm",
    "ghjuhfvvf", "hfcrkflrf", "rkfdbcf", "rkfdbnehe", "rkfdbnnehf",
    "chfpe", "cyjdf", "crjhj", "crazu",
})

# Частые английские слова, набранные в ЙЦУКЕН
EXACT_RU_TO_EN_WORDS = frozenset({
    "еру", "фтв", "ащк", "цшер", "ершы", "ерфе", "акщь", "рфму", "црфе",
    "цруку", "црут", "руддщ", "цщкдв", "еуые", "знерщт", "ыефке", "ыещз",
    "ашду", "сщву", "рудз", "дщму", "ьгышс", "ыщгтв", "цщкл", "пщщв",
    "умукн", "фдд", "тще", "нщг", "нщгк", "ьфлу", "лтуц", "лтщц", "ефлу",
    "пшму", "тфьу", "ешду", "ешьу", "дшту", "дшые", "гыук", "вфеф", "ыфму",
    "щзут", "здфн", "куфв", "цкшеу", "срфтпу", "ыукмук", "сдшуте", "штыефдд",
    "зшз", "пше", "сщььше", "ыефегы", "икфтср",
})

PROTECTED_IT_WORDS = frozenset({
    "git", "pip", "npm", "npx", "pnpm", "yarn", "uv", "node", "python",
    "python3", "pwsh", "powershell", "cmd", "bash", "zsh", "sh", "dir",
    "ls", "cd", "cls", "clear", "echo", "cat", "grep", "rg", "curl",
    "wget", "ssh", "scp", "docker", "kubectl", "pytest", "unittest",
    "venv", "conda", "def", "class", "import", "from", "return", "yield",
    "async", "await", "const", "let", "var", "function", "func", "fn",
    "pub", "struct", "enum", "impl", "true", "false", "null", "none",
    "nil", "undefined", "self", "this", "super", "init", "main", "test",
    "src", "dist", "build", "out", "tmp", "env", "http", "https",
    "localhost", "api", "sdk", "cli", "gui", "ui", "url", "uri", "json",
    "html", "css", "sql", "xml", "yaml", "toml", "csv", "svg", "pdf",
    "utf", "ascii", "ctypes", "tkinter", "pathlib", "commit", "push",
    "pull", "merge", "rebase", "checkout", "branch", "status", "diff",
    "log", "clone", "fetch", "stash", "reset", "config", "sudo", "chmod",
    "chown", "kill", "ps", "top", "df", "du", "find", "sed", "awk",
    "head", "tail", "sort", "uniq", "wc", "tar", "zip", "unzip",
    "win32", "user32", "kernel32", "hkl", "hwnd", "daw", "vst", "midi",
    "wav", "flac", "mp3", "fft", "dsp", "db", "lufs", "ios", "macos",
    "ipad", "iphone", "ebay", "readme", "changelog", "web", "mp", "ip",
})

FILE_EXTENSIONS = (
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".json",
    ".yaml", ".yml", ".toml", ".xml", ".md", ".txt", ".log", ".exe", ".bat",
    ".ps1", ".sh", ".dll", ".so", ".zip", ".tar", ".gz", ".wav", ".flac",
    ".mp3", ".ogg", ".png", ".jpg", ".jpeg", ".svg", ".rpp", ".als", ".song",
    ".dawproject", ".db", ".sqlite", ".avl", ".ivl", ".rs", ".ex", ".exs",
)

# Характерные биграммы для скоринга правдоподобия
RU_GOOD_BIGRAMS = frozenset({
    "ст", "но", "ен", "то", "на", "ов", "ни", "ра", "во", "ко", "ро", "ос",
    "по", "го", "не", "от", "ал", "ре", "пр", "ор", "ли", "ла", "ка", "ес",
    "те", "ер", "та", "ол", "ит", "ль", "ва", "ак", "ин", "ет", "об", "ел",
    "ом", "ри", "ем", "ат", "ть", "за", "ви", "им", "ис", "ед", "ил", "ам",
    "ле", "до", "ан", "их", "од", "де", "да", "ся", "ки", "ве", "ие", "ны",
    "ой", "ей", "ай", "ий", "ый", "ую", "юю", "яю", "лю", "бл", "кл", "пл",
    "бо", "ра", "от", "ек", "кт", "эт", "бу", "ду", "ут", "ло", "мо", "др",
    "чу", "ув", "вс", "тв", "ву", "уе", "еш", "шь", "те", "еп", "пе",
    "гл", "ав", "вн", "ое",
})

RU_IMPOSSIBLE_CLUSTERS = (
    "цщ", "фш", "щт", "щк", "ддщ", "кдв", "знр", "рщ", "ыеф", "акщ", "цш",
    "шд", "сщв", "фд", "ьь", "ъъ", "ыы", "йй", "щщ", "шщ", "жщ", "гт",
    "дщк", "тще", "нщ", "ьф", "лту", "зш", "ср", "вф", "ыф",
)

EN_GOOD_BIGRAMS = frozenset({
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd", "ti", "es",
    "or", "te", "of", "ed", "is", "it", "al", "ar", "st", "to", "nt", "ng",
    "se", "ha", "as", "ou", "io", "le", "ve", "co", "me", "de", "hi", "ri",
    "ro", "ic", "ne", "ea", "ra", "ce", "ll", "el", "lo", "wo", "rl", "ld",
    "py", "yt", "ho", "od", "fr", "wh", "wi", "sh", "ch", "pr", "tr", "st",
    "we", "eb", "ap", "pp", "bo",
})

EN_IMPOSSIBLE_CLUSTERS = (
    "ghb", "bdt", "dtn", "ghj", "jtr", "njk", "kmr", "ctq", "xfc", "dlh",
    "lkt", "yfl", "gjl", "cnj", "vyt", "rnj", "ltv", "ltk", "f,j", "jnf",
    "ftn", "tcn", "gth", "crp", "dcn", "zcn", "xtn", "rfp", "cnb", "k.,",
    ",k.", "jk.", "zх", "qxz", "bxz", "cxz", "kqz", "jqz", "zqj",
    "xed", "cnd", "ntg", "thm", "tim", "rkl", "fcr", "rkf",
    "chf", "hfp", "fpe", "cyj", "crj",
    "ukf", "kfd", "fdy", "yjt",
)

EN_CONTRACTIONS_RE = re.compile(
    r"^[a-zA-Z]+(?:'s|'t|'re|'ve|'ll|'d|'m|n't)$"
)

VALID_RU_FINAL_B_WORDS = frozenset({
    "хлеб", "лоб", "гриб", "дуб", "зуб", "куб", "столб", "гроб", "краб",
    "раб", "горб", "герб", "серб", "штаб", "клуб", "сруб", "чуб", "слаб",
    "груб", "люб", "ушиб", "погиб", "изгиб", "прогиб", "перегиб", "способ",
    "масштаб", "прораб", "гардероб", "микроб", "сугроб", "жалоб", "судеб",
    "свадеб", "особ", "араб", "жлоб", "тулуб", "голуб", "зяб", "ряб", "хляб",
})

COMMON_RU_FINAL_YU_STEMS = frozenset({
    "любл", "вс", "дел", "дела", "зна", "дума", "работа", "чита", "игра",
    "по", "да", "мо", "сво", "тво", "каку", "таку", "нову", "хорошу",
    "большу", "живу", "говор", "смотр", "спл", "вер", "дар", "люб", "гуля",
    "понима", "ожида", "жела", "мечта", "ищ", "хоч", "п", "ш", "л", "б",
    "жив", "плыв", "зов", "рев", "пи", "ду", "чу",
})

COMMON_RU_YU_VERB_SUFFIXES: tuple[str, ...] = (
    "благодар", "говор", "смотр", "довер", "провер", "свер", "увер",
    "повер", "повтор", "раствор", "сотвор", "твор", "подар", "хран",
    "оцен", "измен", "замен", "примен", "отмен", "помен", "звон",
    "помн", "уточн", "объясн", "поясн", "выполн", "дополн", "наполн",
    "устран", "позвол", "раздел", "выдел", "удел", "подел", "хвал",
    "измер", "спор", "любл", "терпл", "купл", "ловл", "ставл",
    "правл", "бавл", "готовл", "удивл", "поздравл", "управл", "оставл",
    "отправл", "исправл", "добавл", "появл", "заявл", "представл", "направл",
    "вставл", "выставл", "оформл", "кормл", "уведомл", "размышл", "мысл",
)

OUTER_WRAP_QUOTES = (("\"", "\""), ("'", "'"), ("«", "»"), ("(", ")"))


def _map_chars(text: str, mapping: dict[str, str]) -> str:
    return "".join(mapping.get(ch, ch) for ch in text)


def fix_caps_lock(word: str) -> str:
    """Исправляет случайный инвертированный регистр (пРИВЕТ -> Привет, hELLO -> Hello)."""
    letters = [ch for ch in word if ch.isalpha()]
    if len(letters) >= 2 and letters[0].islower() and all(ch.isupper() for ch in letters[1:]):
        return word.swapcase()
    return word


def _has_latin(text: str) -> bool:
    return any("a" <= ch.lower() <= "z" for ch in text)


def _has_cyrillic(text: str) -> bool:
    return any(("а" <= ch.lower() <= "я") or ch in "ёЁ" for ch in text)


RU_DIGIT_UNITS = frozenset({
    "мм", "см", "дм", "км", "мг", "кг", "мл", "гл", "кв",
    "шт", "ст", "гр", "гц", "квт", "мвт", "чс", "ср", "вс",
    "пт", "пн", "вт", "чт", "сб",
})


def _extract_mistyped_cyrillic_digit_stem(token: str) -> str | None:
    """Распознаёт опечаточный кириллический токен с цифрами (например, «цуи8» → «web8»)."""
    if not token or not any(ch.isdigit() for ch in token):
        return None
    if not _has_cyrillic(token) or _has_latin(token):
        return None
    if not all(ch.isdigit() or ("а" <= ch.lower() <= "я") or ch in "ёЁ" for ch in token):
        return None

    alpha_ru = "".join(ch for ch in token if ch.isalpha()).lower()
    if len(alpha_ru) < 2 or alpha_ru in RU_DIGIT_UNITS or alpha_ru in COMMON_RU_WORDS:
        return None

    en_stem = _resolve_ru_to_en_core(alpha_ru).lower()
    if not en_stem.isascii() or not en_stem.isalpha():
        return None

    ru_score = _score_ru_plausibility(alpha_ru)
    en_score = _score_en_plausibility(en_stem)
    ru_vowels = sum(1 for ch in alpha_ru if ch in RU_VOWELS)

    if len(alpha_ru) >= 3 and (en_stem in COMMON_EN_WORDS or en_stem in PROTECTED_IT_WORDS):
        return en_stem
    if len(alpha_ru) == 2 and ru_vowels == 0 and en_stem in PROTECTED_IT_WORDS:
        return en_stem
    if len(alpha_ru) >= 3 and (
        (ru_vowels == 0 and en_score >= 2.0)
        or (en_score >= ru_score + 3.0 and en_score >= 2.5 and ru_score < 1.5)
    ):
        return en_stem
    return None


def is_protected_token(token: str) -> bool:
    """DeveloperGuard: защищает код, URL, пути, идентификаторы, XML/HTML-теги и IT-термины."""
    if not token:
        return False

    if re.match(r"^</?[a-zA-Z][a-zA-Z0-9_-]*/?>$", token):
        return True

    if token.startswith(".") and token[1:].lower() in {"env", "git", "gitignore", "qholo", "avl", "w9p", "jsonl", "vscode", "gemini"}:
        return True

    if "://" in token or "www." in token.lower():
        return True

    if "\\" in token or token.startswith(("./", "../", "~/", "/")):
        return True

    if len(token) >= 2 and token[1] == ":" and token[0].isalpha():
        return True

    if "@" in token:
        return True

    stripped = token.strip(".,!?;:()[]\"'")
    if not stripped:
        return False

    lower_stripped = stripped.lower()

    if "_" in stripped and (_has_latin(stripped) or _has_cyrillic(stripped)):
        return True

    has_digit = any(ch.isdigit() for ch in stripped)
    if has_digit and (_has_latin(stripped) or _has_cyrillic(stripped)):
        if _extract_mistyped_cyrillic_digit_stem(stripped) is None:
            return True

    # Путь с внутренним слэшем (не просто конечный знак пунктуации в RU->EN)
    if "/" in stripped and (_has_latin(stripped) or stripped.count("/") >= 1):
        return True

    if any(lower_stripped.endswith(ext) for ext in FILE_EXTENSIONS):
        return True

    # Проверка IT-лексики только для латинских токенов (кириллический опечаточный ввод вроде "знерщт" можно чинить)
    if _has_latin(stripped) and not _has_cyrillic(stripped):
        if lower_stripped in PROTECTED_IT_WORDS:
            return True

        # Флаг консоли вроде -b, --flag
        if token.startswith("-") and len(stripped) >= 1 and _has_latin(stripped):
            return True

        # camelCase (например, myVarName): переход lower -> UPPER и есть строчные после первой буквы
        if len(stripped) >= 3:
            has_camel_step = any(
                stripped[i].islower() and stripped[i + 1].isupper()
                for i in range(len(stripped) - 1)
            )
            has_other_lower = any(ch.islower() for ch in stripped[1:])
            if has_camel_step and has_other_lower:
                return True

        # Сокращение с точкой внутри (e.g., node.js, v1.2, example.com)
        if "." in stripped and not stripped.startswith(".") and not stripped.endswith("."):
            parts = stripped.split(".")
            if all(p.isalnum() for p in parts if p):
                return True

    return False


def _score_ru_plausibility(word: str) -> float:
    low = word.lower()
    if low in COMMON_RU_WORDS:
        return 10.0

    letters = [ch for ch in low if ch.isalpha()]
    if not letters:
        return -5.0

    score = 0.0
    vowels = sum(1 for ch in letters if ch in RU_VOWELS)
    if len(letters) >= 2 and vowels == 0:
        score -= 6.0
    elif vowels > 0:
        ratio = vowels / len(letters)
        if 0.2 <= ratio <= 0.65:
            score += 2.0

    for i in range(len(low) - 1):
        if low[i : i + 2] in RU_GOOD_BIGRAMS:
            score += 1.1

    for bad in RU_IMPOSSIBLE_CLUSTERS:
        if bad in low:
            score -= 4.5

    if low.startswith(("ь", "ъ", "ы")):
        score -= 6.0

    return score


def _score_en_plausibility(word: str) -> float:
    low = word.lower()
    if low in COMMON_EN_WORDS:
        return 10.0

    letters = [ch for ch in low if ch.isalpha()]
    if not letters:
        return -5.0

    score = 0.0
    vowels = sum(1 for ch in letters if ch in EN_VOWELS)
    if len(letters) >= 2 and vowels == 0:
        score -= 6.0
    elif vowels > 0:
        ratio = vowels / len(letters)
        if 0.2 <= ratio <= 0.65:
            score += 2.0

    for i in range(len(low) - 1):
        if low[i : i + 2] in EN_GOOD_BIGRAMS:
            score += 1.1

    for bad in EN_IMPOSSIBLE_CLUSTERS:
        if bad in low:
            score -= 4.5

    if low.endswith("tht"):
        score -= 4.5

    # На EN-раскладке буква 'q' даёт кириллическую 'й': в настоящем английском 'q'
    # почти всегда идёт в паре 'qu' (кроме редких аббревиатур вроде faq/sql)
    if len(letters) >= 4 and "q" in low and "qu" not in low:
        score -= 5.0

    return score


def _split_token(token: str) -> tuple[str, str, str]:
    """Разделяет токен на (prefix_punct, core, suffix_punct), бережно относясь к клавишам-буквам ЙЦУКЕН."""
    prefix = ""
    suffix = ""
    core = token

    for left_q, right_q in OUTER_WRAP_QUOTES:
        if len(core) >= 2 and core.startswith(left_q) and core.endswith(right_q):
            prefix += left_q
            suffix = right_q + suffix
            core = core[1:-1]

    # Снимаем безусловную ведущую пунктуацию (кроме '&' и клавиш QWERTY, которые являются буквами в ЙЦУКЕН: Б, б, Ж, ж, Ю, ю, Х, х, Ъ, ъ, Э, э, Ё, ё)
    while core and not core[0].isalnum():
        if core[0] == "&":
            break
        if (
            not _has_cyrillic(core)
            and len(core) >= 2
            and core[0] in EN_LEADING_LETTER_KEYS
            and core[1].isascii()
            and (core[1].isalpha() or core[1] in EN_INTERNAL_LAYOUT_CHARS)
        ):
            break
        prefix += core[0]
        core = core[1:]

    # Убираем кавычку перед кириллицей (например, "Привет)
    if core.startswith("\"") and len(core) > 1 and _has_cyrillic(core[1:]):
        prefix += "\""
        core = core[1:]

    # Снимаем безусловную хвостовую пунктуацию (!, ), :, ", многоточия)
    while core and (
        core.endswith("...")
        or core[-1] in "!):\"»—–"
    ):
        if core.endswith("..."):
            suffix = "..." + suffix
            core = core[:-3]
        else:
            suffix = core[-1] + suffix
            core = core[:-1]

    return prefix, core, suffix


def _resolve_en_to_ru_core(core: str, has_amp_question: bool = False) -> str:
    """Переводит основу EN -> RU, отличая хвостовые знаки препинания (',', '.', '?') от букв ('б', 'ю')."""
    if not core:
        return ""

    tail_punct = ""

    # Если строка заканчивается на '&', в EN->RU это безусловно '?' (сделает _map_chars)
    if core.endswith("?"):
        if not has_amp_question:
            tail_punct = "?"
            core = core[:-1]

    if core.endswith(","):
        stem = core[:-1]
        if stem:
            stem_ru = _map_chars(stem, EN_TO_RU_MAP)
            candidate_ru = stem_ru + "б"
            # Оставляем ',' как букву 'б' только если слово действительно из списка -б
            if candidate_ru.lower() not in VALID_RU_FINAL_B_WORDS:
                tail_punct = "," + tail_punct
                core = stem

    elif core.endswith(".") and not core.endswith(".."):
        stem = core[:-1]
        if stem:
            stem_ru = _map_chars(stem, EN_TO_RU_MAP)
            stem_low = stem_ru.lower()
            has_ru_vowels = any(ch in RU_VOWELS for ch in stem_low)
            looks_like_yu_word = (
                not has_ru_vowels
                or stem_low.endswith("ь")
                or stem_low.endswith(("бл", "пл", "вл", "мл", "фл"))
                or stem_low in COMMON_RU_FINAL_YU_STEMS
                or stem_low.endswith(COMMON_RU_YU_VERB_SUFFIXES)
                or (
                    len(stem_low) >= 3
                    and stem_low[-1] in "аеиоуыяю"
                    and _score_ru_plausibility(stem_low + "ю") >= 2.0
                    and stem_low not in COMMON_RU_WORDS
                )
            )
            if not looks_like_yu_word:
                tail_punct = "." + tail_punct
                core = stem

    converted = _map_chars(core, EN_TO_RU_MAP)
    return converted + tail_punct


def _resolve_ru_to_en_core(core: str) -> str:
    """Переводит основу RU -> EN, сохраняя хвостовую пунктуацию ',', '.', '?' при необходимости."""
    if not core:
        return ""

    tail_punct = ""
    while core and core[-1] in ",.?":
        tail_punct = core[-1] + tail_punct
        core = core[:-1]

    converted = _map_chars(core, RU_TO_EN_MAP)
    return converted + tail_punct


def detect_mistyped_direction(
    word: str,
    prev_lang: str | None = None,
    has_ru_context: bool = False,
    empathic_memory: Any = None,
) -> str | None:
    """Определяет необходимость переключения слова: 'EN_TO_RU', 'RU_TO_EN' или None."""
    if not word:
        return None

    _, core, _ = _split_token(word)
    if not core:
        return None

    # Одиночный '&' в русском контексте (Shift+7 на английской раскладке) — это '?'
    if core == "&":
        if prev_lang == "RU" or has_ru_context:
            return "EN_TO_RU"
        return None

    # Снимаем хвостовой ? , . для анализа основы
    clean = core.rstrip("?,.")
    if not clean:
        return None

    has_lat = _has_latin(clean)
    has_cyr = _has_cyrillic(clean)

    # Смешанные слова или чисто знаковые строки не трогаем автоматически
    if has_lat and has_cyr:
        return None

    if empathic_memory is not None:
        hint = empathic_memory.anticipate_direction(word, prev_lang=prev_lang, has_ru_context=has_ru_context)
        if hint == "KEEP":
            return None
        if hint in ("EN_TO_RU", "RU_TO_EN"):
            return hint

    if has_lat:
        if EN_CONTRACTIONS_RE.match(clean):
            return None

        low = clean.lower()

        # Однобуквенные русские предлоги/союзы в QWERTY
        if low in AMBIGUOUS_SINGLE_EN_TO_RU:
            if prev_lang == "RU" or has_ru_context:
                return "EN_TO_RU"
            return None

        # Точный словарь опечаточных коротких русских слов
        if low in EXACT_EN_TO_RU_WORDS or core.lower() in EXACT_EN_TO_RU_WORDS:
            return "EN_TO_RU"

        if low in CONTEXTUAL_EN_TO_RU_HOMOGRAPHS:
            if prev_lang == "RU":
                return "EN_TO_RU"
            return None

        if low in COMMON_EN_WORDS:
            return None

        # Наличие внутренних спецсимволов (';', '[', ']', ',', '.', "'", '`'), характерных для ЙЦУКЕН
        internal_body = clean[1:-1] if len(clean) > 2 else clean
        has_layout_chars = (
            any(ch in EN_INTERNAL_LAYOUT_CHARS for ch in internal_body)
            or (len(clean) >= 2 and clean[0] in EN_LEADING_LETTER_KEYS and clean[1].isalpha())
            or (len(clean) >= 2 and core.endswith(".") and not any(ch in RU_VOWELS for ch in _map_chars(clean, EN_TO_RU_MAP)))
        )

        ru_candidate = _resolve_en_to_ru_core(core).rstrip("?,.").lower()
        if ru_candidate in COMMON_RU_WORDS:
            return "EN_TO_RU"

        ru_score = _score_ru_plausibility(ru_candidate)
        en_score = _score_en_plausibility(low)

        if has_layout_chars and ru_score > en_score + 0.5:
            return "EN_TO_RU"

        # Отсутствие английских гласных при сильном русском кандидате
        en_vowels = sum(1 for ch in low if ch in EN_VOWELS)
        if len(low) >= 3 and en_vowels == 0 and ru_score >= 0.0:
            return "EN_TO_RU"

        if ru_score >= en_score + 2.5 and ru_score >= 1.0:
            return "EN_TO_RU"

        return None

    if has_cyr:
        low = clean.lower()

        # Русские одиночные слова ('а', 'в', 'и', 'о', ...) не переводим в EN без явного EN-контекста,
        # кроме буквы 'ф' ('a') и 'Ш' ('I'), которые не являются русскими словами
        if clean == "ф" and prev_lang == "EN":
            return "RU_TO_EN"
        if clean == "Ш" and prev_lang == "EN":
            return "RU_TO_EN"

        if low in EXACT_RU_TO_EN_WORDS:
            return "RU_TO_EN"

        if _extract_mistyped_cyrillic_digit_stem(clean) is not None:
            return "RU_TO_EN"

        if low in COMMON_RU_WORDS:
            return None

        en_candidate = _resolve_ru_to_en_core(core).rstrip("?,.").lower()
        if en_candidate in COMMON_EN_WORDS:
            return "RU_TO_EN"

        en_score = _score_en_plausibility(en_candidate)
        ru_score = _score_ru_plausibility(low)

        ru_vowels = sum(1 for ch in low if ch in RU_VOWELS)
        if len(low) >= 2 and ru_vowels == 0 and en_score >= 0.0:
            return "RU_TO_EN"

        if en_score >= ru_score + 2.5 and en_score >= 1.0:
            return "RU_TO_EN"

    return None


def convert_word(
    word: str,
    target_direction: str | None = None,
    fix_caps: bool = True,
    has_amp_question: bool = False,
) -> str:
    """Конвертирует одиночное слово (в т.ч. принудительно, если target_direction не задан)."""
    if not word:
        return ""

    prefix, core, suffix = _split_token(word)
    if not core:
        return fix_caps_lock(word) if fix_caps else word

    direction = target_direction
    if direction is None:
        if _has_cyrillic(core) and not _has_latin(core):
            direction = "RU_TO_EN"
        elif _has_latin(core) or any(ch in EN_INTERNAL_LAYOUT_CHARS for ch in core) or "&" in core:
            direction = "EN_TO_RU"

    if direction == "EN_TO_RU":
        converted_core = _resolve_en_to_ru_core(core, has_amp_question=has_amp_question)
    elif direction == "RU_TO_EN":
        converted_core = _resolve_ru_to_en_core(core)
    else:
        converted_core = core

    if fix_caps:
        converted_core = fix_caps_lock(converted_core)

    return f"{prefix}{converted_core}{suffix}"


def smart_convert_text(
    text: str,
    developer_guard: bool = True,
    fix_caps: bool = True,
    empathic_memory: Any = None,
) -> tuple[str, dict]:
    """
    Контекстная конвертация фразы или слова с сохранением пробелов, IT-токенов и предлогов.
    Возвращает (converted_text, stats_dict).
    """
    stats = {
        "converted_words": 0,
        "protected_tokens": 0,
        "caps_fixed": 0,
        "directions": [],
    }
    if not text:
        return text, stats

    parts = re.split(r"(\s+)", text)
    has_amp_question = "&" in text

    # Проход 1: классифицируем все токены для выявления языкового контекста фразы
    token_infos: list[dict] = []
    ru_evidence = 0
    en_evidence = 0

    for part in parts:
        if not part or part.isspace():
            token_infos.append({"kind": "ws", "raw": part})
            continue

        if developer_guard and is_protected_token(part):
            stats["protected_tokens"] += 1
            token_infos.append({"kind": "protected", "raw": part})
            continue

        _, core, _ = _split_token(part)
        if core == "&":
            token_infos.append({"kind": "amp_question", "raw": part})
            continue

        clean_low = core.rstrip("?,.").lower()

        if clean_low in AMBIGUOUS_SINGLE_EN_TO_RU:
            token_infos.append({"kind": "ambiguous_ru_single", "raw": part})
            continue

        if core in AMBIGUOUS_SINGLE_RU_TO_EN and clean_low == core.lower():
            token_infos.append({"kind": "ambiguous_en_single", "raw": part})
            continue

        if clean_low in CONTEXTUAL_EN_TO_RU_HOMOGRAPHS:
            token_infos.append({"kind": "ambiguous_ru_homograph", "raw": part})
            continue

        direction = detect_mistyped_direction(
            part,
            prev_lang=None,
            has_ru_context=False,
            empathic_memory=empathic_memory,
        )
        if direction == "EN_TO_RU":
            ru_evidence += 1
            token_infos.append({"kind": "convert", "dir": "EN_TO_RU", "lang": "RU", "raw": part})
        elif direction == "RU_TO_EN":
            en_evidence += 1
            token_infos.append({"kind": "convert", "dir": "RU_TO_EN", "lang": "EN", "raw": part})
        else:
            lang = None
            if _has_cyrillic(core):
                lang = "RU"
                ru_evidence += 1
            elif _has_latin(core):
                lang = "EN"
                en_evidence += 1
            token_infos.append({"kind": "keep", "lang": lang, "raw": part})

    has_ru_context = ru_evidence > 0
    has_en_context = en_evidence > 0

    # Проход 2: разрешаем короткие однобуквенные предлоги и применяем конвертацию / cAPS lOCK
    out_parts: list[str] = []
    last_natural_lang: str | None = None
    last_word_raw: str | None = None

    for idx, info in enumerate(token_infos):
        kind = info["kind"]
        raw = info["raw"]

        if kind == "ws":
            out_parts.append(raw)
            continue

        if kind == "amp_question":
            if last_natural_lang == "RU" or has_ru_context:
                converted = re.sub(r"&", "?", raw, count=1)
                out_parts.append(converted)
                last_natural_lang = "RU"
                last_word_raw = raw
                stats["converted_words"] += 1
                stats["directions"].append("EN_TO_RU")
            else:
                out_parts.append(raw)
                last_word_raw = raw
            continue

        if kind == "protected":
            if (
                (last_natural_lang == "RU" or has_ru_context)
                and raw.endswith("&")
                and not raw.endswith("&&")
            ):
                out_parts.append(raw[:-1] + "?")
                stats["converted_words"] += 1
                stats["directions"].append("EN_TO_RU")
            else:
                out_parts.append(raw)
            last_word_raw = raw
            continue

        if kind == "ambiguous_ru_single":
            # Lookahead до ближайшего естественного (незащищённого) слова
            next_natural_lang = None
            for follow in token_infos[idx + 1 :]:
                if follow["kind"] in ("convert", "keep") and follow.get("lang"):
                    next_natural_lang = follow["lang"]
                    break

            _, single_core, _ = _split_token(raw)
            preserve_latin_marker = False
            if single_core.isupper() and last_word_raw:
                _, prior_core, prior_trail = _split_token(last_word_raw)
                has_break = bool(prior_trail) or (last_word_raw[-1:] in CLAUSE_BREAK_PUNCT)
                if not has_break and _has_latin(prior_core) and not _has_cyrillic(prior_core):
                    preserve_latin_marker = True

            if not preserve_latin_marker and (last_natural_lang == "RU" or next_natural_lang == "RU" or has_ru_context):
                converted = convert_word(
                    raw,
                    target_direction="EN_TO_RU",
                    fix_caps=fix_caps,
                    has_amp_question=has_amp_question,
                )
                out_parts.append(converted)
                last_natural_lang = "RU"
                if converted != raw:
                    stats["converted_words"] += 1
                    stats["directions"].append("EN_TO_RU")
            else:
                out_parts.append(raw)
                last_natural_lang = "EN"
            last_word_raw = raw
            continue

        if kind == "ambiguous_en_single":
            next_natural_lang = None
            for follow in token_infos[idx + 1 :]:
                if follow["kind"] in ("convert", "keep") and follow.get("lang"):
                    next_natural_lang = follow["lang"]
                    break

            if last_natural_lang == "EN" or next_natural_lang == "EN" or (has_en_context and not last_natural_lang):
                converted = convert_word(
                    raw,
                    target_direction="RU_TO_EN",
                    fix_caps=False,
                    has_amp_question=has_amp_question,
                )
                out_parts.append(converted)
                last_natural_lang = "EN"
                if converted != raw:
                    stats["converted_words"] += 1
                    stats["directions"].append("RU_TO_EN")
            else:
                out_parts.append(raw)
                last_natural_lang = "RU"
            last_word_raw = raw
            continue

        if kind == "ambiguous_ru_homograph":
            next_natural_lang = None
            for follow in token_infos[idx + 1 :]:
                if follow["kind"] in ("convert", "keep") and follow.get("lang"):
                    next_natural_lang = follow["lang"]
                    break

            if last_natural_lang == "RU" and next_natural_lang != "EN":
                converted = convert_word(
                    raw,
                    target_direction="EN_TO_RU",
                    fix_caps=fix_caps,
                    has_amp_question=has_amp_question,
                )
                out_parts.append(converted)
                last_natural_lang = "RU"
                if converted != raw:
                    stats["converted_words"] += 1
                    stats["directions"].append("EN_TO_RU")
            else:
                out_parts.append(raw)
                last_natural_lang = "EN"
            last_word_raw = raw
            continue

        if kind == "convert":
            direction = info["dir"]
            converted = convert_word(
                raw,
                target_direction=direction,
                fix_caps=fix_caps,
                has_amp_question=has_amp_question,
            )
            out_parts.append(converted)
            last_natural_lang = info["lang"]
            last_word_raw = raw
            if converted != raw:
                stats["converted_words"] += 1
                stats["directions"].append(direction)
            continue

        # kind == "keep"
        keep_val = raw
        if (
            (last_natural_lang == "RU" or has_ru_context)
            and keep_val.endswith("&")
            and not keep_val.endswith("&&")
        ):
            keep_val = keep_val[:-1] + "?"
            stats["converted_words"] += 1
            stats["directions"].append("EN_TO_RU")

        if fix_caps:
            fixed = fix_caps_lock(keep_val)
            if fixed != keep_val:
                stats["caps_fixed"] += 1
                out_parts.append(fixed)
            else:
                out_parts.append(keep_val)
        else:
            out_parts.append(keep_val)

        if info.get("lang"):
            last_natural_lang = info["lang"]
        last_word_raw = raw

    return "".join(out_parts), stats


def should_retroactively_fix_prev_token(
    prev_word: str,
    converted_prev: str,
    converted_curr: str,
    before_prev_words: list[str] | tuple[str, ...] = (),
) -> bool:
    """Определяет ретроактивное исправление одиночной пограничной буквы (d->в, c->с, Z->Я, ф->a, Ш->I)."""
    if not prev_word or converted_prev == prev_word:
        return False
    lead, core, trail = _split_token(prev_word)
    if lead or trail or len(core) != 1:
        return False

    if core.lower() in AMBIGUOUS_SINGLE_EN_TO_RU:
        if not _has_cyrillic(converted_curr):
            return False
        if before_prev_words and core.isupper():
            prior_raw = before_prev_words[-1]
            _, prior_core, prior_trail = _split_token(prior_raw)
            has_break = bool(prior_trail) or (prior_raw[-1:] in CLAUSE_BREAK_PUNCT)
            if not has_break and _has_latin(prior_core) and not _has_cyrillic(prior_core):
                return False
        return True

    if core in AMBIGUOUS_SINGLE_RU_TO_EN:
        return _has_latin(converted_curr) and not _has_cyrillic(converted_curr)

    return False


def compute_shift_vector(
    word: str,
    prev_lang: str | None = None,
    has_ru_context: bool = False,
) -> tuple[float, float, float, float]:
    """Вычисляет 4D математический вектор признаков (ru, en, code, ctx) в диапазоне [0.0, 1.0]."""
    if not word or not word.strip():
        return (0.0, 0.0, 0.0, 0.0)

    w_code = 1.0 if is_protected_token(word) else 0.0
    w_ctx = 1.0 if (prev_lang == "RU" or has_ru_context) else (0.2 if prev_lang == "EN" else 0.5)

    _, core, _ = _split_token(word)
    clean = core.rstrip("?,.")
    if not clean:
        return (0.0, 0.0, w_code, w_ctx)

    if clean == "&":
        return (0.95 if w_ctx >= 0.5 else 0.1, 0.2, w_code, w_ctx)

    ru_cand = _resolve_en_to_ru_core(core).rstrip("?,.").lower() if _has_latin(clean) else clean.lower()
    en_cand = _resolve_ru_to_en_core(core).rstrip("?,.").lower() if _has_cyrillic(clean) else clean.lower()
    mistyped_en_stem = _extract_mistyped_cyrillic_digit_stem(clean)

    raw_ru = _score_ru_plausibility(ru_cand)
    raw_en = _score_en_plausibility(mistyped_en_stem or en_cand)

    if clean.lower() in EXACT_EN_TO_RU_WORDS or ru_cand in COMMON_RU_WORDS:
        raw_ru = max(raw_ru, 9.0)
    if clean.lower() in EXACT_RU_TO_EN_WORDS or en_cand in COMMON_EN_WORDS or mistyped_en_stem:
        raw_en = max(raw_en, 9.0)

    w_ru = round(min(1.0, max(0.0, (raw_ru + 6.0) / 16.0)), 3)
    w_en = round(min(1.0, max(0.0, (raw_en + 6.0) / 16.0)), 3)
    return (w_ru, w_en, round(w_code, 3), round(w_ctx, 3))
