# JARVIS 🛰️

**JARVIS** is a voice-controlled desktop assistant built in Python — an AI operating system for your PC.

It listens via wake word ("jarvis" / "JARVIS"), processes commands, thinks via local LLM (Ollama / `llama3`), remembers, and speaks back.

## ✨ Features

### Voice Pipeline
- Wake-word driven hands-free control (custom wake word)
- Continuous listening with phrase-time limits
- Text-to-speech responses (pyttsx3, multiple voices)

### AI Brain
- Local LLM via Ollama (`llama3`)
- **Live web search** fallback (via `ddgs`) when offline knowledge is insufficient
- Persistent conversation memory + long-term facts / preferences / projects
- Personality modes: Jarvis (Tony Stark style), Friendly, Executive Assistant

### Smart Home / System Integrations
- Email: send / reply / read via Gmail IMAP + SMTP
- Spotify: play / pause / skip / volume / playlists via pyautogui control
- App launcher: open/close Windows applications by voice
- System status: CPU / memory / disk monitoring via psutil
- Proactivity: monitors email, suggests actions

### Holographic HUD
- Lightweight local web server (`jarvis_hud_server.py`) that renders `jarvis_hud.html`
- Updates via `/api/message`, `/api/system`, `/api/hud/update`

### Developer Vertical
- **"Write a Python/JS/HTML program"** → generates code via LLM → saves to `jarvis_generated.*` → runs it

### Modes
- **Online / Offline** toggle
- Greeting/personality presets

## 🛠 Tech Stack

- **Python 3.11**
- Speech Recognition + PyAudio (speech input)
- pyttsx3 (speech output)
- **Ollama** (`llama3`) — local LLM brain
- **ddgs** — DuckDuckGo live search
- **pyautogui** — system control (Spotify, apps)
- **psutil** — system metrics
- **Google APIs** — Gmail / Calendar (OAuth)
- **Tkinter/local HTTP** — HUD

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/yashanand110606/jarvis-engine.git
cd jarvis-engine

# 2. Install deps
pip install speech_recognition pyaudio pyttsx3 ddgs ollama pyautogui psutil google-api-python-client google-auth-httplib2 google-auth-oauthlib

# 3. Start Ollama + llama3
ollama run llama3

# 4. Configure
cp jarvis_config.example.json jarvis_config.json
# → add Ollama model, Gmail app password, Spotify creds, etc.

# 5. Run
python jarvis.py
```

## 🔧 Project Structure

```
jarvis/
├── jarvis.py             # Main controller (CLI + voice loop)
├── jarvis_core.py        # Core managers (Email, Calendar, ...)
├── jarvis_hud_server.py  # HUD HTTP server
├── jarvis_hud.html       # Holographic HUD UI
├── jarvis_config.json    # Runtime config (NOT committed - contains secrets)
└── jarvis_memory.json    # Persistent memory (NOT committed)
```

## 📜 License

MIT

---

**Built by [Yash Anand](https://github.com/yashanand110606)**

