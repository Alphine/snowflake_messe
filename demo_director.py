#!/usr/bin/env python3
"""
MESSE Copilot — Demo Director
Interactive cue-card CLI for recording the CoCo CLI demo video.

Run this in one terminal pane, `cortex` in another (same project folder).
This tool never drives cortex itself — it choreographs the recording:
shows you exactly what to type, what's happening, and what to call out,
with a live timer so you land inside the 3-5 minute budget.

Bilingual: pick Indonesian or English once at startup (like the project's
site/index.html + site/en/index.html — a fixed choice, not a live switch).

Usage:
    python demo_director.py
"""

import os
import sys
import time
import shutil

# Windows consoles often default to cp1252, which can't encode box-drawing
# or check-mark characters. Force UTF-8 on stdout/stderr so this runs the
# same in PowerShell, Windows Terminal, or a piped/redirected shell.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _enable_windows_ansi():
    """Windows PowerShell / cmd.exe don't interpret ANSI escapes unless the
    console's virtual-terminal-processing flag is turned on first (Windows
    Terminal and PowerShell 7 already default it on, but legacy
    'Windows PowerShell' and cmd.exe do not). Returns True on success."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        if not kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING):
            return False
        return True
    except Exception:
        return False


_ANSI_OK = sys.stdout.isatty() and _enable_windows_ansi()

# ---------------------------------------------------------------- colors --
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    NAVY_BG = "\033[48;5;17m"
    SKY = "\033[38;5;45m"
    GREEN = "\033[38;5;114m"
    YELLOW = "\033[38;5;221m"
    RED = "\033[38;5;210m"
    WHITE = "\033[38;5;255m"
    MUTED = "\033[38;5;103m"
    PURPLE = "\033[38;5;183m"


def supports_color():
    return _ANSI_OK


if not supports_color():
    for attr in dir(C):
        if not attr.startswith("_"):
            setattr(C, attr, "")

WIDTH = min(shutil.get_terminal_size((90, 24)).columns, 96)

# ---------------------------------------------------------------- language --
LANG = "id"  # set by pick_language() before anything else runs


def t(id_text, en_text):
    """Pick the string for the active LANG. Called at render time, not at
    import time, so LANG can change before any output happens."""
    return id_text if LANG == "id" else en_text


# ------------------------------------------------------------ primitives --

def rule(char="─", color=C.MUTED):
    print(f"{color}{char * WIDTH}{C.RESET}")


def center(text, color=C.WHITE, bold=False):
    b = C.BOLD if bold else ""
    pad = max((WIDTH - strip_len(text)) // 2, 0)
    print(" " * pad + f"{b}{color}{text}{C.RESET}")


def strip_len(text):
    return len(text)


def clear():
    if _ANSI_OK:
        print("\033[2J\033[H", end="")
    else:
        print("\n" * 3)


def wait_enter(prompt=None):
    if prompt is None:
        prompt = t("Tekan ENTER untuk lanjut...", "Press ENTER to continue...")
    try:
        input(f"\n{C.DIM}{C.ITALIC}{prompt}{C.RESET}")
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def banner():
    clear()
    rule("═", C.SKY)
    center("MESSE COPILOT — DEMO DIRECTOR", C.SKY, bold=True)
    center(
        t(
            "Snowflake CoCo CLI Hackathon 2026 · Cue card untuk rekaman",
            "Snowflake CoCo CLI Hackathon 2026 · Cue cards for the recording",
        ),
        C.MUTED,
    )
    rule("═", C.SKY)
    print()


def step_box(step_no, total, label, color):
    step_word = t("STEP", "STEP")
    tag = f" {step_word} {step_no}/{total} · {label} "
    inner_w = len(tag)
    print(f"{color}{C.BOLD}┌{'─' * inner_w}┐{C.RESET}")
    print(f"{color}{C.BOLD}│{tag}│{C.RESET}")
    print(f"{color}{C.BOLD}└{'─' * inner_w}┘{C.RESET}")


def typewriter(text, color=C.WHITE, delay=0.014):
    for ch in text:
        sys.stdout.write(f"{color}{ch}{C.RESET}")
        sys.stdout.flush()
        try:
            time.sleep(delay)
        except KeyboardInterrupt:
            sys.stdout.write(f"{color}{text[len(text):]}{C.RESET}")
            break
    print()


def countdown(seconds, label=None):
    if label is None:
        label = t("Bicara di sini", "Talk here")
    for remaining in range(seconds, 0, -1):
        mm, ss = divmod(remaining, 60)
        left = t("tersisa", "left")
        sys.stdout.write(f"\r{C.DIM}  {label} — {mm:02d}:{ss:02d} {left}   {C.RESET}")
        sys.stdout.flush()
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    sys.stdout.write("\r" + " " * WIDTH + "\r")


# ---------------------------------------------------------------- content --
# Every skill carries an "id" and "en" block with identical keys. The demo
# question itself is translated too (not just the narration) — the CoCo CLI
# agent answers in whichever language it's asked, per copilot_spec.md's
# tone rule, but this hasn't been recorded live in English yet. Do one dry
# run in English before trusting it on camera.

SKILLS = [
    {
        "num": 1,
        "core": True,
        "budget_input": 15,
        "budget_processing": 20,
        "budget_output": 25,
        "id": {
            "name": "Stealth-Accumulation Screening",
            "narration": "Copilot ini nge-query langsung ke Snowflake, bukan jawab dari "
                         "ingatan — tiap klaim ada di baliknya ada SQL beneran.",
            "input": "Saham apa yang lagi diakumulasi diam-diam?",
            "processing": [
                "CoCo CLI mem-parse pertanyaan -> nentuin perlu query MART.VW_WATCHLIST",
                "SQL_EXECUTE ke Snowflake (live, bukan cache) -> WHERE SIGNAL_LABEL IN (...)",
                "Agent decompose skor: accumulation intensity, persistence, price quietness",
            ],
            "output_callouts": [
                "Tabel ticker + skor + alasan kenapa masuk watchlist",
                "Ada disclosure otomatis: 'BANDAR_SCORE adalah proxy, bukan broker order flow'",
            ],
        },
        "en": {
            "name": "Stealth-Accumulation Screening",
            "narration": "The copilot queries Snowflake directly instead of answering from "
                         "memory — every claim has real SQL behind it.",
            "input": "Which stocks are being quietly accumulated right now?",
            "processing": [
                "CoCo CLI parses the question -> decides it needs MART.VW_WATCHLIST",
                "SQL_EXECUTE against Snowflake (live, not cached) -> WHERE SIGNAL_LABEL IN (...)",
                "Agent decomposes the score: accumulation intensity, persistence, price quietness",
            ],
            "output_callouts": [
                "Table of tickers + scores + why each made the watchlist",
                "Automatic disclosure: 'BANDAR_SCORE is a proxy, not broker order flow'",
            ],
        },
    },
    {
        "num": 2,
        "core": True,
        "budget_input": 15,
        "budget_processing": 25,
        "budget_output": 35,
        "id": {
            "name": "Kelly Position Sizing + Honesty Beat",
            "narration": "Ini bagian pembeda utama — sistem punya hak buat BILANG TIDAK "
                         "kalau edge-nya belum kebukti secara statistik.",
            "input": "Berapa besar posisi yang wajar untuk PTBA?",
            "processing": [
                "Query MART.VW_POSITION_SIZING untuk ticker itu",
                "Ambil MART.SIGNAL_EDGE (win rate & payoff terukur, N=997 observasi)",
                "Hitung Kelly fraction -> negatif -> di-clip ke 0",
            ],
            "output_callouts": [
                "SUGGESTED_WEIGHT = 0.00%, SIZING_CAVEAT = NO_EDGE",
                "Agent jelasin formula Kelly-nya, bukan cuma nampilin angka mentah",
                "Tegasin: skor tinggi (82.2) TIDAK otomatis dapat posisi",
            ],
        },
        "en": {
            "name": "Kelly Position Sizing + Honesty Beat",
            "narration": "This is the core differentiator — the system is allowed to say NO "
                         "when the edge isn't statistically proven.",
            "input": "What's a reasonable position size for PTBA?",
            "processing": [
                "Query MART.VW_POSITION_SIZING for that ticker",
                "Pull MART.SIGNAL_EDGE (measured win rate & payoff, N=997 observations)",
                "Compute the Kelly fraction -> negative -> clipped to 0",
            ],
            "output_callouts": [
                "SUGGESTED_WEIGHT = 0.00%, SIZING_CAVEAT = NO_EDGE",
                "Agent explains the Kelly formula, not just a raw number",
                "Stress this: a high score (82.2) does NOT automatically get a position",
            ],
        },
    },
    {
        "num": 3,
        "core": True,
        "budget_input": 10,
        "budget_processing": 15,
        "budget_output": 15,
        "id": {
            "name": "Grounding Refusal (anti-halusinasi)",
            "narration": "Tes cepat: kalau ticker-nya nggak ada di data, apa dia ngarang "
                         "jawaban atau jujur bilang nggak ketemu?",
            "input": "Bagaimana sinyal untuk ticker ABCDE?",
            "processing": [
                "SQL_EXECUTE ke VW_WATCHLIST WHERE TICKER = 'ABCDE' -> 0 rows",
                "SQL_EXECUTE ke BANDAR_SCORE history -> 0 rows juga",
                "Tidak ada fallback ke jawaban generik dari training data",
            ],
            "output_callouts": [
                "Agent bilang jujur: ticker tidak ditemukan di database MESSE",
                "Nawarin next step (cek ejaan / cari ticker mirip) — bukan ngarang angka",
            ],
        },
        "en": {
            "name": "Grounding Refusal (anti-hallucination)",
            "narration": "Quick test: if the ticker doesn't exist in the data, does it make "
                         "something up or honestly say it can't find it?",
            "input": "What's the signal for ticker ABCDE?",
            "processing": [
                "SQL_EXECUTE against VW_WATCHLIST WHERE TICKER = 'ABCDE' -> 0 rows",
                "SQL_EXECUTE against BANDAR_SCORE history -> 0 rows too",
                "No fallback to a generic answer from training data",
            ],
            "output_callouts": [
                "Agent states plainly: the ticker isn't in the MESSE database",
                "Offers a next step (check spelling / find similar tickers) — never a made-up number",
            ],
        },
    },
    {
        "num": 4,
        "core": False,
        "budget_input": 10,
        "budget_processing": 15,
        "budget_output": 20,
        "id": {
            "name": "Distribution Warning Screening",
            "narration": "Bukan cuma nyari yang naik — mesin sinyal yang sama juga bisa "
                         "kasih peringatan dini buat saham yang lagi didistribusi.",
            "input": "Saham apa yang sedang didistribusi sekarang?",
            "processing": [
                "Query MART.VW_WATCHLIST WHERE SIGNAL_LABEL = 'DISTRIBUTION'",
                "Sort ascending by BANDAR_SCORE -> skor paling rendah = distribusi paling kuat",
                "Pipeline SQL-nya sama persis dengan skill screening akumulasi, cuma arah beda",
            ],
            "output_callouts": [
                "List ticker skor rendah (mis. ARNA, BYAN, GOTO) + return 20 hari",
                "Nunjukin sistemnya simetris: bukan cuma nyari peluang, tapi juga warning dini",
            ],
        },
        "en": {
            "name": "Distribution Warning Screening",
            "narration": "Not just upside hunting — the same signal engine also gives an "
                         "early warning for stocks currently being distributed.",
            "input": "Which stocks are being distributed right now?",
            "processing": [
                "Query MART.VW_WATCHLIST WHERE SIGNAL_LABEL = 'DISTRIBUTION'",
                "Sort ascending by BANDAR_SCORE -> the lowest score is the strongest distribution",
                "Same SQL pipeline as the accumulation screen, just the opposite direction",
            ],
            "output_callouts": [
                "List of low-score tickers (e.g. ARNA, BYAN, GOTO) + their 20-day return",
                "Shows the system is symmetric: it flags downside risk, not just upside",
            ],
        },
    },
]

BONUS_HONESTY = {
    "id": {
        "name": "Bonus — Honesty Beat Aggregate (penutup)",
        "input": "Dari semua saham yang punya sinyal akumulasi atau distribusi, "
                 "berapa banyak yang punya edge yang benar-benar terbukti secara statistik?",
        "callout": "Jawaban: 0 dari 259 — dan ini yang harus jadi kalimat penutup video.",
        "countdown_label": "Biarkan angka '0 dari 259' jadi kalimat penutup",
    },
    "en": {
        "name": "Bonus — Honesty Beat Aggregate (closing shot)",
        "input": "Of all stocks with an accumulation or distribution signal, how many "
                 "actually have a statistically proven edge?",
        "callout": "Answer: 0 of 259 — make this the closing line of the video.",
        "countdown_label": "Let '0 of 259' land as the closing line",
    },
}


def show_skill(skill, idx, total):
    L = skill[LANG]
    banner()
    color = [C.SKY, C.GREEN, C.YELLOW][idx % 3]
    skill_word = t("SKILL", "SKILL")
    print(f"{color}{C.BOLD}{skill_word} {skill['num']}/{total} — {L['name']}{C.RESET}")
    print(f"{C.ITALIC}{C.MUTED}{L['narration']}{C.RESET}\n")
    wait_enter(t(
        "Siap mulai skill ini? ENTER untuk masuk STEP 1 (Input)",
        "Ready to start this skill? ENTER to go to STEP 1 (Input)",
    ))

    # STEP 1 — INPUT
    banner()
    step_box(1, 3, t("INPUT", "INPUT"), C.SKY)
    print(f"\n{C.DIM}{t('Ketik ini persis di terminal `cortex`:', 'Type this exactly into the `cortex` terminal:')}{C.RESET}\n")
    typewriter(f'  "{L["input"]}"', C.WHITE, delay=0.018)
    budget_label = t("Budget bicara/setup", "Talk/setup budget")
    print(f"\n{C.MUTED}{budget_label}: ~{skill['budget_input']}{t('detik', 's')}{C.RESET}")
    countdown(skill["budget_input"], t("Ketik & jelaskan konteks pertanyaannya", "Type it & explain the context"))
    wait_enter(t(
        "Sudah ketik & Enter di cortex? Lanjut ke STEP 2 (Processing)",
        "Typed it and hit Enter in cortex? Move on to STEP 2 (Processing)",
    ))

    # STEP 2 — PROCESSING
    banner()
    step_box(2, 3, t("PROCESSING", "PROCESSING"), C.YELLOW)
    print(f"\n{C.DIM}{t('Yang lagi kejadian di balik layar (narasikan ini):', 'What is happening behind the scenes (narrate this):')}{C.RESET}\n")
    for line in L["processing"]:
        print(f"  {C.YELLOW}▸{C.RESET} {line}")
    budget_label = t("Budget", "Budget")
    print(f"\n{C.MUTED}{budget_label}: ~{skill['budget_processing']}{t('detik', 's')}{C.RESET}")
    countdown(skill["budget_processing"], t("Biarkan SQL_EXECUTE kelihatan jalan di layar", "Let SQL_EXECUTE stay visible on screen"))
    wait_enter(t(
        "Query sudah selesai jalan? Lanjut ke STEP 3 (Output)",
        "Has the query finished running? Move on to STEP 3 (Output)",
    ))

    # STEP 3 — OUTPUT
    banner()
    step_box(3, 3, t("OUTPUT", "OUTPUT"), C.GREEN)
    print(f"\n{C.DIM}{t('Highlight / sebutkan poin ini dari jawaban agent:', 'Highlight / call out these points from the answer:')}{C.RESET}\n")
    for line in L["output_callouts"]:
        print(f"  {C.GREEN}✓{C.RESET} {line}")
    budget_label = t("Budget", "Budget")
    print(f"\n{C.MUTED}{budget_label}: ~{skill['budget_output']}{t('detik', 's')}{C.RESET}")
    countdown(skill["budget_output"], t("Highlight bagian penting di layar", "Highlight the key part on screen"))
    wait_enter(t(
        f"Skill {skill['num']} selesai. ENTER untuk skill berikutnya",
        f"Skill {skill['num']} done. ENTER for the next skill",
    ))


def show_bonus():
    L = BONUS_HONESTY[LANG]
    banner()
    print(f"{C.PURPLE}{C.BOLD}{L['name']}{C.RESET}\n")
    print(f"{C.DIM}{t('Ketik ini sebagai penutup:', 'Type this as the closer:')}{C.RESET}\n")
    typewriter(f'  "{L["input"]}"', C.WHITE, delay=0.018)
    print(f"\n{C.YELLOW}{C.BOLD}{L['callout']}{C.RESET}")
    countdown(30, L["countdown_label"])
    wait_enter(t("Selesai. ENTER untuk ringkasan akhir", "Done. ENTER for the final summary"))


def total_budget(skills, include_bonus):
    tot = sum(s["budget_input"] + s["budget_processing"] + s["budget_output"] for s in skills)
    if include_bonus:
        tot += 30
    return tot


def summary(skills_done, include_bonus):
    banner()
    rule("─", C.GREEN)
    center(t("RINGKASAN REKAMAN", "RECORDING SUMMARY"), C.GREEN, bold=True)
    rule("─", C.GREEN)
    print()
    n = len(skills_done)
    status = C.GREEN if n >= 2 else C.RED
    label = t("Skill terdemokan", "Skills demoed")
    ok_text = t("(memenuhi syarat min. 2-3 skill)", "(meets the min. 2-3 skill requirement)")
    low_text = t("(KURANG — minimal 2 dibutuhkan)", "(SHORT — at least 2 required)")
    print(f"  {label} : {status}{n}{C.RESET} {ok_text if n >= 2 else low_text}")
    for s in skills_done:
        print(f"    {C.GREEN}✓{C.RESET} {s[LANG]['name']}")
    if include_bonus:
        print(f"    {C.PURPLE}✓{C.RESET} {BONUS_HONESTY[LANG]['name']}")
    est = total_budget(skills_done, include_bonus)
    mm, ss = divmod(est, 60)
    dur_color = C.GREEN if 180 <= est <= 300 else C.YELLOW
    dur_label = t("Estimasi durasi", "Estimated duration")
    target_label = t("target 3-5 menit", "target 3-5 min")
    print(f"\n  {dur_label}  : {dur_color}{mm}m {ss:02d}s{C.RESET} ({target_label} / 180-300s)")
    print(f"\n{C.DIM}{t('Checklist submission:', 'Submission checklist:')}{C.RESET}")
    checks = t(
        [
            "Screen recording nunjukin cortex jalan langsung (bukan mock/slide)",
            "Ada minimal 1 workflow end-to-end yang beneran jalan (input->output nyata)",
            "2-3 skill/capability kelihatan beda satu sama lain",
            "Durasi 3-5 menit",
        ],
        [
            "Screen recording shows cortex actually running (not a mock/slide)",
            "At least 1 fully working end-to-end workflow (real input->output)",
            "2-3 distinctly different skills/capabilities shown",
            "Duration 3-5 minutes",
        ],
    )
    for c in checks:
        print(f"  {C.GREEN}☐{C.RESET} {c}")
    print()
    rule("═", C.SKY)


def pick_language():
    global LANG
    clear()
    rule("═", C.SKY)
    center("MESSE COPILOT — DEMO DIRECTOR", C.SKY, bold=True)
    rule("═", C.SKY)
    print()
    print(f"{C.BOLD}Choose a language / Pilih bahasa:{C.RESET}\n")
    print(f"  {C.SKY}[1]{C.RESET} Bahasa Indonesia")
    print(f"  {C.SKY}[2]{C.RESET} English\n")
    while True:
        try:
            choice = input(f"{C.BOLD}> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if choice == "1" or choice.lower().startswith("id"):
            LANG = "id"
            return
        if choice == "2" or choice.lower().startswith("en"):
            LANG = "en"
            return
        print(f"{C.RED}Pilihan tidak valid / invalid choice.{C.RESET}")


def main_menu():
    while True:
        banner()
        print(f"{C.BOLD}{t('Pilih mode:', 'Choose a mode:')}{C.RESET}\n")
        core_skills = [s for s in SKILLS if s["core"]]
        optional_skills = [s for s in SKILLS if not s["core"]]
        pick_range = f"1-{len(SKILLS)}"

        print(f"  {C.SKY}[1]{C.RESET} " + t(
            f"Sequence inti ({len(core_skills)} skill + bonus honesty beat) — direkomendasikan, muat 3-5 menit",
            f"Core sequence ({len(core_skills)} skills + bonus honesty beat) — recommended, fits 3-5 min",
        ))
        print(f"  {C.SKY}[2]{C.RESET} " + t("Latihan satu skill saja", "Practice a single skill"))
        print(f"  {C.SKY}[3]{C.RESET} " + t(
            "Lihat semua prompt (tanpa timer, buat nyontek cepat)",
            "View all prompts (no timer, quick cheat sheet)",
        ))
        print(f"  {C.SKY}[5]{C.RESET} " + t(
            f"Sequence extended (semua {len(SKILLS)} skill + bonus) — lebih panjang, cek durasi",
            f"Extended sequence (all {len(SKILLS)} skills + bonus) — longer, watch the duration",
        ))
        print(f"  {C.SKY}[6]{C.RESET} " + t("Ganti bahasa", "Switch language"))
        print(f"  {C.SKY}[0]{C.RESET} " + t("Keluar", "Quit") + "\n")
        try:
            choice = input(f"{C.BOLD}> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "1":
            done = []
            for i, skill in enumerate(core_skills):
                show_skill(skill, i, len(core_skills))
                done.append(skill)
            show_bonus()
            summary(done, include_bonus=True)
            wait_enter(t("ENTER untuk kembali ke menu", "ENTER to go back to the menu"))

        elif choice == "2":
            banner()
            for s in SKILLS:
                tag = "" if s["core"] else t(" (opsional)", " (optional)")
                print(f"  {C.SKY}[{s['num']}]{C.RESET} {s[LANG]['name']}{C.MUTED}{tag}{C.RESET}")
            try:
                pick = input(f"\n{C.BOLD}{t(f'Pilih skill ({pick_range}): ', f'Pick a skill ({pick_range}): ')}{C.RESET}").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            matches = [s for s in SKILLS if str(s["num"]) == pick]
            if matches:
                show_skill(matches[0], 0, 1)
                summary(matches, include_bonus=False)
                wait_enter(t("ENTER untuk kembali ke menu", "ENTER to go back to the menu"))

        elif choice == "5":
            done = []
            for i, skill in enumerate(SKILLS):
                show_skill(skill, i, len(SKILLS))
                done.append(skill)
            show_bonus()
            summary(done, include_bonus=True)
            wait_enter(t("ENTER untuk kembali ke menu", "ENTER to go back to the menu"))

        elif choice == "3":
            banner()
            for s in SKILLS:
                L = s[LANG]
                print(f"{C.BOLD}{L['name']}{C.RESET}")
                print(f'  {C.WHITE}"{L["input"]}"{C.RESET}\n')
            LB = BONUS_HONESTY[LANG]
            print(f"{C.BOLD}{LB['name']}{C.RESET}")
            print(f'  {C.WHITE}"{LB["input"]}"{C.RESET}')
            wait_enter(t("ENTER untuk kembali ke menu", "ENTER to go back to the menu"))

        elif choice == "6":
            pick_language()

        elif choice == "0":
            clear()
            print(f"{C.SKY}{t('Selamat merekam. Semoga lolos!', 'Happy recording. Good luck!')}{C.RESET}")
            break


if __name__ == "__main__":
    try:
        pick_language()
        main_menu()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
