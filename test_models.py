#!/usr/bin/env python3
"""
Model Comparison Test Script
=============================
Runs all available STT models against test videos and compares results
with official subtitles.

Usage:
    python test_models.py                     # Run all tests
    python test_models.py --model sensevoice  # Test one model only
    python test_models.py --video 新手必看     # Test one video only
"""
import sys
import os
import time
import argparse
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils import extract_audio_wav

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODELS_DIR = Path("models")
TEST_DIR = Path(".")

# Test videos and their official subtitle files
TEST_VIDEOS = {
    "chinese": {
        "video": "9分钟游遍西安.webm",
        "official_srt": "9分钟游遍西安-zh-Hans.srt",
        "language": "zh",
        "label": "Pure Chinese (纯中文)",
    },
    "english": {
        "video": "Python-for-Beginners.mp4",
        "official_srt": "Python-for-Beginners-ENG-official.srt",
        "language": "en",
        "label": "Pure English",
    },
    "mixed": {
        "video": "新手必看.mp4",
        "official_srt": "新手必看zh-official.srt",
        "language": "zh",
        "label": "Chinese-English Mixed (中英混合)",
    },
    "ted_english": {
        "video": "What Makes a Good Life.mp4",
        "official_srt": "What Makes a Good Life_official_en.srt",
        "language": "en",
        "label": "TED Talk English (What Makes a Good Life)",
    },
}

# Model configurations — model_id must match MODEL_REGISTRY keys
MODEL_CONFIGS = {
    "sensevoice": {
        "model_id": "sensevoice-small-int8",
        "label": "SenseVoice Small (INT8)",
        "engine_class": "SherpaSenseVoiceEngine",
        "engine_module": "engines.sherpa_sensevoice",
    },
    "parakeet": {
        "model_id": "parakeet-tdt-0.6b-v2-int8",
        "label": "Parakeet TDT 0.6B (INT8)",
        "engine_class": "SherpaParakeetEngine",
        "engine_module": "engines.sherpa_parakeet",
    },
}


# ---------------------------------------------------------------------------
# SRT Parsing
# ---------------------------------------------------------------------------

def parse_srt(srt_path: Path) -> list:
    """Parse SRT file into list of (start_sec, end_sec, text)."""
    if not srt_path.exists():
        return []

    content = srt_path.read_text(encoding="utf-8-sig")
    blocks = re.split(r'\n\s*\n', content.strip())
    entries = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue

        # Find the timestamp line
        ts_line = None
        text_lines = []
        for i, line in enumerate(lines):
            if '-->' in line:
                ts_line = line
                text_lines = lines[i+1:]
                break

        if not ts_line:
            continue

        match = re.match(
            r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
            ts_line.strip()
        )
        if not match:
            # Try MM:SS,mmm format
            match = re.match(
                r'(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2})[,.](\d{3})',
                ts_line.strip()
            )
            if match:
                g = match.groups()
                start = int(g[0])*60 + int(g[1]) + int(g[2])/1000
                end = int(g[3])*60 + int(g[4]) + int(g[5])/1000
            else:
                continue
        else:
            g = match.groups()
            start = int(g[0])*3600 + int(g[1])*60 + int(g[2]) + int(g[3])/1000
            end = int(g[4])*3600 + int(g[5])*60 + int(g[6]) + int(g[7])/1000

        text = ' '.join(line.strip() for line in text_lines if line.strip())
        if text:
            entries.append((start, end, text))

    return entries


def srt_to_plain_text(entries: list) -> str:
    """Concatenate SRT entries into plain text for comparison."""
    return ' '.join(e[2] for e in entries)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def strip_punct_spaces(text: str) -> str:
    """Remove all punctuation and spaces for CER comparison."""
    return re.sub(r'[\s\.,!?;:，。！？；：、\-—–\'\"\"\"\'\'()\[\]（）【】「」《》\u200b]', '', text.lower())


def character_error_rate(ref: str, hyp: str) -> float:
    """Compute Character Error Rate using edit distance."""
    ref_clean = strip_punct_spaces(ref)
    hyp_clean = strip_punct_spaces(hyp)

    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0

    # Simple edit distance (Levenshtein)
    n, m = len(ref_clean), len(hyp_clean)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            temp = dp[j]
            if ref_clean[i-1] == hyp_clean[j-1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j-1])
            prev = temp

    return dp[m] / n


def word_error_rate(ref: str, hyp: str) -> float:
    """Compute Word Error Rate (for English)."""
    ref_words = ref.lower().split()
    hyp_words = hyp.lower().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    n, m = len(ref_words), len(hyp_words)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            temp = dp[j]
            if ref_words[i-1] == hyp_words[j-1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j-1])
            prev = temp

    return dp[m] / n


# ---------------------------------------------------------------------------
# Engine helpers
# ---------------------------------------------------------------------------

def get_engine(model_key: str):
    """Dynamically import and instantiate the engine."""
    cfg = MODEL_CONFIGS[model_key]
    model_dir = MODELS_DIR / cfg["model_id"]

    if not model_dir.exists():
        return None

    # Check if required files exist
    if model_key in ("parakeet",):
        if not (model_dir / "encoder.int8.onnx").exists():
            return None
    else:
        if not (model_dir / "model.int8.onnx").exists():
            return None

    import importlib
    mod = importlib.import_module(cfg["engine_module"])
    cls = getattr(mod, cfg["engine_class"])
    return cls(model_dir)


def transcribe_video(engine, wav_path: Path, language: str) -> tuple:
    """Run transcription and return (segments_list, elapsed_seconds)."""
    t0 = time.time()
    segments = list(engine.transcribe_stream(wav_path, language=language))
    elapsed = time.time() - t0
    return segments, elapsed


def segments_to_text(segments) -> str:
    """Join segment texts."""
    return ' '.join(s.text for s in segments)


def segments_to_srt(segments) -> str:
    """Convert segments to SRT format."""
    lines = []
    for i, seg in enumerate(segments):
        start_h = int(seg.start // 3600)
        start_m = int((seg.start % 3600) // 60)
        start_s = int(seg.start % 60)
        start_ms = int((seg.start % 1) * 1000)

        end_h = int(seg.end // 3600)
        end_m = int((seg.end % 3600) // 60)
        end_s = int(seg.end % 60)
        end_ms = int((seg.end % 1) * 1000)

        lines.append(f"{i+1}")
        lines.append(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> "
                     f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}")
        lines.append(seg.text)
        lines.append("")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_test(video_key: str, model_key: str, wav_cache: dict) -> dict:
    """Run a single model on a single video. Returns result dict."""
    vconf = TEST_VIDEOS[video_key]
    mconf = MODEL_CONFIGS[model_key]

    video_path = TEST_DIR / vconf["video"]
    if not video_path.exists():
        return {"error": f"Video not found: {video_path}"}

    # Get or create WAV
    if video_key not in wav_cache:
        wav_path = TEST_DIR / f"_test_{video_key}.wav"
        print(f"  Converting {vconf['video']} to WAV...")
        extract_audio_wav(video_path, wav_path)
        wav_cache[video_key] = wav_path
    wav_path = wav_cache[video_key]

    # Load engine
    print(f"  Loading {mconf['label']}...")
    engine = get_engine(model_key)
    if engine is None:
        return {"error": f"Model not available: {mconf['model_id']}"}

    # Transcribe
    print(f"  Transcribing with {mconf['label']}...")
    segments, elapsed = transcribe_video(engine, wav_path, vconf["language"])

    hyp_text = segments_to_text(segments)

    # Save SRT output
    srt_output = segments_to_srt(segments)
    out_name = f"_test_{video_key}_{model_key}.srt"
    (TEST_DIR / out_name).write_text(srt_output, encoding="utf-8")

    # Parse official subtitle
    official_path = TEST_DIR / vconf["official_srt"]
    official_entries = parse_srt(official_path)
    ref_text = srt_to_plain_text(official_entries)

    # Compute metrics
    cer = character_error_rate(ref_text, hyp_text) if ref_text else None
    wer = word_error_rate(ref_text, hyp_text) if ref_text else None

    # Audio duration from WAV
    import wave
    with wave.open(str(wav_path), "rb") as wf:
        audio_duration = wf.getnframes() / wf.getframerate()

    rtf = elapsed / audio_duration if audio_duration > 0 else 0

    result = {
        "model": mconf["label"],
        "video": vconf["label"],
        "segments": len(segments),
        "chars": len(hyp_text),
        "time_sec": round(elapsed, 1),
        "audio_sec": round(audio_duration, 1),
        "rtf": round(rtf, 3),
        "cer": round(cer * 100, 1) if cer is not None else None,
        "wer": round(wer * 100, 1) if wer is not None else None,
        "srt_file": out_name,
        "first_50": hyp_text[:80],
    }

    # Clean up engine
    engine.cleanup()

    return result


def main():
    parser = argparse.ArgumentParser(description="STT Model Comparison Test")
    parser.add_argument("--model", choices=list(MODEL_CONFIGS.keys()),
                        help="Test specific model only")
    parser.add_argument("--video", choices=list(TEST_VIDEOS.keys()),
                        help="Test specific video only")
    args = parser.parse_args()

    models = [args.model] if args.model else list(MODEL_CONFIGS.keys())
    videos = [args.video] if args.video else list(TEST_VIDEOS.keys())

    # Check available models
    available_models = []
    for mk in models:
        engine = get_engine(mk)
        if engine:
            available_models.append(mk)
            print(f"[OK] {MODEL_CONFIGS[mk]['label']}")
        else:
            print(f"[--] {MODEL_CONFIGS[mk]['label']} (not downloaded)")

    if not available_models:
        print("\nNo models available! Download models first.")
        sys.exit(1)

    print(f"\nRunning {len(available_models)} model(s) x {len(videos)} video(s) = "
          f"{len(available_models) * len(videos)} test(s)\n")

    wav_cache = {}
    results = []

    for vk in videos:
        print(f"\n{'='*60}")
        print(f"VIDEO: {TEST_VIDEOS[vk]['label']} ({TEST_VIDEOS[vk]['video']})")
        print(f"{'='*60}")

        for mk in available_models:
            print(f"\n--- {MODEL_CONFIGS[mk]['label']} ---")
            result = run_test(vk, mk, wav_cache)
            results.append(result)

            if "error" in result:
                print(f"  ERROR: {result['error']}")
            else:
                print(f"  Segments: {result['segments']}")
                print(f"  Time: {result['time_sec']}s (RTF: {result['rtf']})")
                print(f"  CER: {result['cer']}%" if result['cer'] is not None else "  CER: N/A")
                print(f"  WER: {result['wer']}%" if result['wer'] is not None else "  WER: N/A")
                print(f"  Preview: {result['first_50']}...")
                print(f"  Saved: {result['srt_file']}")

    # Summary table
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    # Group by video
    for vk in videos:
        vr = [r for r in results if r.get("video") == TEST_VIDEOS[vk]["label"]]
        if not vr:
            continue

        print(f"\n{TEST_VIDEOS[vk]['label']}")
        print(f"{'─'*70}")
        print(f"{'Model':<30} {'Segs':>6} {'Time':>7} {'RTF':>7} {'CER%':>7} {'WER%':>7}")
        print(f"{'─'*70}")

        for r in vr:
            if "error" in r:
                print(f"{r['model']:<30} {'ERROR':>6}")
            else:
                cer_str = f"{r['cer']:.1f}" if r['cer'] is not None else "N/A"
                wer_str = f"{r['wer']:.1f}" if r['wer'] is not None else "N/A"
                print(f"{r['model']:<30} {r['segments']:>6} {r['time_sec']:>6.1f}s "
                      f"{r['rtf']:>7.3f} {cer_str:>7} {wer_str:>7}")

    # Cleanup temp WAV files
    print("\n\nCleaning up temp WAV files...")
    for wp in wav_cache.values():
        if wp.exists():
            wp.unlink()
            print(f"  Deleted {wp}")

    print("\nDone! SRT outputs saved as _test_*.srt for manual review.")


if __name__ == "__main__":
    main()
