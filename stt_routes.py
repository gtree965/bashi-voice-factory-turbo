import os
import uuid
import json
import time
import threading
import urllib.parse
from pathlib import Path
from flask import Blueprint, request, jsonify, Response, stream_with_context, send_file
from werkzeug.utils import secure_filename

from model_manager import ModelManager
from engines.sherpa_sensevoice import SherpaSenseVoiceEngine
from engines.sherpa_parakeet import SherpaParakeetEngine
from utils import extract_audio_wav

stt_bp = Blueprint("stt", __name__, url_prefix="/api/stt")

# Ensure directories exist
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

model_manager = ModelManager(MODELS_DIR)

# Global state
stt_jobs = {}
engine_instance = None
current_engine_model_id = None
engine_lock = threading.Lock()

# Job cleanup: auto-expire jobs older than 24 hours
JOB_MAX_AGE_SEC = 24 * 60 * 60

def cleanup_expired_jobs():
    """Remove jobs older than JOB_MAX_AGE_SEC from memory."""
    now = time.time()
    expired = [jid for jid, job in stt_jobs.items()
               if now - job.get("created_at", now) > JOB_MAX_AGE_SEC]
    for jid in expired:
        del stt_jobs[jid]
    if expired:
        print(f"[STT] Cleaned up {len(expired)} expired job(s)")

def _cleanup_timer():
    """Run cleanup every hour in a background thread."""
    while True:
        time.sleep(3600)
        try:
            cleanup_expired_jobs()
        except Exception:
            pass

_cleanup_thread = threading.Thread(target=_cleanup_timer, daemon=True)
_cleanup_thread.start()

def get_engine(model_id=None):
    global engine_instance, current_engine_model_id
    with engine_lock:
        if engine_instance is not None and current_engine_model_id != model_id:
            # Swap models: unload current to free up RAM
            print(f"[STT] Swapping active model from {current_engine_model_id} to {model_id}")
            try:
                engine_instance.cleanup()
            except Exception:
                pass
            engine_instance = None
            current_engine_model_id = None

        if engine_instance is None:
            # If no model requested, use default
            if not model_id:
                for m in model_manager.list_installed():
                    if m.get("is_default"):
                        model_id = m["id"]
                        break
                if not model_id:
                    # Still fallback to first installed
                    installed = model_manager.list_installed()
                    if installed:
                        model_id = installed[0]["id"]
            
            if not model_id:
                return None  # No models installed

            model_dir = model_manager.get_model_dir(model_id)
            if not model_dir:
                return None

            # Instantiate correct engine based on registry meta
            meta = next((m for m in model_manager.list_installed() if m["id"] == model_id), None)
            if not meta:
                return None
                
            model_name_lower = meta.get("name", "").lower()

            if "parakeet" in model_name_lower:
                engine_instance = SherpaParakeetEngine(model_dir)
            else:
                engine_instance = SherpaSenseVoiceEngine(model_dir)
                
            try:
                engine_instance.load_model()
                current_engine_model_id = model_id
            except Exception as e:
                engine_instance = None
                current_engine_model_id = None
                print(f"Failed to load engine for {model_id}: {e}")
                
    return engine_instance

@stt_bp.route("/models", methods=["GET"])
def list_models():
    return jsonify({
        "installed": model_manager.list_installed(),
        "available": model_manager.list_available()
    })

@stt_bp.route("/download-model", methods=["POST"])
def download_model():
    data = request.json or {}
    model_id = data.get("model_id")
    use_mirror = data.get("use_mirror", True)
    
    if not model_id:
        return jsonify({"error": "model_id required"}), 400

    def generate():
        try:
            for event in model_manager.download_model(model_id, use_mirror=use_mirror):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), content_type='text/event-stream')

def _process_transcription(job_id: str, file_path: Path, filename: str, language: str, model_id: str):
    """Background thread to process audio extraction and transcription."""
    stt_jobs[job_id]["status"] = "extracting_audio"
    wav_path = UPLOAD_DIR / f"{job_id}.wav"
    
    try:
        # Step 1: Extract Audio
        extract_audio_wav(file_path, wav_path)
        
        # Step 2: Ensure Engine is ready
        stt_jobs[job_id]["status"] = "loading_model"
        engine = get_engine(model_id)
        if not engine:
            raise RuntimeError("Engine could not be loaded. Please ensure models are installed.")
            
        # Step 3: Transcribe
        stt_jobs[job_id]["status"] = "transcribing"
        for segment in engine.transcribe_stream(wav_path, language=language):
            seg_dict = {
                "index": segment.index,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            }
            stt_jobs[job_id]["segments"].append(seg_dict)
            
        # Step 4: Done
        stt_jobs[job_id]["status"] = "done"
        
    except Exception as e:
        stt_jobs[job_id]["status"] = "error"
        stt_jobs[job_id]["error"] = str(e)
    finally:
        # Cleanup temp uploaded file (original media) and extracted WAV
        if file_path.exists():
            file_path.unlink()
        if wav_path.exists():
            wav_path.unlink(missing_ok=True)

@stt_bp.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
        
    language = request.form.get("language", "auto")
    model_id = request.form.get("model_id")
    
    job_id = uuid.uuid4().hex
    safe_filename = secure_filename(file.filename) or f"upload_{job_id}.bin"
    file_path = UPLOAD_DIR / f"{job_id}_{safe_filename}"
    file.save(str(file_path))
    
    stt_jobs[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "status": "pending",
        "segments": [],
        "error": None,
        "created_at": time.time()
    }
    
    # Start background processing
    thread = threading.Thread(
        target=_process_transcription,
        args=(job_id, file_path, file.filename, language, model_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "job_id": job_id})

@stt_bp.route("/progress/<job_id>", methods=["GET"])
def get_progress_sse(job_id):
    def generate():
        last_index = 0
        while True:
            job = stt_jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'status': 'error', 'error': 'job not found'})}\n\n"
                break
                
            status = job["status"]
            segments = job["segments"]
            
            # Send new segments only
            new_segments = segments[last_index:]
            if new_segments or status in ["error", "done", "extracting_audio", "loading_model"]:
                event_data = {
                    "status": status,
                    "new_segments": new_segments
                }
                if job.get("error"):
                    event_data["error"] = job["error"]
                    
                yield f"data: {json.dumps(event_data)}\n\n"
                last_index = len(segments)
                
            if status in ["done", "error"]:
                break

            time.sleep(0.5)

    return Response(stream_with_context(generate()), content_type='text/event-stream')

@stt_bp.route("/result/<job_id>", methods=["GET"])
def get_result(job_id):
    job = stt_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

def format_timestamp(seconds: float, separator: str = ",") -> str:
    """Format seconds into HH:MM:SS,mmm or HH:MM:SS.mmm"""
    ms = int((seconds % 1) * 1000)
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}{separator}{ms:03d}"


def fix_timestamp_overlaps(segments: list) -> list:
    """
    Post-process segments to ensure no timestamp overlaps.
    If seg[i].end > seg[i+1].start, snap seg[i].end = seg[i+1].start.
    Also re-index segments sequentially.
    """
    if not segments:
        return segments

    fixed = []
    for i, seg in enumerate(segments):
        new_seg = dict(seg)
        if i + 1 < len(segments):
            next_start = segments[i + 1]["start"]
            if new_seg["end"] > next_start:
                new_seg["end"] = next_start
        # Ensure end > start (minimum 10ms gap)
        if new_seg["end"] <= new_seg["start"]:
            new_seg["end"] = new_seg["start"] + 0.01
        new_seg["index"] = i
        fixed.append(new_seg)

    return fixed


@stt_bp.route("/export/<job_id>", methods=["GET"])
def export_result(job_id):
    format_type = request.args.get("format", "txt")
    ui_lang = request.args.get("lang", "en")
    job = stt_jobs.get(job_id)

    if not job or job["status"] != "done":
        return jsonify({"error": "Job not found or not finished"}), 404

    segments = fix_timestamp_overlaps(job["segments"])
    filename_base = Path(job["filename"]).stem
    suffix = "转写" if ui_lang == "zh" else "transcription"

    if format_type == "txt":
        content = "\n".join(seg["text"] for seg in segments)
        mimetype = "text/plain"
        ext = "txt"
    elif format_type == "srt":
        lines = []
        for i, seg in enumerate(segments, 1):
            start = format_timestamp(seg["start"], ",")
            end = format_timestamp(seg["end"], ",")
            lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
        content = "\n".join(lines)
        mimetype = "application/x-subrip"
        ext = "srt"
    elif format_type == "vtt":
        lines = ["WEBVTT\n"]
        for seg in segments:
            start = format_timestamp(seg["start"], ".")
            end = format_timestamp(seg["end"], ".")
            lines.append(f"{start} --> {end}\n{seg['text']}\n")
        content = "\n".join(lines)
        mimetype = "text/vtt"
        ext = "vtt"
    else:
        return jsonify({"error": "Unsupported format"}), 400

    export_filename = f"{filename_base}_{suffix}.{ext}"
    response = Response(content, mimetype=mimetype)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{urllib.parse.quote(export_filename)}"
    response.headers["Content-Type"] = f"{mimetype}; charset=utf-8"
    return response

