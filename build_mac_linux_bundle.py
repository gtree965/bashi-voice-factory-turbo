import tarfile
import os

source_dir = "."
bundle_name = "Bashi-Voice-Factory-v3.11-Mac-Linux"
output_filename = f"{bundle_name}.tar.gz"

# Directories to exclude entirely
exclude_dirs = {
    "python-3.12.10-embed-amd64",  # Windows portable Python
    "EdgeTTS-Mac-Linux-v2.16",     # Old version bundle
    "models",                       # Downloaded at runtime (~244+ MB)
    "docs_v3",                      # Dev docs
    "dist",                         # Windows distribution packages
    "tts_readback_outputs",         # TTS readback test outputs
    ".venv",
    ".git",
    ".claude",
    "__pycache__",
    ".DS_Store",
}

# Files to exclude by exact name
exclude_files = {
    output_filename,
    # Windows-only launchers
    "run_portable.bat",
    "run.bat",
    "run_venv.bat",
    # Build/dev scripts
    "build_mac_linux_bundle.py",
    "download_model.py",
    # Test scripts
    "test_stt.py",
    "test_models.py",
    "test_zh_tts_patch.py",
    "test_export_subtitles.py",
    "test_tts_readback.py",
    # Runtime artifacts
    "test_out.wav",
    "launch_log.txt",
    # Dev logs / docs
    "DEVLOG_2026-03-06.md",
    "DEVLOG_v3.0_Upgrade.md",
    "stt_model_comparison.md",
    "walkthrough_multimodel_2.md",
    # Old launchers
    "EdgeTTS-Mac-venv.command",
    # Duplicate requirements
    "requirements - Copy.txt",
}

# Patterns to exclude by suffix
exclude_suffixes = (
    ".tar.gz",   # Old bundles
    ".zip",      # Windows distribution zips
    ".pyc",      # Compiled bytecode
    ".mp4",      # Test / demo video files
    ".webm",     # Test / demo video files
    ".wav",      # Test audio outputs
    ".pdf",      # Documentation PDFs
)

# Patterns to exclude by prefix
exclude_prefixes = (
    "_test_",    # Test output SRT/TXT files
)

# Patterns to exclude by substring in filename
exclude_substrings = (
    "_转写.",     # Transcription output files (*_转写.srt / .txt / .vtt)
    "-转写-",     # Transcription variant files (*-转写-*.srt)
    "_official",  # Official reference subtitles
    "-official",  # Official reference subtitles
    "zh-official", # Official reference subtitles
    "-zh-Hans",   # Official reference subtitles
    "-ENG-official", # Official reference subtitles
    "安装说明",    # Windows installation instructions
    "使用说明",    # Windows usage manual
)


def filter_tar(tarinfo):
    """Enforce POSIX permissions: 755 for dirs/scripts, 644 for regular files."""
    if tarinfo.name.endswith(".sh") or tarinfo.name.endswith(".command"):
        tarinfo.mode = 0o755
    elif tarinfo.isdir():
        tarinfo.mode = 0o755
    else:
        tarinfo.mode = 0o644
    return tarinfo


print(f"Bundling {output_filename} ...")
print(f"  Archive root folder: {bundle_name}/")

file_count = 0
with tarfile.open(output_filename, "w:gz") as tar:
    for root, dirs, files in os.walk(source_dir):
        # Prune excluded directories (in-place edit of dirs[:])
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        for file in files:
            if file in exclude_files or file.startswith('.'):
                continue
            if any(file.endswith(s) for s in exclude_suffixes):
                continue
            if any(file.startswith(p) for p in exclude_prefixes):
                continue
            if any(sub in file for sub in exclude_substrings):
                continue
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, source_dir)
            arcname = os.path.join(bundle_name, arcname).replace('\\', '/')

            # Skip generated runtime files in static/audio and static/uploads
            if "/audio/" in arcname or "/uploads/" in arcname:
                continue

            tar.add(file_path, arcname=arcname, filter=filter_tar)
            file_count += 1

print(f"Done! Packed {file_count} files into {output_filename}")
