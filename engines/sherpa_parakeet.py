import numpy as np
from pathlib import Path
from typing import List, Generator

try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None

from stt_engine import SttEngine, Segment


class SherpaParakeetEngine(SttEngine):
    """STT engine using sherpa-onnx with NeMo Parakeet TDT 0.6B model + Silero VAD.

    Parakeet is NVIDIA's state-of-the-art English ASR model (FastConformer +
    Token-and-Duration Transducer). It outputs punctuation, capitalization,
    and achieves ~1.7% WER on LibriSpeech clean English.

    Uses Silero VAD to split audio into speech segments to avoid OOM on long
    audio, then transcribes each segment with Parakeet.
    """

    def __init__(self, model_dir: Path, num_threads: int = 4):
        super().__init__(model_dir, num_threads)
        self._recognizer = None

    def load_model(self):
        """Load Parakeet TDT transducer model (encoder + decoder + joiner)."""
        if sherpa_onnx is None:
            raise ImportError(
                "sherpa-onnx not installed. "
                "Run: pip install sherpa-onnx"
            )

        encoder_path = self.model_dir / "encoder.int8.onnx"
        decoder_path = self.model_dir / "decoder.int8.onnx"
        joiner_path = self.model_dir / "joiner.int8.onnx"
        tokens_path = self.model_dir / "tokens.txt"

        if not encoder_path.exists():
            raise FileNotFoundError(
                f"Model not found: {encoder_path}\n"
                "Please download the model first via Model Manager."
            )

        self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(encoder_path),
            decoder=str(decoder_path),
            joiner=str(joiner_path),
            tokens=str(tokens_path),
            num_threads=self.num_threads,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="modified_beam_search",
            max_active_paths=4,
            model_type="nemo_transducer",
            debug=False,
        )

        self._model = True  # Mark as loaded

    @staticmethod
    def _split_text_into_segments(text: str, start_sec: float, end_sec: float,
                                   language: str, base_index: int,
                                   char_limit: int = 80) -> list:
        """Split long text into subtitle-sized segments with proportional timestamps.

        For English, we split on sentence boundaries and word boundaries
        with a higher character limit than CJK models.
        """
        if not text:
            return []

        duration = end_sec - start_sec
        total_chars = len(text)
        if total_chars == 0:
            return []

        # For English, split at sentence-ending punctuation or word boundaries
        end_punctuations = {'.', '!', '?', ';'}
        soft_punctuations = {',', ':', '—', '–'}

        lines = []
        current = []
        current_start_char = 0

        for i, ch in enumerate(text):
            current.append(ch)
            current_text = ''.join(current)
            is_last = (i == len(text) - 1)

            should_break = False
            if is_last:
                should_break = True
            elif ch in end_punctuations and i + 1 < len(text) and text[i + 1] == ' ':
                should_break = True
            elif ch in soft_punctuations and len(current) >= (char_limit * 0.5):
                should_break = True
            elif ch == ' ' and len(current) >= char_limit:
                should_break = True

            if should_break and current_text.strip():
                seg_start = start_sec + (current_start_char / total_chars) * duration
                seg_end = start_sec + ((i + 1) / total_chars) * duration

                if seg_end - seg_start < 0.2:
                    seg_end = seg_start + 0.3

                lines.append(Segment(
                    index=base_index + len(lines),
                    start=round(seg_start, 3),
                    end=round(seg_end, 3),
                    text=current_text.strip(),
                    language=language,
                ))
                current = []
                current_start_char = i + 1

        return lines

    def transcribe_stream(
        self,
        audio_path: Path,
        language: str = "auto"
    ) -> Generator[Segment, None, None]:
        """
        Transcribe audio using VAD + Parakeet TDT:
        1. Silero VAD detects speech segments with precise timestamps
        2. Parakeet transcribes each speech segment (English-optimized)
        3. Long segments are split into subtitle-sized chunks
        """
        if not self.is_loaded():
            self.load_model()

        import wave

        # Find the VAD model
        vad_model_path = self.model_dir.parent / "silero_vad.onnx"
        if not vad_model_path.exists():
            for candidate in [Path("models") / "silero_vad.onnx"]:
                if candidate.exists():
                    vad_model_path = candidate
                    break

        if not vad_model_path.exists():
            raise FileNotFoundError(
                f"VAD model not found at {vad_model_path}. "
                "Please ensure silero_vad.onnx is in the models directory."
            )

        with wave.open(str(audio_path), "rb") as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            num_frames = wf.getnframes()

            if sample_rate != 16000:
                raise ValueError(f"Expected 16kHz audio, got {sample_rate}Hz")

            raw = wf.readframes(num_frames)
            if sample_width == 2:
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            elif sample_width == 4:
                samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                raise ValueError(f"Unsupported sample width: {sample_width}")

            if num_channels > 1:
                samples = samples[::num_channels]

        # Configure VAD
        vad_config = sherpa_onnx.VadModelConfig()
        vad_config.silero_vad.model = str(vad_model_path)
        vad_config.silero_vad.min_silence_duration = 0.3
        vad_config.silero_vad.min_speech_duration = 0.25
        vad_config.silero_vad.threshold = 0.3
        vad_config.silero_vad.max_speech_duration = 30.0
        vad_config.sample_rate = sample_rate

        window_size = vad_config.silero_vad.window_size
        vad = sherpa_onnx.VoiceActivityDetector(
            vad_config,
            buffer_size_in_seconds=600
        )

        # Feed all audio through VAD
        offset = 0
        while offset < len(samples):
            end = min(offset + window_size, len(samples))
            chunk = samples[offset:end]
            if len(chunk) < window_size:
                chunk = np.concatenate([chunk, np.zeros(window_size - len(chunk), dtype=np.float32)])
            vad.accept_waveform(chunk)
            offset += window_size

        vad.flush()

        # Collect all speech segments from VAD
        speech_segments = []
        while not vad.empty():
            seg = vad.front
            start_sec = seg.start / sample_rate
            seg_samples = np.array(seg.samples, dtype=np.float32)
            end_sec = start_sec + len(seg_samples) / sample_rate
            speech_segments.append((start_sec, end_sec, seg_samples))
            vad.pop()

        print(f"[Parakeet] VAD detected {len(speech_segments)} speech segments")

        # Transcribe each speech segment with Parakeet
        segment_index = 0
        prev_end_time = 0.0

        for seg_start, seg_end, seg_samples in speech_segments:
            if len(seg_samples) < sample_rate * 0.2:
                continue

            stream = self._recognizer.create_stream()
            stream.accept_waveform(sample_rate, seg_samples)
            self._recognizer.decode_stream(stream)

            text = stream.result.text.strip()
            if not text:
                continue

            # Split long text into subtitle-sized chunks
            sub_segments = self._split_text_into_segments(
                text, seg_start, seg_end,
                language, segment_index,
                char_limit=80
            )

            for sub_seg in sub_segments:
                # Clamp to prevent micro-overlaps between VAD segments
                if sub_seg.start < prev_end_time:
                    sub_seg.start = prev_end_time
                if sub_seg.end <= sub_seg.start:
                    sub_seg.end = sub_seg.start + 0.3
                sub_seg.index = segment_index
                prev_end_time = sub_seg.end
                yield sub_seg
                segment_index += 1

    def supported_languages(self) -> List[str]:
        return ["en"]

    def cleanup(self):
        self._recognizer = None
        self._model = None
