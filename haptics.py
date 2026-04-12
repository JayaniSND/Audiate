import subprocess
import threading
import os

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SWIFT_SRC     = os.path.join(BASE_DIR, "haptic_player.swift")
HAPTIC_BINARY = os.path.join(BASE_DIR, "haptic_player")

# Track the current haptic process so we can kill it
_current_process = None
_process_lock    = threading.Lock()

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

def kill_haptic():
    """Immediately terminate any running haptic process."""
    global _current_process
    with _process_lock:
        if _current_process and _current_process.poll() is None:
            _current_process.terminate()
            _current_process = None

# 7 bands tuned to the human humming range (~C3–C5, MIDI 50–72).
# Each band covers ~4 semitones so every small pitch shift feels different,
# instead of the old orchestral mapping where most hums fell into 2–3 bands.
HAPTIC_BANDS = [
    (50,  "very_low"),   # below D3   — very deep hum
    (55,  "low"),        # D3–G3      — low hum
    (60,  "mid_low"),    # G3–C4      — low-mid hum
    (64,  "mid"),        # C4–E4      — mid hum (most common)
    (68,  "mid_high"),   # E4–Ab4     — upper-mid hum
    (72,  "high"),       # Ab4–C5     — high hum
    (999, "very_high"),  # above C5   — falsetto/very high
]

def map_note_to_mode(midi):
    if midi is None:
        return None
    for threshold, mode in HAPTIC_BANDS:
        if midi < threshold:
            return mode
    return "very_high"

def trigger_haptic_for_note(midi, duration, legato=False):
    """legato=True skips the attack phase for smooth note transitions."""
    global _current_process
    mode = map_note_to_mode(midi)
    if mode is None:
        return

    def _fire():
        global _current_process
        proc = subprocess.Popen(
            [HAPTIC_BINARY, mode, f"{duration:.3f}", "1" if legato else "0"],
        )
        with _process_lock:
            _current_process = proc
        proc.wait()

    threading.Thread(target=_fire, daemon=True).start()