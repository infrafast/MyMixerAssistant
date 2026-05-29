# Synology DSM Docker Deployment

This setup is intended for Synology DSM 7.x with Docker/Container Manager.

## Difficulty

The application itself is not hard to containerize: it is a Python service with Node.js available for MCP servers.

The harder parts are runtime integrations:

- Microphone and speaker access require `/dev/snd` passthrough and working ALSA support on the NAS.
- The mixer MCP server needs LAN access to the mixer, so `network_mode: host` is the simplest Synology setup.
- Offline mode needs Ollama and local Whisper model caches available to the container.
- The XMSeries-MCP repository must be mounted after it has been installed and built.

For a first Synology deployment, use the web monitor and text command injection with `TTS_PROVIDER=none`.

## Files

- `Dockerfile`: builds the Python app image with audio, ffmpeg, Node.js, and npm support.
- `docker-compose.synology.yml`: host-network Synology compose file.
- `.env.synology.example`: copy to `synology/.env` and edit for the NAS.
- `mcp_servers.synology.json`: mixer-only MCP config for a mounted XMSeries-MCP checkout.
- `.dockerignore`: keeps local virtualenvs, caches, and API key files out of the image.

## Folder Layout On The NAS

Create a project folder such as:

```text
/volume1/docker/live-stage-assistant/
  docker-compose.yml
  synology/
    .env
    OPENAI_API_KEY.txt
    ELEVENLABS_API_KEY.txt
    mcp_servers.synology.json
  data/
  XMSeries-MCP/
```

Copy `.env.synology.example` to `synology/.env`.
Copy `mcp_servers.synology.json` to `synology/mcp_servers.synology.json`.
Put API keys in the two text files, or leave the ElevenLabs file empty if `TTS_PROVIDER=none`.

## XMSeries-MCP

If you use the mixer server, clone/install/build XMSeries-MCP before starting the assistant, then mount it as `/xmseries-mcp`.
The compose file already includes the commented volume line:

```yaml
- ./XMSeries-MCP:/xmseries-mcp:ro
```

Enable that line after the folder exists and contains `dist/index.js`.
The corresponding MCP server path is configured in `synology/mcp_servers.synology.json`, not in the agent `.env` file:

```json
"args": ["/xmseries-mcp/dist/index.js"]
```

## Start

From SSH:

```bash
docker compose -f docker-compose.synology.yml up --build -d
docker logs -f live-stage-assistant
```

Or in Synology Container Manager/Project, create a project from the compose file.

The monitor will be reachable at:

```text
http://NAS_IP:8765
```

## Audio Notes

The compose file maps `/dev/snd` and adds the `audio` group. This is only useful if the NAS exposes compatible audio hardware to Docker.
If audio does not work, the app should fall back to text commands through the web monitor.

Recommended first-run settings:

```env
WEB_MONITOR_HOST=0.0.0.0
WEB_MONITOR_PORT=8765
TTS_PROVIDER=none
STT_PROVIDER=openai-whisper
LLM_PROVIDER=openai
```

Once the monitor path is stable, try microphone/speaker passthrough if needed.
