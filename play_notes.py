import json
import time
import sys
import subprocess
from haptics import compile_haptic_binary, trigger_haptic_for_note, kill_haptic

BOUNDARY_GAP = 0.045  # seconds of silence between notes — tweak this to taste

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

    LEGATO_SEMITONES = 3   # interval ≤ this → skip attack (smooth hum transition)

    prev_midi = None
    for i, note in enumerate(notes):
        if i + 1 < len(notes):
            next_start = notes[i + 1]["start_time"]
        else:
            next_start = total_duration

        slot_duration = next_start - note["start_time"]

        # Haptic gets the slot minus the boundary gap on each side
        haptic_duration = max(0.05, slot_duration - BOUNDARY_GAP)

        if not note["is_rest"]:
            midi = note["midi"]
            legato = (
                prev_midi is not None
                and midi is not None
                and abs(midi - prev_midi) <= LEGATO_SEMITONES
            )
            trigger_haptic_for_note(midi, haptic_duration, legato=legato)
            prev_midi = midi
        else:
            prev_midi = None  # rest breaks the legato chain

        # Sleep until (next_note_start - BOUNDARY_GAP) — enforces silence gap
        target_time = start_clock + next_start - BOUNDARY_GAP
        sleep_for = target_time - time.perf_counter()
        if sleep_for > 0:
            time.sleep(sleep_for)

        # Kill any still-running haptic, then wait out the gap
        kill_haptic()
        gap_end = start_clock + next_start
        gap_remaining = gap_end - time.perf_counter()
        if gap_remaining > 0:
            time.sleep(gap_remaining)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_notes.py output.json")
        sys.exit(1)
    play(sys.argv[1])