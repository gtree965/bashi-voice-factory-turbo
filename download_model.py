"""Helper script for run_portable.bat to download the default ASR model."""
from pathlib import Path
from model_manager import ModelManager

mm = ModelManager(Path("models"))
for event in mm.download_model("sensevoice-small-int8", use_mirror=True):
    msg = event.get("message") or event.get("message_zh") or ""
    status = event.get("status", "")
    if msg:
        print(msg)
    if status == "error":
        print(f"Error: {event.get('error', 'Unknown error')}")
    elif status == "done":
        print("Model download complete!")
