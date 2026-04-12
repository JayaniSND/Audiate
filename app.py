"""
Audiate — Flask backend
========================
Accepts audio uploads or recorded blobs, extracts notes, serves static frontend.

Endpoints:
  POST /api/process        — multipart form { audio: <file> }
                             Returns { id, notes: {...}, audio_url }
  GET  /api/audio/<id>     — stream the processed WAV
  GET  /                   — serve frontend
"""

import os, uuid, json, subprocess, sys, re
from flask import Flask, request, jsonify, send_file, abort
from haptics import trigger_haptic_for_note, kill_haptic, compile_haptic_binary

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR     = os.path.join(BASE_DIR, "uploads")
VENV_PYTHON    = os.path.join(BASE_DIR, "venv", "bin", "python")
EXTRACT_SCRIPT = os.path.join(BASE_DIR, "extract_notes.py")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe_id(uid: str) -> str:
    """Strip anything that isn't a hex UUID char so we can use it in paths."""
    return re.sub(r"[^a-f0-9\-]", "", uid)


def _convert_to_wav(src_path: str, dst_path: str) -> bool:
    """
    Convert any audio format to 16 kHz mono WAV using librosa + soundfile.
    Falls back to ffmpeg if librosa fails (handles edge cases like webm/opus).
    """
    try:
        import librosa, soundfile as sf
        audio, sr = librosa.load(src_path, sr=16000, mono=True)
        sf.write(dst_path, audio, 16000)
        return True
    except Exception as e:
        print(f"librosa conversion failed ({e}), trying ffmpeg…")

    result = subprocess.run(
        ["ffmpeg", "-y", "-i", src_path,
         "-ar", "16000", "-ac", "1", "-f", "wav", dst_path],
        capture_output=True
    )
    return result.returncode == 0


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "static", "index.html"))


@app.route("/api/process", methods=["POST"])
def process():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file in request"}), 400

    audio_file = request.files["audio"]
    uid        = str(uuid.uuid4())

    original_ext = os.path.splitext(audio_file.filename or "audio.webm")[1] or ".webm"
    raw_path  = os.path.join(UPLOAD_DIR, f"{uid}_raw{original_ext}")
    wav_path  = os.path.join(UPLOAD_DIR, f"{uid}.wav")
    json_path = os.path.join(UPLOAD_DIR, f"{uid}.json")

    audio_file.save(raw_path)

    if raw_path != wav_path:
        if not _convert_to_wav(raw_path, wav_path):
            return jsonify({"error": "Audio conversion failed. Is ffmpeg installed?"}), 500

    result = subprocess.run(
        [VENV_PYTHON, EXTRACT_SCRIPT, wav_path, json_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("extract_notes stderr:", result.stderr)
        return jsonify({"error": "Note extraction failed", "detail": result.stderr}), 500

    with open(json_path) as f:
        notes_data = json.load(f)

    return jsonify({
        "id":        uid,
        "notes":     notes_data,
        "audio_url": f"/api/audio/{uid}",
    })


@app.route("/api/audio/<uid>")
def serve_audio(uid):
    uid  = _safe_id(uid)
    path = os.path.join(UPLOAD_DIR, f"{uid}.wav")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="audio/wav")


@app.route("/api/haptic", methods=["POST"])
def haptic():
    data     = request.get_json(silent=True) or {}
    midi     = data.get("midi")
    duration = float(data.get("duration", 0.3))
    legato   = bool(data.get("legato", False))
    if midi is None:
        return jsonify({"error": "missing midi"}), 400
    trigger_haptic_for_note(int(midi), duration, legato=legato)
    return jsonify({"ok": True})


@app.route("/api/haptic/stop", methods=["POST"])
def haptic_stop():
    kill_haptic()
    return jsonify({"ok": True})


if __name__ == "__main__":
    compile_haptic_binary()
    port = int(os.environ.get("PORT", 5000))
    print(f"Audiate running → http://localhost:{port}")
    app.run(debug=True, host="0.0.0.0", port=port)


