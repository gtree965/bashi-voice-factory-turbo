#!/usr/bin/env python3
"""
Microsoft Edge TTS readback benchmark for Chinese text normalization.

Purpose:
    Use the current Microsoft Edge TTS backend plus local SenseVoice STT
    as a practical readback loop:

        input text -> Edge TTS audio -> SenseVoice transcript

This helps us identify Chinese text patterns that Microsoft TTS does
not read naturally enough, so we can selectively adopt small,
repo-local patch rules for Bashi Voice Factory's Chinese TTS input.

Modes:
    - raw:   synthesize the original text
    - patch: synthesize text after local zh_tts_patch preprocessing

Outputs:
    - MP3 audio files for manual listening
    - JSON report with transcripts and rough CER against expected spoken text
    - Markdown summary for quick inspection

Usage:
    python test_tts_readback.py
    python test_tts_readback.py --voice zh-CN-XiaoxiaoNeural --limit 4
    python test_tts_readback.py --category classical_ref --keep-wav
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engines.sherpa_sensevoice import SherpaSenseVoiceEngine
from utils import extract_audio_wav
from zh_tts_patch import normalize_chinese_tts_text, TtsPatchOptions


MODELS_DIR = ROOT_DIR / "models"
SENSEVOICE_MODEL_DIR = MODELS_DIR / "sensevoice-small-int8"
OUTPUT_ROOT = ROOT_DIR / "tts_readback_outputs"


@dataclass(frozen=True)
class ReadbackCase:
    id: str
    category: str
    text: str
    expected_spoken: str
    notes: str = ""


@dataclass
class ModeResult:
    synthesized_text: str
    transcript: str
    cer: Optional[float]
    mp3_path: str
    wav_path: Optional[str]
    reused_from_raw: bool = False


@dataclass
class CaseResult:
    case_id: str
    category: str
    text: str
    expected_spoken: str
    notes: str
    raw: ModeResult
    patch: ModeResult
    preferred_mode: str


TEST_CASES = [
    ReadbackCase(
        id="classical_basic",
        category="classical_ref",
        text="请翻到古书1:1。",
        expected_spoken="请翻到古书第一章第一节",
        notes="核心场景：章节号不应按一比一/一点一读。",
    ),
    ReadbackCase(
        id="classical_range",
        category="classical_ref",
        text="今天读诗23:1-6。",
        expected_spoken="今天读诗第二十三篇第一节至第六节",
        notes="篇体作品应读篇，范围应读至。",
    ),
    ReadbackCase(
        id="classical_cross",
        category="classical_ref",
        text="请参考古书1:31-2:3。",
        expected_spoken="请参考古书第一章第三十一节至第二章第三节",
        notes="跨章范围是章节引用 patch 的高价值场景。",
    ),
    ReadbackCase(
        id="phone_mobile",
        category="phone",
        text="请联系张老师，电话138-1234-5678。",
        expected_spoken="请联系张老师电话一三八 一二三四 五六七八",
        notes="手机号应该稳定逐位/分组朗读。",
    ),
    ReadbackCase(
        id="phone_service",
        category="phone",
        text="有问题请拨打12345。",
        expected_spoken="有问题请拨打一二三四五",
        notes="服务短号应逐位读，不要读成一万两千三百四十五。",
    ),
    ReadbackCase(
        id="filepath_windows",
        category="filepath",
        text="文件在C:\\Users\\Alex\\Documents\\bible.txt。",
        expected_spoken="文件在bible txt",
        notes="路径场景更关注不要逐字符念整条路径。",
    ),
    ReadbackCase(
        id="url_basic",
        category="url",
        text="请访问https://www.example.com/classics。",
        expected_spoken="请访问example.com",
        notes="URL 场景更关注域名层级，而不是逐字符朗读。",
    ),
    ReadbackCase(
        id="date_plain",
        category="number_date",
        text="2024年12月25日是圣诞节。",
        expected_spoken="二零二四年十二月二十五日是圣诞节",
        notes="普通日期是观察项，未必需要 patch。",
    ),
    ReadbackCase(
        id="time_plain",
        category="number_date",
        text="下午3:30开会。",
        expected_spoken="下午三点三十分开会",
        notes="时间不应被误处理成章节引用。",
    ),
    ReadbackCase(
        id="mixed_room",
        category="mixed",
        text="请到A302教室上课。",
        expected_spoken="请到A三零二教室上课",
        notes="教室号是观察项，先看微软原生表现。",
    ),
    ReadbackCase(
        id="mixed_version",
        category="mixed",
        text="请安装Python 3.11版本。",
        expected_spoken="请安装Python三点一一版本",
        notes="版本号是观察项，先看原生读法是否可接受。",
    ),
]


def strip_punct_spaces(text: str) -> str:
    """Remove punctuation and whitespace for rough CER comparison."""
    return re.sub(r"[\s\.,!?;:，。！？；：、\-—–'\"()\[\]（）【】「」《》\u200b]", "", text.lower())


def character_error_rate(ref: str, hyp: str) -> Optional[float]:
    ref_clean = strip_punct_spaces(ref)
    hyp_clean = strip_punct_spaces(hyp)

    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0

    n, m = len(ref_clean), len(hyp_clean)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            temp = dp[j]
            if ref_clean[i - 1] == hyp_clean[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp

    return round(dp[m] / n, 4)


def select_cases(category: Optional[str], limit: Optional[int]) -> list[ReadbackCase]:
    cases = TEST_CASES
    if category:
        cases = [case for case in cases if case.category == category]
    if limit is not None:
        cases = cases[:limit]
    return cases


async def synthesize_to_mp3(text: str, output_path: Path, voice: str, rate: str, pitch: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))


def transcribe_audio(engine: SherpaSenseVoiceEngine, input_audio: Path, wav_path: Path) -> str:
    extract_audio_wav(input_audio, wav_path)
    segments = list(engine.transcribe_stream(wav_path, language="zh"))
    return " ".join(seg.text for seg in segments if seg.text.strip()).strip()


def normalize_patch_text(text: str) -> str:
    options = TtsPatchOptions(
        enable_classical_ref=True,
        enable_phone=True,
        enable_filepath=True,
        enable_punctuation_cleanup=True,
    )
    return normalize_chinese_tts_text(text, options=options)


def choose_preferred_mode(raw_cer: Optional[float], patch_cer: Optional[float]) -> str:
    if raw_cer is None and patch_cer is None:
        return "manual"
    if raw_cer is None:
        return "patch"
    if patch_cer is None:
        return "raw"
    if patch_cer < raw_cer:
        return "patch"
    if raw_cer < patch_cer:
        return "raw"
    return "tie"


def write_markdown_report(report_path: Path, results: list[CaseResult], voice: str, elapsed_sec: float) -> None:
    lines = [
        "# Edge TTS Readback Report",
        "",
        f"- Voice: `{voice}`",
        f"- Cases: `{len(results)}`",
        f"- Elapsed: `{elapsed_sec:.1f}s`",
        "",
        "| Case | Category | Preferred | Raw CER | Patch CER |",
        "| --- | --- | --- | ---: | ---: |",
    ]

    for result in results:
        raw_cer = "-" if result.raw.cer is None else f"{result.raw.cer:.3f}"
        patch_cer = "-" if result.patch.cer is None else f"{result.patch.cer:.3f}"
        lines.append(
            f"| {result.case_id} | {result.category} | {result.preferred_mode} | {raw_cer} | {patch_cer} |"
        )

    lines.append("")
    for result in results:
        lines.extend([
            f"## {result.case_id}",
            "",
            f"- Category: `{result.category}`",
            f"- Notes: {result.notes or 'n/a'}",
            f"- Original: `{result.text}`",
            f"- Expected spoken: `{result.expected_spoken}`",
            f"- Raw synthesized: `{result.raw.synthesized_text}`",
            f"- Raw transcript: `{result.raw.transcript}`",
            f"- Raw CER: `{result.raw.cer}`",
            f"- Patch synthesized: `{result.patch.synthesized_text}`",
            f"- Patch transcript: `{result.patch.transcript}`",
            f"- Patch CER: `{result.patch.cer}`",
            "",
        ])

    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edge TTS Chinese readback benchmark")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="Edge TTS voice")
    parser.add_argument("--rate", default="+0%", help="Edge TTS rate")
    parser.add_argument("--pitch", default="+0Hz", help="Edge TTS pitch")
    parser.add_argument(
        "--category",
        choices=sorted({case.category for case in TEST_CASES}),
        help="Run only one category",
    )
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases")
    parser.add_argument("--keep-wav", action="store_true", help="Keep extracted WAV files")
    parser.add_argument("--output-dir", help="Optional output directory")
    return parser.parse_args()


def ensure_prerequisites() -> None:
    if not SENSEVOICE_MODEL_DIR.exists():
        raise FileNotFoundError(
            f"SenseVoice model not found at {SENSEVOICE_MODEL_DIR}. "
            "Please download sensevoice-small-int8 first."
        )


def build_output_dir(custom_output_dir: Optional[str]) -> Path:
    if custom_output_dir:
        output_dir = Path(custom_output_dir)
    else:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        output_dir = OUTPUT_ROOT / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def run_benchmark(args: argparse.Namespace) -> list[CaseResult]:
    ensure_prerequisites()
    selected_cases = select_cases(args.category, args.limit)
    if not selected_cases:
        raise ValueError("No test cases selected.")

    output_dir = build_output_dir(args.output_dir)
    print(f"[readback] Output directory: {output_dir}")
    print(f"[readback] Loading SenseVoice from {SENSEVOICE_MODEL_DIR}")

    engine = SherpaSenseVoiceEngine(SENSEVOICE_MODEL_DIR)
    engine.load_model()

    results = []
    started = time.perf_counter()

    for idx, case in enumerate(selected_cases, 1):
        print(f"[readback] ({idx}/{len(selected_cases)}) {case.id}: {case.text}")
        raw_text = case.text
        patch_text = normalize_patch_text(case.text)

        raw_mp3 = output_dir / f"{case.id}_raw.mp3"
        raw_wav = output_dir / f"{case.id}_raw.wav"

        asyncio.run(synthesize_to_mp3(raw_text, raw_mp3, args.voice, args.rate, args.pitch))
        raw_transcript = transcribe_audio(engine, raw_mp3, raw_wav)
        raw_cer = character_error_rate(case.expected_spoken, raw_transcript)

        if patch_text == raw_text:
            patch_result = ModeResult(
                synthesized_text=patch_text,
                transcript=raw_transcript,
                cer=raw_cer,
                mp3_path=str(raw_mp3),
                wav_path=str(raw_wav) if args.keep_wav else None,
                reused_from_raw=True,
            )
        else:
            patch_mp3 = output_dir / f"{case.id}_patch.mp3"
            patch_wav = output_dir / f"{case.id}_patch.wav"
            asyncio.run(synthesize_to_mp3(patch_text, patch_mp3, args.voice, args.rate, args.pitch))
            patch_transcript = transcribe_audio(engine, patch_mp3, patch_wav)
            patch_cer = character_error_rate(case.expected_spoken, patch_transcript)
            patch_result = ModeResult(
                synthesized_text=patch_text,
                transcript=patch_transcript,
                cer=patch_cer,
                mp3_path=str(patch_mp3),
                wav_path=str(patch_wav) if args.keep_wav else None,
                reused_from_raw=False,
            )
            if not args.keep_wav and patch_wav.exists():
                patch_wav.unlink(missing_ok=True)

        raw_result = ModeResult(
            synthesized_text=raw_text,
            transcript=raw_transcript,
            cer=raw_cer,
            mp3_path=str(raw_mp3),
            wav_path=str(raw_wav) if args.keep_wav else None,
            reused_from_raw=False,
        )

        preferred = choose_preferred_mode(raw_result.cer, patch_result.cer)
        results.append(
            CaseResult(
                case_id=case.id,
                category=case.category,
                text=case.text,
                expected_spoken=case.expected_spoken,
                notes=case.notes,
                raw=raw_result,
                patch=patch_result,
                preferred_mode=preferred,
            )
        )

        if not args.keep_wav and raw_wav.exists():
            raw_wav.unlink(missing_ok=True)

    elapsed = time.perf_counter() - started
    json_path = output_dir / "report.json"
    md_path = output_dir / "report.md"
    payload = {
        "voice": args.voice,
        "rate": args.rate,
        "pitch": args.pitch,
        "elapsed_seconds": round(elapsed, 3),
        "results": [asdict(result) for result in results],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(md_path, results, args.voice, elapsed)

    print(f"[readback] Done in {elapsed:.1f}s")
    print(f"[readback] JSON report: {json_path}")
    print(f"[readback] Markdown report: {md_path}")
    return results


def main() -> int:
    args = parse_args()
    run_benchmark(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
