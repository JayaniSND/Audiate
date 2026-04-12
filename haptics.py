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

HAPTIC_BANDS = [
    (43,  "very_low"),
    (50,  "low"),
    (57,  "mid_low"),
    (64,  "mid"),
    (71,  "mid_high"),
    (79,  "high"),
    (999, "very_high"),
]

def map_note_to_mode(midi):
    if midi is None:
        return None
    for threshold, mode in HAPTIC_BANDS:
        if midi < threshold:
            return mode
    return "very_high"

def trigger_haptic_for_note(midi, duration):
    global _current_process
    mode = map_note_to_mode(midi)
    if mode is None:
        return

    def _fire():
        global _current_process
        proc = subprocess.Popen(
            [HAPTIC_BINARY, mode, f"{duration:.3f}"],
        )
        with _process_lock:
            _current_process = proc
        proc.wait()

    threading.Thread(target=_fire, daemon=True).start()