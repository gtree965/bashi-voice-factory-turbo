# Bashi Voice Factory (巴适声工厂)

**Version:** 3.1

A beautiful web application for bidirectional voice conversion. The **TTS** (text-to-speech) side, powered by Microsoft Edge TTS, supports **14 languages** with 50+ neural voices, up to 50,000 characters of continuous long text, TXT file upload, multi-format export, and smart chunking for shadowing practice. The **STT** (speech-to-text) side features two production-grade offline engines: **SenseVoice** (multilingual: Chinese/English/Japanese/Korean/Cantonese) and **Parakeet TDT** (English specialist, NVIDIA, ~1.7% WER). All transcription runs locally — no audio is uploaded to the cloud.

**Author:** Alex Li (ncorecpu@gmail.com)

**License:** [MIT License](LICENSE)

---

## ✨ Highlight Features

### 🎙️ Local Offline Speech-to-Text (v3.1)
- **High Privacy**: Convert meetings, lectures, and videos to text entirely on your local machine. No audio data is uploaded to the cloud!
- **Dual Engine**: **SenseVoice** (default, multilingual zh/en/ja/ko/yue, 242MB) + **Parakeet TDT** (English specialist, 661MB, NVIDIA). Both powered by the lightweight `sherpa-onnx` runtime.
- **VAD-Based Segmentation**: Silero VAD precisely detects speech boundaries — zero overlap, zero stutter, accurate timestamps.
- **Live Progress**: Features real-time subtitle-by-subtitle display using SSE (Server-Sent Events) and exports seamlessly to TXT, SRT, or VTT.

### 🌍 14-Language World Voice Expansion (v2.16)
- **Global Coverage**: English, Chinese, Japanese, Korean, Hindi, Arabic, Bengali, Spanish, Portuguese, French, German, Russian, Hebrew, and Greek — with region-specific variants (US/UK/AU, Saudi/Egypt, Brazil/Portugal, etc.).
- **Smart Demo Texts**: Quick-text buttons dynamically switch to the active language's demo sentences.

### 📂 TXT File Upload & Multi-Format Export (v2.16)
- **Drag & Drop**: Drop any `.txt` file onto the text area to instantly load its content.
- **Smart Encoding Detection**: Auto-detects UTF-8, GBK/GB2312, Shift-JIS, EUC-KR, Windows-1251/1252/1253/1256, and ISO-8859-1.
- **Multi-Format Export**: Download generated audio in **MP3, WAV, OGG, or FLAC** format (converted via FFmpeg).
- **Speed Range Extended**: Rate slider expanded from ±50% to **±200%** for extreme speed control.

### 🛡️ Smart Network Auto-Retry (v2.15)
- **Loss-Resistant Architecture**: Upgraded the core backend engine with an exponential backoff loop to aggressively maintain connections against unstable Wi-Fi routers and heavy packet losses.
- **Flawless Chunk Recovery**: If a massive synthesis job disconnects mid-way, the engine intuitively resends only that specific failed slice to Microsoft, entirely eliminating the frustration of starting an enormous essay over because of a momentary network glitch.

### 🚀 Zero-Install USB Portable Edition (v2.14)
- **Drive-Ready**: The entire backend app and embedded Python environment exist singularly in one folder. Run it on any locked-down Windows PC directly from a USB flash drive.
- **Isolated Sandbox**: Bootstraps necessary components locally on first launch, permitting swift, plug-and-play executions afterward without polluting system paths.

### 📱 1-Click LAN Sharing & Mobile Access (v2.13)
- **Auto-Routing**: Startup terminal provides a 10-second prompt to dynamically unveil your computer's exact LAN IP address, ignoring VPN noise.
- **Mobile Companion**: Type the URL into your phone/tablet browser on the same Wi-Fi. 100% secure offline router transmission (feel free to bypass the browser's "Not Secure" warning for local IPs).

### 📄 50,000-Character Long Text Engine (v2.12)
- **Massive Capacity**: Convert up to **50,000 characters** (essay-length) in a single massive job.
- **Auto-Chunking UI**: Seamlessly splices audio segments in the background, complemented by a real-time responsive progress bar to eliminate loading anxiety.

## ⭐️ Core Practical Features

### 📝 Smart Chunking for Shadowing
Perfect for English/Chinese shadowing practice!

- **Automatic text splitting** into short, repeatable chunks
- **Adjustable chunk size**: Short (12 words) / Medium (15) / Long (20) / Off
- **Line breaks** create section boundaries - paste one line per section for best results
- **Visual progress tracking** with play/pause/reset controls
- **Adjustable pause** between chunks (0.5s - 5s)

### 🎙️ High-Quality Voices
- **14 languages** with 50+ neural voices total
- English: 16 voices (American, British, Australian) including child voices
- Chinese: 14 voices (Mandarin, Cantonese, Taiwan, Shaanxi, Liaoning) including child voices
- Japanese, Korean, Hindi, Arabic, Bengali, Spanish, Portuguese, French, German, Russian, Hebrew, Greek

### 🎚️ Voice Controls
- Adjustable speech rate (-200% to +200%)
- Adjustable pitch (-50Hz to +50Hz)

---

## Requirements

- **Windows 10/11**, **macOS**, or **Linux**
- **Internet connection** (required for Microsoft Edge TTS)

---

## 🚀 Easy Start

We have provided strictly zero-install, automated launchers for Windows, macOS, and Linux.

### Windows Users (Zero-Install Portable)
1. Extract the downloaded `edge-tts-app` folder to your Desktop or desired location.
2. Enter the folder and double-click: **`run_portable.bat`**
3. *(Note: First-time execution requires an internet connection; the script will securely bootstrap all dependencies locally)*.
4. Follow the minimal on-screen prompts (e.g., choosing whether to allow LAN network sharing).
5. Open your browser and navigate to **http://127.0.0.1:5050** (or the LAN IP shown on screen).
6. To stop the server: press **Ctrl + C** in the black command window.

### 🍎 macOS Users (Native Double-Click Edition)

To ensure the native macOS execution permissions are preserved, please distribute the `.tar.gz` archive directly to Mac users (DO NOT extract the folder on Windows and copy it over an exFAT USB drive).

1. Double-click the `Bashi-Voice-Factory-v3.1-Mac-Linux.tar.gz` file on your Mac to extract it.
2. Open the extracted folder and simply double-click **`Bashi-Voice-Factory-Mac.command`**.
3. If macOS blocks the app with an "Unidentified Developer" warning: Go to `System Settings -> Privacy & Security`, scroll down, and click `Open Anyway`.

### 🐧 Linux Users

1. Extract the `Bashi-Voice-Factory-v3.1-Mac-Linux.tar.gz` archive.
2. Open your terminal, navigate directly into the extracted directory, and run `./run_venv.sh` (all executable `chmod +x` flags are already permanently baked into the archive!).

---

## How to Use

1. **Select Playback Mode:**
   - "Single Audio" for full text playback
   - "Shadowing Chunks" for practice with short segments

2. **Enter your text** or use a demo button

3. **Choose chunk size** (for Shadowing mode):
   - Short (12 words) - for beginners/kids
   - Medium (15 words) - recommended default
   - Long (20 words) - for intermediate learners
   - Off - no chunking, sentence boundaries only

4. **Select a voice** from the grid

5. **Adjust settings** (optional): speed, pitch, pause between chunks

6. **Click "Generate Chunks"** and practice!

### Tips for Best Results

- Paste one sentence or section per line for best results
- The app treats line breaks as section boundaries
- Use "Medium" chunk size for most texts

### 🎙️ Speech-to-Text (STT)

1. **Switch to the STT tab** using the tab bar at the top of the page.
2. **First-time setup**: If the ASR model has not been downloaded yet, select it from the model dropdown and click "Download". The ~244 MB SenseVoice model will be saved locally for all future use.
3. **Upload a file**: Click the upload zone or drag and drop an audio/video file (MP3, MP4, WAV, M4A, OGG, FLAC, MKV, etc.).
4. **Choose a language** (optional): Default is "Auto Detect". You can manually select Chinese, English, Japanese, Korean, or Cantonese for better accuracy.
5. **Click "Transcribe"**: A real-time progress bar and live subtitle segments will appear as the engine processes the audio.
6. **Review results**: The full transcript appears in the result text area. Use "Copy All" to copy to clipboard.
7. **Export**: Choose TXT, SRT, or VTT format from the dropdown and click "Export" to download.

---

## Troubleshooting

### "Port 5050 is already in use"
Edit `app.py`, change `port=5050` to another port like `port=5001`

### No sound generated
- Check your internet connection (Edge TTS requires internet)
- Make sure the text is not empty



---

## 🔄 Changelog

### v3.1 (2026-03-22)
- 🎯 **Dual-Engine STT**: Streamlined to two production-grade models — **SenseVoice** (multilingual default: zh/en/ja/ko/yue, 242MB) and **Parakeet TDT** (English specialist by NVIDIA, ~1.7% WER, 661MB).
- 🔧 **SenseVoice VAD Rewrite**: Replaced 30s chunk-based processing with Silero VAD segmentation. Eliminated all overlap/stutter artifacts, CER improved from 8.9% to 2.1% on Chinese.
- 🦜 **Parakeet TDT Tuning**: Modified beam search (4 paths) and VAD threshold tuning for optimal English subtitle quality.
- 🧹 **Model Cleanup**: Removed experimental models (Paraformer, Zipformer-CTC, FireRedASR) after comprehensive benchmarking.

### v3.0 (2026-03-17)
- ✨ **Local Offline Speech-to-Text (STT)**: Completely private, fully local audio/video transcription using `sherpa-onnx` and `SenseVoiceSmall`.
- 📁 **Universal Media Import**: Drag and drop MP4, MP3, WAV, M4A, OGG, or FLAC files directly for transcription.
- ⚡ **Real-time Streaming**: Enjoy live, scrolling segment updates during transcription, paired with a progress bar and status indicator.
- 📑 **Subtitle Export**: Export your transcriptions cleanly into structured formats: TXT, SRT, or VTT.

### v2.16 (2026-03-05)
- 🌍 **14-Language World Voice Expansion**: Added Japanese, Korean, Hindi, Arabic (Saudi/Egypt), Bengali (Bangladesh/India), Spanish (Spain/Mexico), Portuguese (Brazil/Portugal), French, German, Russian, Hebrew, and Greek — with region-specific neural voices.
- 📂 **TXT File Drag & Drop Upload**: Load text directly from `.txt` files via drag-and-drop or file picker, with automatic encoding detection (UTF-8, GBK, Shift-JIS, EUC-KR, Windows-1251/1252/1253/1256).
- 🎵 **Multi-Format Audio Export**: Download in MP3, WAV, OGG, or FLAC (converted via FFmpeg/imageio-ffmpeg).
- ⚡ **Speed Slider ±200%**: Extended rate control from ±50% to ±200% for extreme speed adjustments.
- 🌐 **Dynamic Demo Texts**: Quick-text buttons automatically switch to demo sentences in the active language.

### v2.15 (2026-03-04)
- 🛡️ **Smart Network Auto-Retry**: Exponential backoff (up to 3 retries per chunk) for resilient long-text generation over unstable networks.
- 🔧 **macOS Port Fix**: Migrated default port from 5000 to 5050 to avoid AirPlay Receiver conflict.
- 🐧 **Linux Auto-Recovery**: Auto-detection and fix for broken `python3-venv`/`ensurepip` on Debian/Mint.

### v2.14 (2026-02-28)
- 🚀 **Zero-Install USB Portable Edition**: Introduced `run_portable.bat` explicitly built to synergize with the official Python Embeddable package. Allows copying the entire application to a USB drive and running it instantly on *any* Windows computer without admin privileges or system Python installations.
- 🔧 **Intelligent Bootstrapping**: The script bypasses restrictions by patching the `.pth` configuration via PowerShell, pulling `pip`, and installing runtime dependencies strictly into the portable folder.

### v2.13 (2026-02-27)
- 📱 **1-Click LAN Sharing**: All startup scripts now dynamically prompt for a 10-second (Y/N) decision to globally unlock local network connectivity.
- 🔧 **VPN Virtual Adapter Bypass**: Windows PowerShell dynamically filters for physical networking cards with valid gateways to prevent incorrect VPN IPs from being captured in LAN links.
- 📑 **HTTPS Safety Warning**: Included instructional messages on how to securely bypass "Not Secure" pop-ups seen on Android/iOS browsers when accessing local environments.

### v2.12 (2026-02-26)
- ✨ **Long Text Support**: Increased standard generation limit from 5,000 to **50,000 characters**.
- 🔄 **Chunked Backend API**: Text exceeding 4,000 characters is automatically split, streamed (via SSE), and smoothly merged.
- ⏳ **Live Progress**: Added a real-time progress bar for long generation jobs to improve UX.

### v2.11 (2026-01-19)
- ✨ Added **Line Breaks** option for Shadowing Chunks: **Line** (split at every newline) vs **Paragraph** (ignore wrapped line breaks).
- 🔧 Backend now supports `newline_hard` parameter to improve chunking for wrapped text (e.g. web/email copy-paste).

### v2.10 (2026-01-19)
- ✨ Added smart chunking for shadowing (max words per chunk)
- ✨ Newline now treated as hard boundary
- ✨ Chunking presets: Short (12) / Medium (15) / Long (20) / Off
- 🔧 Fixed pause/continue toggle button
- 📝 Separate README files: English and Chinese

### v2.09 (2026-01-11)
- 🔧 Fixed Windows batch file encoding issue

### v2.05 (2026-01-11)
- ✨ Added venv-based launchers for all platforms

### v2.00 (2026-01-07)
- ✨ Sentence-by-sentence playback for English shadowing practice
- ✨ Child voices for English and Chinese

---

## 💡 FAQ

**Q: If I run the server on my Wi-Fi, what happens if 2 or 3 devices use the text-to-speech or shadowing feature at the exact same time? Will the audio get mixed up?**

**A:** The experience will be completely seamless, and it will **NOT mix up or interfere at all**!
1. **Isolated Requests (UUIDs)**: Every time a device submits text to be synthesized, the Bashi Voice Factory backend generates a unique file name (e.g., `tts_8f1a...mp3`). Therefore, multiple devices can tap "Generate" simultaneously, and the system will safely merge and return the correct independent audio to each respective device.
2. **Concurrent Multi-threading**: The underlying Flask server operates in a multi-threaded mode by default. Even if a tablet is spending 30 seconds generating a massive 50,000-character article, another phone can instantly submit and receive a short 20-word sentence immediately without being blocked or queued.
3. **Virtually Zero Hardware Cost**: Because the actual heavy-lifting AI voice synthesis is handled exclusively by Microsoft's cloud servers, your local computer simply acts as a router/merger. Using an old laptop to comfortably serve 3-5 concurrent home devices requires virtually zero CPU power. Feel free to fully share it with your family!

---

## ⚖️ License

This project is open-sourced under the **[MIT License](LICENSE)**.

Edge TTS is a product of Microsoft.

---

## 📜 Secondary Development & Attribution

This project was developed with dedication by Alex Li (ncorecpu@gmail.com) to provide maximum convenience for educators and free users worldwide.

This project is licensed under the **MIT License**. You are completely free to use, copy, modify, or integrate this codebase into your own projects. However, as a basic respect for the open-source spirit and the developer's intellectual labor, **if you use the core codebase of this project (such as our portable environment isolation scripts, or the smart chunking long-text synthesis logic), we strongly require you to:**

> Explicitly credit the original author, **Alex Li (ncorecpu@gmail.com)**, in your software's homepage, documentation (README), or "About" page.

Respecting originality makes the open-source community a better place!

---

## ⚖️ Legal Disclaimer & Compliance

To avoid potential copyright and intellectual property disputes, all users and secondary developers must be fully aware of the following terms:

1. **Codebase License vs. Backend Service**: The client-side source code of this application (Python scripts, UI files, etc.) is open-sourced under the **MIT License**, which inherently permits commercial use of the code. However, you must understand that this application integrates third-party engines and models whose licenses are independent of the MIT License on this codebase.
2. **Microsoft's Intellectual Property (TTS)**: The text-to-speech AI engine, the synthetic neural voice models (Neural Voices), and the cloud computing endpoints are the exclusive intellectual property of **Microsoft Corporation**. Whether the audio generated through this interface can be legally deployed for commercial or for-profit projects is strictly governed by [Microsoft's Terms of Use](https://www.microsoft.com/en-us/legal/terms-of-use).
3. **Alibaba SenseVoice Model License (STT)**: The multilingual speech-to-text engine relies on the `SenseVoiceSmall` model released by Alibaba DAMO Academy under the [FunASR Model License](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE). This is **not** an Apache/MIT license — it is a custom model license that permits use (including commercial use) under specific conditions. Users who intend to use the STT-derived output commercially must review and comply with the FunASR Model License terms.
4. **NVIDIA Parakeet TDT Model License (STT)**: The English-specialist speech-to-text engine uses NVIDIA's `Parakeet TDT 0.6B v2` model, released under the [CC-BY-4.0 License](https://creativecommons.org/licenses/by/4.0/). This permits commercial use with attribution. The sherpa-onnx conversion is provided by [csukuangfj](https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8). The `sherpa-onnx` inference runtime is licensed under [Apache 2.0](https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE).
5. **Content Copyright & Operator Liability**: This software acts as a conduit — for TTS, it transmits text to Microsoft's API; for STT, it processes audio locally. The developer does not collect, monitor, nor possess the capability to police your inputs or outputs. If a user processes copyrighted materials (e.g., unauthorized audiobooks, premium articles, copyrighted recordings), the user assumes full legal responsibility. The software and its original author (Alex Li) disclaim all liability for content generated, transcribed, distributed, or monetized by its users.

Edge TTS is a product of Microsoft. SenseVoice is a product of Alibaba DAMO Academy. Parakeet TDT is a product of NVIDIA.

---

## Author

**Alex Li**
Email: ncorecpu@gmail.com

---

## Credits

- Microsoft Edge TTS for the amazing neural voices
- [edge-tts](https://github.com/rany2/edge-tts) Python library by rany2
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) by the Next-gen Kaldi team for the offline STT runtime
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) by Alibaba DAMO Academy for the multilingual speech recognition model
- [Parakeet TDT](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) by NVIDIA for the English speech recognition model
- Flask for the web framework
- The open-source community

---

## Support the Developer

Made with ❤️ by Alex Li for educators and learners worldwide.

All features are free. If you find this tool useful, consider buying the developer a coffee!

WeChat Pay and Alipay QR codes are available in the app.