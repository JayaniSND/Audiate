# Audiate

Hum or sing into your mic — Audiate extracts the notes and plays them back as a synchronized visual and haptic experience.

## How it works

1. **Input** — upload an audio file or record directly in the browser
2. **Extract** — CREPE (pitch tracking) + librosa (onset detection) identify each note, its frequency, timing, and duration
3. **Visualize** — a scrolling piano roll animates in sync with playback, with a live waveform and spectrum analyzer
4. **Haptics** — each note triggers a vibration via `navigator.vibrate()` (works on Android Chrome / mobile browsers)

## Requirements

- Python 3.10+
- `ffmpeg` installed on your system (for non-WAV audio conversion)

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## Setup

```bash
cd Audiate

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install flask
```

> If the venv already exists (e.g. cloned repo), just run `source venv/bin/activate`.

## Run

```bash
./venv/bin/python app.py
```

Then open **http://localhost:5001** in your browser.

## Usage

| Action | How |
|---|---|
| Upload a file | Click **Upload File** or drag-and-drop onto the canvas |
| Record audio | Click **⏺ Record**, sing/hum, click **⏹ Stop** |
| Play | Click **Play** after processing completes |
| Seek | Click anywhere on the progress bar |
| Stop server | `pkill -f app.py` or `lsof -ti:5001 \| xargs kill -9` |

## Project structure

```
Audiate/
├── app.py              # Flask backend — handles upload, conversion, extraction
├── extract_notes.py    # CREPE + librosa note extraction pipeline
├── play_notes.py       # CLI playback with haptics (macOS, uses haptic_player)
├── haptics.py          # Haptic band mapping + subprocess driver
├── haptic_player.swift # macOS NSHapticFeedbackManager binary source
├── static/
│   └── index.html      # Single-page frontend (upload, record, visualize)
├── requirements.txt
└── uploads/            # Created at runtime — processed audio + JSON stored here
```

## Note extraction pipeline (`extract_notes.py`)

```
Audio file
  └─► librosa / soundfile  (load + normalize to 16 kHz mono)
        └─► CREPE           (per-frame Hz + confidence at 100 fps)
              └─► librosa onset detection  (segment into note boundaries)
                    └─► per segment: median Hz → MIDI → note name
                          └─► JSON  { meta: {bpm, …}, notes: […] }
```

Output JSON shape:

```json
{
  "meta": { "bpm": 120.0, "total_duration": 4.2, "note_count": 8, "rest_count": 2 },
  "notes": [
    { "note_name": "A4", "midi": 69, "hz": 440.0,
      "start_time": 0.12, "duration": 0.48, "confidence": 0.91, "is_rest": false }
  ]
}
```

## CLI-only usage (no browser)

Extract notes from a WAV file:

```bash
./venv/bin/python extract_notes.py input.wav output.json
```

Play back with haptics (macOS only — requires compiled `haptic_player` binary):

```bash
./venv/bin/python play_notes.py output.json
```
