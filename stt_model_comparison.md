# STT Model Comparison: SenseVoice vs. Paraformer

Based on the transcription of the **"9分钟游遍西安"** test video, here is a detailed side-by-side comparison of the two available models.

## Summary Table

| Feature | SenseVoice (Small) | Paraformer (Large/VAD) | Winner |
| :--- | :--- | :--- | :--- |
| **Punctuation** | Built-in (commas, periods) | **No punctuation** (Matches Official) | **Paraformer** |
| **Timing Stability** | Significant drift possible | **Rock solid (VAD-sync)** | Paraformer |
| **Stuttering** | Repeats words at chunk boundaries | **Zero stuttering** | Paraformer |
| **Readability** | Easier for casual reading | **Matches Professional Standards** | Paraformer |

---

## Detailed Observations

### 1. Style & Punctuation (Official Match)
- **Official Subtitle:** Has **zero punctuation**. It uses spacing and line breaks for flow.
- **Paraformer:** Matches this style perfectly by providing a clean text stream. 
- **SenseVoice:** Adds commas and periods, which actually makes it *unreliable* if you want to match the original video's minimalist style.

### 2. The "Stutter" Issue (Boundary Overlaps)
- **SenseVoice:** Frequently repeats words at segment boundaries (e.g., `西安西安`).
- **Paraformer:** Uses **VAD-based segmentation**, which transcribes each speech phrase exactly once. No stutters, no repetitions.


### 3. Timestamp Accuracy
- **SenseVoice:** Timestamps are generally good but can drift over long files because it handles the timeline in chunks.
- **Paraformer:** The VAD ensures every segment starts exactly when the person begins speaking and ends when they stop. The sync is identical to the beginning and end of the video.

### 4. Transcription Nuances
- **Homophones:** Both models struggled with "沃野秦川" (Wo Ye Qin Chuan). 
  - SenseVoice: `霍野秦川` (Huo)
  - Paraformer: `过野秦川` (Guo)
- **Isolated Words:** Paraformer struggled slightly with "西安" when it was a stand-alone interjection, transcribing it as `吉安`. SenseVoice was more robust with short isolated terms.

## Recommendation

- **Use SenseVoice** if you want a "good enough" subtitle quickly and don't mind deleting a few repeated words.
- **Use Paraformer** if you are doing professional video editing and need **perfect sync** that won't drift, or if you prefer a clean text stream for professional translation/polishing.
