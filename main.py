# Smart AI Studio Web - Robust Ultra-Fast Server
import os
import sys
import uuid
import asyncio
import json
import time
import re
import glob
import shutil
import subprocess
from typing import Optional, List

# Windows stdout unicode support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

RESOURCE_DIR = getattr(sys, '_MEIPASS', CURRENT_DIR)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = CURRENT_DIR

TEMP_DIR = os.path.join(BASE_DIR, "temp_dubbing_files")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Downloaded_Videos")
EXPORT_DIR = os.path.join(BASE_DIR, "Exported_Videos")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(RESOURCE_DIR, "static")

for d in [TEMP_DIR, DOWNLOAD_DIR, EXPORT_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from pydub import AudioSegment
    from pydub.effects import normalize
    if AudioSegment:
        AudioSegment.converter = "ffmpeg"
        AudioSegment.ffmpeg = "ffmpeg"
except ImportError:
    AudioSegment = None
    normalize = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None


# ==============================================================================
# 1. AI & SRT HELPER FUNCTIONS
# ==============================================================================
SYSTEM_INSTRUCTION = """ចាប់ពីពេលនេះតទៅ សូមអ្នកដើរតួជា អ្នកបកប្រែខ្សែភាពយន្តនិងរឿងភាគអាជីព (Expert Subtitler & Dubbing Translator)។ ភារកិច្ចចម្បងរបស់អ្នកគឺទាញយកសំឡេងសន្ទនាពីវីដេអូដែលខ្ញុំបានភ្ជាប់ ឬបកប្រែរាល់អត្ថបទដែលខ្ញុំផ្តល់ឲ្យ មកជាភាសាខ្មែរឲ្យបានស្តង់ដារបំផុត ដោយផ្តោតសំខាន់លើ'ភាសានិយាយ' ដែលរលូន ស៊ីអារម្មណ៍ និងត្រូវសំឡេងតួអង្គ ១០០%។

សូមអនុវត្តតាមច្បាប់ទាំង ៤ នេះយ៉ាងតឹងរ៉ឹង៖
1. ភាសានិយាយធម្មជាតិ (Natural Spoken Language): ហាមដាច់ខាតការបកប្រែតាមបែបសរសេរស្ងួតៗ។ ត្រូវប្រើប្រាស់ពាក្យពេចន៍ដែលប្រជាជនខ្មែរនិយមនិយាយប្រចាំថ្ងៃ (ណា, ណ៎, ហ្មង, តើ, អញ្ចឹង, វើយ, ហាស, ចា៎)។
2. ត្រូវសំឡេងតួអង្គនិយាយ (Match the actor's voice): ប្រើសព្វនាមហៅគ្នា (បង/អូន, ឯង/អញ, ខ្ញុំ/លោក, ពួកម៉ាក, អា...) ឲ្យត្រូវនឹងអាយុនិងឋានៈតួអង្គ។
3. បញ្ចេញមនោសញ្ចេតនា (Emotional Depth): អានការបកប្រែរួច ត្រូវតែមានអារម្មណ៍ត្រូវនឹងសាច់រឿងដើម។
4. ទម្រង់លទ្ធផល (Output Format): ផ្តល់មកជាទម្រង់ SRT នៅក្នុង Code Block។
បញ្ជាក់ប្រយោគស្រីប្រុសដោយសញ្ញា [សំឡេងស្រី] ឬ [សំឡេងប្រុស] និងប្រយោគគិតក្នុងចិត្តដោយសញ្ញា [សំឡេងគិតស្រី] [សំឡេងគិតប្រុស] នៅដើមបន្ទាត់នីមួយៗ។"""

RECAP_SYSTEM_INSTRUCTION = """ចាប់ពីពេលនេះតទៅ សូមអ្នកដើរតួជា "អ្នកសម្រាយសាច់រឿងភាពយន្ត និងកាត់ត Highlight អាជីព (Expert Movie Recap & Smart Editor)"។ 
ភារកិច្ចចម្បងរបស់អ្នកគឺ៖ មិនមែនសម្រាយតាំងពីដើមដល់ចប់វីដេអូទេ គឺត្រូវ **ជ្រើសរើសកាត់យកតែឈុតឆាកសំខាន់ៗ (Key Highlight Scenes) ក្នុងវីដេអូដើម** មកសម្រាយសង្ខេបឱ្យខ្លី ខ្លឹម ជក់ចិត្ត និងទាក់ទាញបំផុត!

សូមអនុវត្តតាមច្បាប់តឹងរ៉ឹងទាំង ៥ នេះ៖
១. កាត់យកតែកន្លែងសំខាន់ (Highlight Scene Selection): 
   - ជ្រើសរើសតែប្លង់សំខាន់ៗនៃសាច់រឿង (ឧ. ចំណុចចាប់ផ្តើម, ចំណុចខ្ពស់/Climax, ឈុតប្រយុទ្ធ/រំភើប, និងការបញ្ចប់)។
   - កំណត់ Timecode (Start --> End) ឱ្យចំវិនាទីពិតប្រាកដនៃឈុតឆាកនោះ ព្រោះកម្មវិធីនឹងកាត់វីដេអូដើមយកតែតាមម៉ោងដែលអ្នកកំណត់នេះមកច្របាច់បញ្ចូលគ្នា។

២. ក្បាលរឿងទាក់ទាញ (Hooking Intro):
   - បើកឆាកភ្លាម ត្រូវប្រើពាក្យទាក់ទាញអារម្មណ៍អ្នកស្តាប់ភ្លាមៗ (ឧ. "រឿងរ៉ាវមិននឹកស្មានដល់បានកើតឡើង...", "តើអ្នកធ្លាប់គិតទេថា...", "កុំទាន់អាលស្លន់ស្លោ ព្រោះការពិតគឺ...")។

៣. ភាសានិទានរស់រវើក (Storytelling Tone):
   - ប្រើភាសានិយាយបែបសម្រាយរឿងខ្លី (Shorts/TikTok/Reels/Full Movie Recap) កំប្លុកកំប្លែង ជក់ចិត្ត ឬរន្ធត់។

៤. ស្លាកសំឡេងអ្នករៀបរាប់ (Voice Tag):
   - ដាក់ស្លាក [សំឡេងប្រុស] ឬ [សំឡេងស្រី] នៅដើមបន្ទាត់នីមួយៗ។

៥. ទម្រង់លទ្ធផល (Output Format):
   - ផ្តល់លទ្ធផលជាទម្រង់ SRT នៅក្នុង Code Block តែមួយគត់។"""

def clean_text_for_tts(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\[(សំឡេង)?ស្រី\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(សំឡេង)?ប្រុស\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(សំឡេង)?គិត.*?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[គិត\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\{.*?\}", "", text)
    text = re.sub(r"[\*\#\_\~\-\>\<]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def is_thought_voice(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"\[(សំឡេង)?គិត.*?\]|\[គិត\]|\(គិតក្នុងចិត្ត\)", text, re.IGNORECASE))

def detect_gender_from_text(text: str) -> str:
    if not text:
        return "male_normal"
    if re.search(r"\[(សំឡេង)?គិតស្រី\]", text, re.IGNORECASE):
        return "female_thought"
    if re.search(r"\[(សំឡេង)?គិតប្រុស\]", text, re.IGNORECASE):
        return "male_thought"
    if re.search(r"\[(សំឡេង)?គិត.*?\]|\[គិត\]|\(គិតក្នុងចិត្ត\)", text, re.IGNORECASE):
        if any(w in text for w in ["ចា៎", "ចាស", "អូន", "អ្នកនាង", "កញ្ញា", "លោកស្រី", "ម៉ាក់", "នាង"]):
            return "female_thought"
        return "male_thought"

    if re.search(r"\[(សំឡេង)?ស្រី\]", text, re.IGNORECASE) or "(ស្រី)" in text or "ស្រី:" in text:
        return "female_normal"
    if re.search(r"\[(សំឡេង)?ប្រុស\]", text, re.IGNORECASE) or "(ប្រុស)" in text or "ប្រុស:" in text:
        return "male_normal"

    female_keywords = ["ចា៎", "ចាស", "អូន", "អ្នកនាង", "កញ្ញា", "លោកស្រី", "អ្នកម៉ាក់", "ម៉ាក់", "យាយ", "នាង"]
    male_keywords = ["បាទ", "បង", "លោក", "លោកពូ", "ពូ", "តា", "លោកប៉ា", "ប៉ា", "អា"]

    for word in female_keywords:
        if word in text:
            return "female_normal"
    for word in male_keywords:
        if word in text:
            return "male_normal"

    return "male_normal"

def time_to_seconds(t_str: str) -> float:
    t_str = str(t_str).strip().replace(',', '.')
    parts = t_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    try:
        return float(t_str)
    except Exception:
        return 0.0

def seconds_to_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')

def parse_srt_content(raw_text: str) -> list:
    subtitles = []
    if not raw_text:
        return subtitles

    code_block_match = re.search(r'```(?:srt)?\s*(.*?)\s*```', raw_text, re.DOTALL)
    if code_block_match:
        raw_text = code_block_match.group(1)

    pattern = re.compile(
        r'(\d+)?\s*\n?(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*\n([\s\S]*?)(?=(?:\n\s*\n|\n\d+\s*\n|\Z))',
        re.MULTILINE
    )

    matches = list(pattern.finditer(raw_text))
    if matches:
        for idx, match in enumerate(matches):
            start_str = match.group(2).strip().replace('.', ',')
            end_str = match.group(3).strip().replace('.', ',')
            content = match.group(4).strip()
            content = re.sub(r'\n+', ' ', content)

            start_sec = time_to_seconds(start_str)
            end_sec = time_to_seconds(end_str)
            gender_mode = detect_gender_from_text(content)
            voice = "km-KH-SreymomNeural" if "female" in gender_mode else "km-KH-PisethNeural"
            is_thought = "thought" in gender_mode

            subtitles.append({
                "index": idx,
                "start": start_str,
                "end": end_str,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": content,
                "voice": voice,
                "is_thought": is_thought,
                "audio_url": None
            })
    else:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            gender_mode = detect_gender_from_text(line)
            voice = "km-KH-SreymomNeural" if "female" in gender_mode else "km-KH-PisethNeural"
            is_thought = "thought" in gender_mode
            start_sec = idx * 4.0
            end_sec = (idx + 1) * 4.0
            subtitles.append({
                "index": idx,
                "start": seconds_to_time(start_sec),
                "end": seconds_to_time(end_sec),
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": line,
                "voice": voice,
                "is_thought": is_thought,
                "audio_url": None
            })

    return subtitles

async def translate_with_gemini(text_or_prompt: str, api_key: str = None) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("សូមបញ្ចូល Gemini API Key ដើម្បីប្រើប្រាស់មុខងារបកប្រែ AI ដោយស្វ័យប្រវត្តិ!")
    try:
        from google import genai
        client = genai.Client(api_key=key)
        prompt = f"{SYSTEM_INSTRUCTION}\n\nអត្ថបទដែលត្រូវបកប្រែ៖\n{text_or_prompt}"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"កំហុស Gemini API: {str(e)}")

async def recap_with_gemini(text_or_prompt: str, api_key: str = None) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("សូមបញ្ចូល Gemini API Key ដើម្បីប្រើប្រាស់មុខងារសម្រាយរឿង AI!")
    try:
        from google import genai
        client = genai.Client(api_key=key)
        prompt = f"{RECAP_SYSTEM_INSTRUCTION}\n\nព័ត៌មាន/សាច់រឿងដើម៖\n{text_or_prompt}"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"កំហុស Gemini Recap API: {str(e)}")


# ==============================================================================
# 2. AUDIO & TTS HELPER FUNCTIONS
# ==============================================================================
def temp_path(filename: str) -> str:
    return os.path.join(TEMP_DIR, filename)

def enhance_voice_clarity(sound):
    if not sound or not AudioSegment or not normalize:
        return sound
    try:
        sound = sound.set_frame_rate(48000).set_channels(2)
        normalized = normalize(sound).high_pass_filter(70) + 1.5
        return normalized.fade_in(10).fade_out(10)
    except Exception:
        return sound

def add_reverb_thought_effect(sound):
    if not sound or not AudioSegment or not normalize:
        return sound
    try:
        sound = sound.set_frame_rate(48000).set_channels(2)
        delay_1 = AudioSegment.silent(duration=40) + (sound - 4.0)
        delay_2 = AudioSegment.silent(duration=90) + (sound - 7.5)
        delay_3 = AudioSegment.silent(duration=150) + (sound - 11.5)
        mixed = sound.overlay(delay_1).overlay(delay_2).overlay(delay_3)
        return normalize(mixed).fade_in(10).fade_out(10)
    except Exception:
        return sound

def adjust_audio_speed(input_file: str, output_file: str, speed_factor: float):
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
    if not edge_tts:
        return False
    real_idx = item.get('index', 0)
    raw_text = item.get('text', '')
    voice_code = item.get('voice', 'km-KH-PisethNeural')
    has_thought = is_thought_voice(raw_text) or item.get('is_thought', False)
    clean_tts_text = clean_text_for_tts(raw_text)

    start_sec = float(item.get('start_sec', 0.0))
    end_sec = float(item.get('end_sec', 1.0))
    srt_duration = max(0.5, end_sec - start_sec)

    if not clean_tts_text.strip():
        clean_tts_text = "..."

    raw_tts_file = temp_path(f"raw_voice_{session_id}_{real_idx}.mp3")
    final_file = temp_path(f"temp_voice_{session_id}_{real_idx}.mp3")

    for attempt in range(2):
        try:
            communicate = edge_tts.Communicate(clean_tts_text, voice_code)
            await communicate.save(raw_tts_file)

            if os.path.exists(raw_tts_file) and os.path.getsize(raw_tts_file) > 0:
                sound = None
                try:
                    if AudioSegment:
                        sound = AudioSegment.from_file(raw_tts_file)
                except Exception:
                    pass

                tts_duration = len(sound) / 1000.0 if sound else srt_duration

                if tts_duration > 0 and srt_duration > 0:
                    speed_factor = tts_duration / srt_duration
                    adjust_audio_speed(raw_tts_file, final_file, speed_factor)
                else:
                    shutil.copy(raw_tts_file, final_file)

                if not os.path.exists(final_file) or os.path.getsize(final_file) == 0:
                    shutil.copy(raw_tts_file, final_file)

                try:
                    if AudioSegment and os.path.exists(final_file):
                        sound_final = AudioSegment.from_file(final_file)
                        if has_thought:
                            sound_final = add_reverb_thought_effect(sound_final)
                        else:
                            sound_final = enhance_voice_clarity(sound_final)
                        sound_final.export(final_file, format="mp3", bitrate="192k")
                except Exception:
                    pass

                return True
        except Exception as e:
            await asyncio.sleep(0.3 * (attempt + 1))

    return False


# ==============================================================================
# 3. DOWNLOADER HELPER FUNCTIONS
# ==============================================================================
def extract_links_from_url(target_url: str) -> list:
    if not yt_dlp:
        raise RuntimeError("សូមដំឡើង yt-dlp ជាមុនសិន!")
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'skip_download': True,
        'nocheckcertificate': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(target_url, download=False)
        if 'entries' in info:
            urls = []
            for entry in info['entries']:
                if entry and 'url' in entry:
                    urls.append(entry['url'])
            return urls if urls else [target_url]
        return [target_url]

def download_batch_videos(urls: list, progress_callback=None) -> list:
    if not yt_dlp:
        raise RuntimeError("សូមដំឡើង yt-dlp ជាមុនសិន!")
    if not urls:
        raise ValueError("ពុំមាន Link ត្រឹមត្រូវសម្រាប់ទាញយកឡើយ!")

    session_folder = os.path.join(DOWNLOAD_DIR, f"Series_Batch_{time.strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(session_folder, exist_ok=True)

    total_items = len(urls)
    for idx, url in enumerate(urls):
        ep_num = f"{(idx + 1):02d}"
        if progress_callback:
            progress_callback(int((idx / total_items) * 100), f"កំពុងទាញយកភាគ {ep_num}/{total_items}...")

        output_template = os.path.join(session_folder, f"{ep_num}_%(title)s.%(ext)s")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'merge_output_format': 'mp4',
            'quiet': True,
            'noplaylist': False,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if progress_callback:
            progress_callback(int(((idx + 1) / total_items) * 100), f"ទាញយកភាគ {ep_num} រួចរាល់")

    mp4_files = glob.glob(os.path.join(session_folder, "*.mp4")) + glob.glob(os.path.join(session_folder, "*/*.mp4"))
    mp4_files.sort()
    return mp4_files

def download_single_video(url: str, progress_callback=None) -> str:
    if not yt_dlp:
        raise RuntimeError("សូមដំឡើង yt-dlp ជាមុនសិន!")
    if not url or not url.strip().startswith("http"):
        raise ValueError("សូមបញ្ចូល Link វីដេអូដែលត្រឹមត្រូវ!")

    session_folder = os.path.join(DOWNLOAD_DIR, f"Single_{time.strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(session_folder, exist_ok=True)

    if progress_callback:
        progress_callback(20, "កំពុងចាប់ផ្តើមទាញយកវីដេអូ...")

    output_template = os.path.join(session_folder, "%(title)s.%(ext)s")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if progress_callback:
        progress_callback(90, "ទាញយកវីដេអូរួចរាល់ កំពុងរៀបចំ...")

    mp4_files = glob.glob(os.path.join(session_folder, "*.mp4")) + glob.glob(os.path.join(session_folder, "*/*.mp4"))
    if mp4_files:
        if progress_callback:
            progress_callback(100, "ទាញយកវីដេអូជោគជ័យ!")
        return mp4_files[0]

    raise RuntimeError("មិនអាចស្វែងរក File វីដេអូដែលបានទាញយកឡើយ!")


# ==============================================================================
# 4. VIDEO & FFMPEG RENDERING FUNCTIONS (ROBUST & ULTRA FAST)
# ==============================================================================
def check_has_audio(video_path: str) -> bool:
    if not os.path.exists(video_path):
        return False
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "json",
        video_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            return len(data.get("streams", [])) > 0
    except Exception:
        pass
    return False

def get_video_dimension_and_duration(video_path: str):
    if not os.path.exists(video_path):
        return 1280, 720, 60.0

    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration:format=duration",
        "-of", "json",
        video_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            w = 1280
            h = 720
            dur = None

            if streams:
                w = int(streams[0].get("width", 1280))
                h = int(streams[0].get("height", 720))
                if streams[0].get("duration"):
                    try:
                        dur = float(streams[0]["duration"])
                    except Exception:
                        pass

            if (dur is None or dur <= 0) and "format" in data:
                fmt_dur = data["format"].get("duration")
                if fmt_dur:
                    try:
                        dur = float(fmt_dur)
                    except Exception:
                        pass

            if dur is None or dur <= 0:
                cmd_ffmpeg = ["ffmpeg", "-i", video_path]
                res_ffmpeg = subprocess.run(cmd_ffmpeg, capture_output=True, text=True, errors="ignore")
                dur_match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d+)", res_ffmpeg.stderr)
                if dur_match:
                    h_m, m_m, s_m = dur_match.groups()
                    dur = float(h_m) * 3600 + float(m_m) * 60 + float(s_m)

            if dur is None or dur <= 0:
                dur = 60.0

            return w, h, dur
    except Exception:
        pass

    return 1280, 720, 60.0

def generate_title_image_pil(text: str, width: int, height: int, norm_x: float, norm_y: float, color_hex: str, font_size: int = 26) -> str:
    if not text.strip() or not Image:
        return ""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = None
    khmer_font_candidates = [
        r"C:\Windows\Fonts\KhmerOSbattambang.ttf",
        r"C:\Windows\Fonts\KhmerOSsiemreap.ttf",
        r"C:\Windows\Fonts\KhmerOS.ttf",
        "/usr/share/fonts/truetype/khmer/Battambang-Regular.ttf",
        "/usr/share/fonts/truetype/khmer/KhmerOSbattambang.ttf",
        r"C:\Windows\Fontsrial.ttf",
        "arial.ttf"
    ]
    for candidate in khmer_font_candidates:
        if os.path.exists(candidate):
            try:
                font = ImageFont.truetype(candidate, font_size)
                break
            except Exception:
                pass
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            pass

    tx = int(norm_x * width)
    ty = int(norm_y * height)

    stroke_offset = max(2, int(font_size * 0.08))
    for dx in range(-stroke_offset, stroke_offset + 1):
        for dy in range(-stroke_offset, stroke_offset + 1):
            if dx != 0 or dy != 0:
                draw.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 255))

    hex_clean = color_hex.lstrip("#")
    r, g, b = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
    draw.text((tx, ty), text, font=font, fill=(r, g, b, 255))

    out_png = temp_path(f"title_pil_{int(time.time() * 1000)}.png")
    img.save(out_png, "PNG")
    return out_png

def create_ass_subtitle_file(subtitles: list, target_w: int, target_h: int, sub_norm_y: float, sub_color_hex: str, font_family: str, font_size: int, speed_factor: float = 1.0) -> str:
    if not subtitles:
        return ""
    ass_path = temp_path(f"custom_sub_{int(time.time() * 1000)}.ass")
    hex_clean = sub_color_hex.lstrip("#")
    if len(hex_clean) == 6:
        r, g, b = hex_clean[0:2], hex_clean[2:4], hex_clean[4:6]
        ass_color = f"&H00{b}{g}{r}&"
    else:
        ass_color = "&H00FFFFFF&"

    margin_v = max(10, int((1.0 - sub_norm_y) * target_h) - 30)
    scaled_font_size = max(14, int(font_size * (target_h / 540.0)))
    font_name = font_family if font_family else "Khmer OS Battambang"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {target_w}
PlayResY: {target_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{scaled_font_size},{ass_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def format_ass_time(sec):
        sec = sec / speed_factor
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        cs = int((s - int(s)) * 100)
        return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"

    events = []
    for sub in subtitles:
        s_sec = sub.get('start_sec', time_to_seconds(sub.get('start', '00:00:00,000')))
        e_sec = sub.get('end_sec', time_to_seconds(sub.get('end', '00:00:00,000')))
        txt = sub.get('text', '')
        txt = re.sub(r'\[.*?\]', '', txt)
        txt = txt.replace('\n', ' ').strip()
        if txt:
            events.append(f"Dialogue: 0,{format_ass_time(s_sec)},{format_ass_time(e_sec)},Default,,0,0,0,,{txt}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return ass_path

def export_dubbed_video(
    video_path: str,
    subtitles: list,
    output_path: str,
    overlay_options: dict,
    audio_options: dict,
    session_id: str = "default",
    progress_callback=None
) -> str:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"រកមិនឃើញ File វីដេអូ: {video_path}")

    orig_w, orig_h, dur_sec = get_video_dimension_and_duration(video_path)
    has_orig_audio = check_has_audio(video_path)
    aspect_ratio = overlay_options.get("aspect_ratio", "original")

    if aspect_ratio == "16:9":
        target_w, target_h = 1920, 1080
    elif aspect_ratio == "9:16":
        target_w, target_h = 1080, 1920
    elif aspect_ratio == "1:1":
        target_w, target_h = 1080, 1080
    elif aspect_ratio == "4:3":
        target_w, target_h = 1440, 1080
    else:
        target_w, target_h = orig_w, orig_h

    anti_detect = overlay_options.get("anti_detect", False)
    speed_shift = overlay_options.get("speed_shift", False)
    speed_factor = 1.05 if (anti_detect and speed_shift) else 1.0

    tts_chunks = []
    for sub in subtitles:
        idx = sub.get("index", 0)
        s_sec = sub.get("start_sec", time_to_seconds(sub.get("start", "00:00:00,000")))
        final_tts_file = temp_path(f"temp_voice_{session_id}_{idx}.mp3")
        if os.path.exists(final_tts_file) and os.path.getsize(final_tts_file) > 0:
            tts_chunks.append((s_sec / speed_factor, final_tts_file))

    has_tts = len(tts_chunks) > 0
    merged_tts_wav = None

    if has_tts and AudioSegment:
        full_audio_dur_ms = int((dur_sec / speed_factor) * 1000) + 2000
        combined_tts = AudioSegment.silent(duration=full_audio_dur_ms, frame_rate=48000)
        for start_sec, tts_file in tts_chunks:
            try:
                seg = AudioSegment.from_file(tts_file).set_frame_rate(48000).set_channels(2)
                pos_ms = int(start_sec * 1000)
                combined_tts = combined_tts.overlay(seg, position=pos_ms)
            except Exception:
                pass

        merged_tts_wav = temp_path(f"combined_tts_{session_id}_{int(time.time())}.wav")
        combined_tts.export(merged_tts_wav, format="wav")

    inputs = ["-i", video_path]
    v_filters = []
    a_filters = []
    curr_tag = "0:v"
    curr_a_tag = "0:a"

    if (target_w != orig_w or target_h != orig_h):
        v_filters.append(f"[{curr_tag}]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black[v_scaled]")
        curr_tag = "v_scaled"

    if anti_detect:
        v_filters.append(f"[{curr_tag}]eq=contrast=1.05:brightness=0.02:saturation=1.08,unsharp=3:3:0.8[v_enhanced]")
        curr_tag = "v_enhanced"

    if anti_detect and speed_shift:
        v_filters.append(f"[{curr_tag}]setpts={1.0/speed_factor:.6f}*PTS[v_speed]")
        curr_tag = "v_speed"

    if overlay_options.get("enable_blur", False):
        bx = int(overlay_options.get("blur_norm_x", 0.05) * target_w)
        by = int(overlay_options.get("blur_norm_y", 0.05) * target_h)
        bw = max(10, int(overlay_options.get("blur_norm_w", 0.18) * target_w))
        bh = max(10, int(overlay_options.get("blur_norm_h", 0.12) * target_h))
        strength = max(5, int(overlay_options.get("blur_strength", 25)))
        v_filters.append(f"[{curr_tag}]split[v_main][v_blur_in]")
        v_filters.append(f"[v_blur_in]crop={bw}:{bh}:{bx}:{by},boxblur={strength}:5[v_blurred_crop]")
        v_filters.append(f"[v_main][v_blurred_crop]overlay={bx}:{by}[v_blurred_done]")
        curr_tag = "v_blurred_done"

    logo_path = overlay_options.get("logo_path")
    if logo_path and os.path.exists(logo_path):
        logo_input_idx = len(inputs) // 2
        inputs.extend(["-i", logo_path])
        lw = max(20, int(overlay_options.get("logo_norm_w", 0.15) * target_w))
        lx = int(overlay_options.get("logo_norm_x", 0.85) * target_w)
        ly = int(overlay_options.get("logo_norm_y", 0.05) * target_h)
        v_filters.append(f"[{logo_input_idx}:v]scale={lw}:-1[logo_scaled]")
        v_filters.append(f"[{curr_tag}][logo_scaled]overlay={lx}:{ly}[v_logo_done]")
        curr_tag = "v_logo_done"

    title_text = overlay_options.get("title_text", "").strip()
    if title_text:
        title_norm_x = overlay_options.get("title_norm_x", 0.35)
        title_norm_y = overlay_options.get("title_norm_y", 0.08)
        title_color = overlay_options.get("title_color", "#FFEA00")
        title_font_size = overlay_options.get("title_font_size", 26)
        title_png = generate_title_image_pil(title_text, target_w, target_h, title_norm_x, title_norm_y, title_color, title_font_size)
        if title_png and os.path.exists(title_png):
            title_input_idx = len(inputs) // 2
            inputs.extend(["-i", title_png])
            v_filters.append(f"[{curr_tag}][{title_input_idx}:v]overlay=0:0[v_title_done]")
            curr_tag = "v_title_done"

    if overlay_options.get("show_subtitles", True) and subtitles:
        sub_norm_y = overlay_options.get("sub_norm_y", 0.85)
        sub_color = overlay_options.get("sub_color", "#FFFFFF")
        sub_font_family = overlay_options.get("sub_font_family", "Battambang")
        sub_font_size = overlay_options.get("sub_font_size", 18)
        ass_sub_file = create_ass_subtitle_file(subtitles, target_w, target_h, sub_norm_y, sub_color, sub_font_family, sub_font_size, speed_factor)
        if ass_sub_file and os.path.exists(ass_sub_file):
            escaped_ass = ass_sub_file.replace("\\", "/").replace(":", "\\:")
            v_filters.append(f"[{curr_tag}]ass='{escaped_ass}'[v_sub_done]")
            curr_tag = "v_sub_done"

    orig_vol = audio_options.get("orig_audio_volume", 0.35)
    mute_orig = audio_options.get("mute_orig", False)

    # Audio Stream Graph Handling (Zero Crash Guarantee)
    if has_orig_audio:
        if merged_tts_wav and os.path.exists(merged_tts_wav):
            tts_input_idx = len(inputs) // 2
            inputs.extend(["-i", merged_tts_wav])
            if not mute_orig:
                vol_factor = max(0.0, min(orig_vol, 1.0))
                a_filters.append(f"[0:a]stereotools=mlev=0.0,volume={vol_factor:.2f}[bg_music]")
                if anti_detect and speed_shift:
                    a_filters.append(f"[bg_music]atempo={speed_factor}[bg_music_sped]")
                    a_filters.append(f"[bg_music_sped][{tts_input_idx}:a]amix=inputs=2:duration=longest:weights=1 2.5[{curr_a_tag}]")
                else:
                    a_filters.append(f"[bg_music][{tts_input_idx}:a]amix=inputs=2:duration=longest:weights=1 2.5[{curr_a_tag}]")
            else:
                a_filters.append(f"[{tts_input_idx}:a]anull[{curr_a_tag}]")
        elif not mute_orig:
            vol_factor = max(0.0, min(orig_vol, 1.0))
            a_filters.append(f"[0:a]stereotools=mlev=0.0,volume={vol_factor:.2f}[bg_music]")
            if anti_detect and speed_shift:
                a_filters.append(f"[bg_music]atempo={speed_factor}[{curr_a_tag}]")
            else:
                a_filters.append(f"[bg_music]anull[{curr_a_tag}]")
        else:
            a_filters.append(f"aevalsrc=0:d={dur_sec}[{curr_a_tag}]")
    else:
        # Video has NO native audio stream
        if merged_tts_wav and os.path.exists(merged_tts_wav):
            tts_input_idx = len(inputs) // 2
            inputs.extend(["-i", merged_tts_wav])
            a_filters.append(f"[{tts_input_idx}:a]anull[{curr_a_tag}]")
        else:
            a_filters.append(f"aevalsrc=0:d={dur_sec}[{curr_a_tag}]")

    all_filters = v_filters + a_filters

    if progress_callback:
        progress_callback(5, "ចាប់ផ្តើម Render & Encode វីដេអូ (5%)...")

    ffmpeg_export_cmd = ["ffmpeg", "-y"] + inputs
    ffmpeg_export_cmd.extend([
        "-filter_complex", ";".join(all_filters),
        "-map", f"[{curr_tag}]",
        "-map", f"[{curr_a_tag}]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "fastdecode",
        "-crf", "22",
        "-threads", "0",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-avoid_negative_ts", "make_zero",
        "-progress", "pipe:1",
        "-loglevel", "error",
        output_path
    ])

    process = subprocess.Popen(
        ffmpeg_export_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="ignore"
    )

    effective_dur = max(1.0, dur_sec / speed_factor)
    last_reported_percent = -1

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        if line.startswith("out_time_us="):
            parts = line.split("=")
            if len(parts) == 2 and parts[1].isdigit():
                val = int(parts[1])
                cur_time = val / 1000000.0
                render_percent = min(99, max(5, int((cur_time / effective_dur) * 100)))
                if render_percent > last_reported_percent:
                    last_reported_percent = render_percent
                    if progress_callback:
                        progress_callback(render_percent, f"កំពុង Render វីដេអូ ({render_percent}%)...")
        elif line == "progress=end":
            if progress_callback:
                progress_callback(99, "កំពុងបញ្ចប់ការ Render (99%)...")

    retcode = process.wait()
    if retcode != 0:
        err_out = process.stderr.read() if process.stderr else f"Exit code {retcode}"
        raise RuntimeError(f"FFmpeg Error ({err_out.strip()})")

    if progress_callback:
        progress_callback(100, "នាំចេញវីដេអូជោគជ័យ!")

    return output_path

def split_video_into_chunks(video_path: str, chunk_duration_sec: int, progress_callback=None) -> list:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"រកមិនឃើញ File វីដេអូ: {video_path}")
    w, h, total_dur = get_video_dimension_and_duration(video_path)
    if chunk_duration_sec <= 0:
        chunk_duration_sec = 60

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    out_dir = os.path.join(EXPORT_DIR, f"Split_{base_name}_{int(time.time())}")
    os.makedirs(out_dir, exist_ok=True)

    chunks = []
    current_start = 0.0
    part_idx = 1
    total_parts = int(total_dur // chunk_duration_sec) + (1 if total_dur % chunk_duration_sec > 0 else 0)

    while current_start < total_dur:
        if progress_callback:
            prog = int((part_idx / total_parts) * 100)
            progress_callback(prog, f"កំពុងកាត់ភាគទី {part_idx}/{total_parts}...")

        out_file = os.path.join(out_dir, f"{base_name}_Part_{part_idx:02d}.mp4")
        dur_to_cut = min(chunk_duration_sec, total_dur - current_start)

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{current_start:.3f}",
            "-i", video_path,
            "-t", f"{dur_to_cut:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            out_file
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
            chunks.append(out_file)

        current_start += chunk_duration_sec
        part_idx += 1

    if progress_callback:
        progress_callback(100, f"កាត់វីដេអូបាន {len(chunks)} ភាគរួចរាល់!")

    return chunks

def extract_and_merge_highlights(video_path: str, highlight_segments: list, output_path: str, progress_callback=None) -> str:
    if not highlight_segments:
        raise ValueError("ពុំមាន Timecode ឈុត Highlight ឡើយ!")

    temp_clips = []
    total_segs = len(highlight_segments)

    for idx, seg in enumerate(highlight_segments):
        s_sec = seg.get("start_sec", time_to_seconds(seg.get("start", "00:00:00,000")))
        e_sec = seg.get("end_sec", time_to_seconds(seg.get("end", "00:00:00,000")))
        dur = max(0.5, e_sec - s_sec)

        if progress_callback:
            prog = int((idx / (total_segs + 1)) * 100)
            progress_callback(prog, f"កំពុងកាត់ឈុត Highlight ទី {idx+1}/{total_segs}...")

        clip_file = temp_path(f"hl_clip_{int(time.time())}_{idx}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{s_sec:.3f}",
            "-i", video_path,
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            clip_file
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(clip_file) and os.path.getsize(clip_file) > 0:
            temp_clips.append(clip_file)

    if not temp_clips:
        raise RuntimeError("កាត់ឈុត Highlight មិនបានសម្រេច!")

    concat_txt = temp_path(f"hl_concat_{int(time.time())}.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for clip in temp_clips:
            clean_path = clip.replace("\\", "/")
            f.write(f"file '{clean_path}'\n")

    if progress_callback:
        progress_callback(90, "កំពុងច្របាច់ឈុត Highlight ចូលគ្នា...")

    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_txt,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-avoid_negative_ts", "make_zero",
        output_path
    ]
    subprocess.run(concat_cmd, capture_output=True, text=True)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        if progress_callback:
            progress_callback(100, "កាត់ & ច្របាច់ Highlight ជោគជ័យ!")
        return output_path

    raise RuntimeError("បរាជ័យក្នុងការច្របាច់ Highlight!")

def merge_videos(video_files: list, output_path: str, progress_callback=None) -> str:
    if not video_files:
        raise ValueError("ពុំមានបញ្ជី File សម្រាប់ Merge ឡើយ!")

    concat_list_file = temp_path(f"concat_list_{int(time.time())}.txt")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for vf in video_files:
            if os.path.exists(vf):
                clean_p = vf.replace("\\", "/")
                f.write(f"file '{clean_p}'\n")

    if progress_callback:
        progress_callback(20, "កំពុងរៀបចំ Merge វីដេអូ...")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_file,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-avoid_negative_ts", "make_zero",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        if progress_callback:
            progress_callback(100, "Merge វីដេអូជោគជ័យ!")
        return output_path

    raise RuntimeError("ការ Merge វីដេអូបរាជ័យ!")


# ==============================================================================
# 5. FASTAPI APPLICATION SETUP & ENDPOINTS
# ==============================================================================
app = FastAPI(title="Smart AI Studio Web", description="Khmer AI Video Dubbing & Subtitling Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/exports", StaticFiles(directory=EXPORT_DIR), name="exports")
app.mount("/temp", StaticFiles(directory=TEMP_DIR), name="temp")
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

css_dir = os.path.join(STATIC_DIR, "css") if os.path.exists(os.path.join(STATIC_DIR, "css")) else os.path.join(RESOURCE_DIR, "css")
js_dir = os.path.join(STATIC_DIR, "js") if os.path.exists(os.path.join(STATIC_DIR, "js")) else os.path.join(RESOURCE_DIR, "js")
if os.path.exists(css_dir):
    app.mount("/css", StaticFiles(directory=css_dir), name="css")
if os.path.exists(js_dir):
    app.mount("/js", StaticFiles(directory=js_dir), name="js")

active_tasks = {}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    static_index = os.path.join(STATIC_DIR, "index.html")
    root_index = os.path.join(RESOURCE_DIR, "index.html")
    target_file = static_index if os.path.exists(static_index) else root_index
    if os.path.exists(target_file):
        with open(target_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h2>Smart AI Studio is running! Please place index.html in root or static/ folder.</h2>")

@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    w, h, dur = get_video_dimension_and_duration(file_path)
    return {
        "success": True,
        "filename": file.filename,
        "file_path": file_path,
        "file_url": f"/uploads/{filename}",
        "width": w,
        "height": h,
        "duration": dur
    }

@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    filename = f"logo_{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {
        "success": True,
        "file_path": file_path,
        "file_url": f"/uploads/{filename}"
    }

@app.post("/api/parse-srt")
async def parse_srt(raw_text: Optional[str] = Form(None), file: Optional[UploadFile] = File(None)):
    content = ""
    if file:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="ignore")
    elif raw_text:
        content = raw_text

    subtitles = parse_srt_content(content)
    return {"success": True, "count": len(subtitles), "subtitles": subtitles}

@app.post("/api/translate-gemini")
async def translate_gemini_endpoint(request: Request):
    data = await request.json()
    prompt_or_text = data.get("text", "")
    api_key = data.get("api_key", "")
    try:
        translated = await translate_with_gemini(prompt_or_text, api_key)
        subtitles = parse_srt_content(translated)
        return {"success": True, "raw_result": translated, "subtitles": subtitles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recap-gemini")
async def recap_gemini_endpoint(request: Request):
    data = await request.json()
    prompt_or_text = data.get("text", "")
    api_key = data.get("api_key", "")
    try:
        recap_result = await recap_with_gemini(prompt_or_text, api_key)
        subtitles = parse_srt_content(recap_result)
        return {"success": True, "raw_result": recap_result, "subtitles": subtitles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-single-tts")
@app.post("/api/generate-tts-single")
async def generate_tts_single_endpoint(request: Request):
    data = await request.json()
    item = data.get("item", {})
    session_id = data.get("session_id", "default")
    idx = item.get("index", 0)
    ok = await generate_single_tts(item, session_id=session_id)
    if ok:
        filename = f"temp_voice_{session_id}_{idx}.mp3"
        return {"success": True, "audio_url": f"/temp/{filename}?t={int(time.time()*1000)}"}
    raise HTTPException(status_code=500, detail="TTS Generation Failed")

@app.post("/api/generate-batch-tts")
@app.post("/api/generate-tts-batch")
async def generate_tts_batch_endpoint(request: Request):
    data = await request.json()
    subtitles = data.get("items") or data.get("subtitles") or []
    session_id = data.get("session_id", "default")
    task_id = str(uuid.uuid4())

    active_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "ចាប់ផ្តើមបង្កើតសំឡេង AI (ល្បឿនលឿន)...",
        "completed": False,
        "results": []
    }

    async def run_batch():
        total = len(subtitles)
        if total == 0:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["progress"] = 100
            active_tasks[task_id]["message"] = "ពុំមាន Subtitle ត្រូវបង្កើតសំឡេងឡើយ!"
            return

        completed_count = 0
        results = [None] * total
        sem = asyncio.Semaphore(10)

        async def worker(i, sub):
            nonlocal completed_count
            async with sem:
                real_idx = sub.get("index", i)
                ok = await generate_single_tts(sub, session_id=session_id)
                audio_url = f"/temp/temp_voice_{session_id}_{real_idx}.mp3?t={int(time.time()*1000)}" if ok else None
                results[i] = {"index": real_idx, "success": ok, "audio_url": audio_url}
                completed_count += 1
                prog = min(99, int((completed_count / total) * 100))
                active_tasks[task_id]["progress"] = prog
                active_tasks[task_id]["message"] = f"កំពុងបង្កើតសំឡេង AI ({completed_count}/{total}) {prog}%..."

        tasks = [worker(i, sub) for i, sub in enumerate(subtitles)]
        await asyncio.gather(*tasks)

        active_tasks[task_id]["progress"] = 100
        active_tasks[task_id]["message"] = f"បង្កើតសំឡេង AI ជោគជ័យទាំងអស់ {total} ជួរ!"
        active_tasks[task_id]["completed"] = True
        active_tasks[task_id]["results"] = results

    asyncio.create_task(run_batch())
    return {"success": True, "task_id": task_id}

@app.post("/api/export-video")
async def export_video_endpoint(request: Request):
    data = await request.json()
    video_path = data.get("video_path")
    subtitles = data.get("subtitles", [])
    overlay_options = data.get("overlay_options", {})
    audio_options = data.get("audio_options", {})
    session_id = data.get("session_id", "default")

    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="សូមបញ្ចូល File វីដេអូជាមុនសិន!")

    task_id = str(uuid.uuid4())
    out_name = f"Export_{int(time.time())}.mp4"
    output_path = os.path.join(EXPORT_DIR, out_name)

    active_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "កំពុងរៀបចំ Render វីដេអូ...",
        "completed": False,
        "output_url": None,
        "download_url": None
    }

    def progress_cb(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["message"] = msg

    def run_export():
        try:
            export_dubbed_video(
                video_path=video_path,
                subtitles=subtitles,
                output_path=output_path,
                overlay_options=overlay_options,
                audio_options=audio_options,
                session_id=session_id,
                progress_callback=progress_cb
            )
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["output_url"] = f"/exports/{out_name}"
            active_tasks[task_id]["download_url"] = f"/api/download-export/{out_name}"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.get_event_loop().run_in_executor(None, run_export)
    return {"success": True, "task_id": task_id}

@app.get("/api/download-export/{filename}")
async def download_export_file(filename: str):
    file_path = os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="រកមិនឃើញ File នេះឡើយ!")
    return FileResponse(file_path, filename=filename, media_type="video/mp4")

@app.post("/api/split-video")
async def split_video_endpoint(request: Request):
    data = await request.json()
    video_path = data.get("video_path")
    chunk_sec = int(data.get("chunk_seconds", 60))
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="សូមបញ្ចូល File វីដេអូជាមុនសិន!")

    task_id = str(uuid.uuid4())
    active_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "កំពុងកាត់វីដេអូជាកង់ៗ...",
        "completed": False,
        "chunks": []
    }

    def progress_cb(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["message"] = msg

    def run_split():
        try:
            chunks = split_video_into_chunks(video_path, chunk_sec, progress_callback=progress_cb)
            chunk_results = []
            for c in chunks:
                fn = os.path.basename(c)
                rel_dir = os.path.basename(os.path.dirname(c))
                chunk_results.append({
                    "filename": fn,
                    "file_path": c,
                    "download_url": f"/exports/{rel_dir}/{fn}"
                })
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["chunks"] = chunk_results
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.get_event_loop().run_in_executor(None, run_split)
    return {"success": True, "task_id": task_id}

@app.post("/api/export-highlights")
async def export_highlights_endpoint(request: Request):
    data = await request.json()
    video_path = data.get("video_path")
    highlights = data.get("highlights", [])
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="សូមបញ្ចូល File វីដេអូជាមុនសិន!")
    if not highlights:
        raise HTTPException(status_code=400, detail="ពុំមាន Timecode Highlight ឡើយ!")

    task_id = str(uuid.uuid4())
    out_name = f"Highlight_Merged_{int(time.time())}.mp4"
    output_path = os.path.join(EXPORT_DIR, out_name)

    active_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "កំពុងកាត់ & ច្របាច់ Highlight...",
        "completed": False,
        "output_url": None,
        "download_url": None
    }

    def progress_cb(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["message"] = msg

    def run_highlights():
        try:
            extract_and_merge_highlights(video_path, highlights, output_path, progress_callback=progress_cb)
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["output_path"] = output_path
            active_tasks[task_id]["output_url"] = f"/exports/{out_name}"
            active_tasks[task_id]["download_url"] = f"/api/download-export/{out_name}"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.get_event_loop().run_in_executor(None, run_highlights)
    return {"success": True, "task_id": task_id}

@app.post("/api/merge-videos")
async def merge_videos_endpoint(request: Request):
    data = await request.json()
    video_files = data.get("video_files", [])
    if not video_files or len(video_files) < 2:
        raise HTTPException(status_code=400, detail="សូមបញ្ចូលយ៉ាងតិច ២ វីដេអូឡើងទៅ!")

    task_id = str(uuid.uuid4())
    out_name = f"Merged_Series_{int(time.time())}.mp4"
    output_path = os.path.join(EXPORT_DIR, out_name)

    active_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "កំពុង Merge វីដេអូទាំងអស់...",
        "completed": False,
        "output_url": None,
        "download_url": None
    }

    def progress_cb(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["message"] = msg

    def run_merge():
        try:
            merge_videos(video_files, output_path, progress_callback=progress_cb)
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["output_path"] = output_path
            active_tasks[task_id]["output_url"] = f"/exports/{out_name}"
            active_tasks[task_id]["download_url"] = f"/api/download-export/{out_name}"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.get_event_loop().run_in_executor(None, run_merge)
    return {"success": True, "task_id": task_id}

@app.post("/api/download-single")
async def download_single_endpoint(request: Request):
    data = await request.json()
    url = data.get("url", "")
    task_id = str(uuid.uuid4())
    active_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "កំពុងទាញយកវីដេអូ...",
        "completed": False,
        "file_path": None,
        "file_url": None
    }

    def progress_cb(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["message"] = msg

    def run_dl():
        try:
            file_p = download_single_video(url, progress_callback=progress_cb)
            fn = os.path.basename(file_p)
            rel_dir = os.path.basename(os.path.dirname(file_p))
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["file_path"] = file_p
            active_tasks[task_id]["file_url"] = f"/downloads/{rel_dir}/{fn}"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.get_event_loop().run_in_executor(None, run_dl)
    return {"success": True, "task_id": task_id}

@app.post("/api/download-batch")
async def download_batch_endpoint(request: Request):
    data = await request.json()
    urls = data.get("urls", [])
    task_id = str(uuid.uuid4())
    active_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "កំពុងរៀបចំទាញយកវីដេអូជាស៊េរី...",
        "completed": False,
        "video_files": []
    }

    def progress_cb(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["message"] = msg

    def run_batch_dl():
        try:
            files = download_batch_videos(urls, progress_callback=progress_cb)
            video_list = []
            for f in files:
                fn = os.path.basename(f)
                rel_dir = os.path.basename(os.path.dirname(f))
                video_list.append({
                    "filename": fn,
                    "file_path": f,
                    "file_url": f"/downloads/{rel_dir}/{fn}"
                })
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["video_files"] = video_list
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.get_event_loop().run_in_executor(None, run_batch_dl)
    return {"success": True, "task_id": task_id}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="រកមិនឃើញ Task ID នេះទេ!")
    return active_tasks[task_id]

@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            if task_id in active_tasks:
                task = active_tasks[task_id]
                yield f"data: {json.dumps(task, ensure_ascii=False)}\n\n"
                if task.get("completed", False):
                    break
            await asyncio.sleep(0.3)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 កំពុងដំណើរការ Smart AI Studio Web នៅលើ http://0.0.0.0:{port} ...")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
