<h1 align="center"> MCP Live Stage Assistant </h1>
<div align="center" style="margin: 0 auto; max-width: 20%;">
<h2 align="center">built with</h2>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="static/logo_white.svg">
    <source media="(prefers-color-scheme: light)" srcset="static/logo_black.svg">
    <img alt="mcp use logo" src="./static/logo-white.svg" width="80%" style="margin: 20px auto;">
  </picture>
</div>

<p align="center">
    <a href="https://pypi.org/project/mcp_use/" alt="PyPI Version">
        <img src="https://img.shields.io/pypi/v/mcp_use.svg"/></a>
    <a href="https://pypi.org/project/mcp_use/" alt="Python Versions">
        <img src="https://img.shields.io/pypi/pyversions/mcp_use.svg" /></a>
    <a href="https://docs.mcp-use.com" alt="Documentation">
        <img src="https://img.shields.io/badge/docs-mcp--use.com-blue" /></a>
    <a href="https://mcp-use.com" alt="Website">
        <img src="https://img.shields.io/badge/website-mcp--use.io-blue" /></a>
    <a href="https://github.com/pietrozullo/mcp-use/blob/main/LICENSE" alt="License">
        <img src="https://img.shields.io/github/license/pietrozullo/mcp-use" /></a>
    <a href="https://github.com/astral-sh/ruff" alt="Code style: Ruff">
        <img src="https://img.shields.io/badge/code%20style-ruff-000000.svg" /></a>
    <a href="https://github.com/pietrozullo/mcp-use/stargazers" alt="GitHub stars">
        <img src="https://img.shields.io/github/stars/pietrozullo/mcp-use?style=social" /></a>
    </p>
    <p align="center">
    <a href="https://x.com/pietrozullo" alt="Twitter Follow - Pietro">
        <img src="https://img.shields.io/twitter/follow/Pietro?style=social" /></a>
    <a href="https://x.com/pederzh" alt="Twitter Follow - Luigi">
        <img src="https://img.shields.io/twitter/follow/Luigi?style=social" /></a>
    <a href="https://discord.gg/XkNkSkMz3V" alt="Discord">
        <img src="https://dcbadge.limes.pink/api/server/XkNkSkMz3V?style=flat" /></a>
</p>

This is a voice-enabled AI personal assistant that leverages the Model Context Protocol (MCP) to integrate multiple tools and services through natural voice interactions.
It is more specifically design for assisting live musician that gives commands to drive a digital mixer, a DMX console or other on stage equipment.

For developpers: https://deepwiki.com/infrafast/LiveStageAssistant

## Features

- 🎤 **Voice Input**: Real-time speech-to-text using OpenAI Whisper API or local Whisper
- 🔊 **Voice Output**: High-quality text-to-speech using ElevenLabs, pyttsx3, or no spoken output
- 🤖 **AI-Powered**: Conversational AI with memory persistence
- 🌐 **Multiple Model Providers**: Works with OpenAI or local Ollama models that support tool calling
- 🛠️ **Multi-Tool Integration**: Seamlessly connects to any MCP servers:
- 🧭 **MCP-provided Startup Instructions**: Optionally loads system instructions from MCP prompts, resources, or one configured fallback tool
- 🖥️ **Local Web Monitor**: Read-only runtime state, active config, console logs, final prompt, and manual command injection
- 💾 **Conversational Memory**: Maintains context across interactions
- 🗣️ **Optional Wake Word**: Gate spoken commands with a global wake word after STT transcription
- 🎯 **Extensible**: Easy to add new MCP servers and capabilities
- 📴 **Offline Mode**: Can run with Ollama, local Whisper, pyttsx3, and local MCP servers after models/packages are installed

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ User Voice  │ --> │ Speech-to-   │ --> │  LLM with   │ --> │ Text-to-     │
│   Input     │     │ Text (STT)   │     │  MCPAgent   │     │ Speech (TTS) │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                     Whisper             OpenAI  │                ElevenLabs
                     API or local      or local  |                or pyttsx3
                                        (Ollama) │                
                                                 │
                                          ┌──────▼────────┐
                                          │ MCP Servers   │
                                          ├───────────────┤
                                          │ • Linear      │
                                          │ • Playwright  │
                                          │ • Filesystem  │
                                          │ • XMSeries-MCP│
                                          └───────────────┘
```

## Installation

### Prerequisites

1. **Python 3.11+**
2. **uv** (Python package manager): `pip install uv` or `pipx install uv`
3. **Node.js** (for MCP servers)
4. **System dependencies**:
   - macOS: `brew install portaudio`
   - Ubuntu/Debian/Raspberry Pi OS: `sudo apt-get install portaudio19-dev alsa-utils ffmpeg espeak espeak-ng libespeak1 libespeak-ng1`
   - Windows: PyAudio wheel includes PortAudio
5. **Ollama** (optional, required for offline LLM mode)


### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-voice-assistant.git
cd mcp-voice-assistant

# Create a virtual environment with uv
uv venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install in development mode
uv pip install -e .

# Or install directly
uv pip install .
```

### Docker / Synology Quick Start

The Docker setup is designed so API keys stay in text files on the host machine and are mounted into the container.
Do not put the raw OpenAI or ElevenLabs key value directly in `docker-compose.synology.yml`.

Create a local Docker config folder:

```bash
mkdir -p synology data
cp .env.synology.example synology/.env
cp mcp_servers.synology.json synology/mcp_servers.synology.json
```

Put the API keys in files inside the mounted `synology/` folder:

```bash
printf '%s' 'your-openai-api-key' > synology/OPENAI_API_KEY.txt
printf '%s' 'your-elevenlabs-api-key' > synology/ELEVENLABS_API_KEY.txt
```

The Docker env file points to those mounted files from inside the container:

```env
OPENAI_API_KEY_FILE=/config/OPENAI_API_KEY.txt
ELEVENLABS_API_KEY_FILE=/config/ELEVENLABS_API_KEY.txt
```

`docker-compose.synology.yml` mounts `./synology` to `/config`, so the assistant reads:

```text
host:      ./synology/OPENAI_API_KEY.txt
container: /config/OPENAI_API_KEY.txt

host:      ./synology/ELEVENLABS_API_KEY.txt
container: /config/ELEVENLABS_API_KEY.txt
```

The assistant can run without working audio devices: if microphone capture fails because no input device is available, it falls back to text commands from the web monitor or terminal; if speech playback is unavailable, responses are still printed in the console and monitor. For a first run on Synology or another headless Docker host, `TTS_PROVIDER=none` is only the quietest starting point while you validate the container, MCP, and web monitor. Microphone and speaker passthrough can be tested later.

Build and start:

```bash
docker compose -f docker-compose.synology.yml up --build -d
docker logs -f live-stage-assistant
```

Open the monitor from your browser:

```text
http://NAS_IP:8765
```

If you use the mixer MCP server, clone/install/build `XMSeries-MCP` on the host and mount it in `docker-compose.synology.yml`:

```yaml
volumes:
  - ./XMSeries-MCP:/xmseries-mcp:ro
```

Then keep this value in `synology/.env`:

```env
XMSERIES_MCP_PATH=/xmseries-mcp
MCP_CONFIG=/config/mcp_servers.synology.json
```

On DSM 7.0, the exact Docker UI depends on the Synology model and installed Docker package. If the Container Manager "Project" interface is not available, use SSH and the `docker compose` command above, or create an equivalent container manually with the same mounts, host network, and port `8765`.

### Offline Preparation

Offline mode works only after the required Python packages, Node packages, Ollama model, and Whisper model are already available locally.

1. Install dependencies while online:
```bash
uv pip install -e .
```

2. Install and start Ollama, then pull a tool-capable model:
```bash
ollama serve
ollama pull qwen3:8b
```

3. Download/cache the local Whisper model once:
```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='auto', compute_type='int8')"
```

4. Run the local MCP server packages used by `mcp_servers.offline.json`:
```bash
npx -y @modelcontextprotocol/server-filesystem
npx -y @modelcontextprotocol/server-memory --help
```

The offline MCP config uses `npx --offline`, so it will fail instead of reaching the network if those packages were not cached first. After those steps, the assistant can run without OpenAI or ElevenLabs API keys when using Ollama, local Whisper, pyttsx3, and the offline MCP config.

## Configuration

### Environment Variables

Create a `.env` file in your project root (see `.env.example` for a complete template):

```bash
# Required only when using OpenAI LLM or OpenAI Whisper API.
# Put the real key in this ignored local text file.
OPENAI_API_KEY_FILE=OPENAI_API_KEY.txt

# Optional but recommended for better voice output
ELEVENLABS_API_KEY_FILE=ELEVENLABS_API_KEY.txt

# LLM provider selection
LLM_PROVIDER=openai                             # openai | ollama
OPENAI_MODEL=gpt-4o-mini                        # OpenAI: gpt-4o-mini, gpt-4o, gpt-4.1-mini

# Ollama local settings (when LLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434
# OPENAI_MODEL=qwen3:8b                         # Example Ollama model tag

# Speech-to-text settings
STT_PROVIDER=openai-whisper                     # openai-whisper | local-whisper
LOCAL_WHISPER_MODEL=base                        # faster-whisper model size or local model path
STT_LANGUAGE=auto                               # auto-detect, or force en, fr, etc.
STT_PROMPT="Commandes courtes en français..."   # Optional context prompt for Whisper

# Text-to-speech settings
TTS_PROVIDER=elevenlabs                         # elevenlabs | pyttsx3 | none

# Voice Settings
ELEVENLABS_VOICE_OPTIONS=kENkNtk0xyzG09WW40xE (Marcel), 1EmYoP3UnnnwhlJKovEy (Anthony)
ELEVENLABS_VOICE_ID=1EmYoP3UnnnwhlJKovEy      # Selected ElevenLabs voice ID

# Optional - Audio Configuration
VOICE_SILENCE_THRESHOLD=500                     # Lower = more sensitive
VOICE_SILENCE_DURATION=1.5                      # Seconds to wait after speech
THINKING_SOUND_FILE=thinking.wav                # WAV loop while the LLM/MCP agent processes the command

# Optional - Read-only local web monitor
WEB_MONITOR_ENABLED=true                        # Serve runtime state, config, logs, and final prompt
WEB_MONITOR_HOST=127.0.0.1
WEB_MONITOR_PORT=8765

# Optional - Assistant Configuration
WAKE_WORD=                                      # Empty keeps current behavior; set e.g. "Mixeur" to gate commands
ASSISTANT_SYSTEM_PROMPT="You are a helpful voice assistant..."  # Customize personality
MCP_AGENT_MEMORY_ENABLED=true                  # Keep conversational memory; live external state still requires MCP reads
MCP_CONFIG=mcp_servers.offline.json             # Optional config override

# Optional - MCP-provided Assistant Instructions
MCP_LOAD_SERVER_PROMPT=false                    # true | false, default false
MCP_PROMPT_MERGE_MODE=append                    # append | replace, default append

# Optional - MCP Server Specific
LINEAR_API_KEY=your-linear-api-key              # For Linear integration
```

The assistant is configured from an environment file. The CLI intentionally accepts only `--env-file` plus `--help`, so the selected `.env` file is the single source of truth for runtime settings.

API secrets are read through `OPENAI_API_KEY_FILE` and `ELEVENLABS_API_KEY_FILE`. These variables must contain paths to text files that contain the secret, not the secret value itself. In Docker/Synology deployments, place those files in the mounted config folder on the host, for example `./synology/OPENAI_API_KEY.txt`, and point the container env file to `/config/OPENAI_API_KEY.txt`.

The assistant treats current external state as time-sensitive. Conversation memory can preserve context and follow-up references, but when the user asks for the current state of anything outside the conversation, the agent is instructed to call the relevant MCP read tool before answering. Set `MCP_AGENT_MEMORY_ENABLED=false` only if you want to disable MCPAgent conversation memory entirely.

### Wake Word

`WAKE_WORD` is optional. When it is empty, the assistant processes every successful transcription. When it is set, spoken transcriptions are processed only if the wake word appears at the start of the phrase or very close to it.

For example, with `WAKE_WORD=Mixeur`, all of these are accepted and the command text after the wake word is sent to the agent:

```text
Mixeur, increase volume
Hi Mixeur, increase volume
Wakeup Mixeur, increase volume
```

If multiple variants are needed, separate them with a comma, semicolon, or pipe:

```bash
WAKE_WORD=Mixeur,Mixer
```

### Web Monitor

When `WEB_MONITOR_ENABLED=true`, the assistant starts a local web monitor and prints its URL at startup, by default:

```text
Web monitor available at http://127.0.0.1:8765
```

The monitor exposes:

- **State**: current online/offline status, selected env profile, and LLM/STT/TTS/MCP status indicators
- **Inject Command**: a text input that queues a command for the agent
- **Config**: active env and MCP JSON configuration with secrets redacted and possibility to change LLM provider on the fly
- **Console Log**: the same Python console output mirrored into the page
- **Prompt**: the final system prompt after local and MCP-provided prompt merge

The console output path is centralized for Python `stdout` and `stderr`: the same filtered text is written to the terminal and to **Console Log**. High-frequency OSC heartbeat reads for `/xremote` and `/xinfo` are filtered out in both places; other OSC reads and writes remain visible when they pass through the Python console stream.

Injected commands are treated as direct text input after wake word handling. This means the text entered in **Inject Command** should be the command itself, without the wake word. After the monitor accepts the command, the input is cleared. The agent logs the command as consumed before processing it.

The monitor remains decoupled from the assistant logic. The web page only queues text; the agent remains responsible for consuming and processing it. If the assistant is already inside microphone recording when a command is injected, the recording loop stops early and the queued command is consumed immediately after the microphone stream closes.

### Online and Offline Profiles

The repository includes two ready-to-use environment profiles:

- `.env.online`: cloud mode with OpenAI for LLM/STT, ElevenLabs for TTS, and `mcp_servers.json`
- `.env.offline`: local mode with Ollama for LLM, local Whisper for STT, pyttsx3 for TTS, and `mcp_servers.offline.json`
- `auto`: switch to/from online to offline setting depending according to internet connectivity

Start the assistant by passing the profile you want:

```bash
# Online/cloud profile
python voice_assistant/agent.py --env-file .env.online

# Offline/local profile
python voice_assistant/agent.py --env-file .env.offline

# auto
python voice_assistant/agent.py --env-file auto
```

Before using the online profile, create local secret files at the repository root. They are ignored by Git:

```bash
printf '%s' 'your-openai-api-key' > OPENAI_API_KEY.txt
printf '%s' 'your-elevenlabs-api-key' > ELEVENLABS_API_KEY.txt
```

`.env.online` references those files with:

```bash
OPENAI_API_KEY_FILE=OPENAI_API_KEY.txt
ELEVENLABS_API_KEY_FILE=ELEVENLABS_API_KEY.txt
```

The assistant reads API keys only through `OPENAI_API_KEY_FILE` and `ELEVENLABS_API_KEY_FILE`.

Before using the offline profile, make sure Ollama is running and the selected model is available:

```bash
ollama serve
ollama pull qwen3:8b
```

### MCP Server Configuration

The assistant loads MCP server configurations indicated in your environment file (see Online and Offline Profiles and Environment Variables) in the project root. By default, it includes:

- **playwright**: Web automation and browser control
- **linear**: Task and project management
- **mixer**: control of a Behringer digital mixer  (see https://github.com/infrafast/XMSeries-MCP)

For offline mode, use `mcp_servers.offline.json`:

- **filesystem**: local filesystem access inside the configured root
- **memory**: local MCP memory server
- **mixer**: control of a Behringer digital mixer  (see https://github.com/infrafast/XMSeries-MCP)

Set `MCP_CONFIG=mcp_servers.offline.json` in the selected env file.

Server-specific paths belong in the selected MCP JSON file. For a local mixer server, set the `mixer.args` entry directly to the full `XMSeries-MCP/dist/index.js` path for that machine. Environment placeholders can still appear inside JSON string values for secrets or shared settings. If a configured command or Node script cannot be found, the assistant prints that the MCP server instance could not be started and continues with the remaining available servers.

To add more servers, edit `mcp_servers.json` or copy `mcp_servers.example.json` which includes additional servers like:
- filesystem, github, gitlab, google-drive, postgres, sqlite, slack, memory, puppeteer, brave-search, fetch

Environment variables in the config (like `${GITHUB_PERSONAL_ACCESS_TOKEN}`) are automatically substituted from the selected env file.

To override the default configuration programmatically:

```python
config = {
    "mcpServers": {
        "your_server": {
            "command": "npx",
            "args": ["-y", "@your-org/mcp-server"],
            "env": {"YOUR_API_KEY": "${YOUR_API_KEY}"}
        }
    }
}
```

### MCP-provided Startup Instructions

By default, the assistant uses only the local `ASSISTANT_SYSTEM_PROMPT` or the built-in prompt in `voice_assistant/agent.py`.

You can optionally ask the assistant to load additional system instructions from one or more configured MCP servers before `MCPAgent` is created. This is useful when servers want to expose domain-specific behavior, tool usage rules, or operator guidance without hard-coding that content in the voice assistant.

Enable it with:

```bash
MCP_LOAD_SERVER_PROMPT=true
```

Then add an `assistantPrompt` block to each MCP server that should contribute startup instructions. The server name is already the key under `mcpServers`, so it does not need to be repeated in the env file.

```json
{
  "mcpServers": {
    "mixer": {
      "command": "node",
      "args": ["path/to/server.js"],
      "assistantPrompt": {
        "promptName": "xmseries_mixer_assistant",
        "resourceUri": "xmseries://prompt/system",
        "tool": "osc_get_agent_prompt"
      }
    }
  }
}
```

For each server with an `assistantPrompt` block, the assistant tries only the configured sources, in this order:

1. `promptName`: fetch an MCP prompt with `prompts/get`
2. `resourceUri`: read an MCP resource with `resources/read`
3. `tool`: call exactly this fallback tool with empty arguments

It never calls arbitrary tools while loading startup instructions. If the server is missing, does not support prompts/resources, does not expose the configured fallback tool, or returns an error, the assistant logs a warning and continues with the local prompt.

Single-server env configuration:

```bash
MCP_LOAD_SERVER_PROMPT=true
MCP_PROMPT_MERGE_MODE=append
```

Multi-server MCP configuration:

```json
{
  "mcpServers": {
    "mixer": {
      "command": "node",
      "args": ["path/to/mixer-server.js"],
      "assistantPrompt": {
        "promptName": "xmseries_mixer_assistant",
        "resourceUri": "xmseries://prompt/system",
        "tool": "osc_get_agent_prompt"
      }
    },
    "lights": {
      "command": "node",
      "args": ["path/to/lights-server.js"],
      "assistantPrompt": {
        "resourceUri": "lights://prompt/system"
      }
    },
    "stage": {
      "command": "node",
      "args": ["path/to/stage-server.js"],
      "assistantPrompt": {
        "tool": "stage_get_agent_prompt"
      }
    }
  }
}
```

Each `assistantPrompt` block can define:

1. `promptName`: optional MCP prompt name
2. `resourceUri`: optional MCP resource URI
3. `tool`: optional explicit fallback tool name

The prompts are loaded in the order of the servers under `mcpServers`. A failing server prompt logs a warning and does not block the others.

At startup, when instructions are loaded, the assistant writes a console log entry listing the MCP prompt sources that were actually merged, for example:

```text
Loaded and merged 2 MCP prompt source(s) with merge mode 'append': mixer via prompt 'xmseries_mixer_assistant'; lights via resource 'lights://prompt/system'
```

With `MCP_PROMPT_MERGE_MODE=append`, the local prompt stays first and the remote instructions are appended under:

```text
Additional instructions loaded from MCP servers:
Instructions loaded from MCP server "mixer":
...

Instructions loaded from MCP server "lights":
...
```

This mode preserves the local voice constraints, including concise TTS-friendly replies, same-language answers, plain text only, and no emojis, markdown, bullets, or decorative characters.

Even with several MCP prompt sources, `MCP_PROMPT_MERGE_MODE` still has a role: the loaded MCP prompts are always combined together in the configured order, and this setting decides whether that combined block is appended to the local assistant prompt or replaces it.

With `MCP_PROMPT_MERGE_MODE=replace`, only the loaded remote instructions are used. Choose this only if the MCP server prompts already contain all voice and formatting constraints needed by the assistant.


### Running the Assistant

After installation, run the assistant:

```bash
# Default env file: .env
python voice_assistant/agent.py

# Explicit online profile
python voice_assistant/agent.py --env-file .env.online

# Explicit offline profile
python voice_assistant/agent.py --env-file .env.offline

# Auto profile selection
python voice_assistant/agent.py --env-file auto

# Show the only CLI options
python voice_assistant/agent.py --help
```

`OPENAI_API_KEY` is not required when the selected env file uses `LLM_PROVIDER=ollama` and `STT_PROVIDER=local-whisper`.

With `--env-file auto`, the assistant checks internet connectivity at startup. It loads `.env.online` when internet is reachable, otherwise `.env.offline`. It then monitors connectivity every 10 seconds and switches the running assistant profile when the connection state changes:

- `Internet live` is announced with the TTS from `.env.online`
- `Internet inactive` is announced with the TTS from `.env.offline`

After the announcement, the current voice loop is interrupted if needed, the active assistant instance is cleaned up, and a fresh instance is started from the newly detected env file. This reloads the TTS, STT, LLM, and MCP configuration from the selected profile. Any command currently being recorded or processed may be cancelled during the switch, which keeps the implementation simple and avoids mixing services from two profiles. Once the new assistant is ready, it announces that the environment was updated and the in-flight request was cancelled using the TTS from the new profile.

If you run `python voice_assistant/agent.py` without `--env-file`, the assistant loads `.env` when present. If `.env` does not exist, internal defaults are used: OpenAI with `gpt-4o-mini` for the LLM, OpenAI Whisper for STT, ElevenLabs for TTS when `ELEVENLABS_API_KEY` is available, `thinking.wav` for the processing sound, and `mcp_servers.json` when no explicit MCP config is provided. In that default mode, `OPENAI_API_KEY` is required because both the LLM and STT providers use OpenAI.

For short stage commands, `STT_PROMPT` can give Whisper mixer-specific context. The bundled default biases French mixer commands such as `mets Claude`, `baisse snare`, `mute Voc-Claude`, and the assistant also fixes the narrow transcription artifact where a leading `mets` command is fused with the following channel name.

### Changing Model Provider

The voice assistant supports OpenAI and Ollama through LangChain. Any selected model must support tool calling.

```python
# Using OpenAI (default)
assistant = VoiceAssistant(
    openai_api_key="your-key",
    model="gpt-4o-mini",
    llm_provider="openai",
    stt_provider="openai-whisper",
    tts_provider="elevenlabs",
)

# Using Ollama, local Whisper, and local pyttsx3
assistant = VoiceAssistant(
    model="qwen3:8b",
    llm_provider="ollama",
    stt_provider="local-whisper",
    local_whisper_model="base",
    tts_provider="pyttsx3",
)
```

**Note**: Only models with tool calling capabilities can be used. Check your model provider's documentation for supported models.
 
 for ollama:
 https://docs.ollama.com/capabilities/tool-calling

#### Using Ollama (Local LLM)

1. Install Ollama and start it:
```bash
ollama serve
```
2. Pull a tool-capable local model:
```bash
ollama pull qwen3:8b
```
3. Run assistant with the offline env profile:
```bash
python voice_assistant/agent.py --env-file .env.offline
```

The offline profile uses:
```bash
LLM_PROVIDER=ollama
OPENAI_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
STT_PROVIDER=local-whisper
LOCAL_WHISPER_MODEL=base
TTS_PROVIDER=pyttsx3
MCP_CONFIG=mcp_servers.offline.json
```

When `LLM_PROVIDER=ollama`, the app stays on Ollama. Start `ollama serve` and pull the selected model before running the assistant.

### Changing Voice Settings

Pass different parameters when initializing. For offline mode, use `tts_provider="pyttsx3"`; for silent text-only output, use `tts_provider="none"`.

```python
assistant = VoiceAssistant(
    openai_api_key="your-key",
    elevenlabs_api_key="your-key",
    tts_provider="elevenlabs",
    elevenlabs_voice_id="different-voice-id",  # Change voice
    silence_threshold=300,  # More sensitive
    silence_duration=2.0,   # Wait longer
    model="gpt-3.5-turbo"  # Faster model
)
```

Nice voice ID examples:

The web monitor voice dropdown is populated from `ELEVENLABS_VOICE_OPTIONS` in the selected `.env` profile, not from this README. Define the voices you want to expose like this:

```env
ELEVENLABS_VOICE_OPTIONS=kENkNtk0xyzG09WW40xE (Marcel), 1EmYoP3UnnnwhlJKovEy (Anthony), FFXYdAYPzn8Tw8KiHZqg (Ingrid), YxrwjAKoUKULGd0g8K9Y (Lucie)
ELEVENLABS_VOICE_ID=1EmYoP3UnnnwhlJKovEy
```

Each entry uses `voice_id (Display name)`. The dropdown shows the display name and saves the selected voice ID to `ELEVENLABS_VOICE_ID`.

## Troubleshooting

### Common Issues

1. **No Audio Input Detected**
   - Check microphone permissions
   - Lower the `silence_threshold` value
   - Verify PyAudio: `python -c "import pyaudio; pyaudio.PyAudio()"`
   - If no default input device is available, the assistant falls back to text commands instead of retrying microphone capture in a tight loop
   - With the web monitor enabled, use the **Inject Command** field; without it, type commands in the terminal prompt

2. **TTS Not Working**
   - Verify API keys are set correctly
   - Check API quotas
   - Use `TTS_PROVIDER=pyttsx3` in the selected env file for fully local TTS
   - System will fall back to pyttsx3 if ElevenLabs fails
   - On Ubuntu/Debian/Raspberry Pi OS, install the system TTS/audio packages: `sudo apt-get install alsa-utils ffmpeg espeak espeak-ng libespeak1 libespeak-ng1`
   - In headless environments without ALSA, `ffplay`, or `aplay`, spoken output is skipped without noisy playback errors. Use `TTS_PROVIDER=none` to make silent mode explicit.

3. **MCP Server Connection Issues**
   - Ensure Node.js is installed
   - Check internet connection for first-time npx downloads
   - Use `MCP_CONFIG=mcp_servers.offline.json` in the selected env file for local-only MCP servers
   - Verify API keys for specific servers
   - For mixer control, set the `mixer` script path in the selected MCP JSON file to the real `XMSeries-MCP/dist/index.js` path
   - If a configured command or script path is missing, the assistant reports that this MCP server instance could not be started and keeps running with the remaining servers

4. **Thinking Sound Or Audio Output Unavailable**
   - If `pygame` cannot open an audio device, the assistant continues without the thinking sound
   - Set `THINKING_SOUND_FILE=` to leave the thinking sound unset
   - Install an audio backend such as `ffmpeg` or `alsa-utils` only if you need local audio playback

5. **MCP Startup Instructions Not Loaded**
   - Confirm `MCP_LOAD_SERVER_PROMPT=true` in the selected env file
   - Confirm the selected `MCP_CONFIG` file has at least one server with an `assistantPrompt` block
   - Confirm each `assistantPrompt` block defines at least one of `promptName`, `resourceUri`, or `tool`
   - Check the startup warnings for unsupported prompts/resources or a missing fallback tool
   - If the prompt source belongs to a server instance that could not start, such as `mixer`, fix that server's command or script path in the selected MCP JSON file
   - Use `MCP_PROMPT_MERGE_MODE=append` when you want to keep the local voice and TTS constraints

6. **High Latency**
   - Use faster LLM model (e.g., `gpt-3.5-turbo`)
   - Reduce `max_steps` in MCPAgent
   - Consider using local models

7. **Offline Mode Still Tries to Connect**
   - Confirm you started with `python voice_assistant/agent.py --env-file .env.offline`
   - Confirm the selected env file includes `LLM_PROVIDER=ollama`
   - Confirm the selected env file includes `STT_PROVIDER=local-whisper`
   - Confirm the selected env file includes `TTS_PROVIDER=pyttsx3` or `TTS_PROVIDER=none`
   - Confirm the selected env file includes `MCP_CONFIG=mcp_servers.offline.json`
   - Ensure the Ollama model, faster-whisper model, and MCP npm packages were cached before disconnecting

8. **Auto Mode Selected The Wrong Profile**
   - Start with `python voice_assistant/agent.py --env-file auto`
   - Auto mode checks a short TCP connection to `api.openai.com:443`
   - If that host is blocked by your network, auto mode may select `.env.offline`
   - If `.env.online` is selected, make sure `OPENAI_API_KEY.txt` and `ELEVENLABS_API_KEY.txt` exist when those services are configured
   - When the connection status changes, auto mode cancels the current recording or request if needed, then restarts the assistant with `.env.online` or `.env.offline`
