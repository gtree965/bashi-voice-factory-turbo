import os
import uuid
import json
import time
import threading
import urllib.parse
import re
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
_engine_ref_count = 0  # tracks active transcriptions using the engine
_job_active = False    # set at request admission, cleared when worker finishes

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

def acquire_engine(model_id=None):
    """Get engine for the given model and increment its ref count.

    The caller MUST call release_engine() when done to allow future
    model swaps.  Only one transcription job may run at a time because
    sherpa_onnx's OfflineRecognizer is not guaranteed thread-safe for
    concurrent decode_stream() calls on a shared instance.
    """
    global engine_instance, current_engine_model_id, _engine_ref_count
    with engine_lock:
        if _engine_ref_count > 0:
            raise RuntimeError(
                "A transcription is already in progress. "
                "Please wait for it to finish before starting another."
            )

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
                return None

        _engine_ref_count += 1
        return engine_instance


def release_engine():
    """Decrement the engine ref count, allowing future model swaps."""
    global _engine_ref_count
    with engine_lock:
        _engine_ref_count = max(0, _engine_ref_count - 1)

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
        
        # Step 2: Ensure Engine is ready (also increments ref count)
        stt_jobs[job_id]["status"] = "loading_model"
        engine = acquire_engine(model_id)
        if not engine:
            raise RuntimeError("Engine could not be loaded. Please ensure models are installed.")

        # Step 3: Transcribe
        try:
            stt_jobs[job_id]["status"] = "transcribing"
            for segment in engine.transcribe_stream(wav_path, language=language):
                seg_dict = {
                    "index": segment.index,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                }
                stt_jobs[job_id]["segments"].append(seg_dict)
        finally:
            release_engine()

        # Step 4: Done
        stt_jobs[job_id]["status"] = "done"
        
    except Exception as e:
        stt_jobs[job_id]["status"] = "error"
        stt_jobs[job_id]["error"] = str(e)
    finally:
        # Release the job slot so the next transcription can be accepted
        global _job_active
        with engine_lock:
            _job_active = False
        # Cleanup temp uploaded file (original media) and extracted WAV
        if file_path.exists():
            file_path.unlink()
        if wav_path.exists():
            wav_path.unlink(missing_ok=True)

@stt_bp.route("/transcribe", methods=["POST"])
def transcribe():
    global _job_active

    # Reserve the slot atomically — reject before saving file to disk
    with engine_lock:
        if _job_active:
            return jsonify({"error": "A transcription is already in progress. "
                            "Please wait for it to finish."}), 429
        _job_active = True

    worker_started = False
    job_id = None
    file_path = None

    try:
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
            "model_id": model_id,
            "status": "pending",
            "segments": [],
            "error": None,
            "created_at": time.time(),
        }

        # Start background processing (_job_active is cleared in the worker's finally)
        thread = threading.Thread(
            target=_process_transcription,
            args=(job_id, file_path, file.filename, language, model_id),
            daemon=True,
        )
        thread.start()
        worker_started = True

        return jsonify({"success": True, "job_id": job_id})

    finally:
        if not worker_started:
            with engine_lock:
                _job_active = False
            if job_id is not None:
                stt_jobs.pop(job_id, None)
            if file_path is not None and file_path.exists():
                file_path.unlink(missing_ok=True)

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


def _is_cjk(text: str) -> bool:
    """Check if text is predominantly CJK (Chinese/Japanese/Korean)."""
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff' or '\u3040' <= ch <= '\u30ff' or '\uac00' <= ch <= '\ud7af':
            return True
    return False


def _smooth_join(buf_text: str, seg_text: str) -> str:
    """Join two subtitle texts, smoothing punctuation at the boundary.

    English: "What keeps us?" + "healthy and happy" -> "What keeps us healthy and happy"
    Chinese: "军事力量" + "。" -> "军事力量。"  (no space, CJK join)
    """
    if not buf_text or not seg_text:
        return (buf_text or "") + (seg_text or "")

    buf_stripped = buf_text.rstrip()
    cjk = _is_cjk(buf_stripped) or _is_cjk(seg_text)

    # CJK: join without space, no punctuation smoothing needed
    # (Chinese punctuation like 。，is usually correct from the model)
    if cjk:
        return buf_stripped + seg_text

    # English: smooth false sentence breaks from VAD splits
    first_alpha = next((c for c in seg_text if c.isalpha()), "")

    if buf_stripped and buf_stripped[-1] in ".!?":
        starts_lower = first_alpha.islower()
        ends_question = buf_stripped[-1] == "?"

        if starts_lower or ends_question:
            # Remove false sentence-ending punctuation, lowercase continuation
            buf_clean = buf_stripped[:-1].rstrip()
            seg_clean = seg_text[0].lower() + seg_text[1:] if seg_text[0].isupper() else seg_text
            return buf_clean + " " + seg_clean

    return buf_text + " " + seg_text


def merge_short_segments(segments: list, max_duration: float = 7.0) -> list:
    """Merge short subtitle fragments into reader-friendly cards.

    Merges consecutive segments when:
    - The buffer is short, OR the new segment is tiny
    - The gap between segments is small (<1.5s)
    - The combined text fits within a char limit (80 English / 40 CJK)
    - The combined duration stays under max_duration
    """
    if not segments:
        return segments

    # Detect CJK content from first segment with text
    first_text = next((s["text"] for s in segments if s.get("text")), "")
    cjk = _is_cjk(first_text)

    # CJK chars are ~2x wider; use tighter thresholds
    char_limit = 40 if cjk else 80
    buf_short_limit = 6 if cjk else 42      # ~6 CJK chars = fragment
    seg_tiny_limit = 4 if cjk else 20       # ~4 CJK chars = tiny

    merged = [dict(segments[0])]

    for seg in segments[1:]:
        buf = merged[-1]
        buf_chars = len(buf["text"])
        buf_dur = buf["end"] - buf["start"]
        seg_chars = len(seg["text"])
        seg_dur = seg["end"] - seg["start"]
        gap = seg["start"] - buf["end"]
        combined = _smooth_join(buf["text"], seg["text"])
        combined_dur = seg["end"] - buf["start"]

        buf_short = buf_chars < buf_short_limit or buf_dur < 1.5
        seg_tiny = seg_chars < seg_tiny_limit or seg_dur < 0.8
        fits = len(combined) <= char_limit
        close = gap < 1.5
        duration_ok = combined_dur <= max_duration

        if (buf_short or seg_tiny) and fits and close and duration_ok:
            merged[-1] = {
                "start": buf["start"],
                "end": seg["end"],
                "text": combined,
                "index": buf["index"],
            }
        else:
            merged.append(dict(seg))

    # Re-index
    for i, seg in enumerate(merged):
        seg["index"] = i

    return merged


def normalize_subtitle_text(text: str) -> str:
    """Normalize subtitle text for export.

    - CJK-dominant text: remove punctuation; replace mid-sentence punctuation
      with one full-width space U+3000; remove sentence-final punctuation.
    - English-dominant text: keep punctuation unchanged.
    """
    if not text:
        return text

    # CJK subtitle style: remove punctuation, but keep a visual pause in the
    # middle of a sentence using one full-width space.
    full_width_space = "\u3000"
    protected_patterns = re.compile(
        r"(https?://\S+|www\.\S+|"
        r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+(?:/[A-Za-z0-9_./%-]*)?|"
        r"(?<!\d)\d{1,2}:\d{2}(?::\d{2})?(?!\d)|"
        r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|"
        r"\b\d+\.\d+\b)"
    )
    cjk_punctuation_chars = set("，。！？；：、《》【】「」『』〈〉〔〕“”‘’·…—–")
    punctuation_chars = cjk_punctuation_chars | set(
        ",.!?;:()[]{}<>"
        "\"`/\\|_+=*&^%$#@~-"
    )

    if not _is_cjk(text) and not any(ch in cjk_punctuation_chars for ch in text):
        return text

    def is_word_internal_apostrophe(s: str, idx: int) -> bool:
        if s[idx] != "'":
            return False
        if idx == 0 or idx == len(s) - 1:
            return False
        return s[idx - 1].isascii() and s[idx - 1].isalnum() and s[idx + 1].isascii() and s[idx + 1].isalnum()

    def next_visible_char(s: str, start_idx: int) -> str:
        for ch in s[start_idx:]:
            if not ch.isspace():
                return ch
        return ""

    protected = {}

    def protect_match(match: re.Match) -> str:
        key = f"\uFFF0{len(protected)}\uFFF1"
        protected[key] = match.group(0)
        return key

    text = protected_patterns.sub(protect_match, text)

    out = []
    for i, ch in enumerate(text):
        if ch == "'" and is_word_internal_apostrophe(text, i):
            out.append(ch)
            continue

        if ch in punctuation_chars:
            next_ch = next_visible_char(text, i + 1)
            if next_ch:
                out.append(full_width_space)
            continue

        out.append(ch)

    cleaned = "".join(out)
    cleaned = re.sub(r" +", " ", cleaned)
    cleaned = re.sub(rf"{full_width_space}+", full_width_space, cleaned)
    cleaned = re.sub(rf" *{full_width_space} *", full_width_space, cleaned)
    cleaned = cleaned.strip(" " + full_width_space)
    for key, value in protected.items():
        cleaned = cleaned.replace(key, value)
    return cleaned


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

    segments = job["segments"]
    # Merge short fragments for subtitle formats — both Parakeet (English,
    # many tiny VAD segments) and SenseVoice (Chinese, standalone punctuation
    # fragments like 。) benefit from merging into reader-friendly cards.
    if format_type in ("srt", "vtt"):
        segments = merge_short_segments(segments)
    segments = fix_timestamp_overlaps(segments)
    filename_base = Path(job["filename"]).stem
    suffix = "转写" if ui_lang == "zh" else "transcription"

    if format_type == "txt":
        content = "\n".join(seg["text"] for seg in segments)
        mimetype = "text/plain"
        ext = "txt"
    elif format_type == "srt":
        lines = []
        subtitle_segments = []
        for seg in segments:
            text = normalize_subtitle_text(seg["text"])
            if text:
                subtitle_segments.append((seg, text))
        for i, (seg, text) in enumerate(subtitle_segments, 1):
            start = format_timestamp(seg["start"], ",")
            end = format_timestamp(seg["end"], ",")
            lines.append(f"{i}\n{start} --> {end}\n{text}\n")
        content = "\n".join(lines)
        mimetype = "application/x-subrip"
        ext = "srt"
    elif format_type == "vtt":
        lines = ["WEBVTT\n"]
        for seg in segments:
            text = normalize_subtitle_text(seg["text"])
            if not text:
                continue
            start = format_timestamp(seg["start"], ".")
            end = format_timestamp(seg["end"], ".")
            lines.append(f"{start} --> {end}\n{text}\n")
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
