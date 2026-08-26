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
    return normalize(sound).high_pass_filter(80) + 2.0


def add_reverb_thought_effect(sound):
    if not sound or not AudioSegment or not normalize:
        return sound
    delay_1 = AudioSegment.silent(duration=50) + (sound - 3.5)
    delay_2 = AudioSegment.silent(duration=110) + (sound - 7.0)
    delay_3 = AudioSegment.silent(duration=180) + (sound - 11.0)
    return normalize(sound.overlay(delay_1).overlay(delay_2).overlay(delay_3))


def adjust_audio_speed(input_file: str, output_file: str, speed_factor: float):
    filters = []
    curr_speed = speed_factor
    while curr_speed > 2.0:
        filters.append("atempo=2.0")
        curr_speed /= 2.0
    while curr_speed < 0.5:
        filters.append("atempo=0.5")
        curr_speed /= 0.5
    filters.append(f"atempo={curr_speed:.4f}")
    cmd = ["ffmpeg", "-y", "-i", input_file, "-filter:a", ",".join(filters), "-vn", output_file]
    subprocess.run(cmd, capture_output=True, text=True)


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
    real_idx = item['index']
    raw_text = item['text']
    voice_code = item.get('voice', 'km-KH-PisethNeural')
    has_thought = is_thought_voice(raw_text) or item.get('is_thought', False)
    clean_tts_text = clean_text_for_tts(raw_text)

    start_sec = item.get('start_sec', 0.0)
    end_sec = item.get('end_sec', 1.0)
    srt_duration = max(0.5, end_sec - start_sec)

    if not clean_tts_text:
        return False

    raw_tts_file = temp_path(f"raw_voice_{session_id}_{real_idx}.mp3")
    final_file = temp_path(f"temp_voice_{session_id}_{real_idx}.mp3")

    try:
        communicate = edge_tts.Communicate(clean_tts_text, voice_code)
        await communicate.save(raw_tts_file)

        if os.path.exists(raw_tts_file) and os.path.getsize(raw_tts_file) > 0:
            sound = AudioSegment.from_file(raw_tts_file) if AudioSegment else None
            tts_duration = len(sound) / 1000.0 if sound else srt_duration

            if tts_duration > 0:
                speed_factor = tts_duration / srt_duration
                speed_factor = max(0.7, min(speed_factor, 2.2))
                adjust_audio_speed(raw_tts_file, final_file, speed_factor)

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
        print(f"Error generating TTS for row {real_idx}: {e}")
        return False

    return False
