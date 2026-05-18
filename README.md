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

A voice-enabled AI personal assistant that leverages the Model Context Protocol (MCP) to integrate multiple tools and services through natural voice interactions.

## Features

- 🎤 **Voice Input**: Real-time speech-to-text using OpenAI Whisper API or local Whisper
- 🔊 **Voice Output**: High-quality text-to-speech using ElevenLabs, pyttsx3, or no spoken output
- 🤖 **AI-Powered**: Conversational AI with memory persistence
- 🌐 **Multiple Model Providers**: Works with OpenAI or local Ollama models that support tool calling
- 🛠️ **Multi-Tool Integration**: Seamlessly connects to any MCP servers:
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


### Running the Assistant

After installation, run the assistant:

```bash
# Using uv
uv run python voice_assistant/agent.py

# Or using python directly
python voice_assistant/agent.py

# Override specific settings via command line
python voice_assistant/agent.py --model gpt-4o-mini --silence-threshold 300

# Use Ollama local model
python voice_assistant/agent.py --llm-provider ollama --model qwen3:8b

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

Donc, par défaut, il utilise :
LLM : OpenAI avec gpt-4o-mini
STT : Whisper via l’API OpenAI
TTS : ElevenLabs si ELEVENLABS_API_KEY existe, sinon fallback pyttsx3
MCP config : mcp_servers.json, donc actuellement playwright + linear
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

4. **High Latency**
   - Use faster LLM model (e.g., `gpt-3.5-turbo`)
   - Reduce `max_steps` in MCPAgent
   - Consider using local models

5. **Offline Mode Still Tries to Connect**
   - Confirm the command includes `--llm-provider ollama`
   - Confirm the command includes `--stt-provider local-whisper`
   - Confirm the command includes `--tts-provider pyttsx3` or `--tts-provider none`
   - Confirm the command includes `--mcp-config mcp_servers.offline.json`
   - Ensure the Ollama model, faster-whisper model, and MCP npm packages were cached before disconnecting

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on top of [mcp-use](https://github.com/modelcontextprotocol/mcp-use)
- Uses [OpenAI Whisper](https://openai.com/research/whisper) for speech recognition
- Voice synthesis powered by [ElevenLabs](https://elevenlabs.io)
- MCP servers from the [Model Context Protocol](https://modelcontextprotocol.org) ecosystem

## Support

- 📧 Email: your.email@example.com
- 💬 Discord: [Join our server](https://discord.gg/yourinvite)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/mcp-voice-assistant/issues)
- 📖 Documentation: [Full Docs](https://docs.yourproject.com)
