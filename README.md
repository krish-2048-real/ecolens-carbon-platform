# 🌿 EcoLens — Carbon Footprint Awareness Platform

> **Google PromptWars × Hack2Skills — Challenge 3**  
> AI-powered carbon footprint tracking with personalized lifestyle swap recommendations.

## 🚀 Overview

EcoLens is a web application that helps users track and minimize their carbon output. Users can describe daily activities in text or upload receipt/bill images — the app uses **Google Gemini AI** to analyze the carbon impact and suggest actionable, personalized alternatives.

## ✨ Features

- **📝 Text Analysis** — Describe any activity and get instant carbon estimates
- **📷 Image Analysis** — Upload receipts or bills for multimodal carbon analysis
- **📊 Interactive Charts** — Chart.js donut visualization of carbon impact
- **🔄 Personalized Swaps** — 2-3 actionable lifestyle alternatives per analysis
- **♿ Accessibility** — Screen-reader-friendly summaries with ARIA labels
- **🛡️ Security** — Input sanitization against prompt injection & jailbreaks

## 🏗️ Architecture

```
├── main.py              # FastAPI routes & middleware
├── config.py            # Environment configuration
├── schemas.py           # Pydantic models (LLM & API contracts)
├── gemini_client.py     # Gemini API wrapper
├── security.py          # SecurityGuard (input sanitization)
├── utils.py             # Utility helpers
├── test_main.py         # Pytest test suite (20 tests)
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not committed)
└── static/
    ├── index.html       # Frontend SPA
    ├── styles.css       # Premium dark glassmorphism design
    └── app.js           # Frontend logic + Chart.js
```

## 🔧 Setup

### Prerequisites
- Python 3.10+
- Google Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
# Edit .env and add your GEMINI_API_KEY

# Run the application
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000` in your browser.

### Running Tests

```bash
pytest test_main.py -v
```

All tests run fully mocked — no API key required.

## 🔐 Security

The **SecurityGuard** module intercepts all user inputs and filters:
- Prompt injection attempts (25+ regex patterns)
- Jailbreak phrases (DAN mode, developer mode, etc.)
- HTML/script injection (XSS prevention)
- Shell metacharacters

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve frontend SPA |
| `GET` | `/health` | Health check |
| `POST` | `/api/analyze/text` | Analyze text description |
| `POST` | `/api/analyze/image` | Analyze uploaded image |

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Pydantic v2
- **AI**: Google Gemini 2.0 Flash (structured JSON output)
- **Frontend**: HTML5, CSS3 (Glassmorphism), Vanilla JS, Chart.js
- **Testing**: pytest, httpx, unittest.mock
- **Font**: Inter (Google Fonts)

## 📜 License

Built for Google PromptWars × Hack2Skills hackathon.
