"""
JARVIS - PRODUCTION EDITION (CMD ONLY + HUD)
Reliable wake word | Persistent memory | JARVIS personality | Offline mode
Developer vertical | Proactive assistant | Holographic HUD
"""

import os, sys, json, threading, time, datetime, subprocess, webbrowser, re
import urllib.request, urllib.parse

# ==================== DEPENDENCY LOADING ====================
try:
    import speech_recognition as sr
    VOICE_OK = True
except ImportError:
    VOICE_OK = False

try:
    import pyttsx3
    TTS_OK = True
except ImportError:
    TTS_OK = False

try:
    from ddgs import DDGS
    SEARCH_OK = True
except ImportError:
    SEARCH_OK = False

try:
    import ollama
    OLLAMA_OK = True
except ImportError:
    OLLAMA_OK = False

try:
    import pyautogui
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False

try:
    import smtplib, imaplib, email as email_lib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_OK = True
except ImportError:
    EMAIL_OK = False

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

# ==================== CONFIG ====================
CONFIG_PATH = "jarvis_config.json"
MEMORY_PATH = "jarvis_memory.json"
HUD_API_PORT = 8001

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            pass
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

config = load_json(CONFIG_PATH, {
    "email": {"address": "", "password": ""},
    "ollama_model": "llama3",
    "wake_word": "jarvis",
    "offline_mode": False,
    "personality": "jarvis",
    "voice": "david",
    "proactive_enabled": True,
    "hud_enabled": True,
})

# ==================== PERSONALITY ====================
PERSONAS = {
    "jarvis": {
        "name": "JARVIS",
        "tone": ("You are J.A.R.V.I.S., Tony Stark's AI. British, dry-witted, fiercely competent. "
                 "You call the user 'sir'. You are concise but never cold. You anticipate needs. "
                 "You NEVER use emojis. You NEVER write placeholders like [insert ...]. "
                 "You ALWAYS use real data provided. If you don't know, say so plainly."),
        "greeting": "Good day, sir. JARVIS is online and fully operational.",
    },
    "friendly": {
        "name": "Assistant",
        "tone": "You are a warm, helpful assistant. Be friendly and concise.",
        "greeting": "Hey there! I'm ready to help.",
    },
    "professional": {
        "name": "Executive Assistant",
        "tone": "You are a sharp executive assistant. Be direct, professional, efficient.",
        "greeting": "Good morning. I am standing by.",
    },
}

ACTIVE_PERSONA = config.get("personality", "jarvis")
PERSONA = PERSONAS.get(ACTIVE_PERSONA, PERSONAS["jarvis"])

# ==================== HUD CLIENT (NON-BLOCKING) ====================
class HUDClient:
    def __init__(self, port=HUD_API_PORT):
        self.port = port
        self.enabled = config.get("hud_enabled", True)

    def send_message(self, text):
        """Send text to HUD. Runs in a thread so voice is NEVER delayed."""
        if not self.enabled:
            return
        threading.Thread(target=self._send_raw, args=(text,), daemon=True).start()

    def _send_raw(self, text):
        try:
            url = f"http://localhost:{self.port}/api/message"
            data = json.dumps({"message": text}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=0.5).read()
        except Exception:
            pass  # Silent - HUD is optional, voice must never be delayed

hud_client = HUDClient()

# ==================== VOICE ENGINE (P0 - RELIABLE) ====================
class VoiceEngine:
    def __init__(self):
        self.recognizer = None
        self.microphone = None
        self.voice_name = config.get("voice", "david")
        self.speak_lock = threading.Lock()

        if VOICE_OK:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = 0.8
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                print("[Microphone calibrated]")
            except Exception as e:
                print("[Mic init failed: " + str(e) + "]")

    def _fresh_engine(self):
        """Build a brand-new pyttsx3 engine for this one utterance."""
        if not TTS_OK:
            return None
        try:
            eng = pyttsx3.init()
            eng.setProperty('rate', 185)
            eng.setProperty('volume', 1.0)
            voices = eng.getProperty('voices')
            for v in voices:
                if self.voice_name in v.name.lower():
                    eng.setProperty('voice', v.id)
                    break
            return eng
        except Exception:
            return None

    def speak(self, text):
        if not text:
            return
        print("JARVIS: " + text)
        sys.stdout.flush()
        hud_client.send_message(text)  # Update HUD instantly, non-blocking

        with self.speak_lock:
            eng = self._fresh_engine()
            if eng is None:
                print("[TTS unavailable - install pyttsx3]")
                return
            try:
                eng.say(text)
                eng.runAndWait()
            except Exception as e:
                print("[speak error: " + str(e) + "]")

    def _listen_audio(self, timeout, phrase_time_limit):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.15)
            try:
                return self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except TypeError:
                return self.recognizer.listen(source, timeout)

    def listen_once(self, timeout=8):
        if not VOICE_OK or not self.recognizer or not self.microphone:
            return ""
        try:
            audio = self._listen_audio(timeout=timeout, phrase_time_limit=8)
            text = self.recognizer.recognize_google(audio).lower()
            print("YOU: " + text)
            return text
        except Exception as e:
            if str(e):
                print("[listen: " + str(e) + "]")
            return ""

    def listen_continuous(self, wake_word, timeout=10):
        """Bounded listen. NEVER blocks forever."""
        if not VOICE_OK or not self.recognizer or not self.microphone:
            return None
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                try:
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                except TypeError:
                    audio = self.recognizer.listen(source, timeout)
            text = self.recognizer.recognize_google(audio).lower()
            print("YOU: " + text)
            return text
        except Exception as e:
            if str(e):
                print("[listen: " + str(e) + "]")
            return None

# ==================== MEMORY (P1) ====================
class Memory:
    def __init__(self, path=MEMORY_PATH):
        self.path = path
        self.data = load_json(path, {
            "facts": {},
            "conversation": [],
            "preferences": {},
            "projects": {},
        })
        self.max_conversation = 20

    def save(self):
        save_json(self.path, self.data)

    def add_fact(self, key, value):
        self.data["facts"][key] = value
        self.save()

    def get_fact(self, key):
        return self.data["facts"].get(key)

    def add_conversation(self, user_text, jarvis_text):
        self.data["conversation"].append({
            "time": datetime.datetime.now().isoformat(),
            "user": user_text,
            "jarvis": jarvis_text,
        })
        if len(self.data["conversation"]) > self.max_conversation:
            self.data["conversation"] = self.data["conversation"][-self.max_conversation:]
        self.save()

    def get_recent_context(self, n=5):
        recent = self.data["conversation"][-n:]
        lines = []
        for c in recent:
            lines.append("User: " + c["user"])
            lines.append("JARVIS: " + c["jarvis"])
        return "\n".join(lines)

    def set_preference(self, key, value):
        self.data["preferences"][key] = value
        self.save()

    def get_preference(self, key, default=None):
        return self.data["preferences"].get(key, default)

    def add_project(self, name, description):
        self.data["projects"][name] = {
            "description": description,
            "updated": datetime.datetime.now().isoformat(),
        }
        self.save()

    def get_projects(self):
        return self.data["projects"]

# ==================== BRAIN (P0 + P2) ====================
class Brain:
    def __init__(self, model=None):
        self.model = model or config.get("ollama_model", "llama3")
        self.ready = False
        self.offline = config.get("offline_mode", False)

    def warm_up(self):
        if not OLLAMA_OK:
            return
        try:
            ollama.chat(model=self.model, messages=[{'role': 'user', 'content': 'hi'}])
            self.ready = True
            print("[Ollama warmed up]")
        except Exception as e:
            print("[Ollama warm-up failed: " + str(e) + "]")

    def _search(self, query):
        if not SEARCH_OK or self.offline:
            return None
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=4, timelimit='w'))
                return "\n".join([f"- {r['body']}" for r in results]) if results else None
        except Exception:
            return None

    def _news(self):
        if not SEARCH_OK or self.offline:
            return None
        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(max_results=5))
                return "\n".join([f"- {r['title']}" for r in results]) if results else None
        except Exception:
            return None

    def _extract_city(self, command):
        c = command.lower()
        idx = c.find('weather')
        after = c[idx + 7:].strip() if idx != -1 else ""
        for w in ['today', 'now', 'like', 'outside', 'right now', 'currently',
                  'is', 'the', 'in', 'for', 'at', 'what', 'how']:
            if after == w:
                after = ""
            elif after.startswith(w + ' '):
                after = after[len(w) + 1:].strip()
        return after.strip()

    def _weather(self, command):
        city = self._extract_city(command)
        try:
            q = urllib.parse.quote(city) if city else "near+me"
            url = "https://wttr.in/" + q + "?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            cur = data['current_condition'][0]
            return "It is " + cur['temp_C'] + " degrees Celsius and " + cur['weatherDesc'][0]['value'].lower() + "."
        except Exception as e:
            print("[wttr.in failed: " + str(e) + "]")
            raw = self._search("weather " + city if city else "weather near me")
            if not raw:
                return None
            temp = re.search(r'(\d{1,3})[°°]C', raw)
            if temp:
                return "It is " + temp.group(1) + " degrees Celsius."
            return None

    def ask(self, query, memory=None, search_web=True):
        context_parts = []
        if memory:
            facts = memory.data.get("facts", {})
            if facts:
                context_parts.append("WHAT YOU KNOW ABOUT THE USER: " + json.dumps(facts))
            prefs = memory.data.get("preferences", {})
            if prefs:
                context_parts.append("USER PREFERENCES: " + json.dumps(prefs))
            recent = memory.get_recent_context(4)
            if recent:
                context_parts.append("RECENT CONVERSATION:\n" + recent)

        live = None
        if search_web and not self.offline:
            live = self._search(query)

        if live:
            prompt = ("LIVE DATA FROM THE WEB RIGHT NOW:\n" + live + "\n\n"
                      "QUESTION: " + query + "\n\n"
                      "RULES: Use ONLY the live data above. NEVER write placeholders like "
                      "[insert ...]. If data is missing, say you don't have it. Be concise. "
                      "Refer to user as sir.")
        else:
            prompt = ("You are JARVIS. Answer the question. Be concise. "
                      "Refer to user as sir. If unsure, say so plainly.")

        if context_parts:
            prompt = "\n".join(context_parts) + "\n\n" + prompt

        if not OLLAMA_OK:
            return "Ollama is not installed, sir."

        try:
            r = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': PERSONA["tone"]},
                {'role': 'user', 'content': prompt},
            ])
            return r['message']['content']
        except Exception as e:
            return "My brain is momentarily unavailable, sir: " + str(e)

    def quick(self, query):
        if not OLLAMA_OK:
            return "Ollama offline, sir."
        try:
            r = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': PERSONA["tone"]},
                {'role': 'user', 'content': query},
            ])
            return r['message']['content']
        except Exception as e:
            return "Brain error: " + str(e)

# ==================== APP LAUNCHER ====================
APP_MAP = {
    'chrome': 'chrome.exe', 'firefox': 'firefox.exe', 'edge': 'msedge.exe',
    'notepad': 'notepad.exe', 'calculator': 'calc.exe', 'paint': 'mspaint.exe',
    'word': 'winword.exe', 'excel': 'excel.exe', 'powerpoint': 'powerpnt.exe',
    'vs code': 'code.exe', 'vscode': 'code.exe', 'visual studio code': 'code.exe',
    'spotify': 'spotify.exe', 'discord': 'discord.exe', 'telegram': 'telegram.exe',
    'explorer': 'explorer.exe', 'file explorer': 'explorer.exe',
    'settings': 'control.exe', 'task manager': 'taskmgr.exe',
    'cmd': 'cmd.exe', 'terminal': 'wt.exe', 'powershell': 'powershell.exe',
    'steam': 'steam.exe', 'whatsapp': 'whatsapp.exe',
    'outlook': 'outlook.exe', 'skype': 'skype.exe',
}

def open_app(name):
    name = name.lower().strip()
    if name in APP_MAP:
        try:
            os.system("start " + APP_MAP[name])
            return True
        except:
            pass
    for pf in [r"C:\\Program Files", r"C:\\Program Files (x86)"]:
        if os.path.exists(pf):
            for root, dirs, files in os.walk(pf):
                for f in files:
                    if name in f.lower() and f.endswith('.exe'):
                        try:
                            os.startfile(os.path.join(root, f))
                            return True
                        except:
                            pass
    return False

def close_app(name):
    name = name.lower().strip()
    exe = APP_MAP.get(name, name + ".exe")
    os.system("taskkill /f /im " + exe)

# ==================== SPOTIFY ====================
def play_spotify(query):
    if not PYAUTOGUI_OK:
        return "pyautogui not installed, sir."
    query = (query.replace('play ', '').replace('song ', '').replace('music ', '')
             .replace('spotify', '').replace('on ', '').replace('from ', '')
             .replace('search', '').replace('for ', '').strip())
    if not query:
        query = "Billie Jean"
    try:
        os.system('start spotify')
        time.sleep(2.5)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.3)
        pyautogui.write(query)
        time.sleep(1.5)
        pyautogui.press('enter')
        time.sleep(2)
        pyautogui.press('space')
        return "Playing " + query + " on Spotify"
    except Exception as e:
        return "Could not control Spotify: " + str(e)

def play_from_playlist(playlist, song=""):
    if not PYAUTOGUI_OK:
        return "pyautogui not installed, sir."
    try:
        os.system('start spotify')
        time.sleep(2.5)
        pyautogui.hotkey('ctrl', 'k')
        time.sleep(1)
        pyautogui.write(playlist)
        time.sleep(1.5)
        pyautogui.press('enter')
        time.sleep(2)
        if song:
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.write(song)
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(1.5)
        pyautogui.press('space')
        return "Playing from " + playlist
    except Exception as e:
        return "Could not play playlist: " + str(e)

def spotify_control(action):
    if not PYAUTOGUI_OK:
        return "pyautogui not available, sir."
    actions = {
        'pause': ('playpause', 'Paused'),
        'play': ('playpause', 'Playing'),
        'next': ('nexttrack', 'Next track'),
        'previous': ('previoustrack', 'Previous track'),
        'volume up': ('volumeup', 'Volume up'),
        'volume down': ('volumedown', 'Volume down'),
        'mute': ('volumemute', 'Muted'),
    }
    if action in actions:
        pyautogui.press(actions[action][0])
        return actions[action][1]
    return "Unknown command, sir."

# ==================== EMAIL ====================
def send_email(to, subject, body):
    addr = config.get("email", {}).get("address", "")
    pwd = config.get("email", {}).get("password", "")
    if not addr or not pwd:
        return "Email not configured. Add your Gmail App Password to jarvis_config.json"
    try:
        msg = MIMEMultipart()
        msg['From'] = addr
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(addr, pwd)
        server.send_message(msg)
        server.quit()
        return "Email sent to " + to
    except Exception as e:
        return "Failed to send email: " + str(e)

def reply_to_latest(body):
    addr = config.get("email", {}).get("address", "")
    pwd = config.get("email", {}).get("password", "")
    if not addr or not pwd:
        return "Email not configured, sir."
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(addr, pwd)
        mail.select('inbox')
        status, data = mail.search(None, 'UNSEEN')
        ids = data[0].split()
        if not ids:
            mail.close()
            return "No emails to reply to, sir."
        status, msg_data = mail.fetch(ids[-1], '(RFC822)')
        msg = email_lib.message_from_bytes(msg_data[0][1])
        sender = str(msg.get('From'))
        subject = str(msg.get('Subject'))
        result = send_email(sender, "Re: " + subject, body)
        mail.close()
        return result
    except Exception as e:
        return "Reply failed: " + str(e)

def get_emails():
    addr = config.get("email", {}).get("address", "")
    pwd = config.get("email", {}).get("password", "")
    if not addr or not pwd:
        return []
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(addr, pwd)
        mail.select('inbox')
        status, data = mail.search(None, 'UNSEEN')
        ids = data[0].split()
        results = []
        for num in ids:
            status, msg_data = mail.fetch(num, '(RFC822)')
            msg = email_lib.message_from_bytes(msg_data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body += part.get_payload(decode=True).decode(errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
            results.append({
                'from': str(msg.get('From')),
                'subject': str(msg.get('Subject')),
                'body': body[:200]
            })
        mail.close()
        return results
    except Exception:
        return []

def read_emails_aloud(voice):
    emails = get_emails()
    if not emails:
        voice.speak("No new emails, sir.")
        return
    voice.speak("You have " + str(len(emails)) + " new emails, sir.")
    for e in emails:
        voice.speak("From " + e['from'] + ". Subject: " + e['subject'])

# ==================== CODE WRITER ====================
def write_code(language, description, brain):
    prompt = ("Write a complete, working " + language +
              " program that does: " + description +
              ". Return ONLY the code, no explanations, no markdown fences.")
    code = brain.quick(prompt)
    code = re.sub(r'^```(?:\w+)?\n?', '', code)
    code = re.sub(r'\n?```$', '', code)
    ext = {'python': '.py', 'javascript': '.js', 'html': '.html',
           'java': '.java', 'c': '.cpp', 'typescript': '.ts'}.get(language.lower(), '.py')
    filename = "jarvis_generated" + ext
    with open(os.path.join(os.getcwd(), filename), 'w') as f:
        f.write(code)
    return filename

def run_code(filename):
    if not os.path.exists(filename):
        return filename + " does not exist, sir."
    if filename.endswith('.py'):
        os.system("start cmd /k python " + filename)
    elif filename.endswith('.js') or filename.endswith('.ts'):
        os.system("start cmd /k node " + filename)
    else:
        os.startfile(filename)
    return "Running " + filename

# ==================== SYSTEM ====================
def get_system_status():
    if not PSUTIL_OK:
        return "System monitoring unavailable, sir."
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return ("System status, sir: CPU at " + str(int(cpu)) +
            "%, memory at " + str(int(mem)) +
            "%, disk at " + str(int(disk)) + "%.")

def get_time():
    return "It is " + datetime.datetime.now().strftime('%I:%M %p')

def get_date():
    return "Today is " + datetime.datetime.now().strftime('%B %d, %Y')

# ==================== PROACTIVE MONITOR (P1) ====================
class ProactiveMonitor:
    def __init__(self, voice, brain, memory):
        self.voice = voice
        self.brain = brain
        self.memory = memory
        self.running = True
        self.last_email_check = 0
        self.email_interval = 300

    def run(self):
        while self.running:
            try:
                now = time.time()
                if config.get("proactive_enabled", True) and now - self.last_email_check > self.email_interval:
                    self.last_email_check = now
                    emails = get_emails()
                    if emails:
                        self.voice.speak("Sir, you have " + str(len(emails)) + " new emails. Say 'read my emails' to hear them.")
                time.sleep(30)
            except Exception as e:
                print("[proactive error: " + str(e) + "]")
                time.sleep(30)

    def stop(self):
        self.running = False

# ==================== COMMAND PROCESSOR ====================
def process_command(cmd, voice, brain, memory):
    c = cmd.lower().strip()
    if not c:
        return True

    wake = config.get("wake_word", "jarvis")
    if c.startswith(wake + " "):
        c = c[len(wake) + 1:].strip()
    elif c == wake:
        voice.speak("Yes, sir?")
        return True

    # --- INSTANT COMMANDS (no AI) ---
    if 'time' in c:
        voice.speak(get_time())

    elif 'weather' in c:
        voice.speak("Checking the weather, sir.")
        result = brain._weather(c)
        voice.speak(result if result else "I couldn't get the weather, sir.")

    elif 'date' in c or 'today' in c:
        voice.speak(get_date())

    elif 'news' in c:
        voice.speak("Getting today's news, sir.")
        news = brain._news()
        if news:
            voice.speak(brain.quick("Summarize today's top headlines concisely: " + news))
        else:
            voice.speak("I couldn't get the news, sir.")

    elif any(w in c for w in ['read my emails', 'read my mail', 'read emails', 'my emails', 'my mail']):
        read_emails_aloud(voice)

    elif c.startswith('email to '):
        parts = c.replace('email to ', '').split(' subject ')
        if len(parts) == 2:
            to = parts[0].strip()
            rest = parts[1].split(' body ')
            subject = rest[0].strip() if rest else "No subject"
            body = rest[1].strip() if len(rest) > 1 else "Sent via JARVIS"
            voice.speak(send_email(to, subject, body))
        else:
            voice.speak("Say: email to person subject subject text body body")

    elif 'reply' in c and 'email' in c:
        body = c.replace('reply', '').replace('email', '').replace('to', '').strip()
        voice.speak(reply_to_latest(body))

    elif 'email' in c or 'mail' in c:
        emails = get_emails()
        if emails:
            for e in emails[:3]:
                print("  - " + e['from'] + ": " + e['subject'])
            voice.speak("You have " + str(len(emails)) + " unread emails, sir.")
        else:
            voice.speak("No new emails, sir.")

    elif c.startswith('open '):
        name = c.replace('open ', '').strip()
        if open_app(name):
            voice.speak("Opening " + name)
        else:
            voice.speak("I couldn't find " + name + ", sir")

    elif c.startswith('close '):
        name = c.replace('close ', '').strip()
        close_app(name)
        voice.speak("Closing " + name)

    elif 'playlist' in c:
        if 'from playlist' in c:
            parts = c.replace('play ', '').replace('from playlist', '').strip().split(' song ')
            playlist = parts[0].strip()
            song = parts[1].strip() if len(parts) > 1 else ""
            voice.speak(play_from_playlist(playlist, song))
        else:
            playlist = c.replace('play', '').replace('playlist', '').replace('from', '').strip()
            voice.speak(play_from_playlist(playlist))

    elif 'play' in c:
        voice.speak(play_spotify(c))

    elif 'pause' in c and ('music' in c or 'spotify' in c):
        voice.speak(spotify_control('pause'))
    elif 'resume' in c or ('play' in c and 'music' in c):
        voice.speak(spotify_control('play'))
    elif 'next track' in c or 'skip' in c:
        voice.speak(spotify_control('next'))
    elif 'previous track' in c:
        voice.speak(spotify_control('previous'))
    elif 'volume up' in c:
        voice.speak(spotify_control('volume up'))
    elif 'volume down' in c:
        voice.speak(spotify_control('volume down'))
    elif 'mute' in c:
        voice.speak(spotify_control('mute'))

    elif c.startswith('write a ') or c.startswith('code '):
        if 'python' in c:
            lang = 'python'
        elif 'javascript' in c or 'js' in c:
            lang = 'javascript'
        elif 'html' in c:
            lang = 'html'
        elif 'typescript' in c or 'ts' in c:
            lang = 'typescript'
        else:
            lang = 'python'
        desc = c.replace('write a ', '').replace('code ', '').strip()
        voice.speak("Writing that " + lang + " program, sir.")
        filename = write_code(lang, desc, brain)
        voice.speak("Created " + filename + ". Say 'run it' to execute.")

    elif 'run it' in c or 'run the code' in c:
        files = [f for f in os.listdir('.') if f.startswith('jarvis_generated')]
        if files:
            voice.speak(run_code(files[-1]))
        else:
            voice.speak("No generated code to run, sir.")

    elif 'remind' in c:
        task = c.replace('remind me to', '').replace('remind', '').replace('that', '').strip()
        if task:
            memory.add_fact("reminder_" + str(int(time.time())), task)
            voice.speak("Reminder saved: " + task)
        else:
            voice.speak("What should I remind you about, sir?")

    elif 'system status' in c or 'how is my pc' in c or 'system' in c:
        voice.speak(get_system_status())

    elif 'search' in c or 'google' in c:
        query = c.replace('search', '').replace('google', '').replace('for', '').strip()
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query))
        voice.speak("Searching for " + query)

    elif 'youtube' in c:
        query = c.replace('youtube', '').strip()
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query))
        voice.speak("Searching YouTube")

    elif 'hud' in c or 'display' in c or 'screen' in c:
        voice.speak("Opening holographic interface, sir.")
        import webbrowser
        webbrowser.open(f"http://localhost:{HUD_API_PORT}/")

    # === OFFLINE / ONLINE MODE (P2) ===
    elif 'offline' in c:
        if 'online' in c or 'back online' in c or 'go online' in c:
            config["offline_mode"] = False
            save_json(CONFIG_PATH, config)
            voice.speak("Online mode enabled, sir. I have access to the live internet again.")
        else:
            config["offline_mode"] = True
            save_json(CONFIG_PATH, config)
            voice.speak("Offline mode enabled, sir. I will only use local knowledge from now on.")

    elif 'online' in c and ('mode' in c or 'go online' in c or 'back online' in c):
        config["offline_mode"] = False
        save_json(CONFIG_PATH, config)
        voice.speak("Online mode enabled, sir. I have access to the live internet again.")

    elif 'lock' in c:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        voice.speak("Locked, sir.")

    elif 'shutdown' in c:
        voice.speak("Shutting down in 10 seconds, sir.")
        os.system("shutdown /s /t 10")

    elif 'restart' in c:
        voice.speak("Restarting in 10 seconds, sir.")
        os.system("shutdown /r /t 10")

    elif any(w in c for w in ['goodbye', 'sleep', 'stop', 'shut up']):
        voice.speak("Going to sleep, sir. Say my name to wake me.")
        return False

    elif 'exit' in c or 'quit' in c:
        voice.speak("Shutting down. Goodbye, sir.")
        return "exit"

    else:
        # AI with live search + memory
        voice.speak("One moment, sir.")
        response = brain.ask(c, memory, search_web=True)
        voice.speak(response)
        memory.add_conversation(c, response)

    return True

# ==================== CMD TEXT INPUT ====================
def cmd_input_loop(voice, brain, memory):
    while True:
        try:
            line = input()
        except EOFError:
            break
        except Exception:
            continue
        line = line.strip()
        if not line:
            continue
        result = process_command(line, voice, brain, memory)
        if result == "exit":
            os._exit(0)
        elif result is False:
            pass

# ==================== MAIN ====================
def main():
    print("=" * 65)
    print("   J.A.R.V.I.S.  -  PRODUCTION EDITION (CMD + HOLOGRAPHIC HUD)")
    print("=" * 65)
    print("Persona: " + PERSONA["name"])
    print("Model: " + config.get("ollama_model", "llama3"))
    print("Offline: " + str(config.get("offline_mode", False)))
    print("-" * 65)

    voice = VoiceEngine()
    brain = Brain()
    memory = Memory()

    warmup_thread = threading.Thread(target=brain.warm_up, daemon=True)
    warmup_thread.start()

    print("Console: type commands here (or just speak). Type 'exit' to quit.")
    print("Tip: Say 'open display' to launch the holographic HUD.")

    proactive = ProactiveMonitor(voice, brain, memory)
    proactive_thread = threading.Thread(target=proactive.run, daemon=True)
    proactive_thread.start()

    voice.speak(PERSONA["greeting"])
    print("JARVIS is standing by. Say '" + config.get("wake_word", "jarvis") + "' to wake me.")

    talking = False
    last_interaction = time.time()
    conversation_timeout = 25

    input_thread = threading.Thread(target=cmd_input_loop, args=(voice, brain, memory), daemon=True)
    input_thread.start()

    while True:
        try:
            text = voice.listen_continuous(config.get("wake_word", "jarvis"))
            if text is None:
                continue

            wake = config.get("wake_word", "jarvis")
            if wake in text:
                rest = text[text.find(wake) + len(wake):].strip()
                if rest == "":
                    voice.speak("Yes, sir?")
                else:
                    result = process_command(rest, voice, brain, memory)
                    if result == "exit":
                        proactive.stop()
                        break
                    elif result is False:
                        talking = False
                        continue
                talking = True
                last_interaction = time.time()
                continue

            if not talking:
                continue

            result = process_command(text, voice, brain, memory)
            if result == "exit":
                proactive.stop()
                break
            elif result is False:
                talking = False
                continue

            talking = True
            last_interaction = time.time()

            if talking and (time.time() - last_interaction) > conversation_timeout:
                voice.speak("Going to sleep, sir. Say my name to wake me.")
                talking = False

        except KeyboardInterrupt:
            print("\nShutting down...")
            proactive.stop()
            break
        except Exception as e:
            print("[main loop error: " + str(e) + "]")
            time.sleep(1)

if __name__ == "__main__":
    main()
