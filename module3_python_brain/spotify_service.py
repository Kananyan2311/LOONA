import os
import sys
import json
import time
import asyncio
import subprocess
import urllib.parse
import webbrowser
from typing import Optional, Dict, Any, Callable
from config import config

# Optional Spotipy library for official Spotify Web API playback
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"


class SpotifyService:
    def __init__(self):
        self.sp: Optional[Any] = None
        self.has_credentials: bool = bool(config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET)
        self.current_track_info: Dict[str, Any] = {"status": "idle", "title": "", "artist": "", "query": ""}
        
        # Audio Streaming Subprocess & Task for MAX98357A
        self.current_proc: Optional[subprocess.Popen] = None
        self.is_streaming: bool = False
        self.stream_task: Optional[asyncio.Task] = None

        if SPOTIPY_AVAILABLE and self.has_credentials:
            try:
                scope = "user-modify-playback-state user-read-playback-state user-read-currently-playing"
                auth_manager = SpotifyOAuth(
                    client_id=config.SPOTIFY_CLIENT_ID,
                    client_secret=config.SPOTIFY_CLIENT_SECRET,
                    redirect_uri=config.SPOTIFY_REDIRECT_URI,
                    scope=scope,
                    open_browser=True
                )
                self.sp = spotipy.Spotify(auth_manager=auth_manager)
                print("[SPOTIFY] Connected to official Spotify Web API.")
            except Exception as e:
                print(f"[SPOTIFY] Could not initialize Spotify Web API: {e}. Using direct stream fallback.")
                self.sp = None
        else:
            print("[SPOTIFY] Initialized with MAX98357A Robot Speaker Streamer & Desktop Fallback.")

    def play(self, query: str, send_bytes_cb: Optional[Callable] = None, notify_cb: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Searches and plays music on Spotify:
        1. If send_bytes_cb is provided (esp32_audio_socket), streams 24kHz raw PCM directly to MAX98357A!
        2. Also opens/controls official Spotify app / Desktop URI for synced display.
        """
        cleaned_query = query.strip()
        encoded = urllib.parse.quote(cleaned_query)
        spotify_uri = f"spotify:search:{encoded}"
        web_url = f"https://open.spotify.com/search/{encoded}"

        # 1. Stop any previous robot speaker stream
        self.stop_stream()

        # 2. Update track status
        self.current_track_info = {
            "status": "playing",
            "title": cleaned_query,
            "artist": "Spotify Music Stream",
            "query": cleaned_query,
            "url": web_url,
            "uri": spotify_uri
        }

        # 3. If audio callback is provided, launch background PCM streamer to MAX98357A
        if send_bytes_cb:
            self.stream_task = asyncio.create_task(
                self._stream_to_speaker_task(cleaned_query, send_bytes_cb, notify_cb)
            )

        # 4. Optional desktop URI sync (launch in background if on desktop)
        try:
            if self.sp:
                results = self.sp.search(q=cleaned_query, limit=1, type="track")
                tracks = results.get("tracks", {}).get("items", [])
                if tracks:
                    track = tracks[0]
                    self.sp.start_playback(uris=[track["uri"]])
                    self.current_track_info["title"] = track["name"]
                    self.current_track_info["artist"] = track["artists"][0]["name"]
        except Exception:
            pass

        print(f"[SPOTIFY] Playing music '{cleaned_query}' -> MAX98357A onboard speaker.")
        return self.current_track_info

    async def _stream_to_speaker_task(self, query: str, send_bytes_cb: Callable, notify_cb: Optional[Callable] = None):
        """Streams 24kHz 16-bit Stereo PCM chunks to ESP32 MAX98357A speaker."""
        self.is_streaming = True
        print(f"[SPOTIFY-STREAM] Searching audio stream for '{query}'...")
        
        loop = asyncio.get_running_loop()
        stream_url = None
        title = query

        try:
            # Run yt-dlp in threadpool to avoid blocking asyncio loop
            def fetch_url():
                import yt_dlp
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'noplaylist': True,
                    'quiet': True,
                    'default_search': 'ytsearch1'
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"{query} audio", download=False)
                    entries = info.get('entries', [info])
                    if entries and entries[0]:
                        return entries[0].get('url'), entries[0].get('title', query)
                return None, query

            stream_url, title = await loop.run_in_executor(None, fetch_url)
        except Exception as e:
            print(f"[SPOTIFY-STREAM] Search error: {e}")

        if not stream_url or not self.is_streaming:
            print("[SPOTIFY-STREAM] Could not acquire audio stream.")
            return

        self.current_track_info["title"] = title
        if notify_cb:
            try:
                await notify_cb(self.current_track_info)
            except Exception:
                pass

        # Spawn ffmpeg to decode into 24kHz stereo 16-bit raw PCM
        # Sample rate: 24,000 Hz, 2 channels, 16-bit signed little-endian = 96,000 bytes/sec
        ffmpeg_cmd = [
            FFMPEG_EXE,
            "-y",
            "-loglevel", "error",
            "-i", stream_url,
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "2",
            "-"
        ]

        print(f"[SPOTIFY-STREAM] Streaming '{title}' to MAX98357A speaker...")
        try:
            self.current_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=32768
            )

            CHUNK_SIZE = 1024
            bytes_sent = 0
            bytes_per_sec = 24000 * 4.0  # 96,000 bytes/sec
            start_time = None
            initial_sent = 0

            while self.is_streaming and self.current_proc:
                raw_chunk = await loop.run_in_executor(None, self.current_proc.stdout.read, CHUNK_SIZE)
                if not raw_chunk:
                    break

                # Send raw PCM chunk to ESP32-S3 CAM WebSocket
                await send_bytes_cb(raw_chunk)
                bytes_sent += len(raw_chunk)

                # Pre-buffer first 2048 bytes with gentle delay to avoid socket choking
                if bytes_sent <= 2048:
                    await asyncio.sleep(0.005)
                    continue
                elif start_time is None:
                    start_time = time.perf_counter()
                    initial_sent = bytes_sent
                    continue

                # Pace the remaining audio accurately to avoid buffer under-runs
                audio_progress = (bytes_sent - initial_sent) / bytes_per_sec
                elapsed = time.perf_counter() - start_time
                sleep_needed = audio_progress - elapsed - 0.02
                if sleep_needed > 0.005:
                    await asyncio.sleep(sleep_needed)
                else:
                    await asyncio.sleep(0.001)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[SPOTIFY-STREAM] Playback stream interrupted: {e}")
        finally:
            self.stop_stream()
            self.current_track_info["status"] = "idle"
            if notify_cb:
                try:
                    await notify_cb(self.current_track_info)
                except Exception:
                    pass
            print("[SPOTIFY-STREAM] Stream finished or halted.")

    def pause(self) -> Dict[str, Any]:
        """Pauses audio playback."""
        self.stop_stream()
        if self.sp:
            try:
                self.sp.pause_playback()
            except Exception:
                pass
        self._send_windows_media_key(0xB3)  # VK_MEDIA_PLAY_PAUSE
        self.current_track_info["status"] = "paused"
        return {"status": "paused"}

    def resume(self, send_bytes_cb: Optional[Callable] = None, notify_cb: Optional[Callable] = None) -> Dict[str, Any]:
        """Resumes audio playback."""
        if self.current_track_info.get("query"):
            return self.play(self.current_track_info["query"], send_bytes_cb, notify_cb)
        if self.sp:
            try:
                self.sp.start_playback()
            except Exception:
                pass
        self._send_windows_media_key(0xB3)
        self.current_track_info["status"] = "playing"
        return {"status": "playing"}

    def stop_stream(self):
        """Terminates active audio decoder subprocess immediately."""
        self.is_streaming = False
        if self.current_proc:
            try:
                self.current_proc.terminate()
                self.current_proc.kill()
            except Exception:
                pass
            self.current_proc = None
        if self.stream_task and not self.stream_task.done():
            self.stream_task.cancel()
            self.stream_task = None

    def next_track(self) -> Dict[str, Any]:
        self.stop_stream()
        if self.sp:
            try:
                self.sp.next_track()
                return {"status": "next"}
            except Exception:
                pass
        self._send_windows_media_key(0xB0)
        return {"status": "next"}

    def previous_track(self) -> Dict[str, Any]:
        self.stop_stream()
        if self.sp:
            try:
                self.sp.previous_track()
                return {"status": "previous"}
            except Exception:
                pass
        self._send_windows_media_key(0xB1)
        return {"status": "previous"}

    def _send_windows_media_key(self, vk_code: int):
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
            except Exception:
                pass


spotify_service = SpotifyService()
