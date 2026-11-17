"""
jarvis_core.py — Reusable managers for JARVIS.

Kept separate from the main controller so each subsystem (LLM, email, calendar)
can be imported and tested independently.
"""

import os, sys, time, threading
from datetime import datetime, timedelta

try:
    import ollama
    OLLAMA_OK = True
except ImportError:
    OLLAMA_OK = False

try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    GOOGLE_OK = True
except ImportError:
    GOOGLE_OK = False

try:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib, imaplib, email
    EMAIL_OK = True
except ImportError:
    EMAIL_OK = False

DEFAULT_SYSTEM_PROMPT = "You are JARVIS. Be concise. Refer to user as sir."


class OllamaManager:
    """Thin wrapper around a local Ollama model, with lazy warm-up."""

    def __init__(self, model="llama3"):
        self.model = model
        self.ready = False

    def warm_up(self):
        if not OLLAMA_OK:
            return
        try:
            ollama.chat(model=self.model, messages=[{'role': 'user', 'content': 'hi'}])
            self.ready = True
        except Exception as e:
            print(f"Ollama warm-up failed: {e}")

    def chat(self, prompt, system=DEFAULT_SYSTEM_PROMPT):
        if not self.ready:
            return "Still warming up, sir."
        try:
            r = ollama.chat(model=self.model, messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': prompt},
            ])
            return r['message']['content']
        except Exception as e:
            return f"AI error: {e}"


class EmailMonitor:
    """IMAP read + SMTP send against a Gmail account."""

    def __init__(self, address, password, imap="imap.gmail.com", smtp="smtp.gmail.com"):
        self.address = address
        self.password = password
        self.imap = imap
        self.smtp = smtp

    def get_unread(self, limit=5):
        if not EMAIL_OK:
            return []
        try:
            mail = imaplib.IMAP4_SSL(self.imap)
            mail.login(self.address, self.password)
            mail.select("inbox")
            status, data = mail.search(None, 'UNSEEN')
            ids = data[0].split()[-limit:]
            results = []
            for num in ids:
                status, msg_data = mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(errors='ignore')
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                results.append({
                    'from': str(msg.get('From')),
                    'subject': str(msg.get('Subject')),
                    'body': body[:300]
                })
            mail.close()
            return results
        except Exception as e:
            print(f"Email error: {e}")
            return []

    def send(self, to, subject, body):
        if not EMAIL_OK:
            return False
        try:
            msg = MIMEMultipart()
            msg['From'] = self.address
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            server = smtplib.SMTP(self.smtp, 587)
            server.starttls()
            server.login(self.address, self.password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False


class CalendarManager:
    """Google Calendar reader using an OAuth installed-app flow."""

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, creds_file="credentials.json", token_file="token.json"):
        self.creds_file = creds_file
        self.token_file = token_file
        self.service = None
        self._init_service()

    def _init_service(self):
        if not GOOGLE_OK:
            return
        try:
            creds = None
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    flow = InstalledAppFlow.from_client_secrets_file(self.creds_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(self.token_file, 'w') as t:
                    t.write(creds.to_json())
            self.service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            print(f"Calendar init error: {e}")

    def get_events(self, max_results=10):
        if not self.service:
            return []
        try:
            events = self.service.events().list(
                calendarId='primary', timeMin=datetime.utcnow().isoformat() + 'Z',
                maxResults=max_results, singleEvents=True, orderBy='startTime'
            ).execute().get('items', [])
            return [{
                'summary': e.get('summary'),
                'start': e['start'].get('dateTime', e['start'].get('date')),
                'location': e.get('location', '')
            } for e in events]
        except Exception as e:
            print(f"Calendar error: {e}")
            return []
