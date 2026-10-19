import sys
import os
import asyncio
import io
import math
import struct
from typing import AsyncGenerator
from config import config

# Ensure UTF-8 output on Windows consoles to prevent charmap UnicodeEncodeError
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Check if edge_tts is installed
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Check if imageio_ffmpeg is available for direct PCM transcoding
try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

import time
import subprocess
import tempfile

# LOONA (loonatheworld) Charismatic K-Pop Idol Voice Presets Configuration
VOICE_PRESETS = {
    "kpop_idol_en": {
        "voice": "en-US-JennyNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "label": "🌙 K-Pop Idol English (Jenny - Natural)"
    },
    "kpop_idol_kr": {
        "voice": "ko-KR-SunHiNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "label": "🇰🇷 K-Pop Idol Korean (SunHi - Natural)"
    },
    "kpop_ava_en": {
        "voice": "en-US-AvaNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "label": "✨ K-Pop Idol Global (Ava - Natural)"
    },
    "kpop_en": {
        "voice": "en-US-JennyNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "label": "🌙 K-Pop Idol English (Default)"
    },
    "kpop_kr": {
        "voice": "ko-KR-SunHiNeural",
        "pitch": "+0Hz",
        "rate": "+0%",
        "label": "🇰🇷 K-Pop Idol Korean (Default)"
    }
}


class TTSService:
    def __init__(self, preset: str = config.TTS_PRESET, sample_rate: int = config.SPK_SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._pcm_cache: dict = {}
        self.set_preset(preset)

    def set_preset(self, preset_key: str):
        """Sets the active voice preset, pitch, and speed."""
        preset = VOICE_PRESETS.get(preset_key, VOICE_PRESETS["kpop_idol_en"])
        self.preset_key = preset_key
        self.voice = preset["voice"]
        self.pitch = preset["pitch"]
        self.rate = preset["rate"]
        print(f"[TTS] Active K-Pop Idol Voice Preset: {preset['label']} (Voice: {self.voice}, Pitch: {self.pitch}, Rate: {self.rate})")

    def _decode_audio_to_pcm(self, input_bytes: bytes, in_format: str = "mp3") -> bytes:
        """Converts raw MP3 or WAV audio bytes to 16-bit 24kHz Stereo PCM using FFmpeg."""
        cmd = [
            FFMPEG_EXE,
            "-y",
            "-loglevel", "error",
            "-f", in_format,
            "-i", "pipe:0",
            "-f", "s16le",
            "-ar", str(self.sample_rate),
            "-ac", "2",
            "pipe:1"
        ]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        pcm_out, err = proc.communicate(input=input_bytes)
        if proc.returncode != 0 or not pcm_out:
            raise RuntimeError(f"FFmpeg decode error: {err.decode('utf-8', errors='ignore')}")
        return pcm_out

    def _fallback_sapi_tts(self, text: str) -> bytes:
        """Offline Windows SAPI voice synthesizer fallback when Edge-TTS is unavailable."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name

            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            filestream = win32com.client.Dispatch("SAPI.SpFileStream")
            filestream.Open(tmp_path, 3, False)  # 3 = SSFMCreateForWrite
            speaker.AudioOutputStream = filestream
            speaker.Speak(text)
            filestream.Close()

            with open(tmp_path, "rb") as wf:
                wav_bytes = wf.read()

            if wav_bytes:
                print(f"[TTS-SAPI] Synthesized {len(wav_bytes)} bytes using Windows offline voice.")
                return self._decode_audio_to_pcm(wav_bytes, in_format="wav")
        except Exception as e:
            print(f"[TTS-SAPI] Offline voice fallback failed: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        return b""

    def _generate_synthetic_tone(self, duration_s: float = 0.5, freq: float = 880.0) -> bytes:
        """Absolute last resort robotic synth audio."""
        num_samples = int(self.sample_rate * duration_s)
        pcm_data = bytearray()
        for i in range(num_samples):
            f = freq + 260.0 * math.sin(i / 350.0)
            sample = int(32767.0 * 0.45 * math.sin(2.0 * math.pi * f * i / self.sample_rate))
            pcm_data.extend(struct.pack("<hh", sample, sample))
        return bytes(pcm_data)

    async def text_to_pcm(self, text: str) -> bytes:
        """Converts text into raw 16-bit 24kHz Stereo PCM bytes with Anime Voice modulation."""
        clean_text = text.strip()
        if not clean_text:
            return b""

        cache_key = f"{self.voice}:{clean_text}"
        if cache_key in self._pcm_cache:
            return self._pcm_cache[cache_key]

        # 1. Primary: Edge-TTS Neural Voice
        if EDGE_TTS_AVAILABLE:
            for attempt in [1, 2]:
                try:
                    # Attempt 1: Full pitch & rate modulation
                    # Attempt 2: Natural modulation without custom pitch/rate
                    use_pitch = self.pitch if attempt == 1 else "+0Hz"
                    use_rate = self.rate if attempt == 1 else "+0%"

                    communicate = edge_tts.Communicate(
                        clean_text,
                        self.voice,
                        pitch=use_pitch,
                        rate=use_rate
                    )
                    mp3_buffer = io.BytesIO()
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            mp3_buffer.write(chunk["data"])

                    mp3_bytes = mp3_buffer.getvalue()
                    if mp3_bytes:
                        loop = asyncio.get_running_loop()
                        pcm_audio = await loop.run_in_executor(None, self._decode_audio_to_pcm, mp3_bytes, "mp3")
                        if len(self._pcm_cache) < 150:
                            self._pcm_cache[cache_key] = pcm_audio
                        return pcm_audio
                except Exception as e:
                    if attempt == 1:
                        continue
                    print(f"[TTS] edge-tts error: {e}. Trying offline voice fallback...")

        # 2. Secondary: Windows Offline SAPI Voice
        sapi_pcm = self._fallback_sapi_tts(clean_text)
        if sapi_pcm:
            return sapi_pcm

        # 3. Tertiary fallback tone
        print("[TTS] Generating synthetic expressive audio tone...")
        return self._generate_synthetic_tone(duration_s=0.8, freq=800.0)

    async def text_to_mp3(self, text: str) -> bytes:
        """Synthesizes text into high-quality MP3 bytes directly for phone and browser playback."""
        clean_text = text.strip()
        if not clean_text or not EDGE_TTS_AVAILABLE:
            return b""
        try:
            communicate = edge_tts.Communicate(
                clean_text,
                self.voice,
                pitch=self.pitch,
                rate=self.rate
            )
            mp3_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_buffer.write(chunk["data"])
            return mp3_buffer.getvalue()
        except Exception as e:
            print(f"[TTS] text_to_mp3 error: {e}")
            return b""

    async def stream_pcm_chunks(self, text: str, chunk_size: int = 1024) -> AsyncGenerator[bytes, None]:
        """Yields raw PCM chunks with jitter-free, gentle pre-buffering that never floods ESP32 WebSocket."""
        raw_pcm = await self.text_to_pcm(text)
        if not raw_pcm:
            return

        total_bytes = len(raw_pcm)
        bytes_sent = 0
        bytes_per_sec = self.sample_rate * 4.0  # 96,000 bytes/sec @ 24kHz 16-bit Stereo

        # 1. Gentle pre-buffer: 2048 bytes (2 chunks of 1024) to prime DMA without overflowing socket
        prebuffer_limit = min(2048, total_bytes)
        while bytes_sent < prebuffer_limit:
            end = min(bytes_sent + chunk_size, prebuffer_limit)
            yield raw_pcm[bytes_sent : end]
            bytes_sent = end
            await asyncio.sleep(0.002)

        # 2. Precision pacing for remaining chunks
        start_time = time.perf_counter()
        initial_sent = bytes_sent

        while bytes_sent < total_bytes:
            end = min(bytes_sent + chunk_size, total_bytes)
            yield raw_pcm[bytes_sent : end]
            bytes_sent = end

            # Target playback progress
            audio_duration_sent = (bytes_sent - initial_sent) / bytes_per_sec
            elapsed = time.perf_counter() - start_time
            sleep_needed = audio_duration_sent - elapsed - 0.010  # 10ms lead

            if sleep_needed > 0.010:
                await asyncio.sleep(sleep_needed)
            else:
                await asyncio.sleep(0)

tts_engine = TTSService()

