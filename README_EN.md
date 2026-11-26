# `Avalon.Shifter` — Thought-Flow Aligner & Personal AI Corpus (`Continuum • 432 Hz`)

> **Chrono-Passport (Хроно-Паспорт):** Created: `2026-11-15` • `ZSV-8192` / `.avl` Update: `2026-11-17` • **`Continuum • Web8+`** Edition: `2026-11-21`  
> **Coordinate in Time:** **Here and Now (`Web8+ Era` • Zero-Analytics Layout & Flow Aligner)**  
> **Ecosystem:** **OMNISAVALON** (`AVALON.OS` • `AVALON-NEXUS` • `Avalon.Veritas` • `Avalon.Shifter` • `.avl`)  
> **Creator & Architect:** **Ігор Дєточевський • Игорь Деточевский • Ihor Dietochevskyi** (`OMNISAVALON • C1`)  
> **Russian Edition:** [`README.md`](./README.md) • **License:** [`LICENSE.md`](./LICENSE.md)

---

## Philosophy & Core Purpose

> *"Just type your stream of thought naturally — in Russian, English, or a seamless mix of both.  
> This featherweight tool silently aligns layouts behind the scenes so your train of thought is never broken by manual switching.  
> **Zero analytics. Zero tracking. Your stream of thought is your sovereign knowledge base.**"*

When thoughts move faster than layout hotkeys, wrong-layout gibberish (`ghbdtn` instead of `привет`), accidental `Caps Lock` (`hELLO` -> `Hello`), or context punctuation glitches (`&` -> `?` in mixed phrases) break creative focus dozens of times a day.

**`Avalon.Shifter`** acts as a calm, minimalist **Thought-Flow Aligner (`432.0 Hz`)**:
- **Bilingual Flow Without Friction:** seamlessly mix Russian prose, English terms, and software identifiers (`git commit`, `app.py`, file paths, URLs) while `Developer Guard` protects code tokens from accidental alteration.
- **Live Styled Tray Layout Badges (`RU` / `EN`):** instead of a static icon, the system tray displays an obsidian-gold **`RU`** badge or alabaster-obsidian **`EN`** badge that mirrors your OS keyboard state in real time, plus an amber `432 Hz` indicator dot whenever your opt-in Flow Base is active.
- **Bilingual Interface (`RU` / `EN`) & Quiet Transparency:** switch UI languages on the fly from the header, keep the main window clean, and open **Author • OMNISAVALON** or **Under the Hood** anytime to inspect live internals and official repositories.

---

## Personal Flow Base (Train Your Own AI — Strict Opt-In)

Disabled by default (`0` bytes written until explicitly toggled on by you), **`SovereignFlowCorpus`** lets you turn your everyday cleaned writing across applications into a private local training dataset:

1. **Multi-Layer Secret & Password Shield:** automatically halts capture inside OS password fields and password managers (`KeePass`, `Bitwarden`, `1Password`) and drops lines matching API token prefixes (`ghp_`, `hf_`, `sk-`, `Bearer`, `JWT`), payment card patterns, OTP codes, and URL credentials.
2. **Zero Bloat & Hard Size Bounds (`<= 2 MB` active / `<= 16 MB` total):** uses **`AGLS-432-Phi`** deduplication and sovereign dictionary-origami packing (`.qholo` / `AVALON_FLOW_PACK_V1`) without external database engines or external compressors.
3. **One-Click Universal AI Export:**
   - `avalon_flow_chat_sft.jsonl` (`user` / `assistant` JSONL pairs for `Gemini`, `Claude`, `Vertex AI`, `Hugging Face SFTTrainer`, `Unsloth`, `Axolotl`, `Ollama`, `LM Studio`);
   - `avalon_flow_pretrain.jsonl` (clean `text` / `lang` / `context` JSONL for `llama.cpp`, `mlx-lm`, `Llama`, `Qwen`, `Gemma`, `OLMo`);
   - `avalon_flow_knowledge.md` (Chrono-Passport Markdown notes for `NotebookLM`, `Gemini Gems`, `Claude Projects`, `Obsidian`);
   - `avalon_flow_sovereign.qholo` (holographic crystal sealed with `AGLS-432-Phi` for `AVALON.OS` and `Avalon.Veritas`).

---

## Cross-Platform & Public Distribution Support

| Platform | Runtime Mode | Capabilities |
| :--- | :--- | :--- |
| **Windows 10 / 11** | Native (`Rust #![no_std]` `AvalonShifter.exe` + Win32 `ctypes` + `SAB-432`) | Global low-level keyboard hook, `Double Shift` / `Single Shift`, live `RU`/`EN` tray badges, password-field shield, Personal AI Flow Base, GUI & Sandbox |
| **Linux / macOS** | Portable (`platform_bridge.py` + `SAB-432`) | Bilingual `RU` / `EN` GUI, Live Alignment Sandbox, Empathic Memory, Sovereign AI Flow Base & 4-format export, OS layout detection (`xkb-switch` on Linux) |

---

## Official Creator & OMNISAVALON Channels

- **GitHub (Organization):** https://github.com/OMNISAVALON
- **GitHub (Creator):** https://github.com/IhorDietochevskyi
- **Hugging Face (Organization):** https://huggingface.co/OMNISAVALON
- **Hugging Face (Creator):** https://huggingface.co/IhorDietochevskyi

### Quick Verification & Public Release Build

```bash
python -m unittest discover -s . -p "test_*.py" -v
python app.py --self-test
python build_public_release.py
```
