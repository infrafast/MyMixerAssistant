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
import os
import sys
import tempfile
import wave

import numpy as np
import openai
import pyaudio
import pygame
import pyttsx3
from elevenlabs import play
from elevenlabs.client import ElevenLabs
from elevenlabs.types.voice_settings import VoiceSettings
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

TTS_ENGINE = pyttsx3.init()
DEFAULT_ELEVENLABS_VOICE_ID = "1EmYoP3UnnnwhlJKovEy"  # french male; ZF6FPAbjXT4488VcRRnw = english female


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
        silence_threshold: int = 500,
        silence_duration: float = 1.5,
        mcp_config: dict | None = None,
        notes_dir: str | None = None,
        system_prompt: str | None = None,
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
            silence_threshold: Audio silence detection threshold
            silence_duration: How long to wait after speech stops
            mcp_config: Optional MCP server configuration dict
            notes_dir: Directory for storing notes (default: temp dir)
            system_prompt: Optional custom system prompt for the assistant
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

        # MCP configuration
        self.mcp_config = mcp_config
        self.mcp_client = None
        self.agent = None
        
        #self.system_prompt = system_prompt or (
        #    "You are a helpful voice assistant with access to various tools. Your name is mcp-use "
        #    "Be concise in your responses since they will be spoken aloud. Summarize your results. "
        #    "Reply in the same language as the user's latest request whenever possible. "
        #    "Behave like a great motivational speaker, and motivate me throughout the conversation."
        #)

        self.system_prompt = system_prompt or (
            "You are a helpful voice assistant with access to various tools. Your name is Live Stage Assistant. "
            "Be concise in your responses since they will be spoken aloud and have to be suitable for text-to-speech and API calls.. Summarize your results. "
            "Reply in the same language as the user's latest request whenever possible. "
            "Use plain text only. Do not use emojis, emoticons, markdown, bullets, symbols, or decorative characters. "
            "Behave like a friendly calm and motivating assistant."
        )        

        # Create a proper notes directory
        if notes_dir:
            self.notes_dir = notes_dir
        else:
            self.notes_dir = os.path.join(tempfile.gettempdir(), "voice_assistant_notes")
        os.makedirs(self.notes_dir, exist_ok=True)

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

            # Create LLM
            llm = self._build_llm()

            # Create agent with memory
            self.agent = MCPAgent(
                llm=llm,
                client=self.mcp_client,
                max_steps=10,
                memory_enabled=True,
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

        try:
            response = await self.agent.run(text)
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

    async def run(self):
        """Main loop for the voice assistant."""
        print("\n===== Voice-First AI Assistant (Improved) =====")
        print("\nCommands: 'help', 'clear', 'exit'")
        print("===============================================\n")

        # Initialize MCP
        if not await self.initialize_mcp():
            print("Failed to initialize MCP. Exiting.")
            return

        try:
            while True:
                # Record audio or get text input
                audio_data = self.record_audio()
                if not audio_data:
                    continue

                # Convert to text
                text = self.audio_to_text(audio_data)
                if not text:
                    continue

                # Process command
                response = await self.process_command(text)
                print(f"\nAssistant: {response}")

                # Check for exit
                if text.lower() in ["exit", "quit", "goodbye"]:
                    break

                # Try to speak the response
                await self.text_to_speech(response)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
        finally:
            # Cleanup
            self.audio.terminate()
            pygame.mixer.quit()
            if self.mcp_client and self.mcp_client.sessions:
                await self.mcp_client.close_all_sessions()


async def main():
    """Run the improved voice assistant."""
    # Example usage - in production, load these from environment or config
    import argparse

    from dotenv import load_dotenv

    # Load environment variables if .env exists
    load_dotenv()

    parser = argparse.ArgumentParser(description="Voice-enabled AI assistant")
    parser.add_argument("--openai-api-key", default=os.getenv("OPENAI_API_KEY"), help="OpenAI API key")
    parser.add_argument("--elevenlabs-api-key", default=os.getenv("ELEVENLABS_API_KEY"), help="ElevenLabs API key")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="LLM model to use")
    parser.add_argument(
        "--llm-provider",
        default=os.getenv("LLM_PROVIDER", "openai"),
        choices=["openai", "ollama"],
        help="LLM provider to use",
    )
    parser.add_argument(
        "--ollama-base-url",
        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        help="Base URL for Ollama server",
    )
    parser.add_argument(
        "--stt-provider",
        default=os.getenv("STT_PROVIDER", "openai-whisper"),
        choices=["openai-whisper", "local-whisper"],
        help="Speech-to-text provider",
    )
    parser.add_argument(
        "--local-whisper-model",
        default=os.getenv("LOCAL_WHISPER_MODEL", "base"),
        help="faster-whisper model size or local model path",
    )
    parser.add_argument(
        "--stt-language",
        default=os.getenv("STT_LANGUAGE", "auto"),
        help="Speech language code for Whisper; use 'auto' to auto-detect",
    )
    parser.add_argument(
        "--tts-provider",
        default=os.getenv("TTS_PROVIDER", "elevenlabs"),
        choices=["elevenlabs", "pyttsx3", "none"],
        help="Text-to-speech provider",
    )
    parser.add_argument(
        "--voice-id", default=os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE_ID), help="ElevenLabs voice ID"
    )
    parser.add_argument(
        "--silence-threshold",
        type=int,
        default=int(os.getenv("VOICE_SILENCE_THRESHOLD", "500")),
        help="Silence detection threshold",
    )
    parser.add_argument(
        "--silence-duration",
        type=float,
        default=float(os.getenv("VOICE_SILENCE_DURATION", "1.5")),
        help="Silence duration",
    )
    parser.add_argument(
        "--system-prompt", default=os.getenv("ASSISTANT_SYSTEM_PROMPT"), help="Custom system prompt for the assistant"
    )
    parser.add_argument(
        "--mcp-config",
        default=os.getenv("MCP_CONFIG"),
        help="Path to an MCP server JSON config file. Defaults to mcp_servers.json",
    )

    args = parser.parse_args()
    stt_language = None if args.stt_language.lower() == "auto" else args.stt_language

    print(f"Using ElevenLabs voice ID: {args.voice_id}")
    print(f"Using LLM provider: {args.llm_provider}")
    print(f"Using STT provider: {args.stt_provider}")
    print(f"Using TTS provider: {args.tts_provider}")

    if (args.llm_provider == "openai" or args.stt_provider == "openai-whisper") and not args.openai_api_key:
        print("Error: OpenAI API key is required")
        print("Set OPENAI_API_KEY, pass --openai-api-key, or use --llm-provider ollama --stt-provider local-whisper")
        sys.exit(1)

    mcp_config = None
    if args.mcp_config:
        with open(args.mcp_config) as f:
            mcp_config = json.load(f)

    assistant = VoiceAssistant(
        openai_api_key=args.openai_api_key,
        elevenlabs_api_key=args.elevenlabs_api_key,
        model=args.model,
        llm_provider=args.llm_provider,
        ollama_base_url=args.ollama_base_url,
        stt_provider=args.stt_provider,
        local_whisper_model=args.local_whisper_model,
        stt_language=stt_language,
        tts_provider=args.tts_provider,
        elevenlabs_voice_id=args.voice_id,
        silence_threshold=args.silence_threshold,
        silence_duration=args.silence_duration,
        mcp_config=mcp_config,
        system_prompt=args.system_prompt,
    )
    await assistant.run()


if __name__ == "__main__":
    asyncio.run(main())
