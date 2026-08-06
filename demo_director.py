#!/usr/bin/env python3
"""
MESSE Copilot — Demo Director
Interactive cue-card CLI for recording the CoCo CLI demo video.

Run this in one terminal pane, `cortex` in another (same project folder).
This tool never drives cortex itself — it choreographs the recording:
shows you exactly what to type, what's happening, and what to call out,
with a live timer so you land inside the 3-5 minute budget.

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


def wait_enter(prompt="Tekan ENTER untuk lanjut..."):
    try:
        input(f"\n{C.DIM}{C.ITALIC}{prompt}{C.RESET}")
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def banner():
    clear()
    rule("═", C.SKY)
    center("MESSE COPILOT — DEMO DIRECTOR", C.SKY, bold=True)
    center("Snowflake CoCo CLI Hackathon 2026 · Cue cards for the recording", C.MUTED)
    rule("═", C.SKY)
    print()


def step_box(step_no, total, label, color):
    tag = f" STEP {step_no}/{total} · {label} "
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


def countdown(seconds, label="Bicara di sini"):
    for remaining in range(seconds, 0, -1):
        mm, ss = divmod(remaining, 60)
        sys.stdout.write(f"\r{C.DIM}  {label} — {mm:02d}:{ss:02d} tersisa   {C.RESET}")
        sys.stdout.flush()
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    sys.stdout.write("\r" + " " * (WIDTH) + "\r")


# ---------------------------------------------------------------- content --

SKILLS = [
    {
        "id": 1,
        "name": "Stealth-Accumulation Screening",
        "narration": "Copilot ini nge-query langsung ke Snowflake, bukan jawab dari ingatan — "
                      "tiap klaim ada di baliknya ada SQL beneran.",
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
        "budget_input": 15,
        "budget_processing": 20,
        "budget_output": 25,
    },
    {
        "id": 2,
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
        "budget_input": 15,
        "budget_processing": 25,
        "budget_output": 35,
    },
    {
        "id": 3,
        "name": "Grounding Refusal (anti-halusinasi)",
        "narration": "Tes cepat: kalau ticker-nya nggak ada di data, apa dia ngarang jawaban "
                      "atau jujur bilang nggak ketemu?",
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
        "budget_input": 10,
        "budget_processing": 15,
        "budget_output": 15,
    },
]

BONUS_HONESTY = {
    "name": "Bonus — Honesty Beat Aggregate (closing shot)",
    "input": "Dari semua saham yang punya sinyal akumulasi atau distribusi, "
             "berapa banyak yang punya edge yang benar-benar terbukti secara statistik?",
    "callout": "Jawaban: 0 dari 259 — dan ini yang harus jadi kalimat penutup video.",
}


def show_skill(skill, idx, total):
    banner()
    color = [C.SKY, C.GREEN, C.YELLOW][idx % 3]
    print(f"{color}{C.BOLD}SKILL {skill['id']}/{total} — {skill['name']}{C.RESET}")
    print(f"{C.ITALIC}{C.MUTED}{skill['narration']}{C.RESET}\n")
    wait_enter("Siap mulai skill ini? ENTER untuk masuk STEP 1 (Input)")

    # STEP 1 — INPUT
    banner()
    step_box(1, 3, "INPUT", C.SKY)
    print(f"\n{C.DIM}Ketik ini persis di terminal `cortex`:{C.RESET}\n")
    typewriter(f'  "{skill["input"]}"', C.WHITE, delay=0.018)
    print(f"\n{C.MUTED}Budget bicara/setup: ~{skill['budget_input']} detik{C.RESET}")
    countdown(skill["budget_input"], "Ketik & jelaskan konteks pertanyaannya")
    wait_enter("Sudah ketik & Enter di cortex? Lanjut ke STEP 2 (Processing)")

    # STEP 2 — PROCESSING
    banner()
    step_box(2, 3, "PROCESSING", C.YELLOW)
    print(f"\n{C.DIM}Yang lagi kejadian di balik layar (narasikan ini):{C.RESET}\n")
    for line in skill["processing"]:
        print(f"  {C.YELLOW}▸{C.RESET} {line}")
    print(f"\n{C.MUTED}Budget: ~{skill['budget_processing']} detik{C.RESET}")
    countdown(skill["budget_processing"], "Biarkan SQL_EXECUTE kelihatan jalan di layar")
    wait_enter("Query sudah selesai jalan? Lanjut ke STEP 3 (Output)")

    # STEP 3 — OUTPUT
    banner()
    step_box(3, 3, "OUTPUT", C.GREEN)
    print(f"\n{C.DIM}Highlight / sebutkan poin ini dari jawaban agent:{C.RESET}\n")
    for line in skill["output_callouts"]:
        print(f"  {C.GREEN}✓{C.RESET} {line}")
    print(f"\n{C.MUTED}Budget: ~{skill['budget_output']} detik{C.RESET}")
    countdown(skill["budget_output"], "Highlight bagian penting di layar")
    wait_enter(f"Skill {skill['id']} selesai. ENTER untuk skill berikutnya")


def show_bonus():
    banner()
    print(f"{C.PURPLE}{C.BOLD}{BONUS_HONESTY['name']}{C.RESET}\n")
    print(f"{C.DIM}Ketik ini sebagai penutup:{C.RESET}\n")
    typewriter(f'  "{BONUS_HONESTY["input"]}"', C.WHITE, delay=0.018)
    print(f"\n{C.YELLOW}{C.BOLD}{BONUS_HONESTY['callout']}{C.RESET}")
    countdown(30, "Biarkan angka '0 dari 259' jadi kalimat penutup")
    wait_enter("Selesai. ENTER untuk ringkasan akhir")


def total_budget(skills, include_bonus):
    t = sum(s["budget_input"] + s["budget_processing"] + s["budget_output"] for s in skills)
    if include_bonus:
        t += 30
    return t


def summary(skills_done, include_bonus):
    banner()
    rule("─", C.GREEN)
    center("RINGKASAN REKAMAN", C.GREEN, bold=True)
    rule("─", C.GREEN)
    print()
    n = len(skills_done)
    status = C.GREEN if n >= 2 else C.RED
    print(f"  Skill terdemokan : {status}{n}/3{C.RESET} "
          f"{'(memenuhi syarat 2-3 skill)' if n >= 2 else '(KURANG — minimal 2 dibutuhkan)'}")
    for s in skills_done:
        print(f"    {C.GREEN}✓{C.RESET} {s['name']}")
    if include_bonus:
        print(f"    {C.PURPLE}✓{C.RESET} {BONUS_HONESTY['name']}")
    est = total_budget(skills_done, include_bonus)
    mm, ss = divmod(est, 60)
    dur_color = C.GREEN if 180 <= est <= 300 else C.YELLOW
    print(f"\n  Estimasi durasi  : {dur_color}{mm}m {ss:02d}s{C.RESET} "
          f"(target 3-5 menit / 180-300 detik)")
    print(f"\n{C.DIM}Checklist submission:{C.RESET}")
    checks = [
        "Screen recording nunjukin cortex jalan langsung (bukan mock/slide)",
        "Ada minimal 1 workflow end-to-end yang beneran jalan (input->output nyata)",
        "2-3 skill/capability kelihatan beda satu sama lain",
        "Durasi 3-5 menit",
    ]
    for c in checks:
        print(f"  {C.GREEN}☐{C.RESET} {c}")
    print()
    rule("═", C.SKY)


def main_menu():
    while True:
        banner()
        print(f"{C.BOLD}Pilih mode:{C.RESET}\n")
        print(f"  {C.SKY}[1]{C.RESET} Full demo sequence (3 skill + bonus honesty beat) — direkomendasikan")
        print(f"  {C.SKY}[2]{C.RESET} Latihan satu skill saja")
        print(f"  {C.SKY}[3]{C.RESET} Lihat semua prompt (tanpa timer, buat nyontek cepat)")
        print(f"  {C.SKY}[0]{C.RESET} Keluar\n")
        try:
            choice = input(f"{C.BOLD}> {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "1":
            done = []
            for i, skill in enumerate(SKILLS):
                show_skill(skill, i, len(SKILLS))
                done.append(skill)
            show_bonus()
            summary(done, include_bonus=True)
            wait_enter("ENTER untuk kembali ke menu")

        elif choice == "2":
            banner()
            for s in SKILLS:
                print(f"  {C.SKY}[{s['id']}]{C.RESET} {s['name']}")
            try:
                pick = input(f"\n{C.BOLD}Pilih skill (1-3): {C.RESET}").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            matches = [s for s in SKILLS if str(s["id"]) == pick]
            if matches:
                show_skill(matches[0], 0, 1)
                summary(matches, include_bonus=False)
                wait_enter("ENTER untuk kembali ke menu")

        elif choice == "3":
            banner()
            for s in SKILLS:
                print(f"{C.BOLD}{s['name']}{C.RESET}")
                print(f'  {C.WHITE}"{s["input"]}"{C.RESET}\n')
            print(f"{C.BOLD}{BONUS_HONESTY['name']}{C.RESET}")
            print(f'  {C.WHITE}"{BONUS_HONESTY["input"]}"{C.RESET}')
            wait_enter("ENTER untuk kembali ke menu")

        elif choice == "0":
            clear()
            print(f"{C.SKY}Selamat merekam. Semoga lolos! {C.RESET}")
            break


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
        sys.exit(0)
