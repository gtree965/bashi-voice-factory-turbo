"""
巴适声工厂 (Bashi Voice Factory) v3.1
A bilingual text-to-speech and speech-to-text web interface.

New in v3.1:
- Streamlined to 2 production STT models: SenseVoice (multilingual) + Parakeet TDT (English)
- Parakeet TDT 0.6B: NVIDIA's best English ASR (~1.7% WER), beam search + tuned VAD
- SenseVoice VAD rewrite: eliminated overlap/stutter, CER improved from 8.9% to 2.1%
- Removed experimental models (Paraformer, Zipformer-CTC, FireRedASR)

New in v3.0:
- Added local offline Speech-to-Text (STT) capabilities using sherpa-onnx + SenseVoice
- VAD segmentation for long audio processing
- Model manager and background downloads

New in v2.16:
- World language expansion: 14 languages (Top 10 + Korean + German + Hebrew + Greek)
- TXT file drag-and-drop upload for long texts
- Multi-format audio export (WAV/OGG/FLAC) via FFmpeg conversion
- Speed slider expanded from ±50% to ±200%

New in v2.15:
- Smart network auto-retry with exponential backoff (up to 3 retries per chunk)
- Migrated default port from 5000 to 5050 (avoids macOS AirPlay Receiver conflict)
- Linux Debian/Mint auto-recovery for broken venv/pip installations

New in v2.14:
- USB Portable Edition: embedded Python 3.12 for zero-install Windows deployment
- Portable launcher (run_portable.bat) with automatic pip bootstrap and ._pth patching
- Console output encoding fixes for Windows Command Prompt UTF-8 handling

New in v2.13:
- Added Local Area Network (LAN) sharing via launch scripts and backend args
- Auto-detect local IP to show access link for mobile devices

New in v2.12:
- Long text support up to 50,000 characters with chunked generation
- Live progress bar for long text generation via SSE
- Shadowing mode retains 5,000 character limit

New in v2.11:
- Added smart chunking for shadowing (max words per chunk)
- Newline now treated as hard boundary
- Chunking presets: Short (12) / Medium (15) / Long (20) / Off
- Fixed pause/continue toggle button
- Separate README files: English and Chinese
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from flask import Flask, render_template

from tts_routes import tts_bp, VERSION, OUTPUT_DIR
from stt_routes import stt_bp, UPLOAD_DIR
from utils import cleanup_old_files

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(tts_bp)
app.register_blueprint(stt_bp)

@app.route('/')
def index():
    return render_template('index.html', version=VERSION)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bashi Voice Factory (巴适声工厂)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host IP to bind to")
    parser.add_argument("--port", type=int, default=5050, help="Port to bind to")
    args = parser.parse_args()

    # Clean up old audio files on startup (older than 24 hours)
    cleanup_old_files(OUTPUT_DIR, max_age_hours=24)
    cleanup_old_files(UPLOAD_DIR, max_age_hours=24)
    
    print("=" * 50)
    print(f"Bashi Voice Factory v{VERSION} (巴适声工厂)")
    print("NEW in v3.1: SenseVoice (multilingual) + Parakeet TDT (best English)!")
    print("v3.1 新功能: SenseVoice多语言 + Parakeet英文专用模型!")
    print("=" * 50)
    
    if args.host == "0.0.0.0":
        print(f"Starting server at http://0.0.0.0:{args.port} (Network Accessible)")
    else:
        print(f"Starting server at http://{args.host}:{args.port} (Local Only)")
        
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Run the server
    app.run(debug=False, host=args.host, port=args.port)
