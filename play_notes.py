import json
import time
import sys
from haptics import compile_haptic_binary, trigger_haptic_for_note

def play(json_path):
    if not compile_haptic_binary():
        print("Warning: haptics unavailable, continuing without.")

    with open(json_path) as f:
        data = json.load(f)

    meta  = data["meta"]
    notes = data["notes"]
    print(f"BPM: {meta['bpm']} | Notes: {meta['note_count']} | Duration: {meta['total_duration']}s")

    total_duration = meta["total_duration"]
    start_clock = time.perf_counter()

    for i, note in enumerate(notes):
        # How long until the NEXT note starts (or the file ends)
        if i + 1 < len(notes):
            next_start = notes[i + 1]["start_time"]
        else:
            next_start = total_duration

        slot_duration = next_start - note["start_time"]

        # Trim haptic to 90% of the slot so it never bleeds into next note
        haptic_duration = slot_duration * 0.90

        if not note["is_rest"]:
            trigger_haptic_for_note(note["midi"], haptic_duration)

        # Sleep until the exact moment the next note should start
        target_time = start_clock + next_start
        sleep_for = target_time - time.perf_counter()
        if sleep_for > 0:
            time.sleep(sleep_for)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_notes.py output.json")
        sys.exit(1)
    play(sys.argv[1])