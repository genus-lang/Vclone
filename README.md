# VoxAI - Advanced Local TTS Studio

VoxAI is a powerful, locally-hosted Text-to-Speech (TTS) studio and API designed for creating high-quality, long-form audio with fine-grained voice and pronunciation controls. It provides a beautiful web UI for voice cloning, A/B testing settings, and managing a custom pronunciation dictionary.

Powered by Coqui XTTS (with fallback to Edge-TTS), it features robust text processing pipelines and an integrated Digital Signal Processing (DSP) chain using Spotify's Pedalboard.

## 🚀 Features

* **Instant Voice Cloning**: Upload a short audio sample to instantly clone any voice.
* **Smart Text Pipeline**: Automatic text chunking, abbreviation expansion, and a user-editable pronunciation dictionary (Hinglish/Hindi optimized).
* **Audio Quality Engine**: Real-time VAD segmentation and quality scoring to ensure your source audio meets cloning standards.
* **DSP Enhancements**: Built-in audio processing (EQ, compression, high-pass filters, presence boost) applied automatically to generated audio.
* **Voice Studio UI**: A dedicated interface to experiment with speed, pitch, expressiveness, clarity, and more with A/B comparison tools.
* **FastAPI Backend**: Clean, extensible API for integrating TTS into your own webnovel/audiobook pipelines.

## 🛠 Prerequisites

* Python 3.10 or 3.11 (3.12 may have issues with some TTS dependencies)
* NVIDIA GPU with at least 6GB VRAM (Highly Recommended)
* FFmpeg (must be available in your system path or included in the project directory)

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/voxai-tts.git
   cd voxai-tts
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

To start the server, simply run the included batch script:

```bash
.\start.bat
```

*(This automatically handles cleaning up old processes and ensures you start from the correct directory).*

Once running, open your browser and navigate to:
**http://127.0.0.1:8000/studio/**

### API Documentation
Interactive API docs (Swagger) are available at:
**http://127.0.0.1:8000/docs**

## 🧩 Architecture

* `backend/main.py` - FastAPI entry point and routing
* `backend/engines/` - XTTS and Edge-TTS wrapper implementations
* `backend/text/` - Text normalization, regex chunking, and pronunciation pipeline
* `backend/audio/` - VAD segmentation, Quality Checking, DSP processing, and encoding
* `frontend/` - Static HTML/CSS/JS for the Voice Studio interface
* `voices/` - Storage for cloned reference audio files and VAD segments

## 📄 License

This project is open-source. Note that Coqui XTTS v2 has its own specific licensing terms (CPML) which you must review if you intend to use it commercially.
