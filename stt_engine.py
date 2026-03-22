from dataclasses import dataclass
from typing import List, Generator
from pathlib import Path


@dataclass
class Segment:
    """A single transcribed segment with timestamps."""
    index: int
    start: float   # seconds
    end: float     # seconds
    text: str
    language: str = ""


@dataclass
class TranscriptionResult:
    """Complete transcription output."""
    segments: List[Segment]
    full_text: str
    language_detected: str
    duration_seconds: float
    processing_seconds: float


class SttEngine:
    """Abstract interface for STT engines."""

    def __init__(self, model_dir: Path, num_threads: int = 4):
        self.model_dir = model_dir
        self.num_threads = num_threads
        self._model = None

    def load_model(self):
        """Load the ASR model into memory. Call once."""
        raise NotImplementedError

    def is_loaded(self) -> bool:
        return self._model is not None

    def transcribe_stream(
        self,
        audio_path: Path,
        language: str = "auto"
    ) -> Generator[Segment, None, None]:
        """Transcribe audio file, yielding segments as they complete.

        Args:
            audio_path: Path to 16kHz mono WAV file
            language: Language code or "auto"

        Yields:
            Segment objects as they are recognized
        """
        raise NotImplementedError

    def supported_languages(self) -> List[str]:
        """Return list of supported language codes."""
        raise NotImplementedError

    def cleanup(self):
        """Release model from memory."""
        self._model = None
