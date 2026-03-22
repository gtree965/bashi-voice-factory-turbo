import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import threading
from pathlib import Path

from model_manager import ModelManager
from engines.sherpa_sensevoice import SherpaSenseVoiceEngine

def main():
    print("=== 巴适声工厂 (Bashi Voice Factory) 引擎测试 ===")
    
    # Check if models exist, if not download
    models_dir = Path("models")
    mm = ModelManager(models_dir)
    default_model = "sensevoice-small-int8"

    if not mm._is_model_complete(default_model):
        print(f"Model {default_model} missing, downloading...")
        for event in mm.download_model(default_model, use_mirror=True):
            msg = event.get('message', '')
            status = event.get('status', '')
            if status == "error":
                print(f"Error: {event.get('error')}")
            elif msg:
                print(f"[{status}] {msg}")
        print("Download complete.")
    else:
        print("Model forms already downloaded.")

    # Initialize Engine
    print("Loading Sherpa-ONNX + SenseVoiceEngine...")
    engine = SherpaSenseVoiceEngine(models_dir / default_model)
    engine.load_model()
    print("Loaded engine successfully!")

    if len(sys.argv) > 1:
        audio_file = Path(sys.argv[1])
        if not audio_file.exists():
            print(f"File not found: {audio_file}")
            return
            
        print(f"Transcribing {audio_file}...")
        for segment in engine.transcribe_stream(audio_file):
            print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
            
    else:
        print("Test file not provided. Run: python test_stt.py <wav_file_16kHz>")

if __name__ == "__main__":
    main()
