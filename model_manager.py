import hashlib
import urllib.request
from pathlib import Path
from typing import Generator, Optional


# Model registry
MODEL_REGISTRY = {
    "sensevoice-small-int8": {
        "name": "SenseVoice Small (INT8)",
        "name_zh": "SenseVoice 小型 (INT8量化)",
        "engine": "sherpa-onnx",
        "size_mb": 242,
        "languages": ["zh", "en", "ja", "ko", "yue"],
        "files": {
            "model.int8.onnx": {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/model.int8.onnx",
                "mirror": "https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/model.int8.onnx",
                "sha256": "c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51",
            },
            "tokens.txt": {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt",
                "mirror": "https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/main/tokens.txt",
                "sha256": "f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc",
            },
        },
        "is_default": True,
        "description": "Fast & accurate for Chinese/English/Cantonese. Recommended.",
        "description_zh": "中英粤语快速准确，推荐默认使用。",
    },
    "parakeet-tdt-0.6b-v2-int8": {
        "name": "Parakeet TDT 0.6B (INT8)",
        "name_zh": "Parakeet TDT 0.6B (INT8量化)",
        "engine": "sherpa-onnx",
        "size_mb": 661,
        "languages": ["en"],
        "files": {
            "encoder.int8.onnx": {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/encoder.int8.onnx",
                "mirror": "https://hf-mirror.com/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/encoder.int8.onnx",
                "sha256": "a32b12d17bbbc309d0686fbbcc2987b5e9b8333a7da83fa6b089f0a2acd651ab",
            },
            "decoder.int8.onnx": {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/decoder.int8.onnx",
                "mirror": "https://hf-mirror.com/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/decoder.int8.onnx",
                "sha256": "b6bb64963457237b900e496ee9994b59294526439fbcc1fecf705b31a15c6b4e",
            },
            "joiner.int8.onnx": {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/joiner.int8.onnx",
                "mirror": "https://hf-mirror.com/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/joiner.int8.onnx",
                "sha256": "7946164367946e7f9f29a122407c3252b680dbae9a51343eb2488d057c3c43d2",
            },
            "tokens.txt": {
                "url": "https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/tokens.txt",
                "mirror": "https://hf-mirror.com/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/resolve/main/tokens.txt",
                "sha256": "ec182b70dd42113aff6c5372c75cac58c952443eb22322f57bbd7f53977d497d",
            },
        },
        "is_default": False,
        "description": "Best English ASR. NVIDIA Parakeet, ~1.7% WER. ~661MB download.",
        "description_zh": "最佳英文语音识别，NVIDIA Parakeet，约661MB。",
    },
}

# VAD model (shared across engines)
VAD_MODEL = {
    "silero_vad.onnx": {
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx",
        "size_mb": 2,
        "sha256": "9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6",
    }
}


class ModelManager:
    """Manage ASR model downloads and availability."""

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def list_installed(self) -> list:
        """List installed models with their metadata."""
        installed = []
        for model_id, meta in MODEL_REGISTRY.items():
            if self._is_model_complete(model_id):
                installed.append({**meta, "id": model_id})
        return installed

    def list_available(self) -> list:
        """List models available for download (not yet installed)."""
        available = []
        for model_id, meta in MODEL_REGISTRY.items():
            if not self._is_model_complete(model_id):
                available.append({**meta, "id": model_id})
        return available

    def _is_model_complete(self, model_id: str) -> bool:
        """Check if all model files exist."""
        meta = MODEL_REGISTRY.get(model_id)
        if not meta:
            return False
        model_dir = self.models_dir / model_id
        return all(
            (model_dir / fname).exists()
            for fname in meta["files"]
        )

    def get_model_dir(self, model_id: str) -> Optional[Path]:
        """Get path to installed model directory."""
        if self._is_model_complete(model_id):
            return self.models_dir / model_id
        return None

    def get_default_model_dir(self) -> Optional[Path]:
        """Get path to the default installed model."""
        for model_id, meta in MODEL_REGISTRY.items():
            if meta.get("is_default") and self._is_model_complete(model_id):
                return self.models_dir / model_id
        for model_id in MODEL_REGISTRY:
            if self._is_model_complete(model_id):
                return self.models_dir / model_id
        return None

    def download_model(
        self,
        model_id: str,
        use_mirror: bool = False
    ) -> Generator[dict, None, None]:
        """Download model files with progress updates."""
        meta = MODEL_REGISTRY.get(model_id)
        if not meta:
            yield {"status": "error", "error": f"Unknown model: {model_id}"}
            return

        model_dir = self.models_dir / model_id
        model_dir.mkdir(parents=True, exist_ok=True)

        total_files = len(meta["files"])
        files_done = 0

        vad_path = self.models_dir / "silero_vad.onnx"
        if not vad_path.exists():
            yield {"status": "downloading", "message": "Downloading VAD model...",
                   "message_zh": "正在下载语音活动检测模型..."}
            try:
                vad_info = VAD_MODEL["silero_vad.onnx"]
                self._download_file(vad_info["url"], vad_path, vad_info.get("sha256"))
            except Exception as e:
                yield {"status": "error", "error": f"VAD download failed: {e}"}
                return

        for fname, urls in meta["files"].items():
            dest = model_dir / fname
            if dest.exists():
                files_done += 1
                continue

            # Try mirror first (faster in China), fall back to main URL
            if use_mirror:
                url_order = [urls.get("mirror"), urls.get("url")]
            else:
                url_order = [urls.get("url"), urls.get("mirror")]
            url_order = [u for u in url_order if u]  # remove None

            progress = round((files_done / total_files) * 100, 1) if total_files > 0 else 0
            yield {
                "status": "downloading",
                "file": fname,
                "file_index": files_done + 1,
                "total_files": total_files,
                "progress": progress,
                "message": f"Downloading {fname}...",
                "message_zh": f"正在下载 {fname}...",
            }

            last_error = None
            for url in url_order:
                try:
                    self._download_file(url, dest, urls.get("sha256"))
                    files_done += 1
                    last_error = None
                    break
                except Exception as e:
                    last_error = e
                    if url != url_order[-1]:
                        yield {
                            "status": "downloading",
                            "message": f"Mirror failed, trying fallback for {fname}...",
                            "message_zh": f"镜像下载失败，正在尝试备用地址 {fname}...",
                        }

            if last_error:
                yield {"status": "error", "error": f"Download failed: {last_error}"}
                return

        yield {"status": "done", "model_id": model_id}

    @staticmethod
    def _sha256_file(path: Path) -> str:
        """Compute SHA256 hex digest of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 64), b""):
                h.update(chunk)
        return h.hexdigest()

    def _download_file(self, url: str, dest: Path, expected_sha256: str = None):
        """Download a file from URL to destination using chunked streaming."""
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            # Use a long timeout (10 min) — model files can be 200+ MB on slow connections
            with urllib.request.urlopen(req, timeout=600) as response, open(tmp, 'wb') as out_file:
                chunk_size = 1024 * 64  # 64 KB chunks — flat memory usage regardless of file size
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
            # Verify checksum if provided
            if expected_sha256:
                actual = self._sha256_file(tmp)
                if actual != expected_sha256:
                    tmp.unlink()
                    raise RuntimeError(
                        f"Checksum mismatch for {dest.name}: "
                        f"expected {expected_sha256[:12]}..., got {actual[:12]}..."
                    )
            # Atomic rename: only appears at dest once fully written
            tmp.replace(dest)
        except Exception:
            # Remove partial file so next attempt retries cleanly
            if tmp.exists():
                tmp.unlink()
            raise
