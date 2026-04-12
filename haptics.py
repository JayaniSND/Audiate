import subprocess
import threading
import os

# Paths relative to this file
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SWIFT_SRC     = os.path.join(BASE_DIR, "haptic_player.swift")
HAPTIC_BINARY = os.path.join(BASE_DIR, "haptic_player")        # compiled output

def compile_haptic_binary():
    """Compile the Swift binary. Skips if already compiled."""
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

def map_note_to_haptic(midi, duration):
    """Map MIDI pitch + duration → (pattern, pulse_count, interval)"""
    if midi is None:
        return None, 0, 0.0

    if midi < 48:
        pattern = "levelChange"   # low/heavy
    elif midi > 72:
        pattern = "alignment"     # high/light
    else:
        pattern = "generic"       # mid

    count    = min(max(1, int(duration / 0.15)), 8)
    interval = (duration / count) if count > 1 else 0.0

    return pattern, count, interval

def trigger_haptic_for_note(midi, duration):
    """Fire haptic async — won't block the main playback loop."""
    pattern, count, interval = map_note_to_haptic(midi, duration)
    if count == 0:
        return

    def _fire():
        subprocess.run(
            [HAPTIC_BINARY, pattern, str(count), f"{interval:.3f}"],
            capture_output=True
        )
    threading.Thread(target=_fire, daemon=True).start()