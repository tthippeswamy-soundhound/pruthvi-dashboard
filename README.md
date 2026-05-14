# Voice Transcription Analyzer

A web application that transcribes audio files using OpenAI Whisper and optionally analyzes transcripts with LLMs. Export results to Excel.

## Features

- **Multi-file upload** with drag-and-drop support
- **Audio transcription** using OpenAI Whisper (runs locally, no API key needed)
- **Optional LLM analysis** using OpenAI GPT models (requires API key)
- **Excel export** with styled output including transcripts and analysis
- **Purple-themed UI** - clean, modern, and responsive

## Supported Audio Formats

MP3, WAV, M4A, OGG, FLAC, WebM, MP4, AAC, WMA

## Prerequisites

- Python 3.10+
- ffmpeg (`sudo apt install ffmpeg` on Ubuntu/Debian)

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python run.py
```

Open http://localhost:8000 in your browser.

## Streamlit Dashboard

This repo also includes a Streamlit version of the API timing dashboard in `streamlit_app.py`.

Install dashboard dependencies:

```bash
pip install -r requirements_dashboard.txt
```

Run locally:

```bash
streamlit run streamlit_app.py
```

The app opens at http://localhost:8501 by default.

### Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create a new app from your repo.
3. Set main file path to `streamlit_app.py`.
4. Set dependencies file to `requirements_dashboard.txt` (advanced settings).
5. Deploy.

## Usage

1. Upload one or more audio files via drag-and-drop or file picker
2. Click **Transcribe Files** to generate transcripts
3. (Optional) Enter your OpenAI API key in Settings, enable LLM Analysis toggle, and click **Run LLM Analysis**
4. Click **Export to Excel** to download results as `.xlsx`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/transcribe` | POST | Upload and transcribe audio files |
| `/api/analyze` | POST | Run LLM analysis on transcripts |
| `/api/export` | POST | Export results to Excel |
| `/docs` | GET | Interactive API documentation |
