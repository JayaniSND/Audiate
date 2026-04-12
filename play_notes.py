import json
import time
import sys
from haptics import compile_haptic_binary, trigger_haptic_for_note

def play(json_path):
    if not compile_haptic_binary():
        print("Warning: haptics unavailable, continuing without.")

    with open(json_path) as f:
        data = json.load(f)

    notes = data["notes"]
    print(f"Playing {len(notes)} notes...")

    print(f"Playing {len(notes)} notes...")
    for note in notes:
        if not note["is_rest"]:
            trigger_haptic_for_note(note["midi"], note["duration"])
            # animation call will go here later

        time.sleep(note["duration"])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_notes.py output.json")
        sys.exit(1)
    play(sys.argv[1])