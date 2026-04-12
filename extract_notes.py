"""
Hum → Note extraction pipeline
================================
Dependencies:
    pip install crepe librosa numpy scipy soundfile

Usage:
    python extract_notes.py input.wav output.json

Pipeline:
    1. Load audio
    2. CREPE  → time-series of Hz values at ~100fps
    3. Librosa onset detection → chop Hz series into discrete note segments
    4. Per segment: median Hz → MIDI → note name
    5. Write (note_name, midi, start_time, duration, confidence) to JSON
"""

import sys
import json
import numpy as np
import librosa
import crepe
import soundfile as sf


# ─── CONFIG ──────────────────────────────────────────────────────────────────

CREPE_MODEL_CAPACITY = "medium"   # tiny | small | medium | large | full
CREPE_STEP_SIZE      = 10         # ms between pitch frames → 100fps at 10ms
MIN_CONFIDENCE       = 0.5        # CREPE confidence threshold to trust a frame
MIN_NOTE_DURATION    = 0.05       # seconds — drop anything shorter (noise)
MIN_NOTE_HZ          = 80         # ignore pitches below ~E2 (hum floor)
MAX_NOTE_HZ          = 1200       # ignore pitches above ~D6 (hum ceiling)

# Librosa onset detection tuning
ONSET_BACKTRACK      = True       # snap onsets back to nearest low-energy dip
ONSET_DELTA          = 0.07       # sensitivity (higher = fewer onsets detected)

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def hz_to_midi(hz: float) -> int:
    """Convert Hz to nearest MIDI note number."""
    return int(round(69 + 12 * np.log2(hz / 440.0)))


def midi_to_name(midi: int) -> str:
    """E.g. 69 → 'A4', 60 → 'C4'."""
    octave = (midi // 12) - 1
    name   = NOTE_NAMES[midi % 12]
    return f"{name}{octave}"


def midi_to_hz(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12.0))


# ─── STAGE 1: Load audio ─────────────────────────────────────────────────────

def load_audio(path: str):
    """
    Load any audio file, resample to 16 kHz mono.
    CREPE expects 16 kHz; librosa works fine at any SR but we keep it consistent.
    """
    audio, sr = sf.read(path, always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)           # stereo → mono
    if sr != 16000:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        sr = 16000
    # Normalise amplitude
    audio = audio / (np.max(np.abs(audio)) + 1e-9)
    return audio.astype(np.float32), sr


# ─── STAGE 2: CREPE pitch tracking ───────────────────────────────────────────

def run_crepe(audio: np.ndarray, sr: int):
    """
    Returns:
        times      : np.ndarray  shape (N,)  — time in seconds for each frame
        frequencies: np.ndarray  shape (N,)  — Hz, 0.0 if unvoiced
        confidences: np.ndarray  shape (N,)  — 0–1 CREPE confidence
    """
    times, frequencies, confidences, _ = crepe.predict(
        audio,
        sr,
        model_capacity=CREPE_MODEL_CAPACITY,
        step_size=CREPE_STEP_SIZE,      # ms
        viterbi=True,                   # Viterbi decoding → smoother pitch curve
        verbose=0
    )

    # Zero out low-confidence frames so they don't pollute note segments
    frequencies[confidences < MIN_CONFIDENCE] = 0.0

    return times, frequencies, confidences


# ─── STAGE 3: Librosa onset detection ────────────────────────────────────────

def get_onsets(audio: np.ndarray, sr: int) -> np.ndarray:
    """
    Returns onset times in seconds using librosa's spectral-flux onset detector.
    ONSET_BACKTRACK shifts each onset back to the nearest energy dip so the
    onset aligns with the note attack rather than slightly after.
    """
    # Compute onset envelope
    onset_env = librosa.onset.onset_strength(
        y=audio,
        sr=sr,
        aggregate=np.median,   # more robust than mean for humming
    )

    # Pick onset frames
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env,
        sr=sr,
        backtrack=ONSET_BACKTRACK,
        delta=ONSET_DELTA,
        units='frames'
    )

    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # Estimate BPM from onset spacing
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])

    return onset_times, bpm


# ─── STAGE 4: Combine CREPE + onsets → note list ────────────────────────────

def build_note_list(times, frequencies, confidences, onset_times, total_duration):
    """
    Slice the CREPE pitch series at each onset boundary.
    For each segment: take the median Hz of voiced frames → MIDI → note name.
    Returns a list of dicts.
    """
    # Add a sentinel at the end
    boundaries = np.append(onset_times, total_duration)

    notes = []
    for i in range(len(boundaries) - 1):
        t_start = boundaries[i]
        t_end   = boundaries[i + 1]
        dur     = t_end - t_start

        if dur < MIN_NOTE_DURATION:
            continue

        # Grab CREPE frames that fall inside this segment
        mask = (times >= t_start) & (times < t_end)
        seg_hz   = frequencies[mask]
        seg_conf = confidences[mask]

        # Only keep voiced, in-range frames
        voiced = seg_hz[(seg_hz >= MIN_NOTE_HZ) & (seg_hz <= MAX_NOTE_HZ)]

        if len(voiced) == 0:
            # Segment has no clear pitch → rest
            notes.append({
                "note_name":   "rest",
                "midi":        None,
                "hz":          None,
                "start_time":  round(float(t_start), 4),
                "duration":    round(float(dur), 4),
                "confidence":  0.0,
                "is_rest":     True
            })
            continue

        median_hz   = float(np.median(voiced))
        midi        = hz_to_midi(median_hz)
        note_name   = midi_to_name(midi)
        # mean_conf   = float(np.mean(seg_conf[mask & (frequencies >= MIN_NOTE_HZ)]))
        valid_mask = (seg_hz >= MIN_NOTE_HZ) & (seg_hz <= MAX_NOTE_HZ)
        mean_conf  = float(np.mean(seg_conf[valid_mask]))

        notes.append({
            "note_name":   note_name,
            "midi":        midi,
            "hz":          round(median_hz, 2),
            "start_time":  round(float(t_start), 4),
            "duration":    round(float(dur), 4),
            "confidence":  round(mean_conf, 3),
            "is_rest":     False
        })

    return notes


# ─── STAGE 5: Write JSON ──────────────────────────────────────────────────────

def write_json(notes, bpm, output_path, audio_duration):
    payload = {
        "meta": {
            "bpm":            round(bpm, 1),
            "total_duration": round(audio_duration, 4),
            "note_count":     len([n for n in notes if not n["is_rest"]]),
            "rest_count":     len([n for n in notes if n["is_rest"]]),
            "pipeline":       "CREPE + librosa",
        },
        "notes": notes
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {len(notes)} events → {output_path}")
    print(f"  BPM: {bpm:.1f}  |  notes: {payload['meta']['note_count']}  |  rests: {payload['meta']['rest_count']}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def extract(audio_path: str, output_path: str):
    print(f"Loading: {audio_path}")
    audio, sr = load_audio(audio_path)
    duration  = len(audio) / sr
    print(f"  Duration: {duration:.2f}s  SR: {sr} Hz")

    print("Running CREPE pitch tracking…")
    times, frequencies, confidences = run_crepe(audio, sr)
    voiced_pct = 100 * np.mean(frequencies > 0)
    print(f"  Voiced frames: {voiced_pct:.1f}%")

    print("Running librosa onset detection…")
    onset_times, bpm = get_onsets(audio, sr)
    print(f"  Onsets found: {len(onset_times)}  |  BPM: {bpm:.1f}")

    print("Building note list…")
    notes = build_note_list(times, frequencies, confidences, onset_times, duration)

    write_json(notes, bpm, output_path, duration)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_notes.py <input.wav> <output.json>")
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2])