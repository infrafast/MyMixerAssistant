"""
Voice-First AI Personal Assistant with MCP Integration (Improved Version)

This example demonstrates a voice-enabled personal assistant that uses:
- Speech-to-text for voice input (OpenAI Whisper API or local Whisper)
- MCPAgent with multiple MCP servers (Linear, filesystem)
- Text-to-speech for voice output (ElevenLabs speak, system TTS, or none)

This version includes better error handling and fallback options.
"""

import asyncio
import io
import json
import logging
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import wave

import numpy as np
import openai
import pyaudio
import pygame
import pyttsx3
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from elevenlabs.types.voice_settings import VoiceSettings
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient
from pydantic import AnyUrl

TTS_ENGINE = pyttsx3.init()
TTS_LOCK = threading.Lock()
DEFAULT_ELEVENLABS_VOICE_ID = "1EmYoP3UnnnwhlJKovEy"  # french male; ZF6FPAbjXT4488VcRRnw = english female
LOGGER = logging.getLogger(__name__)
AUTO_ENV_ONLINE = Path(".env.online")
AUTO_ENV_OFFLINE = Path(".env.offline")
AUTO_CONNECTIVITY_HOST = "api.openai.com"
AUTO_CONNECTIVITY_PORT = 443
AUTO_CONNECTIVITY_TIMEOUT = 2.0
AUTO_CHECK_INTERVAL = 10.0
EXTERNAL_STATE_FRESHNESS_RULE = (
    "Use conversation memory for context, preferences, and follow-up references, but not as the source of truth "
    "for live external state. When the user asks about the current state of anything outside this conversation, "
    "treat the answer as time-sensitive. Use the relevant MCP read tool before answering. Do not answer current "
    "external state from memory, previous tool results, or assumptions. If no suitable read tool is available, "
    "say that you cannot verify the current state."
)
CURRENT_STATE_QUERY_MARKERS = (
    "current",
    "currently",
    "now",
    "right now",
    "status",
    "state",
    "value",
    "level",
    "position",
    "configuration",
    "how much",
    "what is",
    "what's",
    "etat",
    "état",
    "actuel",
    "actuelle",
    "maintenant",
    "en ce moment",
    "statut",
    "valeur",
    "niveau",
    "combien",
    "quel est",
    "quelle est",
    "a combien",
    "à combien",
)


def check_internet_connection(
    host: str = AUTO_CONNECTIVITY_HOST,
    port: int = AUTO_CONNECTIVITY_PORT,
    timeout: float = AUTO_CONNECTIVITY_TIMEOUT,
) -> bool:
    """Return whether a short TCP connection to a known internet host succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def read_secret_from_env_values(values: dict, name: str) -> str | None:
    """Read a secret from a *_FILE entry in a parsed env profile."""
    file_path = (values.get(f"{name}_FILE") or "").strip()
    if not file_path:
        return None

    try:
        secret = Path(file_path).read_text().strip()
    except OSError as e:
        print(f"Auto monitor could not read {name}_FILE '{file_path}': {e}")
        return None

    return secret or None


def speak_auto_network_status(text: str, env_file: Path, dotenv_values_func) -> None:
    """Speak a network status message with the TTS configured by the detected env file."""
    values = dotenv_values_func(env_file)
    tts_provider = (values.get("TTS_PROVIDER") or "elevenlabs").strip().lower()
    voice_id = (values.get("ELEVENLABS_VOICE_ID") or DEFAULT_ELEVENLABS_VOICE_ID).strip()

    with TTS_LOCK:
        if tts_provider == "none":
            print(f"Auto network status: {text}")
            return

        if tts_provider == "elevenlabs":
            elevenlabs_api_key = read_secret_from_env_values(values, "ELEVENLABS_API_KEY")
            if elevenlabs_api_key:
                try:
                    client = ElevenLabs(api_key=elevenlabs_api_key)
                    audio = client.text_to_speech.convert(
                        text=text,
                        voice_id=voice_id,
                        model_id="eleven_multilingual_v2",
                        output_format="mp3_44100_128",
                        optimize_streaming_latency="2",
                        voice_settings=VoiceSettings(speed=1.1),
                    )
                    play(audio)
                    return
                except Exception as e:
                    print(f"Auto network status ElevenLabs TTS failed: {e}")

        try:
            TTS_ENGINE.say(text)
            TTS_ENGINE.runAndWait()
        except Exception as e:
            print(f"Auto network status local TTS failed: {e}")


class AutoNetworkMonitor:
    """Auto monitor: announce internet status changes and request runtime reloads."""

    def __init__(
        self,
        initial_online: bool,
        dotenv_values_func,
        reload_event: threading.Event | None = None,
        interval: float = AUTO_CHECK_INTERVAL,
    ):
        self.current_online = initial_online
        self.dotenv_values_func = dotenv_values_func
        self.reload_event = reload_event
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="auto-network-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def announce_initial_status(self) -> None:
        self._announce(self.current_online)

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval):
            online = check_internet_connection()
            if online == self.current_online:
                continue

            self.current_online = online
            self._announce(online)
            if self.reload_event:
                self.reload_event.set()

    def _announce(self, online: bool) -> None:
        status_text = "Internet est en ligne" if online else "Connexion internet coupée"
        detected_env = AUTO_ENV_ONLINE if online else AUTO_ENV_OFFLINE
        print(f"Auto network status changed: {status_text}. Detected profile: {detected_env}")
        speak_auto_network_status(status_text, detected_env, self.dotenv_values_func)

    @property
    def detected_env_file(self) -> Path:
        return AUTO_ENV_ONLINE if self.current_online else AUTO_ENV_OFFLINE


class VoiceAssistant:
    """Improved voice-enabled AI assistant with better error handling."""

    def __init__(
        self,
        openai_api_key: str | None = None,
        elevenlabs_api_key: str | None = None,
        model: str = "gpt-4o-mini",
        llm_provider: str = "openai",
        ollama_base_url: str = "http://localhost:11434",
        stt_provider: str = "openai-whisper",
        local_whisper_model: str = "base",
        stt_language: str | None = None,
        tts_provider: str = "elevenlabs",
        elevenlabs_voice_id: str = DEFAULT_ELEVENLABS_VOICE_ID,
        thinking_sound_file: str = "thinking.wav",
        silence_threshold: int = 500,
        silence_duration: float = 1.5,
        mcp_config: dict | None = None,
        mcp_load_server_prompt: bool = False,
        mcp_prompt_server: str | None = None,
        mcp_prompt_name: str | None = None,
        mcp_prompt_resource_uri: str | None = None,
        mcp_prompt_tool: str | None = None,
        mcp_prompt_sources: list[dict] | None = None,
        mcp_prompt_merge_mode: str = "append",
        mcp_agent_memory_enabled: bool = True,
        notes_dir: str | None = None,
        system_prompt: str | None = None,
        reload_event: threading.Event | None = None,
    ):
        """Initialize the voice assistant.

        Args:
            openai_api_key: OpenAI API key for Whisper API and GPT models
            elevenlabs_api_key: Optional ElevenLabs API key for TTS
            model: LLM model name to use (default: gpt-4o-mini)
            llm_provider: LLM provider (openai or ollama)
            ollama_base_url: Base URL for local Ollama server
            stt_provider: Speech-to-text provider (openai-whisper or local-whisper)
            local_whisper_model: Local faster-whisper model size or path
            stt_language: Transcription language code, or None for auto-detect
            tts_provider: Text-to-speech provider (elevenlabs, pyttsx3, or none)
            elevenlabs_voice_id: ElevenLabs voice ID (default: Rachel)
            thinking_sound_file: WAV file to loop while the LLM/MCP agent is processing a command
            silence_threshold: Audio silence detection threshold
            silence_duration: How long to wait after speech stops
            mcp_config: Optional MCP server configuration dict
            mcp_load_server_prompt: Whether to load extra system instructions from an MCP server
            mcp_prompt_server: Logical MCP server name to query for instructions
            mcp_prompt_name: Optional MCP prompt name to fetch
            mcp_prompt_resource_uri: Optional MCP resource URI to read
            mcp_prompt_tool: Optional fallback MCP tool name to call for prompt text
            mcp_prompt_sources: Optional ordered list of MCP prompt sources
            mcp_prompt_merge_mode: How to merge remote instructions: append or replace
            mcp_agent_memory_enabled: Whether MCPAgent should keep conversation memory
            notes_dir: Directory for storing notes (default: temp dir)
            system_prompt: Optional custom system prompt for the assistant
            reload_event: Optional event used by auto mode to interrupt and reload the assistant
        """
        # Audio configuration
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        # Initialize audio components
        self.audio = pyaudio.PyAudio()
        pygame.mixer.init()

        # Speech-to-text configuration
        self.openai_api_key = openai_api_key
        self.stt_provider = stt_provider.lower()
        self.local_whisper_model_name = local_whisper_model
        self.stt_language = stt_language or None
        self.openai_client = None
        self.local_whisper_model = None
        if self.stt_provider == "openai-whisper":
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

        self.model = model
        self.llm_provider = llm_provider.lower()
        self.ollama_base_url = ollama_base_url

        # ElevenLabs client for text-to-speech
        self.tts_provider = tts_provider.lower()
        self.elevenlabs_client = None
        self.elevenlabs_voice_id = elevenlabs_voice_id
        if self.tts_provider == "elevenlabs" and elevenlabs_api_key:
            self.elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

        # Short audio feedback while the agent is processing the user's command.
        self.thinking_sound_file = thinking_sound_file or "thinking.wav"
        self.thinking_sound_path = self._resolve_asset_path(self.thinking_sound_file)
        self.thinking_sound = None
        self.thinking_sound_channel = None
        self.thinking_sound_warning_shown = False
        self.thinking_sound_lock = threading.Lock()
        if self.thinking_sound_path:
            try:
                self.thinking_sound = pygame.mixer.Sound(str(self.thinking_sound_path))
            except pygame.error as e:
                print(f"Could not load thinking sound '{self.thinking_sound_path}': {e}")
                self.thinking_sound_warning_shown = True

        # MCP configuration
        self.mcp_config = mcp_config
        self.mcp_load_server_prompt = mcp_load_server_prompt
        self.mcp_prompt_server = mcp_prompt_server
        self.mcp_prompt_name = mcp_prompt_name
        self.mcp_prompt_resource_uri = mcp_prompt_resource_uri
        self.mcp_prompt_tool = mcp_prompt_tool
        self.mcp_prompt_sources = mcp_prompt_sources or []
        self.mcp_prompt_merge_mode = (mcp_prompt_merge_mode or "append").lower()
        self.mcp_agent_memory_enabled = mcp_agent_memory_enabled
        self.mcp_client = None
        self.agent = None
        self.reload_event = reload_event
        
        #self.system_prompt = system_prompt or (
        #    "You are a helpful voice assistant with access to various tools. Your name is mcp-use "
        #    "Be concise in your responses since they will be spoken aloud. Summarize your results. "
        #    "Reply in the same language as the user's latest request whenever possible. "
        #    "Behave like a great motivational speaker, and motivate me throughout the conversation."
        #)

        base_system_prompt = system_prompt or (
            "You are a helpful voice assistant with access to various tools. Your name is Live Stage Assistant. "
            "Be concise in your responses since they will be spoken aloud and have to be suitable for text-to-speech and API calls.. Summarize your results. "
            "Reply in the same language as the user's latest request whenever possible. "
            "Use plain text only. Do not use emojis, emoticons, markdown, bullets, symbols, or decorative characters. "
            "Behave like a friendly calm and motivating assistant."
        )
        self.system_prompt = f"{base_system_prompt.rstrip()} {EXTERNAL_STATE_FRESHNESS_RULE}"

        # Create a proper notes directory
        if notes_dir:
            self.notes_dir = notes_dir
        else:
            self.notes_dir = os.path.join(tempfile.gettempdir(), "voice_assistant_notes")
        os.makedirs(self.notes_dir, exist_ok=True)

        self._log_configured_mcp_prompt_sources()

    def _resolve_asset_path(self, value: str) -> Path | None:
        """Resolve a configured asset path, falling back to ./assets for bare filenames."""
        configured_path = Path(value).expanduser()
        if configured_path.is_absolute() and configured_path.exists():
            return configured_path

        if configured_path.exists():
            return configured_path

        assets_path = Path("assets") / configured_path
        if assets_path.exists():
            return assets_path

        return None

    def start_thinking_sound(self) -> None:
        """Loop the configured thinking sound until stop_thinking_sound is called."""
        if not self.thinking_sound:
            if not self.thinking_sound_warning_shown:
                print(
                    f"Thinking sound '{self.thinking_sound_file}' not found. "
                    "Set THINKING_SOUND_FILE to a WAV file or place it in assets/."
                )
                self.thinking_sound_warning_shown = True
            return

        with self.thinking_sound_lock:
            if self.thinking_sound_channel and self.thinking_sound_channel.get_busy():
                return
            self.thinking_sound_channel = self.thinking_sound.play(loops=-1)

    def stop_thinking_sound(self) -> None:
        """Stop the thinking sound if it is currently playing."""
        with self.thinking_sound_lock:
            if self.thinking_sound_channel:
                self.thinking_sound_channel.stop()
                self.thinking_sound_channel = None

    def _substitute_env_vars(self, config):
        """Recursively substitute environment variable placeholders in config."""
        if isinstance(config, dict):
            result = {}
            for key, value in config.items():
                result[key] = self._substitute_env_vars(value)
            return result

        if isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]

        if isinstance(config, str):
            # Support full-value env placeholders like "${API_KEY}"
            if config.startswith("${") and config.endswith("}"):
                env_key = config[2:-1]
                return os.getenv(env_key, "")
            return config

        return config

    def _build_llm(self):
        """Build the configured LLM."""
        if self.llm_provider == "ollama":
            print(f"Using Ollama model: {self.model} ({self.ollama_base_url})")
            return ChatOllama(model=self.model, base_url=self.ollama_base_url)

        print(f"Using OpenAI model: {self.model}")
        return ChatOpenAI(model=self.model, api_key=self.openai_api_key)

    def _text_from_mcp_content(self, content) -> str | None:
        """Extract text from common MCP prompt/resource/tool content objects."""
        if content is None:
            return None

        if isinstance(content, str):
            return content

        text = getattr(content, "text", None)
        if isinstance(text, str):
            return text

        resource = getattr(content, "resource", None)
        if resource is not None:
            return self._text_from_mcp_content(resource)

        return None

    def _join_mcp_texts(self, values) -> str | None:
        texts = []
        for value in values or []:
            text = self._text_from_mcp_content(value)
            if text:
                texts.append(text.strip())
        joined = "\n\n".join(text for text in texts if text)
        return joined or None

    def _mcp_capability_enabled(self, session, capability_name: str) -> bool | None:
        capabilities = getattr(getattr(session, "connector", None), "capabilities", None)
        if capabilities is None:
            return None
        return bool(getattr(capabilities, capability_name, None))

    def _build_mcp_prompt_sources(self, config: dict) -> list[dict]:
        sources = []
        for server_name, server_config in config.get("mcpServers", {}).items():
            prompt_config = server_config.get("assistantPrompt") or server_config.get("agentPrompt")
            if isinstance(prompt_config, dict):
                source = dict(prompt_config)
                source["server"] = server_name
                sources.append(source)

        if sources:
            return sources

        if self.mcp_prompt_sources:
            return self.mcp_prompt_sources

        if not any([self.mcp_prompt_server, self.mcp_prompt_name, self.mcp_prompt_resource_uri, self.mcp_prompt_tool]):
            return []

        return [
            {
                "server": self.mcp_prompt_server,
                "prompt_name": self.mcp_prompt_name,
                "resource_uri": self.mcp_prompt_resource_uri,
                "tool": self.mcp_prompt_tool,
            }
        ]

    def _source_value(self, source: dict, *keys: str) -> str | None:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _log_configured_mcp_prompt_sources(self) -> None:
        if not self.mcp_config:
            return

        sources = self._build_mcp_prompt_sources(self.mcp_config)
        if not sources:
            return

        if self.mcp_load_server_prompt:
            self._log_mcp_prompt_info(
                "MCP startup prompt loading is enabled; configured source(s): "
                f"{self._describe_mcp_prompt_sources(sources)}"
            )
            return

        self._log_mcp_prompt_warning(
            "MCP startup prompt loading is disabled; configured source(s) will not be loaded: "
            f"{self._describe_mcp_prompt_sources(sources)}"
        )

    def _describe_mcp_prompt_source(self, source: dict) -> str:
        server_name = self._source_value(source, "server", "server_name") or "unspecified"
        prompt_name = self._source_value(source, "promptName", "prompt_name", "prompt", "name")
        resource_uri = self._source_value(source, "resourceUri", "resource_uri", "resource")
        tool_name = self._source_value(source, "tool", "toolName", "tool_name")
        parts = [f"server='{server_name}'"]
        if prompt_name:
            parts.append(f"prompt='{prompt_name}'")
        if resource_uri:
            parts.append(f"resource='{resource_uri}'")
        if tool_name:
            parts.append(f"tool='{tool_name}'")
        return " ".join(parts)

    def _describe_mcp_prompt_sources(self, sources: list[dict]) -> str:
        return "; ".join(self._describe_mcp_prompt_source(source) for source in sources)

    def _log_mcp_prompt_info(self, message: str) -> None:
        print(message)
        LOGGER.info(message)

    def _log_mcp_prompt_warning(self, message: str) -> None:
        print(f"⚠️ Warning: {message}")
        LOGGER.warning(message)

    def _format_loaded_mcp_prompts(self, loaded_prompts: list[dict]) -> str:
        sections = []
        for item in loaded_prompts:
            server_name = item["server"]
            text = item["text"].strip()
            sections.append(f'Instructions loaded from MCP server "{server_name}":\n{text}')
        return "\n\n".join(sections)

    def _describe_loaded_mcp_prompts(self, loaded_prompts: list[dict]) -> str:
        descriptions = []
        for item in loaded_prompts:
            source_type = item.get("source_type") or "unknown"
            source_id = item.get("source_id") or "unspecified"
            descriptions.append(f"{item['server']} via {source_type} '{source_id}'")
        return "; ".join(descriptions)

    def _merge_system_prompt(self, loaded_prompts: list[dict]) -> str:
        remote_prompt = self._format_loaded_mcp_prompts(loaded_prompts)
        if self.mcp_prompt_merge_mode == "replace":
            return remote_prompt

        if self.mcp_prompt_merge_mode != "append":
            self._log_mcp_prompt_warning(
                f"Unsupported MCP_PROMPT_MERGE_MODE '{self.mcp_prompt_merge_mode}'; using append mode."
            )

        return (
            f"{self.system_prompt.rstrip()}\n\n"
            "Additional instructions loaded from MCP servers:\n"
            f"{remote_prompt}"
        )

    async def _get_mcp_prompt_text(self, session, prompt_name: str, server_name: str) -> str | None:
        if not hasattr(session, "get_prompt"):
            self._log_mcp_prompt_warning(f"MCP server '{server_name}' cannot fetch prompts with this mcp-use session.")
            return None
        if self._mcp_capability_enabled(session, "prompts") is False:
            self._log_mcp_prompt_warning(f"MCP server '{server_name}' does not advertise prompt support.")
            return None

        try:
            prompts = await session.list_prompts() if hasattr(session, "list_prompts") else []
            if prompts and prompt_name not in {getattr(prompt, "name", None) for prompt in prompts}:
                self._log_mcp_prompt_warning(f"MCP prompt '{prompt_name}' was not found on server '{server_name}'.")
                return None

            result = await session.get_prompt(prompt_name)
            return self._join_mcp_texts(
                getattr(message, "content", None) for message in getattr(result, "messages", [])
            )
        except Exception as e:
            self._log_mcp_prompt_warning(
                f"Failed to load MCP prompt '{prompt_name}' from server '{server_name}': {e}"
            )
            return None

    async def _get_mcp_resource_text(self, session, resource_uri: str, server_name: str) -> str | None:
        if not hasattr(session, "read_resource"):
            self._log_mcp_prompt_warning(f"MCP server '{server_name}' cannot read resources with this mcp-use session.")
            return None
        if self._mcp_capability_enabled(session, "resources") is False:
            self._log_mcp_prompt_warning(f"MCP server '{server_name}' does not advertise resource support.")
            return None

        try:
            resources = await session.list_resources() if hasattr(session, "list_resources") else []
            if resources and resource_uri not in {str(getattr(resource, "uri", "")) for resource in resources}:
                self._log_mcp_prompt_warning(
                    f"MCP resource '{resource_uri}' was not found on server '{server_name}'."
                )
                return None

            result = await session.read_resource(AnyUrl(resource_uri))
            return self._join_mcp_texts(getattr(result, "contents", []))
        except Exception as e:
            self._log_mcp_prompt_warning(
                f"Failed to read MCP resource '{resource_uri}' from server '{server_name}': {e}"
            )
            return None

    async def _get_mcp_tool_prompt_text(self, session, tool_name: str, server_name: str) -> str | None:
        if not hasattr(session, "call_tool"):
            self._log_mcp_prompt_warning(f"MCP server '{server_name}' cannot call tools with this mcp-use session.")
            return None
        if self._mcp_capability_enabled(session, "tools") is False:
            self._log_mcp_prompt_warning(
                f"MCP server '{server_name}' does not advertise tool support for fallback prompt loading."
            )
            return None

        try:
            tools = await session.list_tools() if hasattr(session, "list_tools") else []
            if tools and tool_name not in {getattr(tool, "name", None) for tool in tools}:
                self._log_mcp_prompt_warning(
                    f"MCP prompt fallback tool '{tool_name}' was not found on server '{server_name}'."
                )
                return None

            result = await session.call_tool(tool_name, {})
            if getattr(result, "isError", False):
                self._log_mcp_prompt_warning(
                    f"MCP prompt fallback tool '{tool_name}' returned an error on server '{server_name}'."
                )
                return None

            text = self._join_mcp_texts(getattr(result, "content", []))
            if text:
                return text

            structured_content = getattr(result, "structuredContent", None)
            if isinstance(structured_content, dict):
                for key in ("prompt", "system_prompt", "instructions", "text"):
                    value = structured_content.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except Exception as e:
            self._log_mcp_prompt_warning(
                f"Failed to call MCP prompt fallback tool '{tool_name}' on server '{server_name}': {e}"
            )
            return None

        return None

    async def _load_prompt_from_mcp_source(self, source: dict, config: dict) -> dict | None:
        server_name = self._source_value(source, "server", "server_name")
        prompt_name = self._source_value(source, "promptName", "prompt_name", "prompt", "name")
        resource_uri = self._source_value(source, "resourceUri", "resource_uri", "resource")
        tool_name = self._source_value(source, "tool", "toolName", "tool_name")

        if not server_name:
            self._log_mcp_prompt_warning("Skipping MCP prompt source without a server name.")
            return None

        if server_name not in config.get("mcpServers", {}):
            self._log_mcp_prompt_warning(
                f"MCP prompt server '{server_name}' is not configured; skipping this prompt source."
            )
            return None

        if not any([prompt_name, resource_uri, tool_name]):
            self._log_mcp_prompt_warning(
                f"MCP prompt source for server '{server_name}' has no prompt name, resource URI, "
                "or fallback tool configured."
            )
            return None

        try:
            session = self.mcp_client.get_session(server_name)
        except ValueError:
            try:
                session = await self.mcp_client.create_session(server_name)
            except Exception as e:
                self._log_mcp_prompt_warning(f"Failed to create MCP session for prompt server '{server_name}': {e}")
                return None

        if session is None:
            self._log_mcp_prompt_warning(f"MCP prompt server '{server_name}' did not provide a usable session.")
            return None

        remote_prompt = None
        source_type = None
        source_id = None
        if prompt_name:
            remote_prompt = await self._get_mcp_prompt_text(session, prompt_name, server_name)
            source_type = "prompt"
            source_id = prompt_name

        if not remote_prompt and resource_uri:
            remote_prompt = await self._get_mcp_resource_text(session, resource_uri, server_name)
            source_type = "resource"
            source_id = resource_uri

        if not remote_prompt and tool_name:
            remote_prompt = await self._get_mcp_tool_prompt_text(session, tool_name, server_name)
            source_type = "tool"
            source_id = tool_name

        if not remote_prompt:
            self._log_mcp_prompt_warning(f"No MCP server instructions were loaded from server '{server_name}'.")
            return None

        return {
            "server": server_name,
            "source_type": source_type,
            "source_id": source_id,
            "text": remote_prompt,
        }

    async def _load_mcp_server_prompt(self, config: dict) -> str | None:
        sources = self._build_mcp_prompt_sources(config)
        if not self.mcp_load_server_prompt:
            return None

        if not sources:
            self._log_mcp_prompt_warning("MCP_LOAD_SERVER_PROMPT is true but no MCP prompt sources are configured.")
            return None

        self._log_mcp_prompt_info(
            "MCP startup prompt loading enabled. Requested source(s): "
            f"{self._describe_mcp_prompt_sources(sources)}"
        )

        loaded_prompts = []
        for source in sources:
            loaded_prompt = await self._load_prompt_from_mcp_source(source, config)
            if loaded_prompt:
                loaded_prompts.append(loaded_prompt)

        if not loaded_prompts:
            self._log_mcp_prompt_warning("No MCP server instructions were loaded; keeping the local system prompt.")
            return None

        loaded_summary = self._describe_loaded_mcp_prompts(loaded_prompts)
        log_message = (
            f"Loaded and merged {len(loaded_prompts)} MCP prompt source(s) "
            f"with merge mode '{self.mcp_prompt_merge_mode}': {loaded_summary}"
        )
        self._log_mcp_prompt_info(log_message)

        return self._merge_system_prompt(loaded_prompts)

    async def _create_missing_mcp_sessions(self) -> None:
        """Create any sessions not already opened by startup prompt loading."""
        for server_name in self.mcp_client.get_server_names():
            if server_name not in self.mcp_client.sessions:
                await self.mcp_client.create_session(server_name)

    async def initialize_mcp(self):
        """Initialize MCP client and agent with proper error handling."""
        print("Initializing MCP servers...")
        config = {"mcpServers": {}}

        # Use provided config or load from file
        if self.mcp_config:
            config = self.mcp_config
        else:
            # Try to load from mcp_servers.json
            config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_servers.json")
            if os.path.exists(config_file):
                with open(config_file) as f:
                    config = json.load(f)

        # Replace environment variable placeholders
        config = self._substitute_env_vars(config)

        try:
            # Create MCP client
            self.mcp_client = MCPClient.from_dict(config)
            merged_prompt = await self._load_mcp_server_prompt(config)
            if merged_prompt:
                self.system_prompt = merged_prompt
            if self.mcp_load_server_prompt and self.mcp_client.sessions:
                await self._create_missing_mcp_sessions()

            # Create LLM
            llm = self._build_llm()

            # Create agent with memory
            self.agent = MCPAgent(
                llm=llm,
                client=self.mcp_client,
                max_steps=10,
                memory_enabled=self.mcp_agent_memory_enabled,
                system_prompt=self.system_prompt,
            )
            await self.agent.initialize()

            print("✓ MCP servers initialized successfully!")
            return True

        except Exception as e:
            print(f"✗ Error initializing MCP: {e}")
            return False

    def detect_silence(self, audio_data: bytes) -> bool:
        """Detect if audio contains silence."""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        return np.max(np.abs(audio_array)) < self.silence_threshold

    def record_audio(self) -> bytes | None:
        """Record audio from microphone."""
        print("\nListening... (speak now)")

        try:
            stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
            )

            frames = []
            silence_frames = 0
            silence_frame_threshold = int(self.rate / self.chunk * self.silence_duration)
            has_speech = False

            while True:
                if self.reload_event and self.reload_event.is_set():
                    print("Auto environment reload requested while recording.")
                    break

                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)

                if self.detect_silence(data):
                    silence_frames += 1
                    if has_speech and silence_frames > silence_frame_threshold:
                        break
                else:
                    silence_frames = 0
                    has_speech = True

                if len(frames) > self.rate / self.chunk * 30:
                    break

            stream.stop_stream()
            stream.close()

            if self.reload_event and self.reload_event.is_set():
                return None

            if not has_speech:
                print("No speech detected.")
                return None

            print("Processing...")
            return b"".join(frames)

        except Exception as e:
            print(f"Error recording audio: {e}")
            return None

    def _write_wav(self, audio_data: bytes, audio_file) -> None:
        """Write recorded audio bytes as a WAV file-like object."""
        with wave.open(audio_file, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
            wf.setframerate(self.rate)
            wf.writeframes(audio_data)

    def _load_local_whisper_model(self):
        """Lazy-load faster-whisper so online-only users do not pay the import cost."""
        if self.local_whisper_model:
            return self.local_whisper_model

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("Local Whisper requires faster-whisper. Install it with: uv pip install -e .")
            return None

        print(f"Loading local Whisper model: {self.local_whisper_model_name}")
        self.local_whisper_model = WhisperModel(self.local_whisper_model_name, device="auto", compute_type="int8")
        return self.local_whisper_model

    def audio_to_text(self, audio_data: bytes) -> str | None:
        """Convert audio to text using the configured speech-to-text provider."""
        if self.stt_provider == "local-whisper":
            return self.audio_to_text_local_whisper(audio_data)
        return self.audio_to_text_openai_whisper(audio_data)

    def audio_to_text_openai_whisper(self, audio_data: bytes) -> str | None:
        """Convert audio to text using OpenAI Whisper API."""
        if not self.openai_client:
            print("OpenAI Whisper is selected, but no OpenAI client is configured.")
            return None

        try:
            wav_buffer = io.BytesIO()
            self._write_wav(audio_data, wav_buffer)
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"

            kwargs = {"model": "whisper-1", "file": wav_buffer}
            if self.stt_language:
                kwargs["language"] = self.stt_language
            response = self.openai_client.audio.transcriptions.create(**kwargs)

            return response.text.strip()

        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def audio_to_text_local_whisper(self, audio_data: bytes) -> str | None:
        """Convert audio to text using faster-whisper locally."""
        model = self._load_local_whisper_model()
        if not model:
            return None

        wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                wav_path = wav_file.name
                self._write_wav(audio_data, wav_file)

            segments, _info = model.transcribe(wav_path, language=self.stt_language)
            text = "".join(segment.text for segment in segments).strip()
            return text or None

        except Exception as e:
            print(f"Error transcribing audio locally: {e}")
            return None

        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

    async def text_to_speech(self, text: str) -> bool:
        """Convert text to speech using the configured provider."""
        if self.tts_provider == "none":
            return False

        if self.tts_provider == "pyttsx3":
            return self.text_to_speech_pyttsx3(text)

        # Try ElevenLabs first
        if self.elevenlabs_client:
            try:
                # Generate audio using ElevenLabs
                with TTS_LOCK:
                    audio = self.elevenlabs_client.text_to_speech.convert(
                        text=text,
                        voice_id=self.elevenlabs_voice_id,
                        model_id="eleven_multilingual_v2",  # Best for high-quality output and multilingual
                        output_format="mp3_44100_128",  # Balanced quality + size
                        optimize_streaming_latency="2",  # Optional: best for real-time feel without delay
                        voice_settings=VoiceSettings(speed=1.1),
                    )

                    # Play the audio
                    play(audio)
                return True
            except Exception as e:
                print(f"ElevenLabs TTS failed: {e}")
                print("Falling back to local pyttsx3 TTS...")
        elif self.tts_provider == "elevenlabs":
            print("ElevenLabs TTS selected but ELEVENLABS_API_KEY is missing. Falling back to pyttsx3...")

        return self.text_to_speech_pyttsx3(text)

    def text_to_speech_pyttsx3(self, text: str) -> bool:
        """Speak text through the local system TTS engine."""
        try:
            with TTS_LOCK:
                TTS_ENGINE.say(text)
                TTS_ENGINE.runAndWait()
            return True
        except Exception as e:
            print(f"Local pyttsx3 TTS failed: {e}")
            return False

    async def process_command(self, text: str) -> str:
        """Process user command with MCP agent."""
        print(f"\nYou said: {text}")

        # Special commands
        if text.lower() in ["exit", "quit", "goodbye"]:
            return "Goodbye! Have a great day!"

        if text.lower() == "clear":
            if self.agent:
                self.agent.clear_conversation_history()
            return "Conversation history cleared."

        # Process with MCP agent
        if not self.agent:
            return "Sorry, the assistant is not properly initialized."

        self.start_thinking_sound()
        try:
            agent_input = self._with_freshness_instruction_if_needed(text)
            response = await self.agent.run(agent_input)
            return response
        except Exception as e:
            error_text = str(e)
            if "context_length_exceeded" in error_text or "maximum context length" in error_text:
                return (
                    "I reached the model context limit because tool definitions are too large for the current model. "
                    "Please switch to a larger-context model (for example gpt-4o-mini or gpt-4o), "
                    "or reduce enabled MCP servers/tools."
                )
            return f"Sorry, I encountered an error: {error_text}"
        finally:
            self.stop_thinking_sound()

    def _looks_like_current_external_state_query(self, text: str) -> bool:
        normalized = text.lower()
        return any(marker in normalized for marker in CURRENT_STATE_QUERY_MARKERS)

    def _with_freshness_instruction_if_needed(self, text: str) -> str:
        if not self._looks_like_current_external_state_query(text):
            return text

        return (
            f"{text}\n\n"
            "Internal freshness rule: this appears to ask for current external state. "
            "Use the relevant MCP read tool before answering. Do not answer from memory, "
            "previous tool results, or assumptions. If no suitable read tool is available, "
            "say that you cannot verify the current state. Do not mention this internal rule."
        )

    async def run(self):
        """Main loop for the voice assistant."""
        print("\n===== Voice-First AI Assistant (Improved) =====")
        print("\nCommands: 'help', 'clear', 'exit'")
        print("===============================================\n")

        # Initialize MCP
        if not await self.initialize_mcp():
            print("Failed to initialize MCP. Exiting.")
            return "exit"

        try:
            while True:
                if self.reload_event and self.reload_event.is_set():
                    print("Auto environment reload requested. Stopping current assistant.")
                    return "reload"

                # Record audio or get text input
                audio_data = self.record_audio()
                if self.reload_event and self.reload_event.is_set():
                    print("Auto environment reload requested. Stopping current assistant.")
                    return "reload"
                if not audio_data:
                    continue

                # Convert to text
                text = self.audio_to_text(audio_data)
                if self.reload_event and self.reload_event.is_set():
                    print("Auto environment reload requested. Stopping current assistant.")
                    return "reload"
                if not text:
                    continue

                # Process command
                process_task = asyncio.create_task(self.process_command(text))
                while not process_task.done():
                    if self.reload_event and self.reload_event.is_set():
                        print("Auto environment reload requested. Cancelling current command.")
                        process_task.cancel()
                        try:
                            await process_task
                        except asyncio.CancelledError:
                            pass
                        return "reload"
                    await asyncio.sleep(0.1)

                response = await process_task
                if self.reload_event and self.reload_event.is_set():
                    print("Auto environment reload requested. Discarding current response.")
                    return "reload"

                print(f"\nAssistant: {response}")

                # Check for exit
                if text.lower() in ["exit", "quit", "goodbye"]:
                    break

                # Try to speak the response
                await self.text_to_speech(response)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            return "exit"
        finally:
            # Cleanup
            self.stop_thinking_sound()
            self.audio.terminate()
            pygame.mixer.quit()
            if self.mcp_client and self.mcp_client.sessions:
                await self.mcp_client.close_all_sessions()

        return "exit"


async def main():
    """Run the improved voice assistant."""
    import argparse

    from dotenv import dotenv_values, load_dotenv

    def env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    def env_int(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None or value.strip() == "":
            return default
        try:
            return int(value)
        except ValueError:
            print(f"Error: {name} must be an integer, got: {value}")
            sys.exit(1)

    def env_float(name: str, default: float) -> float:
        value = os.getenv(name)
        if value is None or value.strip() == "":
            return default
        try:
            return float(value)
        except ValueError:
            print(f"Error: {name} must be a number, got: {value}")
            sys.exit(1)

    def env_optional(name: str) -> str | None:
        value = os.getenv(name)
        if value is None or value.strip() == "":
            return None
        return value

    def env_secret(name: str) -> str | None:
        file_path = env_optional(f"{name}_FILE")
        if not file_path:
            return None

        try:
            with open(file_path) as secret_file:
                secret = secret_file.read().strip()
        except OSError as e:
            print(f"Error: could not read {name}_FILE '{file_path}': {e}")
            sys.exit(1)

        return secret or None

    def clear_env_keys(env_files: list[Path]) -> None:
        """Clear keys owned by env profiles so auto reloads do not keep stale values."""
        env_keys = set()
        for profile in env_files:
            if profile.exists():
                env_keys.update(dotenv_values(profile).keys())

        for key in env_keys:
            os.environ.pop(key, None)

    def build_assistant_from_env(env_file: Path, reload_event: threading.Event | None = None) -> VoiceAssistant:
        """Load one env profile and build a fresh assistant instance from it."""
        clear_profiles = [env_file]
        if auto_env_mode:
            clear_profiles.extend([AUTO_ENV_ONLINE, AUTO_ENV_OFFLINE])
        clear_env_keys(clear_profiles)
        load_dotenv(env_file, override=True)

        openai_api_key = env_secret("OPENAI_API_KEY")
        elevenlabs_api_key = env_secret("ELEVENLABS_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        stt_provider = os.getenv("STT_PROVIDER", "openai-whisper").lower()
        local_whisper_model = os.getenv("LOCAL_WHISPER_MODEL", "base")
        stt_language_value = os.getenv("STT_LANGUAGE", "auto")
        stt_language = None if stt_language_value.lower() == "auto" else stt_language_value
        tts_provider = os.getenv("TTS_PROVIDER", "elevenlabs").lower()
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE_ID)
        thinking_sound_file = os.getenv("THINKING_SOUND_FILE", "thinking.wav")
        silence_threshold = env_int("VOICE_SILENCE_THRESHOLD", 500)
        silence_duration = env_float("VOICE_SILENCE_DURATION", 1.5)
        system_prompt = env_optional("ASSISTANT_SYSTEM_PROMPT")
        mcp_config_path = env_optional("MCP_CONFIG")
        mcp_prompt_merge_mode = os.getenv("MCP_PROMPT_MERGE_MODE", "append").lower()
        mcp_agent_memory_enabled = env_bool("MCP_AGENT_MEMORY_ENABLED", True)

        if llm_provider not in {"openai", "ollama"}:
            print(f"Error: LLM_PROVIDER must be 'openai' or 'ollama', got: {llm_provider}")
            sys.exit(1)
        if stt_provider not in {"openai-whisper", "local-whisper"}:
            print(f"Error: STT_PROVIDER must be 'openai-whisper' or 'local-whisper', got: {stt_provider}")
            sys.exit(1)
        if tts_provider not in {"elevenlabs", "pyttsx3", "none"}:
            print(f"Error: TTS_PROVIDER must be 'elevenlabs', 'pyttsx3', or 'none', got: {tts_provider}")
            sys.exit(1)
        if mcp_prompt_merge_mode not in {"append", "replace"}:
            print(f"Error: MCP_PROMPT_MERGE_MODE must be 'append' or 'replace', got: {mcp_prompt_merge_mode}")
            sys.exit(1)

        print(f"Using env file: {env_file}")
        print(f"Using ElevenLabs voice ID: {voice_id}")
        print(f"Using LLM provider: {llm_provider}")
        print(f"Using STT provider: {stt_provider}")
        print(f"Using TTS provider: {tts_provider}")
        print(f"Using thinking sound file: {thinking_sound_file}")
        print(f"Using MCP agent memory: {mcp_agent_memory_enabled}")

        if (llm_provider == "openai" or stt_provider == "openai-whisper") and not openai_api_key:
            print("Error: OpenAI API key is required")
            print(
                "Set OPENAI_API_KEY_FILE, or use an offline env file with "
                "LLM_PROVIDER=ollama and STT_PROVIDER=local-whisper"
            )
            sys.exit(1)

        mcp_config = None
        if mcp_config_path:
            try:
                with open(mcp_config_path) as f:
                    mcp_config = json.load(f)
            except OSError as e:
                print(f"Error: could not read MCP_CONFIG '{mcp_config_path}': {e}")
                sys.exit(1)
            except json.JSONDecodeError as e:
                print(f"Error: invalid JSON in MCP_CONFIG '{mcp_config_path}': {e}")
                sys.exit(1)

        return VoiceAssistant(
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            model=model,
            llm_provider=llm_provider,
            ollama_base_url=ollama_base_url,
            stt_provider=stt_provider,
            local_whisper_model=local_whisper_model,
            stt_language=stt_language,
            tts_provider=tts_provider,
            elevenlabs_voice_id=voice_id,
            thinking_sound_file=thinking_sound_file,
            silence_threshold=silence_threshold,
            silence_duration=silence_duration,
            mcp_config=mcp_config,
            mcp_load_server_prompt=env_bool("MCP_LOAD_SERVER_PROMPT", False),
            mcp_prompt_merge_mode=mcp_prompt_merge_mode,
            mcp_agent_memory_enabled=mcp_agent_memory_enabled,
            system_prompt=system_prompt,
            reload_event=reload_event,
        )

    parser = argparse.ArgumentParser(description="Voice-enabled AI assistant")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment file to load before starting the assistant (default: .env)",
    )
    args = parser.parse_args()

    auto_env_mode = args.env_file.strip().lower() == "auto"
    if auto_env_mode:
        internet_online = check_internet_connection()
        env_file = AUTO_ENV_ONLINE if internet_online else AUTO_ENV_OFFLINE
        print(
            "Auto env mode selected "
            f"{env_file} because internet is {'live' if internet_online else 'inactive'}."
        )
    else:
        env_file = Path(args.env_file)

    if not env_file.exists():
        print(f"Error: env file not found: {env_file}")
        print("Use one of the provided profiles, for example:")
        print("  python voice_assistant/agent.py --env-file .env.online")
        print("  python voice_assistant/agent.py --env-file .env.offline")
        print("  python voice_assistant/agent.py --env-file auto")
        sys.exit(1)

    if not auto_env_mode:
        assistant = build_assistant_from_env(env_file)
        await assistant.run()
        return

    reload_event = threading.Event()
    auto_monitor = AutoNetworkMonitor(
        initial_online=internet_online,
        dotenv_values_func=dotenv_values,
        reload_event=reload_event,
        interval=AUTO_CHECK_INTERVAL,
    )
    auto_monitor.announce_initial_status()
    auto_monitor.start()

    try:
        announce_reload_complete = False
        while True:
            env_file = auto_monitor.detected_env_file
            if not env_file.exists():
                print(f"Error: env file not found: {env_file}")
                sys.exit(1)

            reload_event.clear()
            assistant = build_assistant_from_env(env_file, reload_event=reload_event)
            if announce_reload_complete:
                await assistant.text_to_speech("Environnement mis à jour. La demande en cours a été annulée.")
                announce_reload_complete = False

            run_result = await assistant.run()
            if run_result != "reload":
                break

            next_env_file = auto_monitor.detected_env_file
            print(f"Auto env reload requested. Restarting assistant with {next_env_file}.")
            announce_reload_complete = True
    finally:
        auto_monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
