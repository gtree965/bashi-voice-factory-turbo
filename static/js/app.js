/**
 * Bashi Voice Factory v3.1 - JavaScript Application
 * Bilingual (English/Chinese) text-to-speech interface
 * NEW: 14 languages, TXT upload, multi-format export, ±200% speed
 */

// State Management
const state = {
    currentAppTab: 'tts', // 'tts' or 'stt'
    sttModels: [],
    selectedSttModel: '',
    sttFile: null,
    sttJobId: null,
    currentLang: 'en',
    selectedVoice: 'en-US-AriaNeural',
    selectedCategory: 'en',
    voices: null,
    currentAudioUrl: null,
    // Sentence playback state
    playbackMode: 'single', // 'single' or 'sentence'
    sentences: [],
    currentSentenceIndex: 0,
    isPlaying: false,
    isPaused: false,  // NEW: track paused state for toggle
    pauseDuration: 2, // seconds between sentences
    // NEW: Chunking settings
    chunkingEnabled: true,
    maxWords: 15,  // Default: Medium (15 words)
    newlineHard: true  // treat every newline as a boundary (line-by-line mode)
};

// DOM Elements
const elements = {
    textInput: document.getElementById('text-input'),
    voiceGrid: document.getElementById('voice-grid'),
    generateBtn: document.getElementById('generate-btn'),
    generateBtnText: document.getElementById('generate-btn-text'),
    loading: document.getElementById('loading'),
    playerSection: document.getElementById('player-section'),
    audioPlayer: document.getElementById('audio-player'),
    downloadBtn: document.getElementById('download-btn'),
    rateSlider: document.getElementById('rate-slider'),
    pitchSlider: document.getElementById('pitch-slider'),
    pauseSlider: document.getElementById('pause-slider'),
    rateValue: document.getElementById('rate-value'),
    pitchValue: document.getElementById('pitch-value'),
    pauseValue: document.getElementById('pause-value'),
    charCount: document.querySelector('.char-count'),
    toast: document.getElementById('toast'),
    // Sentence playback elements
    sentencePlayerSection: document.getElementById('sentence-player-section'),
    sentenceList: document.getElementById('sentence-list'),
    sentenceAudio: document.getElementById('sentence-audio'),
    progressFill: document.getElementById('progress-fill'),
    sentenceProgress: document.getElementById('sentence-progress'),
    pauseSetting: document.getElementById('pause-setting'),
    modeHint: document.getElementById('mode-hint'),
    fileInput: document.getElementById('file-input'),
    uploadBtn: document.getElementById('upload-btn'),
    dropZone: document.getElementById('drop-zone'),
    formatSelect: document.getElementById('format-select'),
    // App Tabs
    ttsContainer: document.getElementById('tts-container'),
    sttContainer: document.getElementById('stt-container'),
    // STT Elements
    sttFileInput: document.getElementById('stt-file-input'),
    sttUploadZone: document.getElementById('stt-upload-zone'),
    sttSelectedFile: document.getElementById('stt-selected-file'),
    sttFilenameDisplay: document.getElementById('stt-filename-display'),
    sttModelSelect: document.getElementById('stt-model-select'),
    sttDownloadBtn: document.getElementById('stt-download-btn'),
    sttModelProgress: document.getElementById('stt-model-progress'),
    sttTranscribeBtn: document.getElementById('stt-transcribe-btn'),
    sttLangSelect: document.getElementById('stt-lang-select'),
    sttJobProgress: document.getElementById('stt-job-progress'),
    sttLiveSegments: document.getElementById('stt-live-segments'),
    sttResultSection: document.getElementById('stt-result-section'),
    sttResultText: document.getElementById('stt-result-text'),
};

// Demo texts for each language category
// Texts are chosen to produce 4-6 chunks in shadowing mode (Medium preset),
// and to clearly show different chunk counts across Short / Medium / Long presets.
const DEMO_TEXTS = {
    en: [
        { text: 'Hello! Welcome to Bashi Voice Factory. In shadowing mode, your text is split into short chunks for easy repetition. Each chunk plays one by one, and you can repeat any chunk by clicking on it.', en: 'English Demo', zh: '英文示例' },
    ],
    zh: [
        { text: '你好！欢迎使用巴适声工厂。在跟读模式下，文本会被自动切分成短小片段，每个片段播放后会自动暂停，你可以随时重复任何片段来练习发音。', en: 'Chinese Demo', zh: '中文示例' },
    ],
    ja: [
        { text: 'こんにちは！Bashi Voice Factoryへようこそ。高品質なテキスト読み上げのデモンストレーションです。', en: 'Japanese Demo', zh: '日语示例' },
    ],
    hi: [
        { text: 'नमस्ते! Bashi Voice Factory में आपका स्वागत है। यह उच्च गुणवत्ता वाले टेक्स्ट टू स्पीच का प्रदर्शन है। कोई भी आवाज़ चुनें, और बेहतरीन ध्वनि के लिए गति और स्वर को समायोजित करें।', en: 'Hindi Demo', zh: '印地语示例' },
    ],
    ar: [
        { text: 'مرحباً! أهلاً بك في Bashi Voice Factory. هذا عرض توضيحي لتحويل النص إلى كلام عالي الجودة. اختر أي صوت بسهولة, وقم بضبط السرعة والنبرة للعثور على الإعدادات المثالية لك.', en: 'Arabic Demo', zh: '阿拉伯语示例' },
    ],
    bn: [
        { text: 'নমস্কার! Bashi Voice Factory-তে আপনাকে স্বাগতম। এটি উচ্চমানের টেক্সট টু স্পিচ এর একটি প্রদর্শন। যেকোনো কণ্ঠস্বর বেছে নিন, এবং নিখুঁত ফলাফলের জন্য গতি এবং পিচ সামঞ্জস্য করুন।', en: 'Bengali Demo', zh: '孟加拉语示例' },
    ],
    es: [
        { text: '¡Hola! Bienvenido a Bashi Voice Factory. Esta es una demostración de síntesis de voz de alta calidad. Selecciona una voz, y ajusta la velocidad y el tono para encontrar la configuración perfecta.', en: 'Spanish Demo', zh: '西班牙语示例' },
    ],
    pt: [
        { text: 'Olá! Bem-vindo ao Bashi Voice Factory. Esta é uma demonstração de síntese de fala de alta qualidade. Selecione qualquer voz, e ajuste a velocidade e o tom para encontrar as configurações perfeitas.', en: 'Portuguese Demo', zh: '葡萄牙语示例' },
    ],
    fr: [
        { text: 'Bonjour! Bienvenue dans Bashi Voice Factory. Ceci est une démonstration de synthèse vocale de haute qualité. Sélectionnez une voix, et ajustez la vitesse et la tonalité pour trouver les réglages parfaits.', en: 'French Demo', zh: '法语示例' },
    ],
    ru: [
        { text: 'Здравствуйте! Добро пожаловать в Bashi Voice Factory. Это демонстрация высококачественного синтеза речи. Выберите голос, и настройте скорость и высоту тона, чтобы найти идеальные параметры для себя.', en: 'Russian Demo', zh: '俄语示例' },
    ],
    he: [
        { text: 'שלום! ברוכים הבאים ל-Bashi Voice Factory. זוהי הדגמה של המרת טקסט לדיבור באיכות גבוהה. בחר כל קול, וכוונן את המהירות ואת גובה הצליל כדי למצוא את ההגדרות המושלמות עבורך.', en: 'Hebrew Demo', zh: '希伯来语示例' },
    ],
    el: [
        { text: 'Γεια σας! Καλώς ήρθατε στο Bashi Voice Factory. Αυτή είναι μια επίδειξη σύνθεσης ομιλίας υψηλής ποιότητας. Επιλέξτε μια φωνή, και ρυθμίστε την ταχύτητα και τον τόνο για ιδανικά αποτελέσματα.', en: 'Greek Demo', zh: '希腊语示例' },
    ],
    ko: [
        { text: '안녕하세요! Bashi Voice Factory에 오신 것을 환영합니다. 고품질 텍스트 투 스피치의 데모입니다. 원하는 목소리를 선택하고, 속도와 음조 슬라이더를 자유롭게 조절하여 자신만의 완벽한 음성을 만들어 보세요.', en: 'Korean Demo', zh: '韩语示例' },
    ],
    de: [
        { text: 'Hallo! Willkommen im Bashi Voice Factory. Dies ist eine Demonstration hochwertiger Sprachsynthese. Wählen Sie eine Stimme, und passen Sie Geschwindigkeit und Tonhöhe für den perfekten Klang an.', en: 'German Demo', zh: '德语示例' },
    ],
};

// Initialize Application
document.addEventListener('DOMContentLoaded', init);

async function init() {
    await loadVoices();
    await loadSttModels();
    setupEventListeners();
    updateCharCount();

    // Check for saved language preference
    const savedLang = localStorage.getItem('edgetts_lang');
    if (savedLang) {
        switchLanguage(savedLang);
    }
}

// Load Voices from API
async function loadVoices() {
    try {
        const response = await fetch('/api/voices');
        state.voices = await response.json();
        // Always default to the first voice of the initial category
        const initialVoices = state.voices[state.selectedCategory]?.voices;
        if (initialVoices && initialVoices.length > 0) {
            state.selectedVoice = initialVoices[0].id;
        }
        renderVoices(state.selectedCategory);
    } catch (error) {
        console.error('Failed to load voices:', error);
        showToast('Failed to load voices', 'error');
    }
}

// Render Voice Cards
function renderVoices(category) {
    const categoryData = state.voices[category];
    if (!categoryData) return;

    elements.voiceGrid.innerHTML = categoryData.voices.map(voice => {
        const isChild = voice.isChild ? true : false;
        const childBadge = isChild ? '<span class="child-badge">CHILD 儿童</span>' : '';
        return `
            <div class="voice-card ${voice.id === state.selectedVoice ? 'selected' : ''} ${isChild ? 'child-voice' : ''}" 
                 data-voice-id="${voice.id}"
                 onclick="selectVoice('${voice.id}')">
                <div class="voice-name">${voice.name} ${childBadge}</div>
                <div class="voice-meta">
                    <span class="voice-tag">${voice.gender}</span>
                </div>
                <div class="voice-style">${voice.style}</div>
            </div>
        `;
    }).join('');
}

// Select Voice
function selectVoice(voiceId) {
    state.selectedVoice = voiceId;

    // Update UI
    document.querySelectorAll('.voice-card').forEach(card => {
        card.classList.toggle('selected', card.dataset.voiceId === voiceId);
    });
}

// Set Playback Mode
function setPlaybackMode(mode) {
    state.playbackMode = mode;

    // Update mode buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Show/hide sentence-specific settings
    const chunkingSettings = document.getElementById('chunking-settings');
    if (mode === 'sentence') {
        elements.pauseSetting.style.display = 'block';
        elements.modeHint.style.display = 'block';
        if (chunkingSettings) chunkingSettings.style.display = 'block';
        elements.generateBtnText.setAttribute('data-en', 'Generate Chunks');
        elements.generateBtnText.setAttribute('data-zh', '生成跟读片段');
        elements.generateBtnText.textContent = state.currentLang === 'zh' ? '生成跟读片段' : 'Generate Chunks';
        elements.textInput.maxLength = 5000;
    } else {
        elements.pauseSetting.style.display = 'none';
        elements.modeHint.style.display = 'none';
        if (chunkingSettings) chunkingSettings.style.display = 'none';
        elements.generateBtnText.setAttribute('data-en', 'Generate Speech');
        elements.generateBtnText.setAttribute('data-zh', '生成语音');
        elements.generateBtnText.textContent = state.currentLang === 'zh' ? '生成语音' : 'Generate Speech';
        elements.textInput.maxLength = 50000;
    }

    updateCharCount();

    // Hide previous results
    elements.playerSection.style.display = 'none';
    elements.sentencePlayerSection.style.display = 'none';
}

// Set Chunking Preset
function setChunkingPreset(preset) {
    // Update button states
    document.querySelectorAll('.chunk-preset-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.preset === preset);
    });

    // Set max words based on preset
    switch (preset) {
        case 'short':
            state.maxWords = 12;
            state.chunkingEnabled = true;
            break;
        case 'medium':
            state.maxWords = 15;
            state.chunkingEnabled = true;
            break;
        case 'long':
            state.maxWords = 20;
            state.chunkingEnabled = true;
            break;
        case 'off':
            state.maxWords = 0;
            state.chunkingEnabled = false;
            break;
    }
}

// Set Newline Handling Mode
function setNewlineMode(mode) {
    // mode: 'hard' (each newline is a boundary) or 'flow' (ignore single newlines)
    state.newlineHard = (mode === 'hard');

    document.querySelectorAll('.newline-mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
}

// Setup Event Listeners
function setupEventListeners() {
    // Text Input
    elements.textInput.addEventListener('input', updateCharCount);

    // Voice Category Tabs
    document.querySelectorAll('.voice-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const category = tab.dataset.category;
            state.selectedCategory = category;

            // Update tab UI
            document.querySelectorAll('.voice-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Always select the first voice of the new category
            const categoryVoices = state.voices[category].voices;
            if (categoryVoices.length > 0) {
                state.selectedVoice = categoryVoices[0].id;
            }

            renderVoices(category);
            updateDemoButtons(category);
        });
    });

    // Quick Text Buttons
    document.querySelectorAll('.quick-text-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            elements.textInput.value = btn.dataset.text;
            updateCharCount();
        });
    });

    // Sliders
    elements.rateSlider.addEventListener('input', () => {
        const value = elements.rateSlider.value;
        elements.rateValue.textContent = `${value >= 0 ? '+' : ''}${value}%`;
    });

    elements.pitchSlider.addEventListener('input', () => {
        const value = elements.pitchSlider.value;
        elements.pitchValue.textContent = `${value >= 0 ? '+' : ''}${value}Hz`;
    });

    elements.pauseSlider.addEventListener('input', () => {
        state.pauseDuration = parseFloat(elements.pauseSlider.value);
        elements.pauseValue.textContent = `${state.pauseDuration}s`;
    });

    // Generate Button
    elements.generateBtn.addEventListener('click', generateSpeech);

    // Download Button
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', downloadAudio);
    }

    // Keyboard shortcut (Ctrl/Cmd + Enter to generate)
    elements.textInput.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            generateSpeech();
        }
    });

    // Sentence audio ended event
    elements.sentenceAudio.addEventListener('ended', onSentenceEnded);

    // TXT File Upload - Click
    if (elements.uploadBtn) {
        elements.uploadBtn.addEventListener('click', () => {
            elements.fileInput.click();
        });
    }

    // TXT File Upload - File selected
    if (elements.fileInput) {
        elements.fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) loadTextFile(file);
            e.target.value = ''; // Reset so same file can be re-selected
        });
    }

    // TXT File Upload - Drag & Drop on textarea
    const inputSection = elements.textInput.closest('.input-section');
    if (inputSection) {
        inputSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            if (elements.dropZone) elements.dropZone.classList.add('active');
        });

        inputSection.addEventListener('dragleave', (e) => {
            // Only deactivate if leaving the section entirely
            if (!inputSection.contains(e.relatedTarget)) {
                if (elements.dropZone) elements.dropZone.classList.remove('active');
            }
        });

        inputSection.addEventListener('drop', (e) => {
            e.preventDefault();
            if (elements.dropZone) elements.dropZone.classList.remove('active');
            const file = e.dataTransfer.files[0];
            if (file && file.name.endsWith('.txt')) {
                loadTextFile(file);
            } else {
                const msg = state.currentLang === 'zh' ? '请拖放 .txt 文本文件' : 'Please drop a .txt file';
                showToast(msg, 'error');
            }
        });
    }

    // STT File Upload
    if (elements.sttFileInput) {
        elements.sttFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                state.sttFile = e.target.files[0];
                showSttFileInfo(state.sttFile);
            }
        });
    }

    if (elements.sttUploadZone) {
        elements.sttUploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            elements.sttUploadZone.style.borderColor = 'var(--primary-color)';
        });
        elements.sttUploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            elements.sttUploadZone.style.borderColor = '';
        });
        elements.sttUploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            elements.sttUploadZone.style.borderColor = '';
            if (e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                // Check if audio or video
                if (file.type.startsWith('audio/') || file.type.startsWith('video/') || file.name.match(/\.(mp3|mp4|wav|m4a|ogg|flac|aac|wma|msv|mkv)$/i)) {
                    state.sttFile = file;
                    showSttFileInfo(state.sttFile);
                } else {
                    const msg = state.currentLang === 'zh' ? '只支持音频和视频文件' : 'Only audio/video files supported';
                    showToast(msg, 'error');
                }
            }
        });
    }
}

// Update Character Count
function updateCharCount() {
    const count = elements.textInput.value.length;
    const max = elements.textInput.maxLength > 0 ? elements.textInput.maxLength : 50000;
    elements.charCount.textContent = `${count} / ${max}`;

    if (count > max * 0.96) {
        elements.charCount.style.color = '#f5576c';
    } else if (count > max * 0.90) {
        elements.charCount.style.color = '#ffc107';
    } else {
        elements.charCount.style.color = '';
    }
}

// Generate Speech
async function generateSpeech() {
    const text = elements.textInput.value.trim();

    if (!text) {
        const msg = state.currentLang === 'zh' ? '请输入文本' : 'Please enter some text';
        showToast(msg, 'error');
        return;
    }

    // Get settings
    const rate = `${elements.rateSlider.value >= 0 ? '+' : ''}${elements.rateSlider.value}%`;
    const pitch = `${elements.pitchSlider.value >= 0 ? '+' : ''}${elements.pitchSlider.value}Hz`;

    // Show loading state
    elements.generateBtn.style.display = 'none';
    elements.loading.classList.add('active');
    elements.playerSection.style.display = 'none';
    elements.sentencePlayerSection.style.display = 'none';
    const progressDiv = document.getElementById('long-text-progress');
    if (progressDiv) progressDiv.style.display = 'none';

    try {
        if (state.playbackMode === 'sentence') {
            await generateSentences(text, rate, pitch);
        } else {
            if (text.length > 4000) {
                // Hide generic spinner since long audio has its own detailed progress bar
                elements.loading.classList.remove('active');
                await generateLongAudio(text, rate, pitch);
            } else {
                await generateSingleAudio(text, rate, pitch);
            }
        }
    } catch (error) {
        console.error('Synthesis error:', error);
        if (progressDiv) progressDiv.style.display = 'none';
        const msg = state.currentLang === 'zh' ? '生成失败，请重试' : 'Generation failed, please try again';
        showToast(msg, 'error');
    } finally {
        // Hide loading state
        elements.generateBtn.style.display = 'flex';
        elements.loading.classList.remove('active');
    }
}

// Generate Single Audio
async function generateSingleAudio(text, rate, pitch) {
    const response = await fetch('/api/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            voice: state.selectedVoice,
            rate: rate,
            pitch: pitch
        })
    });

    const result = await response.json();

    if (result.success) {
        state.currentAudioUrl = result.audio_url;
        elements.audioPlayer.src = result.audio_url;
        elements.playerSection.style.display = 'block';

        // Auto-play
        elements.audioPlayer.play().catch(() => { });

        const msg = state.currentLang === 'zh' ? '语音生成成功！' : 'Speech generated successfully!';
        showToast(msg, 'success');
    } else {
        const errorMsg = state.currentLang === 'zh' ? result.error_zh : result.error;
        showToast(errorMsg, 'error');
    }
}

// Generate Long Audio via SSE
async function generateLongAudio(text, rate, pitch) {
    const progressDiv = document.getElementById('long-text-progress');
    const fill = document.getElementById('long-progress-fill');
    const textEl = document.getElementById('long-progress-text');
    const countEl = document.getElementById('long-progress-count');

    progressDiv.style.display = 'block';
    fill.style.width = '0%';

    // Switch to English text immediately if needed to avoid flicker
    textEl.setAttribute('data-en', 'Initializing...');
    textEl.setAttribute('data-zh', '初始化...');
    textEl.textContent = state.currentLang === 'zh' ? '初始化...' : 'Initializing...';

    try {
        const response = await fetch('/api/synthesize-long', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                voice: state.selectedVoice,
                rate: rate,
                pitch: pitch
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();
                    if (!dataStr) continue;

                    const data = JSON.parse(dataStr);

                    if (data.status === 'generating') {
                        const percent = ((data.chunk - 1) / data.total) * 100;
                        fill.style.width = `${percent}%`;
                        countEl.textContent = `${data.chunk} / ${data.total}`;

                        textEl.setAttribute('data-en', `Generating chunk ${data.chunk}...`);
                        textEl.setAttribute('data-zh', `正在生成第 ${data.chunk} 组...`);
                        textEl.textContent = state.currentLang === 'zh' ? `正在生成第 ${data.chunk} 组...` : `Generating chunk ${data.chunk}...`;
                    }
                    else if (data.status === 'merging') {
                        fill.style.width = '95%';
                        textEl.setAttribute('data-en', 'Merging audio files...');
                        textEl.setAttribute('data-zh', '正在合并音频文件...');
                        textEl.textContent = state.currentLang === 'zh' ? '正在合并音频文件...' : 'Merging audio files...';
                    }
                    else if (data.status === 'done') {
                        fill.style.width = '100%';
                        state.currentAudioUrl = data.audio_url_mp3;
                        elements.audioPlayer.src = data.audio_url_mp3;

                        elements.playerSection.style.display = 'block';
                        progressDiv.style.display = 'none';

                        // Auto-play
                        elements.audioPlayer.play().catch(() => { });

                        const msg = state.currentLang === 'zh' ? '长文本语音生成完成！' : 'Long text speech generated successfully!';
                        showToast(msg, 'success');

                        // Hide loading spinner since we are done
                        elements.generateBtn.style.display = 'flex';
                        elements.loading.classList.remove('active');
                        return;
                    }
                    else if (data.status === 'error') {
                        throw new Error(data.error);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Long synthesis error:', error);
        progressDiv.style.display = 'none';
        const msg = state.currentLang === 'zh' ? '长文本生成失败，请重试' : 'Long text generation failed, please try again';
        showToast(msg, 'error');
        throw error; // Let main logic catch it
    }
}

// Generate Sentences/Chunks
async function generateSentences(text, rate, pitch) {
    const response = await fetch('/api/synthesize-sentences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            voice: state.selectedVoice,
            rate: rate,
            pitch: pitch,
            max_words: state.maxWords,  // chunk size preset
            newline_hard: state.newlineHard  // NEW: newline handling
        })
    });

    const result = await response.json();

    if (result.success) {
        state.sentences = result.sentences;
        state.currentSentenceIndex = 0;
        state.isPlaying = false;
        state.isPaused = false;

        renderSentenceList();
        updateProgress();
        updatePauseButton();  // Reset pause button state

        elements.sentencePlayerSection.style.display = 'block';

        const chunkWord = state.currentLang === 'zh' ? '个片段' : ' chunks';
        const msg = state.currentLang === 'zh'
            ? `已生成 ${result.total}${chunkWord}！`
            : `Generated ${result.total}${chunkWord}!`;
        showToast(msg, 'success');
    } else {
        const errorMsg = state.currentLang === 'zh' ? result.error_zh : result.error;
        showToast(errorMsg, 'error');
    }
}

// Render Sentence List
function renderSentenceList() {
    elements.sentenceList.innerHTML = state.sentences.map((s, i) => `
        <div class="sentence-item" id="sentence-${i}" onclick="playSentence(${i})">
            <span class="sentence-number">${i + 1}</span>
            <span class="sentence-text">${escapeHtml(s.text)}</span>
            <button class="sentence-play-btn" onclick="event.stopPropagation(); playSentence(${i})">▶️</button>
        </div>
    `).join('');
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Update Progress
function updateProgress() {
    const total = state.sentences.length;
    const current = state.currentSentenceIndex;
    const progress = total > 0 ? (current / total) * 100 : 0;

    elements.progressFill.style.width = `${progress}%`;
    elements.sentenceProgress.textContent = `${current} / ${total}`;
}

// Play Single Sentence
function playSentence(index) {
    if (index >= state.sentences.length) return;

    // Update UI - remove previous states
    document.querySelectorAll('.sentence-item').forEach((el, i) => {
        el.classList.remove('playing');
        if (i < index) {
            el.classList.add('completed');
        } else {
            el.classList.remove('completed');
        }
    });

    // Highlight current sentence
    const currentEl = document.getElementById(`sentence-${index}`);
    if (currentEl) {
        currentEl.classList.add('playing');
        currentEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Play audio
    elements.sentenceAudio.src = state.sentences[index].audio_url;
    elements.sentenceAudio.play();

    state.currentSentenceIndex = index;
    updateProgress();
}

// Play All Sentences
function playAllSentences() {
    if (state.sentences.length === 0) return;

    state.isPlaying = true;
    state.isPaused = false;
    updatePauseButton();
    playSentence(state.currentSentenceIndex);
}

// Toggle Pause/Continue Playback
function pausePlayback() {
    if (state.isPaused) {
        // Continue playback
        state.isPaused = false;
        state.isPlaying = true;
        updatePauseButton();
        elements.sentenceAudio.play();
    } else {
        // Pause playback
        state.isPaused = true;
        state.isPlaying = false;
        updatePauseButton();
        elements.sentenceAudio.pause();
    }
}

// Update Pause Button State
function updatePauseButton() {
    const pauseBtn = document.getElementById('pause-btn');
    if (!pauseBtn) return;

    const iconSpan = pauseBtn.querySelector('span:first-child');
    const textSpan = pauseBtn.querySelector('span:last-child');

    if (state.isPaused) {
        iconSpan.textContent = '▶️';
        textSpan.setAttribute('data-en', 'Continue');
        textSpan.setAttribute('data-zh', '继续');
        textSpan.textContent = state.currentLang === 'zh' ? '继续' : 'Continue';
    } else {
        iconSpan.textContent = '⏸️';
        textSpan.setAttribute('data-en', 'Pause');
        textSpan.setAttribute('data-zh', '暂停');
        textSpan.textContent = state.currentLang === 'zh' ? '暂停' : 'Pause';
    }
}

// Reset Playback
function resetPlayback() {
    state.isPlaying = false;
    state.isPaused = false;
    state.currentSentenceIndex = 0;
    elements.sentenceAudio.pause();

    // Reset UI
    document.querySelectorAll('.sentence-item').forEach(el => {
        el.classList.remove('playing', 'completed');
    });

    updateProgress();
    updatePauseButton();
}

// On Sentence Ended
function onSentenceEnded() {
    if (!state.isPlaying) return;

    // Mark current as completed
    const currentEl = document.getElementById(`sentence-${state.currentSentenceIndex}`);
    if (currentEl) {
        currentEl.classList.remove('playing');
        currentEl.classList.add('completed');
    }

    state.currentSentenceIndex++;
    updateProgress();

    if (state.currentSentenceIndex < state.sentences.length) {
        // Wait for pause duration, then play next
        setTimeout(() => {
            if (state.isPlaying) {
                playSentence(state.currentSentenceIndex);
            }
        }, state.pauseDuration * 1000);
    } else {
        // Finished all sentences
        state.isPlaying = false;
        const msg = state.currentLang === 'zh' ? '播放完成！' : 'Playback complete!';
        showToast(msg, 'success');
    }
}

// Update Demo Buttons based on selected language
function updateDemoButtons(category) {
    const demos = DEMO_TEXTS[category] || DEMO_TEXTS['en'];
    const container = document.querySelector('.quick-texts');
    if (!container) return;

    // Remove existing quick-text-btn elements (keep upload button and file input)
    container.querySelectorAll('.quick-text-btn').forEach(btn => btn.remove());

    // Insert new demo buttons before the upload button
    const uploadBtn = container.querySelector('.upload-btn');
    demos.forEach(demo => {
        const btn = document.createElement('button');
        btn.className = 'quick-text-btn';
        btn.dataset.text = demo.text;
        btn.dataset.en = demo.en;
        btn.dataset.zh = demo.zh;
        btn.textContent = state.currentLang === 'zh' ? demo.zh : demo.en;
        btn.addEventListener('click', () => {
            elements.textInput.value = demo.text;
            updateCharCount();
        });
        container.insertBefore(btn, uploadBtn);
    });
}

// Load Text File (with comprehensive encoding auto-detection)
function loadTextFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const buffer = e.target.result;

        // Step 1: Try UTF-8 first
        let text = new TextDecoder('utf-8').decode(buffer);
        if (!text.includes('\uFFFD')) {
            finishLoadText(text, file);
            return;
        }

        // Step 2: Try multi-byte encodings (fatal mode throws on invalid sequences)
        const multiByteEncodings = ['gbk', 'shift-jis', 'euc-kr'];
        for (const enc of multiByteEncodings) {
            try {
                text = new TextDecoder(enc, { fatal: true }).decode(buffer);
                finishLoadText(text, file);
                return;
            } catch { /* not this encoding, continue */ }
        }

        // Step 3: Try single-byte encodings with Unicode range heuristics
        const singleByteEncodings = [
            { enc: 'windows-1251', test: /[\u0400-\u04FF]/ },   // Cyrillic (Russian)
            { enc: 'windows-1253', test: /[\u0370-\u03FF]/ },   // Greek
            { enc: 'windows-1256', test: /[\u0600-\u06FF]/ },   // Arabic
            { enc: 'windows-1252', test: /[\u00C0-\u00FF]/ },   // Latin extended (French/German/Spanish/Portuguese)
        ];
        for (const { enc, test } of singleByteEncodings) {
            try {
                const decoded = new TextDecoder(enc).decode(buffer);
                if (test.test(decoded)) {
                    finishLoadText(decoded, file);
                    return;
                }
            } catch { /* continue */ }
        }

        // Step 4: Final fallback — ISO-8859-1 (never fails)
        text = new TextDecoder('iso-8859-1').decode(buffer);
        finishLoadText(text, file);
    };
    reader.readAsArrayBuffer(file);
}

function finishLoadText(text, file) {
    // Truncate to the current textarea maxlength (5000 in shadowing mode, 50000 in single mode)
    const maxLen = elements.textInput.maxLength > 0 ? elements.textInput.maxLength : 50000;
    if (text.length > maxLen) {
        text = text.substring(0, maxLen);
        const msg = state.currentLang === 'zh'
            ? `文件已截断至${maxLen.toLocaleString()}字符上限`
            : `File truncated to ${maxLen.toLocaleString()} character limit`;
        showToast(msg, 'info');
    }
    elements.textInput.value = text;
    updateCharCount();
    const msg = state.currentLang === 'zh'
        ? `已加载文件: ${file.name}`
        : `Loaded file: ${file.name}`;
    showToast(msg, 'info');
}

// Download Audio (with format conversion)
async function downloadAudio() {
    if (!state.currentAudioUrl) return;

    const format = elements.formatSelect ? elements.formatSelect.value : 'mp3';
    const mp3Filename = state.currentAudioUrl.split('/').pop();

    if (format === 'mp3') {
        // Direct MP3 download, no conversion needed
        const link = document.createElement('a');
        link.href = state.currentAudioUrl;
        link.download = `edge-tts-${Date.now()}.mp3`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } else {
        // Convert via backend
        const msg = state.currentLang === 'zh' ? `正在转换为 ${format.toUpperCase()}...` : `Converting to ${format.toUpperCase()}...`;
        showToast(msg, 'info');

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: mp3Filename, format: format })
            });
            const data = await response.json();
            if (data.success) {
                const link = document.createElement('a');
                link.href = `/api/download/${data.filename}`;
                link.download = `edge-tts-${Date.now()}.${format}`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                const errMsg = state.currentLang === 'zh' ? '转换失败' : 'Conversion failed';
                showToast(errMsg, 'error');
            }
        } catch (err) {
            console.error('Format conversion error:', err);
            const errMsg = state.currentLang === 'zh' ? '转换失败' : 'Conversion failed';
            showToast(errMsg, 'error');
        }
    }
}

// Language Switching
function switchLanguage(lang) {
    state.currentLang = lang;
    localStorage.setItem('edgetts_lang', lang);

    // Update language buttons
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });

    // Update HTML lang attribute
    document.documentElement.setAttribute('data-lang', lang);

    // Update all translatable elements
    document.querySelectorAll('[data-en][data-zh]').forEach(el => {
        el.textContent = el.getAttribute(`data-${lang}`);
    });

    // Update textarea placeholder
    const textarea = elements.textInput;
    if (textarea.dataset.placeholderEn && textarea.dataset.placeholderZh) {
        textarea.placeholder = textarea.getAttribute(`data-placeholder-${lang}`);
    }

    // Update voice tab selection based on language
    if (lang === 'zh' && state.selectedCategory === 'en') {
        const zhTab = document.querySelector('.voice-tab[data-category="zh"]');
        if (zhTab) zhTab.click();
    } else if (lang === 'en' && state.selectedCategory === 'zh') {
        const enTab = document.querySelector('.voice-tab[data-category="en"]');
        if (enTab) enTab.click();
    }
}

// Toast Notification
function showToast(message, type = 'info') {
    const toast = elements.toast;
    toast.querySelector('.toast-message').textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Toggle Donation Section
function toggleDonation() {
    const content = document.getElementById('donation-content');
    const toggle = document.getElementById('donation-toggle');

    if (content.classList.contains('show')) {
        content.classList.remove('show');
        toggle.classList.remove('open');
    } else {
        content.classList.add('show');
        toggle.classList.add('open');
        checkQRImages();
    }
}

// Check if QR images exist and show hint if missing
function checkQRImages() {
    const qrCodes = document.getElementById('qr-codes');
    const hint = document.getElementById('qr-missing-hint');

    // Check after a short delay to allow onerror handlers to fire
    setTimeout(() => {
        const visibleQRs = qrCodes.querySelectorAll('.qr-item:not([style*="display: none"])');
        if (visibleQRs.length === 0 && hint) {
            hint.style.display = 'block';
        }
    }, 100);
}

// Expose functions to global scope
window.switchLanguage = switchLanguage;
window.selectVoice = selectVoice;
window.setPlaybackMode = setPlaybackMode;
window.setChunkingPreset = setChunkingPreset;
window.setNewlineMode = setNewlineMode;
window.playSentence = playSentence;
window.playAllSentences = playAllSentences;
window.pausePlayback = pausePlayback;
window.resetPlayback = resetPlayback;
window.toggleDonation = toggleDonation;

// STT functions
window.switchAppTab = switchAppTab;
window.onSttModelChange = onSttModelChange;
window.downloadSelectedModel = downloadSelectedModel;
window.clearSttFile = clearSttFile;
window.startTranscription = startTranscription;
window.exportTranscription = exportTranscription;
window.copySttResult = copySttResult;

/* ===============================================
   v3.1 - STT Logic
   =============================================== */

// Switch Main App Tab
function switchAppTab(tabId) {
    state.currentAppTab = tabId;
    document.querySelectorAll('.app-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.app-tab[data-tab="${tabId}"]`).classList.add('active');

    document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
    document.getElementById(tabId === 'tts' ? 'tts-container' : 'stt-container').classList.add('active');
}

// Load STT Models
async function loadSttModels() {
    try {
        const response = await fetch('/api/stt/models');
        const data = await response.json();
        
        elements.sttModelSelect.innerHTML = '';
        const allModels = [...data.installed, ...data.available];
        state.sttModels = allModels;
        
        allModels.forEach(m => {
            const isInstalled = data.installed.some(inst => inst.id === m.id);
            const opt = document.createElement('option');
            opt.value = m.id;
            const statusZh = isInstalled ? '✓' : '(未下载)';
            const statusEn = isInstalled ? '✓' : '(Not downloaded)';
            opt.textContent = `${m.name} ${state.currentLang === 'zh' ? statusZh : statusEn}`;
            opt.dataset.enStr = `${m.name} ${statusEn}`;
            opt.dataset.zhStr = `${m.name} ${statusZh}`;
            opt.dataset.installed = isInstalled;
            
            elements.sttModelSelect.appendChild(opt);
            
            // Default to SenseVoice if possible
            if (m.id.includes('sensevoice') && isInstalled) {
                elements.sttModelSelect.value = m.id;
            }
        });
        
        onSttModelChange();
    } catch (e) {
        console.error('Failed to load STT models', e);
    }
}

function onSttModelChange() {
    const opt = elements.sttModelSelect.options[elements.sttModelSelect.selectedIndex];
    if (!opt) return;
    
    if (opt.dataset.installed === 'true') {
        elements.sttDownloadBtn.style.display = 'none';
        elements.sttTranscribeBtn.disabled = false;
        elements.sttTranscribeBtn.style.opacity = '1';
        elements.sttTranscribeBtn.style.cursor = 'pointer';
    } else {
        elements.sttDownloadBtn.style.display = 'block';
        elements.sttTranscribeBtn.disabled = true;
        elements.sttTranscribeBtn.style.opacity = '0.5';
        elements.sttTranscribeBtn.style.cursor = 'not-allowed';
    }
}

async function downloadSelectedModel() {
    const modelId = elements.sttModelSelect.value;
    if (!modelId) return;
    
    elements.sttDownloadBtn.disabled = true;
    elements.sttModelSelect.disabled = true;
    elements.sttModelProgress.style.display = 'block';
    
    const fill = document.getElementById('model-dl-fill');
    const text = document.getElementById('model-dl-text');
    
    try {
        const response = await fetch('/api/stt/download-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId, use_mirror: true })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();
                    if (!dataStr) continue;
                    const data = JSON.parse(dataStr);
                    
                    if (data.status === 'downloading') {
                        fill.style.width = `${data.progress}%`;
                        text.textContent = `Downloading ${data.file}... ${Math.round(data.progress)}%`;
                    } else if (data.status === 'done') {
                        fill.style.width = '100%';
                        text.textContent = 'Download Complete!';
                        await loadSttModels(); // refresh dropdown
                        setTimeout(() => {
                            elements.sttModelProgress.style.display = 'none';
                            elements.sttModelSelect.disabled = false;
                            elements.sttDownloadBtn.disabled = false;
                        }, 2000);
                        return;
                    } else if (data.status === 'error') {
                        throw new Error(data.error);
                    }
                }
            }
        }
    } catch (e) {
        const msg = state.currentLang === 'zh' ? '下载失败' : 'Download failed';
        showToast(msg + ': ' + e.message, 'error');
        elements.sttDownloadBtn.disabled = false;
        elements.sttModelSelect.disabled = false;
        elements.sttModelProgress.style.display = 'none';
    }
}

function clearSttFile(e) {
    if (e) e.stopPropagation();
    state.sttFile = null;
    if (elements.sttFileInput) elements.sttFileInput.value = '';
    elements.sttSelectedFile.style.display = 'none';
    elements.sttUploadZone.style.display = 'block';
    elements.sttResultSection.style.display = 'none';
}

async function startTranscription() {
    if (!state.sttFile) {
        const msg = state.currentLang === 'zh' ? '请先选择文件' : 'Please select a file first';
        showToast(msg, 'error');
        return;
    }
    
    // Check if model is downloaded
    const opt = elements.sttModelSelect.options[elements.sttModelSelect.selectedIndex];
    if (!opt || opt.dataset.installed !== 'true') {
        const msg = state.currentLang === 'zh' ? '请先下载选择的模型' : 'Please download the selected model first';
        showToast(msg, 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', state.sttFile);
    formData.append('language', elements.sttLangSelect.value);
    formData.append('model_id', opt.value);
    
    elements.sttTranscribeBtn.style.display = 'none';
    document.getElementById('stt-loading').style.display = 'flex';
    elements.sttResultSection.style.display = 'none';
    elements.sttJobProgress.style.display = 'none';
    elements.sttLiveSegments.innerHTML = '';
    
    try {
        const response = await fetch('/api/stt/transcribe', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        
        state.sttJobId = data.job_id;
        elements.sttJobProgress.style.display = 'block';
        
        pollSttProgress();
    } catch (e) {
        showToast(e.message || 'Error starting transcription', 'error');
        elements.sttTranscribeBtn.style.display = 'flex';
        document.getElementById('stt-loading').style.display = 'none';
    }
}

async function pollSttProgress() {
    if (!state.sttJobId) return;
    
    const eventSource = new EventSource(`/api/stt/progress/${state.sttJobId}`);
    
    eventSource.onmessage = function(event) {
        const dataStr = event.data;
        if (!dataStr) return;
        const data = JSON.parse(dataStr);
        const titleEl = document.getElementById('stt-progress-title');
        
        if (data.status === 'extracting_audio') {
            titleEl.textContent = state.currentLang === 'zh' ? '正在提取音频...' : 'Extracting audio...';
        } else if (data.status === 'loading_model') {
            titleEl.textContent = state.currentLang === 'zh' ? '正在加载模型...' : 'Loading model...';
        } else if (data.status === 'transcribing') {
            titleEl.textContent = state.currentLang === 'zh' ? '正在转写音频...' : 'Transcribing Audio...';
            
            if (data.new_segments && data.new_segments.length > 0) {
                data.new_segments.forEach(seg => {
                    const p = document.createElement('p');
                    p.textContent = `[${formatTime(seg.start)} - ${formatTime(seg.end)}] ${seg.text}`;
                    elements.sttLiveSegments.appendChild(p);
                });
                elements.sttLiveSegments.scrollTop = elements.sttLiveSegments.scrollHeight;
            }
        } else if (data.status === 'done') {
            eventSource.close();
            
            // fetch final result
            fetch(`/api/stt/result/${state.sttJobId}`)
                .then(r => r.json())
                .then(res => {
                    elements.sttResultText.value = res.segments.map(s => s.text).join('\n');
                    elements.sttResultSection.style.display = 'block';
                    elements.sttTranscribeBtn.style.display = 'flex';
                    document.getElementById('stt-loading').style.display = 'none';
                    elements.sttJobProgress.style.display = 'none';
                    showToast(state.currentLang === 'zh' ? '转写完成！' : 'Transcription complete!', 'success');
                });
        } else if (data.status === 'error') {
            eventSource.close();
            showToast(data.error, 'error');
            elements.sttTranscribeBtn.style.display = 'flex';
            document.getElementById('stt-loading').style.display = 'none';
            elements.sttJobProgress.style.display = 'none';
        }
    };
    
    eventSource.onerror = function() {
        eventSource.close();
        // Fallback UI reset
        elements.sttTranscribeBtn.style.display = 'flex';
        document.getElementById('stt-loading').style.display = 'none';
    };
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function exportTranscription() {
    if (!state.sttJobId) return;
    const format = document.getElementById('stt-export-format').value;
    window.location.href = `/api/stt/export/${state.sttJobId}?format=${format}&lang=${state.currentLang}`;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function showSttFileInfo(file) {
    elements.sttFilenameDisplay.textContent = file.name;
    const sizeEl = document.getElementById('stt-filesize-display');
    if (sizeEl) sizeEl.textContent = formatFileSize(file.size);
    elements.sttUploadZone.style.display = 'none';
    elements.sttSelectedFile.style.display = 'flex';
}

function copySttResult() {
    const textarea = document.getElementById('stt-result-text');
    if (!textarea || !textarea.value) return;
    navigator.clipboard.writeText(textarea.value).then(() => {
        const msg = state.currentLang === 'zh' ? '已复制到剪贴板' : 'Copied to clipboard';
        showToast(msg, 'success');
    }).catch(() => {
        textarea.select();
        document.execCommand('copy');
        const msg = state.currentLang === 'zh' ? '已复制到剪贴板' : 'Copied to clipboard';
        showToast(msg, 'success');
    });
}
