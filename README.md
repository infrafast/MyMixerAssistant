<h1 align="center"> MCP Voice Assistant </h1>
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

## Features

- 🎤 **Voice Input**: Real-time speech-to-text using OpenAI Whisper API or local Whisper
- 🔊 **Voice Output**: High-quality text-to-speech using ElevenLabs, pyttsx3, or no spoken output
- 🤖 **AI-Powered**: Conversational AI with memory persistence
- 🌐 **Multiple Model Providers**: Works with OpenAI or local Ollama models that support tool calling
- 🛠️ **Multi-Tool Integration**: Seamlessly connects to any MCP servers:
- 🧭 **MCP-provided Startup Instructions**: Optionally loads system instructions from MCP prompts, resources, or one configured fallback tool
- 💾 **Conversational Memory**: Maintains context across interactions
- 🎯 **Extensible**: Easy to add new MCP servers and capabilities
- 📴 **Offline Mode**: Can run with Ollama, local Whisper, pyttsx3, and local MCP servers after models/packages are installed

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ User Voice  │ --> │ Speech-to-   │ --> │  LLM with   │ --> │ Text-to-     │
│   Input     │     │ Text (STT)   │     │  MCPAgent   │     │ Speech (TTS) │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                         Whisper                 │                ElevenLabs
                    API or local                 │                or pyttsx3
                                                 │
                                          ┌──────▼──────┐
                                          │ MCP Servers │
                                          ├─────────────┤
                                          │ • Linear    │
                                          │ • Playwright│
                                          │ • Filesystem│
                                          └─────────────┘
```

## Installation

### Prerequisites

1. **Python 3.11+**
2. **uv** (Python package manager): `pip install uv` or `pipx install uv`
3. **Node.js** (for MCP servers)
4. **System dependencies**:
   - macOS: `brew install portaudio`
   - Ubuntu/Debian: `sudo apt-get install portaudio19-dev`
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
# Required only when using OpenAI LLM or OpenAI Whisper API
OPENAI_API_KEY=your-openai-api-key

# Optional but recommended for better voice output
ELEVENLABS_API_KEY=your-elevenlabs-api-key

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

# Text-to-speech settings
TTS_PROVIDER=elevenlabs                         # elevenlabs | pyttsx3 | none

# Voice Settings
ELEVENLABS_VOICE_ID=ZF6FPAbjXT4488VcRRnw      # Default: Rachel voice

# Optional - Audio Configuration
VOICE_SILENCE_THRESHOLD=500                     # Lower = more sensitive
VOICE_SILENCE_DURATION=1.5                      # Seconds to wait after speech

# Optional - Assistant Configuration
ASSISTANT_SYSTEM_PROMPT="You are a helpful voice assistant..."  # Customize personality
MCP_CONFIG=mcp_servers.offline.json             # Optional config override

# Optional - MCP-provided Assistant Instructions
MCP_LOAD_SERVER_PROMPT=false                    # true | false, default false
MCP_PROMPT_SERVER=mixer                         # Logical server name from mcp_servers.json
MCP_PROMPT_NAME=xmseries_mixer_assistant        # Optional MCP prompt name
MCP_PROMPT_RESOURCE_URI=xmseries://prompt/system # Optional MCP resource URI
MCP_PROMPT_TOOL=osc_get_agent_prompt            # Optional fallback tool name
MCP_PROMPT_SOURCES='[{"server":"mixer","prompt_name":"xmseries_mixer_assistant"},{"server":"lights","resource_uri":"lights://prompt/system"}]' # Optional multi-server JSON list
MCP_PROMPT_MERGE_MODE=append                    # append | replace, default append

# Optional - MCP Server Specific
LINEAR_API_KEY=your-linear-api-key              # For Linear integration
```

All environment variables can be overridden via command-line arguments when using the CLI.

### MCP Server Configuration

The assistant loads MCP server configurations from `mcp_servers.json` in the project root. By default, it includes:

- **playwright**: Web automation and browser control
- **linear**: Task and project management

For offline mode, use `mcp_servers.offline.json`:

- **filesystem**: local filesystem access inside the configured root
- **memory**: local MCP memory server

```bash
python voice_assistant/agent.py --mcp-config mcp_servers.offline.json
```

To add more servers, edit `mcp_servers.json` or copy `mcp_servers.example.json` which includes additional servers like:
- filesystem, github, gitlab, google-drive, postgres, sqlite, slack, memory, puppeteer, brave-search, fetch

Environment variables in the config (like `${GITHUB_PERSONAL_ACCESS_TOKEN}`) are automatically substituted from your `.env` file.

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
MCP_PROMPT_SERVER=mixer
```

`MCP_PROMPT_SERVER` must match the logical server name in your MCP config:

```json
{
  "mcpServers": {
    "mixer": {
      "command": "node",
      "args": ["path/to/server.js"]
    }
  }
}
```

The assistant tries only the sources you configure, in this order:

1. `MCP_PROMPT_NAME`: fetch an MCP prompt with `prompts/get`
2. `MCP_PROMPT_RESOURCE_URI`: read an MCP resource with `resources/read`
3. `MCP_PROMPT_TOOL`: call exactly this fallback tool with empty arguments

It never calls arbitrary tools while loading startup instructions. If the server is missing, does not support prompts/resources, does not expose the configured fallback tool, or returns an error, the assistant logs a warning and continues with the local prompt.

Single-server example configuration:

```bash
MCP_LOAD_SERVER_PROMPT=true
MCP_PROMPT_SERVER=mixer
MCP_PROMPT_NAME=xmseries_mixer_assistant
MCP_PROMPT_RESOURCE_URI=xmseries://prompt/system
MCP_PROMPT_TOOL=osc_get_agent_prompt
MCP_PROMPT_MERGE_MODE=append
```

For several MCP servers, use `MCP_PROMPT_SOURCES`. It is an ordered JSON list. When it is set, it takes precedence over the single-source variables `MCP_PROMPT_SERVER`, `MCP_PROMPT_NAME`, `MCP_PROMPT_RESOURCE_URI`, and `MCP_PROMPT_TOOL`.

Multi-server example configuration:

```bash
MCP_LOAD_SERVER_PROMPT=true
MCP_PROMPT_SOURCES='[
  {"server":"mixer","prompt_name":"xmseries_mixer_assistant"},
  {"server":"lights","resource_uri":"lights://prompt/system"},
  {"server":"stage","tool":"stage_get_agent_prompt"}
]'
MCP_PROMPT_MERGE_MODE=append
```

Each source can define:

1. `server`: required, the logical server name under `mcpServers`
2. `prompt_name`: optional MCP prompt name
3. `resource_uri`: optional MCP resource URI
4. `tool`: optional explicit fallback tool name

For each source, the assistant tries `prompt_name`, then `resource_uri`, then `tool`. It then moves to the next source. A failing source logs a warning and does not block the others.

At startup, when instructions are loaded, the assistant writes a console log entry listing the MCP prompt sources that were actually merged, for example:

```text
Loaded and merged 2 MCP prompt source(s) with merge mode 'append': mixer via prompt 'xmseries_mixer_assistant'; lights via resource 'lights://prompt/system'
```

With `MCP_PROMPT_MERGE_MODE=append`, the local prompt stays first and the remote instructions are appended under:

example:
python voice_assistant/agent.py --mcp-load-server-prompt --mcp-prompt-server mixer  --mcp-prompt-sources '[{"server":"mixer","prompt_name":"xmseries_mixer_assistant"}]' --mcp-prompt-merge-mode append 


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

The same settings can be provided through CLI flags:

```bash
python voice_assistant/agent.py \
  --mcp-load-server-prompt \
  --mcp-prompt-server mixer \
  --mcp-prompt-name xmseries_mixer_assistant \
  --mcp-prompt-resource-uri xmseries://prompt/system \
  --mcp-prompt-tool osc_get_agent_prompt \
  --mcp-prompt-merge-mode append
```

Multi-server CLI example:

```bash
python voice_assistant/agent.py \
  --mcp-load-server-prompt \
  --mcp-prompt-sources '[{"server":"mixer","prompt_name":"xmseries_mixer_assistant"},{"server":"lights","resource_uri":"lights://prompt/system"}]' \
  --mcp-prompt-merge-mode append
```


### Running the Assistant

After installation, run the assistant:

```bash
# Using uv
uv run python voice_assistant/agent.py

# Or using python directly
python voice_assistant/agent.py

# Override specific settings via command line
python voice_assistant/agent.py --model gpt-4o-mini --silence-threshold 300

# Example how to use only local model
python voice_assistant/agent.py --llm-provider ollama --model qwen3:8b --local-whisper-model base --tts-provider pyttsx3

# Offline mode after local models and MCP packages are cached
python voice_assistant/agent.py \
  --llm-provider ollama \
  --model qwen3:8b \
  --stt-provider local-whisper \
  --local-whisper-model base \
  --tts-provider pyttsx3 \
  --mcp-config mcp_servers.offline.json

# Provide all settings via command line (no .env needed)
python voice_assistant/agent.py \
  --openai-api-key YOUR_KEY \
  --elevenlabs-api-key YOUR_ELEVENLABS_KEY \
  --model gpt-4 \
  --stt-provider openai-whisper \
  --tts-provider elevenlabs \
  --voice-id ZF6FPAbjXT4488VcRRnw \
  --silence-threshold 500 \
  --silence-duration 1.5

# Load optional startup instructions from one configured MCP server
python voice_assistant/agent.py \
  --mcp-load-server-prompt \
  --mcp-prompt-server mixer \
  --mcp-prompt-name xmseries_mixer_assistant \
  --mcp-prompt-merge-mode append

# Load startup instructions from several configured MCP servers
python voice_assistant/agent.py \
  --mcp-load-server-prompt \
  --mcp-prompt-sources '[{"server":"mixer","prompt_name":"xmseries_mixer_assistant"},{"server":"lights","resource_uri":"lights://prompt/system"}]' \
  --mcp-prompt-merge-mode append

# See all available options
python voice_assistant/agent.py --help
```

**Note**: Command-line arguments take precedence over environment variables. `OPENAI_API_KEY` is not required when both `--llm-provider ollama` and `--stt-provider local-whisper` are used.


Si tu lances simplement : python voice_assistant/agent.py

les paramètres par défaut sont :

--llm-provider openai
--model gpt-4o-mini
--ollama-base-url http://localhost:11434

--stt-provider openai-whisper
--local-whisper-model base
--stt-language auto

--tts-provider elevenlabs
--voice-id 1EmYoP3UnnnwhlJKovEy

--silence-threshold 500
--silence-duration 1.5

--mcp-config non défini
--mcp-load-server-prompt false
--mcp-prompt-merge-mode append

Donc, par défaut, il utilise :
LLM : OpenAI avec gpt-4o-mini
STT : Whisper via l’API OpenAI
TTS : ElevenLabs si ELEVENLABS_API_KEY existe, sinon fallback pyttsx3
MCP config : mcp_servers.json, donc actuellement playwright + linear
Prompt MCP au démarrage : désactivé, donc seul le prompt local est utilisé
Langue transcription : auto-detection
Voix ElevenLabs : 1EmYoP3UnnnwhlJKovEy
Important : sans paramètres, OPENAI_API_KEY est obligatoire, parce que le LLM par défaut est OpenAI et le STT par défaut est aussi OpenAI Whisper.


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
3. Run assistant with Ollama provider:
```bash
python voice_assistant/agent.py --llm-provider ollama --model qwen3:8b
```

For a full offline run, also select local Whisper, local TTS, and local MCP config:
```bash
python voice_assistant/agent.py \
  --llm-provider ollama \
  --model qwen3:8b \
  --stt-provider local-whisper \
  --tts-provider pyttsx3 \
  --mcp-config mcp_servers.offline.json
```

You can also configure this via `.env`:
```bash
LLM_PROVIDER=ollama
OPENAI_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
STT_PROVIDER=local-whisper
LOCAL_WHISPER_MODEL=base
TTS_PROVIDER=pyttsx3
MCP_CONFIG=mcp_servers.offline.json
```

compatibles models for an imac 24Gb could be:
- qwen3:8b (ou tag équivalent disponible dans ta lib Ollama) Bon compromis qualité/vitesse pour agent outillé.
- llama3.1:8b Très stable, largement utilisé, bon fallback.
- mistral-nemo:12b Plus lourd, mais souvent meilleur en raisonnement/instructions.
- command-r-plus (si tu acceptes plus de latence/ressources) Très bon en usage “tools/RAG”, mais plus coûteux localement.


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

### Evolutions

1. introduce a "thinking" looping sound which is played between the user prompt and until the TTS reply to the user so he has a semantic feedback that his request is being processed
2. add a web page to configure all the environement variables
3. if agent.py is called with parameter "--auto" , add a mecasnism to check internet connexion at startup and then monitor it at periodic interval (every 10sec.) so the system can determine dynamically which configuration he uses (offline or online) to use the right provider for TTS, STT and LLM. This forces and superseed all parameters
4. 

1. **No Audio Input Detected**


## Troubleshooting

### Common Issues

1. **No Audio Input Detected**
   - Check microphone permissions
   - Lower the `silence_threshold` value
   - Verify PyAudio: `python -c "import pyaudio; pyaudio.PyAudio()"`

2. **TTS Not Working**
   - Verify API keys are set correctly
   - Check API quotas
   - Use `--tts-provider pyttsx3` for fully local TTS
   - System will fall back to pyttsx3 if ElevenLabs fails

3. **MCP Server Connection Issues**
   - Ensure Node.js is installed
   - Check internet connection for first-time npx downloads
   - Use `--mcp-config mcp_servers.offline.json` for local-only MCP servers
   - Verify API keys for specific servers

4. **MCP Startup Instructions Not Loaded**
   - Confirm `MCP_LOAD_SERVER_PROMPT=true` or pass `--mcp-load-server-prompt`
   - For single-source mode, confirm `MCP_PROMPT_SERVER` matches a key under `mcpServers`
   - For multi-source mode, confirm every `server` in `MCP_PROMPT_SOURCES` matches a key under `mcpServers`
   - Configure at least one of `MCP_PROMPT_NAME`, `MCP_PROMPT_RESOURCE_URI`, or `MCP_PROMPT_TOOL`, or provide `MCP_PROMPT_SOURCES`
   - Ensure `MCP_PROMPT_SOURCES` is valid JSON when using multi-source mode
   - Check the startup warnings for unsupported prompts/resources or a missing fallback tool
   - Use `MCP_PROMPT_MERGE_MODE=append` when you want to keep the local voice and TTS constraints

5. **High Latency**
   - Use faster LLM model (e.g., `gpt-3.5-turbo`)
   - Reduce `max_steps` in MCPAgent
   - Consider using local models

6. **Offline Mode Still Tries to Connect**
   - Confirm the command includes `--llm-provider ollama`
   - Confirm the command includes `--stt-provider local-whisper`
   - Confirm the command includes `--tts-provider pyttsx3` or `--tts-provider none`
   - Confirm the command includes `--mcp-config mcp_servers.offline.json`
   - Ensure the Ollama model, faster-whisper model, and MCP npm packages were cached before disconnecting
