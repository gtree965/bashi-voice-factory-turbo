import tarfile
import os

source_dir = "."
bundle_name = "Bashi-Voice-Factory-v3.1-Mac-Linux"
output_filename = f"{bundle_name}.tar.gz"

# Directories to exclude entirely
exclude_dirs = {
    "python-3.12.10-embed-amd64",  # Windows portable Python
    "EdgeTTS-Mac-Linux-v2.16",     # Old version bundle
    "models",                       # Downloaded at runtime (~244 MB)
    "docs_v3",                      # Dev docs
    ".venv",
    ".git",
    "__pycache__",
    ".DS_Store",
}

# Files to exclude
exclude_files = {
    output_filename,
    "run_portable.bat",            # Windows only
    "run.bat",
    "run_venv.bat",
    "build_mac_linux_bundle.py",   # This script itself
    "test_stt.py",                 # Test file
    "test_out.wav",                # Test output
    "launch_log.txt",              # Runtime log
    "DEVLOG_2026-03-06.md",        # Dev log
    "DEVLOG_v3.0_Upgrade.md",      # Dev log
    "EdgeTTS-Mac-venv.command",    # Old name, replaced by Bashi-Voice-Factory-Mac.command
}

# Patterns to exclude
exclude_suffixes = (".tar.gz", ".pyc")


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
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, source_dir)
            arcname = os.path.join(bundle_name, arcname).replace('\\', '/')

            # Skip generated runtime files in static/audio and static/uploads
            if "/audio/" in arcname or "/uploads/" in arcname:
                continue

            tar.add(file_path, arcname=arcname, filter=filter_tar)
            file_count += 1

print(f"Done! Packed {file_count} files into {output_filename}")
