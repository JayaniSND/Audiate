import subprocess
import threading
import os

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SWIFT_SRC     = os.path.join(BASE_DIR, "haptic_player.swift")
HAPTIC_BINARY = os.path.join(BASE_DIR, "haptic_player")

def compile_haptic_binary():
    if os.path.exists(HAPTIC_BINARY):
        return True
    print("Compiling haptic binary...")
    result = subprocess.run(
        ["swiftc", SWIFT_SRC, "-o", HAPTIC_BINARY],
        capture_output=True
    )
    if result.returncode != 0:
        print("Compile failed:", result.stderr.decode())
        return False
    print("Haptic binary ready.")
    return True

# 7 bands — maps the full MIDI range to distinct vibration speeds
# Boundary notes chosen to match natural musical registers
HAPTIC_BANDS = [
    (43,  "very_low"),   # below G2  — contrabass
    (50,  "low"),        # G2–D3     — bass
    (57,  "mid_low"),    # D3–A3     — cello/baritone
    (64,  "mid"),        # A3–E4     — viola/tenor (middle of human voice)
    (71,  "mid_high"),   # E4–B4     — violin/soprano
    (79,  "high"),       # B4–G5     — high violin/flute
    (999, "very_high"),  # above G5  — piccolo/whistle register
]

def map_note_to_mode(midi):
    if midi is None:
        return None
    for threshold, mode in HAPTIC_BANDS:
        if midi < threshold:
            return mode
    return "very_high"

def trigger_haptic_for_note(midi, duration):
    mode = map_note_to_mode(midi)
    if mode is None:
        return

    def _fire():
        subprocess.run(
            [HAPTIC_BINARY, mode, f"{duration:.3f}"],
            capture_output=True
        )
    threading.Thread(target=_fire, daemon=True).start()