import os
import shutil
import asyncio
import subprocess
import edge_tts
from services.ai_service import clean_text_for_tts, is_thought_voice

try:
    from pydub import AudioSegment
    from pydub.effects import normalize
except ImportError:
    AudioSegment = None
    normalize = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, "temp_dubbing_files")
os.makedirs(TEMP_DIR, exist_ok=True)


def temp_path(filename: str) -> str:
    return os.path.join(TEMP_DIR, filename)


def enhance_voice_clarity(sound):
    if not sound or not AudioSegment or not normalize:
        return sound
    # 48000Hz stereo normalization with subtle high pass and smooth micro fades
    sound = sound.set_frame_rate(48000).set_channels(2)
    normalized = normalize(sound).high_pass_filter(70) + 1.5
    return normalized.fade_in(10).fade_out(10)


def add_reverb_thought_effect(sound):
    if not sound or not AudioSegment or not normalize:
        return sound
    sound = sound.set_frame_rate(48000).set_channels(2)
    delay_1 = AudioSegment.silent(duration=40) + (sound - 4.0)
    delay_2 = AudioSegment.silent(duration=90) + (sound - 7.5)
    delay_3 = AudioSegment.silent(duration=150) + (sound - 11.5)
    mixed = sound.overlay(delay_1).overlay(delay_2).overlay(delay_3)
    return normalize(mixed).fade_in(10).fade_out(10)


def adjust_audio_speed(input_file: str, output_file: str, speed_factor: float):
    # Keep natural pacing: clamp speed strictly between 0.85 and 1.25 for crystal-clear human voice
    safe_speed = max(0.85, min(speed_factor, 1.25))
    if abs(safe_speed - 1.0) < 0.03:
        shutil.copy(input_file, output_file)
        return

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-filter:a", f"atempo={safe_speed:.4f},aresample=48000",
        "-ar", "48000",
        "-ac", "2",
        "-vn", output_file
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        shutil.copy(input_file, output_file)


async def generate_single_tts(item: dict, session_id: str = "default") -> bool:
    """
    item: {
        'index': int,
        'start_sec': float,
        'end_sec': float,
        'text': str,
        'voice': str ('km-KH-SreymomNeural' | 'km-KH-PisethNeural'),
        'is_thought': bool
    }
    """
    real_idx = item.get('index', 0)
    raw_text = item.get('text', '')
    voice_code = item.get('voice', 'km-KH-PisethNeural')
    has_thought = is_thought_voice(raw_text) or item.get('is_thought', False)
    clean_tts_text = clean_text_for_tts(raw_text)

    start_sec = float(item.get('start_sec', 0.0))
    end_sec = float(item.get('end_sec', 1.0))
    srt_duration = max(0.5, end_sec - start_sec)

    if not clean_tts_text.strip():
        return False

    raw_tts_file = temp_path(f"raw_voice_{session_id}_{real_idx}.mp3")
    final_file = temp_path(f"temp_voice_{session_id}_{real_idx}.mp3")

    # Retry up to 3 times with exponential backoff for network stability
    for attempt in range(3):
        try:
            communicate = edge_tts.Communicate(clean_tts_text, voice_code)
            await communicate.save(raw_tts_file)

            if os.path.exists(raw_tts_file) and os.path.getsize(raw_tts_file) > 0:
                sound = AudioSegment.from_file(raw_tts_file) if AudioSegment else None
                tts_duration = len(sound) / 1000.0 if sound else srt_duration

                if tts_duration > 0 and srt_duration > 0:
                    speed_factor = tts_duration / srt_duration
                    adjust_audio_speed(raw_tts_file, final_file, speed_factor)
                else:
                    shutil.copy(raw_tts_file, final_file)

                if not os.path.exists(final_file) or os.path.getsize(final_file) == 0:
                    shutil.copy(raw_tts_file, final_file)

                if AudioSegment and os.path.exists(final_file):
                    sound_final = AudioSegment.from_file(final_file)
                    if has_thought:
                        sound_final = add_reverb_thought_effect(sound_final)
                    else:
                        sound_final = enhance_voice_clarity(sound_final)

                    sound_final.export(final_file, format="mp3", bitrate="320k")

                return True
        except Exception as e:
            print(f"Attempt {attempt + 1} TTS error for row {real_idx}: {e}")
            await asyncio.sleep(0.5 * (attempt + 1))

    return False

