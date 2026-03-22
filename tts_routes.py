"""
Bashi Voice Factory v3.1
A bilingual (English/Chinese) text-to-speech web interface using Microsoft Edge TTS

New in v3.1:
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

New in v2.09:
- Fixed Windows batch file encoding issue

New in v2.05:
- Added venv-based launchers for all platforms

New in v2.03:
- Voluntary donation section
- Security: local-only mode by default

New in v2.00:
- Sentence-by-sentence playback for English shadowing practice
"""

import asyncio
import os
import re
import time
import uuid
import json
import argparse
from pathlib import Path
from flask import render_template, request, jsonify, send_from_directory, Response, stream_with_context, Blueprint
import edge_tts
import imageio_ffmpeg
import subprocess

tts_bp = Blueprint("tts", __name__)

# Configuration
OUTPUT_DIR = Path("static/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Application Version — read from VERSION file for single-source-of-truth
_version_file = Path(__file__).parent / "VERSION"
VERSION = _version_file.read_text().strip() if _version_file.exists() else "3.1"

# Voices organized by language - ONLY voices available in Edge TTS
# Note: Many Azure Speech Service voices (Abbi, Alfie, Xiaochen, Xiaohan, etc.) 
# are NOT available in Edge TTS. Only the voices below are confirmed working.
VOICES = {
    "en": {
        "category": "English",
        "voices": [
            # Child voices first (marked with isChild)
            {"id": "en-US-AnaNeural", "name": "Ana (US Child)", "gender": "Female", "style": "American child voice", "isChild": True},
            {"id": "en-GB-MaisieNeural", "name": "Maisie (UK Child)", "gender": "Female", "style": "British child voice", "isChild": True},
            # American English adult voices
            {"id": "en-US-AriaNeural", "name": "Aria (US)", "gender": "Female", "style": "Natural, friendly"},
            {"id": "en-US-JennyNeural", "name": "Jenny (US)", "gender": "Female", "style": "Warm, professional"},
            {"id": "en-US-MichelleNeural", "name": "Michelle (US)", "gender": "Female", "style": "Bright, engaging"},
            {"id": "en-US-GuyNeural", "name": "Guy (US)", "gender": "Male", "style": "Clear, confident"},
            {"id": "en-US-ChristopherNeural", "name": "Christopher (US)", "gender": "Male", "style": "Deep, authoritative"},
            {"id": "en-US-EricNeural", "name": "Eric (US)", "gender": "Male", "style": "Friendly, casual"},
            {"id": "en-US-RogerNeural", "name": "Roger (US)", "gender": "Male", "style": "Narrator style"},
            {"id": "en-US-SteffanNeural", "name": "Steffan (US)", "gender": "Male", "style": "Modern, youthful"},
            # British English adult voices (Edge TTS available)
            {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "gender": "Female", "style": "British, clear"},
            {"id": "en-GB-LibbyNeural", "name": "Libby (UK)", "gender": "Female", "style": "British, warm"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (UK)", "gender": "Male", "style": "British, confident"},
            {"id": "en-GB-ThomasNeural", "name": "Thomas (UK)", "gender": "Male", "style": "British, calm"},
            # Australian English
            {"id": "en-AU-NatashaNeural", "name": "Natasha (AU)", "gender": "Female", "style": "Australian, friendly"},
            {"id": "en-AU-WilliamNeural", "name": "William (AU)", "gender": "Male", "style": "Australian, clear"},
        ]
    },
    "zh": {
        "category": "中文",
        "voices": [
            # Child voice (Edge TTS available)
            {"id": "zh-CN-YunxiaNeural", "name": "云夏 Yunxia (男孩)", "gender": "男", "style": "儿童、童声 Child boy", "isChild": True},
            # Adult voices (Edge TTS available - confirmed working)
            {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 Xiaoxiao", "gender": "女", "style": "温暖、自然"},
            {"id": "zh-CN-XiaoyiNeural", "name": "晓伊 Xiaoyi", "gender": "女", "style": "活泼、年轻"},
            {"id": "zh-CN-YunjianNeural", "name": "云健 Yunjian", "gender": "男", "style": "专业、沉稳"},
            {"id": "zh-CN-YunxiNeural", "name": "云希 Yunxi", "gender": "男", "style": "阳光、青春"},
            {"id": "zh-CN-YunyangNeural", "name": "云扬 Yunyang", "gender": "男", "style": "新闻播报"},
            # Regional/Dialect voices
            {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "晓北 Xiaobei (辽宁)", "gender": "女", "style": "东北方言 Liaoning dialect"},
            {"id": "zh-CN-shaanxi-XiaoniNeural", "name": "晓妮 Xiaoni (陕西)", "gender": "女", "style": "陕西方言 Shaanxi dialect"},
            # Hong Kong Cantonese
            {"id": "zh-HK-HiuGaaiNeural", "name": "曉佳 HiuGaai (粤语)", "gender": "女", "style": "粤语 Cantonese"},
            {"id": "zh-HK-HiuMaanNeural", "name": "曉曼 HiuMaan (粤语)", "gender": "女", "style": "粤语 Cantonese"},
            {"id": "zh-HK-WanLungNeural", "name": "雲龍 WanLung (粤语)", "gender": "男", "style": "粤语 Cantonese"},
            # Taiwan Mandarin
            {"id": "zh-TW-HsiaoChenNeural", "name": "曉臻 HsiaoChen (台湾)", "gender": "女", "style": "台湾腔 Taiwan"},
            {"id": "zh-TW-HsiaoYuNeural", "name": "曉雨 HsiaoYu (台湾)", "gender": "女", "style": "台湾腔 Taiwan"},
            {"id": "zh-TW-YunJheNeural", "name": "雲哲 YunJhe (台湾)", "gender": "男", "style": "台湾腔 Taiwan"},
        ]
    },
    "ja": {
        "category": "日本語",
        "voices": [
            {"id": "ja-JP-NanamiNeural", "name": "Nanami (七海)", "gender": "Female", "style": "Natural, warm"},
            {"id": "ja-JP-KeitaNeural", "name": "Keita (圭太)", "gender": "Male", "style": "Clear, professional"},
        ]
    },
    "hi": {
        "category": "हिन्दी",
        "voices": [
            {"id": "hi-IN-SwaraNeural", "name": "Swara (स्वरा)", "gender": "Female", "style": "Warm, natural"},
            {"id": "hi-IN-MadhurNeural", "name": "Madhur (मधुर)", "gender": "Male", "style": "Clear, confident"},
        ]
    },
    "ar": {
        "category": "العربية",
        "voices": [
            # Saudi Arabia
            {"id": "ar-SA-ZariyahNeural", "name": "Zariyah 🇸🇦", "gender": "Female", "style": "Saudi Arabic"},
            {"id": "ar-SA-HamedNeural", "name": "Hamed 🇸🇦", "gender": "Male", "style": "Saudi Arabic"},
            # Egypt
            {"id": "ar-EG-SalmaNeural", "name": "Salma 🇪🇬", "gender": "Female", "style": "Egyptian Arabic"},
            {"id": "ar-EG-ShakirNeural", "name": "Shakir 🇪🇬", "gender": "Male", "style": "Egyptian Arabic"},
        ]
    },
    "bn": {
        "category": "বাংলা",
        "voices": [
            # Bangladesh
            {"id": "bn-BD-NabanitaNeural", "name": "Nabanita 🇧🇩", "gender": "Female", "style": "Bangladeshi Bengali"},
            {"id": "bn-BD-PradeepNeural", "name": "Pradeep 🇧🇩", "gender": "Male", "style": "Bangladeshi Bengali"},
            # India
            {"id": "bn-IN-TanishaaNeural", "name": "Tanishaa 🇮🇳", "gender": "Female", "style": "Indian Bengali"},
            {"id": "bn-IN-BashkarNeural", "name": "Bashkar 🇮🇳", "gender": "Male", "style": "Indian Bengali"},
        ]
    },
    "es": {
        "category": "Español",
        "voices": [
            # Spain
            {"id": "es-ES-ElviraNeural", "name": "Elvira 🇪🇸", "gender": "Female", "style": "Castilian Spanish"},
            {"id": "es-ES-AlvaroNeural", "name": "Álvaro 🇪🇸", "gender": "Male", "style": "Castilian Spanish"},
            # Mexico
            {"id": "es-MX-DaliaNeural", "name": "Dalia 🇲🇽", "gender": "Female", "style": "Mexican Spanish"},
            {"id": "es-MX-JorgeNeural", "name": "Jorge 🇲🇽", "gender": "Male", "style": "Mexican Spanish"},
        ]
    },
    "pt": {
        "category": "Português",
        "voices": [
            # Brazil
            {"id": "pt-BR-ThalitaNeural", "name": "Thalita 🇧🇷", "gender": "Female", "style": "Brazilian Portuguese"},
            {"id": "pt-BR-AntonioNeural", "name": "Antônio 🇧🇷", "gender": "Male", "style": "Brazilian Portuguese"},
            # Portugal
            {"id": "pt-PT-FernandaNeural", "name": "Fernanda 🇵🇹", "gender": "Female", "style": "European Portuguese"},
            {"id": "pt-PT-DuarteNeural", "name": "Duarte 🇵🇹", "gender": "Male", "style": "European Portuguese"},
        ]
    },
    "fr": {
        "category": "Français",
        "voices": [
            {"id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "Female", "style": "Natural, warm"},
            {"id": "fr-FR-HenriNeural", "name": "Henri", "gender": "Male", "style": "Clear, professional"},
        ]
    },
    "ru": {
        "category": "Русский",
        "voices": [
            {"id": "ru-RU-SvetlanaNeural", "name": "Светлана (Svetlana)", "gender": "Female", "style": "Natural, warm"},
            {"id": "ru-RU-DmitryNeural", "name": "Дмитрий (Dmitry)", "gender": "Male", "style": "Clear, confident"},
        ]
    },
    "he": {
        "category": "עברית",
        "voices": [
            {"id": "he-IL-HilaNeural", "name": "הילה (Hila)", "gender": "Female", "style": "Modern Hebrew"},
            {"id": "he-IL-AvriNeural", "name": "אברי (Avri)", "gender": "Male", "style": "Modern Hebrew"},
        ]
    },
    "el": {
        "category": "Ελληνικά",
        "voices": [
            {"id": "el-GR-AthinaNeural", "name": "Αθηνά (Athina)", "gender": "Female", "style": "Modern Greek"},
            {"id": "el-GR-NestorasNeural", "name": "Νέστορας (Nestoras)", "gender": "Male", "style": "Modern Greek"},
        ]
    },
    "ko": {
        "category": "한국어",
        "voices": [
            {"id": "ko-KR-SunHiNeural", "name": "선히 (SunHi)", "gender": "Female", "style": "Natural, warm"},
            {"id": "ko-KR-InJoonNeural", "name": "인준 (InJoon)", "gender": "Male", "style": "Clear, professional"},
        ]
    },
    "de": {
        "category": "Deutsch",
        "voices": [
            {"id": "de-DE-KatjaNeural", "name": "Katja", "gender": "Female", "style": "Natural, warm"},
            {"id": "de-DE-ConradNeural", "name": "Conrad", "gender": "Male", "style": "Clear, professional"},
        ]
    },
}


def split_text_for_tts(text: str, max_chars: int = 4000) -> list:
    """Split long text into chunks at natural sentence boundaries for generation."""
    if len(text) <= max_chars:
        return [text]
        
    chunks = []
    # Try splitting at strong boundaries first
    paragraphs = text.replace('\r\n', '\n').split('\n')
    
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # Split paragraph at sentence boundaries
        sentences = re.split(r'(?<=[.!?。！？\n])', para)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # If a single sentence is super long, force split it
            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                    
                # Force split long sentence
                sub_parts = [sentence[i:i+max_chars] for i in range(0, len(sentence), max_chars)]
                for k, part in enumerate(sub_parts):
                    if k < len(sub_parts) - 1:
                        chunks.append(part.strip())
                    else:
                        current_chunk = part
            else:
                if len(current_chunk) + len(sentence) + 1 <= max_chars:
                    current_chunk += (" " if current_chunk else "") + sentence
                else:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                    
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return [c for c in chunks if c]


def merge_audio_files(input_files: list, base_filename: str) -> str:
    """Merge multiple mp3 files into one using ffmpeg."""
    if not input_files:
        return None
        
    mp3_path = OUTPUT_DIR / f"{base_filename}.mp3"
    list_path = OUTPUT_DIR / f"list_{base_filename}.txt"
    
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        
        with open(list_path, "w", encoding="utf-8") as f:
            for file in input_files:
                abs_path = (OUTPUT_DIR / file).absolute()
                safe_path = str(abs_path).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
                
        subprocess.run([
            ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path.absolute()), "-c", "copy", str(mp3_path.absolute())
        ], check=True, capture_output=True)
        
        if list_path.exists():
            list_path.unlink()
            
    except subprocess.CalledProcessError as e:
        print(f"Error merging audio files: {e}")
        if e.stderr:
            print(f"FFmpeg STDERR:\n{e.stderr.decode('utf-8', errors='ignore')}")
        return None
    except Exception as e:
        print(f"Error merging audio files: {e}")
        return None
    
    return f"{base_filename}.mp3"


def split_into_chunks(text: str, max_words: int = 0, newline_hard: bool = True) -> list:
    """
    Split text into chunks for shadowing practice.
    
    Args:
        text: Input text to split
        max_words: Maximum words per chunk (0 = no limit, use sentence boundaries only)
        newline_hard: Treat every newline as a hard boundary (best for line-by-line text); if False, single newlines inside paragraphs are ignored
    
    Returns:
        List of text chunks suitable for shadowing
    
    Features:
    - Newlines are treated as hard boundaries (section breaks)
    - Sentences are split at punctuation (.!?。！？)
    - Long sentences are further split at conjunctions if over max_words
    """
    chunks = []
    
    # Step 1: Handle newlines
    # - newline_hard=True: every newline is a boundary (best for line-by-line text)
    # - newline_hard=False: ignore single newlines inside a paragraph (better for wrapped text)
    if newline_hard:
        paragraphs = text.strip().split('\n')
    else:
        # Split by blank lines into paragraphs, then join any remaining newlines
        paragraphs = re.split(r'\n\s*\n+', text.strip())
        paragraphs = [re.sub(r'\s*\n\s*', ' ', p).strip() for p in paragraphs]

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Step 2: Split paragraph into sentences
        # Pattern matches sentences ending with global punctuation:
        # . ! ? (Latin)
        # 。 ！ ？ (CJK)
        # । (Hindi/Bengali Danda)
        # ؟ (Arabic Question)
        # ; (Greek Question)
        sentence_pattern = r'([^.!?。！？।؟;]+[.!?。！？।؟;]+)'
        sentences = re.findall(sentence_pattern, para)
        
        # Handle text without sentence-ending punctuation
        remaining = re.sub(sentence_pattern, '', para).strip()
        if remaining:
            sentences.append(remaining)
        
        # If no sentences found, use the whole paragraph
        if not sentences:
            sentences = [para]
        
        # Step 3: Process each sentence - split if too long
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence is CJK (uses chars instead of words)
            is_cjk = bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', sentence))
            
            # For CJK, max_words translates to approx 2x max_chars
            # For others, count space-separated words
            chunk_length = len(sentence) if is_cjk else len(sentence.split())
            adjusted_limit = max_words * 2 if is_cjk else max_words
            
            if max_words == 0 or chunk_length <= adjusted_limit:
                chunks.append(sentence)
            else:
                # Split long sentence into smaller chunks
                sub_chunks = split_long_sentence(sentence, adjusted_limit, is_cjk)
                chunks.extend(sub_chunks)
    
    return chunks


def split_long_sentence(sentence: str, limit: int, is_cjk: bool = False) -> list:
    """
    Split a long sentence into smaller chunks at natural break points.
    
    Priority order:
    1. Semicolon (;) or CJK comma (，、) if CJK
    2. Colon (:)
    3. Multi-language Conjunctions (and, but, y, pero, et, mais, aber, und)
    4. Regular comma (,)
    """
    chunks = []
    
    # Helper to measure length
    def measure(text):
        return len(text) if is_cjk else len(text.split())
    
    # Helper to split recursively
    def split_recursively(part):
        if measure(part) <= limit:
            return [part]
        return split_long_sentence(part, limit, is_cjk)

    # For CJK, standard commas/pauses are the best break points
    if is_cjk and re.search(r'[，、]', sentence):
        parts = re.split(r'([，、])', sentence)
        result = []
        current_chunk = ""
        for i in range(0, len(parts)-1, 2):
            part = parts[i] + parts[i+1] # string + punctuation
            if measure(current_chunk + part) <= limit and current_chunk:
                current_chunk += part
            else:
                if current_chunk: result.append(current_chunk)
                current_chunk = part
        if parts[-1]: # tail without punctuation
            if measure(current_chunk + parts[-1]) <= limit and current_chunk:
                current_chunk += parts[-1]
            else:
                if current_chunk: result.append(current_chunk)
                current_chunk = parts[-1]
        
        if current_chunk: result.append(current_chunk)
        # If it successfully broke it down, return
        if len(result) > 1: return result

    # Try splitting at semicolon
    if ';' in sentence:
        parts = [p.strip() for p in sentence.split(';') if p.strip()]
        for part in parts:
            if measure(part) <= limit:
                chunks.append(part + (';' if part != parts[-1] else ''))
            else:
                chunks.extend(split_recursively(part))
        return chunks
    
    # Try splitting at colon
    if ':' in sentence and sentence.count(':') == 1:
        parts = [p.strip() for p in sentence.split(':') if p.strip()]
        if len(parts) == 2:
            first_part = parts[0] + ':'
            chunks.extend(split_recursively(first_part))
            chunks.extend(split_recursively(parts[1]))
            return chunks
    
    # Try splitting at multi-language comma + conjunction
    conjunction_pattern = r',\s*(and|but|so|for|or|yet|y|pero|o|et|mais|ou|aber|und|oder)\s+'
    match = re.search(conjunction_pattern, sentence, re.IGNORECASE)
    if match:
        split_pos = match.start()
        first_part = sentence[:split_pos + 1].strip()
        second_part = sentence[match.end():].strip()
        
        chunks.extend(split_recursively(first_part))
        chunks.extend(split_recursively(second_part))
        return chunks
    
    # Try splitting at any comma (Latin comma)
    if ',' in sentence:
        parts = sentence.split(',')
        result = []
        current_chunk = ""
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            test_part = part + (',' if i < len(parts) - 1 else '')
            
            if not current_chunk:
                current_chunk = test_part
            elif measure(current_chunk + ' ' + test_part) <= limit:
                current_chunk += ' ' + test_part
            else:
                if current_chunk:
                    result.append(current_chunk.strip())
                current_chunk = test_part
        
        if current_chunk:
            result.append(current_chunk.strip())
        
        if len(result) > 1:
            return result
    
    # Last resort: force split
    if is_cjk:
        # Split by characters
        result = []
        for i in range(0, len(sentence), limit):
            result.append(sentence[i:i + limit])
        return result
    else:
        # Split by words
        words = sentence.split()
        result = []
        for i in range(0, len(words), limit):
            chunk = ' '.join(words[i:i + limit])
            result.append(chunk)
        return result


def split_into_sentences(text: str) -> list:
    """
    Legacy function for backward compatibility.
    Split text into sentences for sentence-by-sentence playback.
    """
    return split_into_chunks(text, max_words=0, newline_hard=True)


async def generate_speech(text: str, voice: str, rate: str = "+0%", pitch: str = "+0Hz", max_retries: int = 3) -> str:
    """Generate speech using Edge TTS and return the file path, with automatic retries."""
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = OUTPUT_DIR / filename
    
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))
            return filename
        except (OSError, ConnectionError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                print(f"Failed to generate speech after {max_retries} attempts. Last error: {e}")
                raise
            else:
                wait_time = 2 ** attempt
                print(f"Network chunk glitch detected ({e}). Retrying chunk ({attempt + 1}/{max_retries}) in {wait_time}s...")
                await asyncio.sleep(wait_time)


async def generate_sentence_audio(sentences: list, voice: str, rate: str = "+0%", pitch: str = "+0Hz", max_retries: int = 3) -> list:
    """Generate audio for each sentence separately, with automatic retries."""
    results = []
    
    for i, sentence in enumerate(sentences):
        if sentence.strip():
            filename = f"{uuid.uuid4().hex}_s{i}.mp3"
            output_path = OUTPUT_DIR / filename
            
            # Retry loop for each sentence chunk
            for attempt in range(max_retries):
                try:
                    communicate = edge_tts.Communicate(sentence, voice, rate=rate, pitch=pitch)
                    await communicate.save(str(output_path))
                    break  # Success, exit retry loop
                except (OSError, ConnectionError, asyncio.TimeoutError) as e:
                    if attempt == max_retries - 1:
                        print(f"Failed to generate sentence {i} after {max_retries} attempts. Last error: {e}")
                        raise
                    else:
                        wait_time = 2 ** attempt
                        print(f"Network glitch on sentence {i} ({e}). Retrying ({attempt + 1}/{max_retries}) in {wait_time}s...")
                        await asyncio.sleep(wait_time)
            
            results.append({
                "index": i,
                "text": sentence,
                "audio_url": f"/static/audio/{filename}",
                "filename": filename
            })
    
    return results


async def get_all_voices():
    """Fetch all available voices from Edge TTS."""
    voices = await edge_tts.list_voices()
    return voices





@tts_bp.route("/api/voices")
def get_voices():
    """Return the list of available voices."""
    return jsonify(VOICES)


@tts_bp.route("/api/all-voices")
def get_all_available_voices():
    """Return all available Edge TTS voices."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        voices = loop.run_until_complete(get_all_voices())
        return jsonify(voices)
    finally:
        loop.close()


@tts_bp.route("/api/synthesize", methods=["POST"])
def synthesize():
    """Synthesize speech from text - single audio file."""
    data = request.json
    text = data.get("text", "").strip()
    voice = data.get("voice", "en-US-AriaNeural")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")
    
    if not text:
        return jsonify({"error": "Text is required", "error_zh": "请输入文本"}), 400
    
    if len(text) > 50000:
        return jsonify({
            "error": "Text too long. Maximum 50000 characters.",
            "error_zh": "文本过长，最多50000个字符。"
        }), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        filename = loop.run_until_complete(generate_speech(text, voice, rate, pitch))
        
        return jsonify({
            "success": True,
            "audio_url": f"/static/audio/{filename}",
            "filename": filename
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "error_zh": f"合成失败: {str(e)}"
        }), 500
    finally:
        loop.close()


@tts_bp.route("/api/synthesize-long", methods=["POST"])
def synthesize_long():
    """Synthesize long speech using chunked generation and return status via SSE."""
    data = request.json
    text = data.get("text", "").strip()
    voice = data.get("voice", "en-US-AriaNeural")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")
    
    if not text:
        return jsonify({"error": "Text is required", "error_zh": "请输入文本"}), 400
        
    if len(text) > 50000:
        return jsonify({
            "error": "Text too long. Maximum 50000 characters.",
            "error_zh": "文本过长，最多50000个字符。"
        }), 400

    chunks = split_text_for_tts(text, max_chars=4000)
    total_chunks = len(chunks)
    base_filename = uuid.uuid4().hex
    
    def generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            temp_files = []
            for i, chunk in enumerate(chunks):
                # Send progress update (ensure flush)
                yield f"data: {json.dumps({'status': 'generating', 'chunk': i + 1, 'total': total_chunks})}\n\n"
                
                # Generate chunk
                chunk_filename = loop.run_until_complete(generate_speech(chunk, voice, rate, pitch))
                temp_files.append(chunk_filename)
                
            # Done generation, start merging
            yield f"data: {json.dumps({'status': 'merging'})}\n\n"
            
            mp3_name = merge_audio_files(temp_files, base_filename)
            
            # Cleanup temp chunk files
            for f in temp_files:
                try:
                    (OUTPUT_DIR / f).unlink(missing_ok=True)
                except Exception as e:
                    print(f"Failed to delete temp file {f}: {e}")
                    
            if mp3_name:
                yield f"data: {json.dumps({'status': 'done', 'audio_url_mp3': f'/static/audio/{mp3_name}', 'filename_mp3': mp3_name})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'error', 'error': 'Merging failed'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
        finally:
            loop.close()
            
    return Response(stream_with_context(generate()), content_type='text/event-stream')


@tts_bp.route("/api/synthesize-sentences", methods=["POST"])
def synthesize_sentences():
    """
    Synthesize speech chunk by chunk for language learning/shadowing.
    逐句合成语音，方便跟读练习。
    
    Parameters:
        text: The text to synthesize
        voice: Voice ID to use
        rate: Speech rate adjustment
        pitch: Pitch adjustment
        max_words: Maximum words per chunk (0 = no limit)
                   Presets: 12 (short), 15 (medium), 20 (long), 0 (off)
    """
    data = request.json
    text = data.get("text", "").strip()
    voice = data.get("voice", "en-US-AriaNeural")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")
    max_words = data.get("max_words", 15)  # Default to medium (15 words)
    newline_hard = data.get("newline_hard", True)  # Default: hard boundary (line-by-line)
    
    if not text:
        return jsonify({"error": "Text is required", "error_zh": "请输入文本"}), 400
    
    if len(text) > 5000:
        return jsonify({
            "error": "Text too long for shadowing mode. Maximum 5000 characters.",
            "error_zh": "跟读模式文本过长，最多5000个字符。"
        }), 400
    
    # Split text into chunks using smart chunking
    chunks = split_into_chunks(text, max_words=max_words, newline_hard=newline_hard)
    
    if not chunks:
        return jsonify({"error": "No text chunks found", "error_zh": "未找到文本块"}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(generate_sentence_audio(chunks, voice, rate, pitch))
        return jsonify({
            "success": True,
            "sentences": results,
            "total": len(results),
            "max_words": max_words,
            "newline_hard": newline_hard
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "error_zh": f"合成失败: {str(e)}"
        }), 500
    finally:
        loop.close()


ALLOWED_FORMATS = {"wav", "ogg", "flac"}

@tts_bp.route("/api/convert", methods=["POST"])
def convert_audio():
    """Convert an MP3 audio file to another format using ffmpeg."""
    data = request.get_json()
    if not data or "filename" not in data or "format" not in data:
        return jsonify({"error": "Missing filename or format"}), 400

    source_filename = data["filename"]
    target_format = data["format"].lower().strip()

    if target_format not in ALLOWED_FORMATS:
        return jsonify({"error": f"Unsupported format: {target_format}. Use: {', '.join(ALLOWED_FORMATS)}"}), 400

    source_path = OUTPUT_DIR / source_filename
    if not source_path.exists():
        return jsonify({"error": "Source file not found"}), 404

    # Security: ensure filename doesn't escape OUTPUT_DIR
    try:
        source_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Invalid filename"}), 400

    target_filename = source_path.stem + f".{target_format}"
    target_path = OUTPUT_DIR / target_filename

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg_exe, "-y", "-i", str(source_path.absolute()), str(target_path.absolute())],
            check=True, capture_output=True
        )
        return jsonify({"success": True, "filename": target_filename})
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg conversion error: {e}")
        if e.stderr:
            print(f"FFmpeg STDERR:\n{e.stderr.decode('utf-8', errors='ignore')}")
        return jsonify({"error": "Conversion failed"}), 500
    except Exception as e:
        print(f"Conversion error: {e}")
        return jsonify({"error": str(e)}), 500


@tts_bp.route("/api/download/<filename>")
def download_audio(filename):
    """Download the generated audio file."""
    try:
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


@tts_bp.route("/static/audio/<filename>")
def serve_audio(filename):
    """Serve audio files."""
    return send_from_directory(OUTPUT_DIR, filename)



