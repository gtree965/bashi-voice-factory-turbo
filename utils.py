import subprocess
import time
import imageio_ffmpeg
from pathlib import Path

def extract_audio_wav(input_path: Path, output_path: Path) -> Path:
    """Extract audio from any media file to 16kHz mono WAV.

    Uses the ffmpeg bundled with imageio-ffmpeg.

    Args:
        input_path: Source audio/video file
        output_path: Destination .wav file

    Returns:
        Path to the output WAV file
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-y",                    # Overwrite output
        "-i", str(input_path),   # Input file
        "-vn",                   # No video
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",          # 16kHz sample rate
        "-ac", "1",              # Mono
        str(output_path)
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600  # 10 min timeout for large files
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed: {result.stderr[:500]}"
        )

    return output_path

def cleanup_old_files(output_dir: Path, max_age_hours: int = 24):
    """Remove audio files older than max_age_hours."""
    now = time.time()
    cleaned = 0
    for file in output_dir.iterdir():
        if file.suffix.lower() in ('.mp3', '.wav', '.ogg', '.flac'):
            try:
                if now - file.stat().st_mtime > max_age_hours * 3600:
                    file.unlink()
                    cleaned += 1
            except (PermissionError, OSError):
                # File may be locked or in use, skip it
                pass
    if cleaned > 0:
        print(f"Cleaned up {cleaned} old audio file(s)")
