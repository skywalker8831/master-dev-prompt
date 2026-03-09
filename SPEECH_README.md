# Speech Features — Setup & Usage Guide

This document covers the speech capabilities added to the **Master Dev Prompt** project:

| Interface | File | Features |
|-----------|------|---------|
| Web (browser) | `chat.html` | TTS (Read Aloud), STT (Microphone), Copy to Clipboard |
| Python CLI | `tts.py` | Text-to-Speech from string or file |
| Python CLI | `stt.py` | Speech-to-Text saved to stdout or file |

---

## 1. `chat.html` — Browser-based Chat Interface

A self-contained chat page that works by simply opening `chat.html` in any modern browser.  
No server, no build step, no CDN dependencies — everything is inline HTML/CSS/JS.

### Features

| Feature | How It Works |
|---------|-------------|
| 🔊 **Read Aloud** | Appears next to every assistant message. Reads the message using the browser's built-in `SpeechSynthesis` API. |
| 🔇 **Stop Speaking** | Global button in the header that cancels any ongoing speech immediately. |
| 🎤 **Microphone (STT)** | Click to start listening; transcribed speech fills the chat input. Click again to stop. Visual pulsing red indicator while active. |
| 📋 **Copy** | Appears next to every message. Copies text to clipboard with a brief "✓ Copied!" confirmation. |

### Usage

1. Open `chat.html` in Chrome, Edge, or another Chromium-based browser.
2. Type a message and press **Enter** (or **Shift+Enter** for a newline).
3. Click **🎤** to dictate your message; click again to stop.
4. Hover over any message to reveal the **📋 Copy** and **🔊 Read Aloud** buttons.
5. Click **🔇 Stop Speaking** to cancel reading.

### Connecting to a Backend

The chat currently shows a mock response. To connect it to a real API, edit the `sendMessage()` function in `chat.html` and replace the `setTimeout` mock with one of the following examples:

**Local FastAPI server (`app.py` in this repo):**

```javascript
fetch('/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript: text }),
})
.then(r => r.json())
.then(data => appendMessage('assist', JSON.stringify(data, null, 2)))
.catch(err => appendMessage('assist', 'Error: ' + err.message));
```

**OpenAI / ChatGPT API:**

```javascript
fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_API_KEY',
    },
    body: JSON.stringify({
        model: 'gpt-4o',
        messages: [{ role: 'user', content: text }],
    }),
})
.then(r => r.json())
.then(data => {
    const reply = data.choices?.[0]?.message?.content || '(no response)';
    appendMessage('assist', reply);
})
.catch(err => appendMessage('assist', 'Error: ' + err.message));
```

---

## 2. `tts.py` — Python Command-Line Text-to-Speech

Uses **pyttsx3** for fully offline, cross-platform text-to-speech.

### Installation

```bash
pip install pyttsx3
```

> **Linux only:** Install `espeak` first:
> ```bash
> sudo apt-get install espeak
> ```

### Usage Examples

```bash
# Speak a string directly
python tts.py "Hello, world!"

# Read a file aloud
python tts.py --file conversation-log.md

# Adjust speech rate (words per minute) and volume
python tts.py --file conversation-log.md --rate 150 --volume 0.8

# List available voices on your system
python tts.py --list-voices

# Use a specific voice by index (from --list-voices)
python tts.py "Hello" --voice 1
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `text` (positional) | — | Text string to speak |
| `--file PATH` | — | Read and speak a text/markdown file |
| `--rate WPM` | `175` | Speech rate in words per minute |
| `--volume LEVEL` | `1.0` | Volume from `0.0` (silent) to `1.0` (full) |
| `--voice INDEX` | `0` | Voice index (see `--list-voices`) |
| `--list-voices` | — | Print available voices and exit |

---

## 3. `stt.py` — Python Command-Line Speech-to-Text

Uses **SpeechRecognition** with **pyaudio** for microphone access and Google's free recognition service for transcription.

### Installation

```bash
pip install SpeechRecognition pyaudio
```

> **Linux only:** Install portaudio first:
> ```bash
> sudo apt-get install portaudio19-dev
> pip install pyaudio
> ```

> **macOS only:**
> ```bash
> brew install portaudio
> pip install pyaudio
> ```

### Usage Examples

```bash
# Listen until silence and print transcript to stdout
python stt.py

# Save transcript to a file
python stt.py --output transcript.txt

# Listen for exactly 10 seconds
python stt.py --duration 10

# Listen for 30 seconds and save to file
python stt.py --output out.txt --duration 30

# Use a different language
python stt.py --language fr-FR
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--output PATH` | — | Save transcript to a file (prints to stdout if omitted) |
| `--duration SECONDS` | (until silence) | Maximum listening duration |
| `--adjust SECONDS` | `1.0` | Time to calibrate for ambient noise |
| `--language LANG` | `en-US` | BCP-47 language tag (e.g., `es-ES`, `fr-FR`) |

---

## Browser Compatibility Notes

The `chat.html` page uses two Web Speech APIs:

| API | Chrome | Edge | Firefox | Safari |
|-----|--------|------|---------|--------|
| `SpeechSynthesis` (TTS) | ✅ | ✅ | ✅ | ✅ |
| `SpeechRecognition` (STT) | ✅ | ✅ | ❌ (not supported) | ⚠️ Partial (iOS 14.5+) |

**Recommended browsers:** Chrome 33+ or Edge 79+ for full functionality.

> **Note:** `SpeechRecognition` requires either:
> - A secure origin (HTTPS), **or**
> - `localhost` (for local development)
>
> It will not work when opening the HTML file directly as `file://` in some browser configurations.

---

## Troubleshooting

### Microphone permission denied (browser)
- Click the lock icon in your browser's address bar and allow microphone access.
- If you accidentally blocked it, go to **Settings → Privacy → Site Settings → Microphone**.

### `SpeechRecognition` not available (browser)
- Switch to Chrome or Edge — Firefox does not support the `SpeechRecognition` API.

### `pyaudio` installation fails (Python)

On **Linux**, install the native library first:
```bash
sudo apt-get install portaudio19-dev python3-dev
pip install pyaudio
```

On **macOS**, use Homebrew:
```bash
brew install portaudio
pip install pyaudio
```

On **Windows**, use a prebuilt wheel:
```bash
pip install pipwin
pipwin install pyaudio
```

### `pyttsx3` produces no sound on Linux
Make sure `espeak` is installed:
```bash
sudo apt-get install espeak
```

### Google Speech Recognition request error (`stt.py`)
- Check your internet connection (Google's free API is used by default).
- Try again — occasional service timeouts are normal.
- For offline use, install `vosk` and replace `recognize_google()` with `recognize_vosk()`.

---

## Full Installation (all dependencies)

```bash
pip install pyttsx3 SpeechRecognition pyaudio
```

Or install everything at once from the project root:

```bash
pip install -r requirements.txt
```
