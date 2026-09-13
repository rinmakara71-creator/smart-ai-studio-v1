import os
import time
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont
from services.ai_service import time_to_seconds, clean_text_for_tts

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, "temp_dubbing_files")
EXPORT_DIR = os.path.join(BASE_DIR, "Exported_Videos")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)


def temp_path(filename: str) -> str:
    return os.path.join(TEMP_DIR, filename)


def get_video_dimension_and_duration(video_path: str):
    w, h, dur = 1920, 1080, 0.0
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,duration:format=duration",
            "-of", "json", video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        data = json.loads(res.stdout)
        if "format" in data and data["format"].get("duration"):
            try:
                dur = float(data["format"]["duration"])
            except Exception:
                pass
        if "streams" in data and len(data["streams"]) > 0:
            for st in data["streams"]:
                if st.get("width") and st.get("height"):
                    w = int(st["width"])
                    h = int(st["height"])
                if dur <= 0.0 and st.get("duration"):
                    try:
                        dur = float(st["duration"])
                    except Exception:
                        pass
    except Exception as e:
        print(f"ffprobe error: {e}")

    # Fallback to ffmpeg -i parsing if duration is still 0
    if dur <= 0.0:
        try:
            cmd2 = ["ffmpeg", "-i", video_path]
            res2 = subprocess.run(cmd2, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, timeout=10)
            import re
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res2.stderr)
            if m:
                dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        except Exception:
            pass

    if dur <= 0.0:
        dur = 60.0  # sensible 1-minute fallback instead of 2 hours

    return w, h, dur


def generate_khmer_title_image_pil(text: str, width: int, height: int, norm_x: float, norm_y: float, color_hex: str, font_family: str, font_size: int) -> str:
    if not text.strip():
        return ""

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Try to load Windows Khmer font or fallback
    font = None
    khmer_font_candidates = [
        r"C:\Windows\Fonts\KhmerOSbattambang.ttf",
        r"C:\Windows\Fonts\KhmerOSsiemreap.ttf",
        r"C:\Windows\Fonts\KhmerOS.ttf",
        r"C:\Windows\Fonts\arial.ttf",
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

    # Draw black shadow / stroke
    stroke_offset = max(2, int(font_size * 0.08))
    for dx in range(-stroke_offset, stroke_offset + 1):
        for dy in range(-stroke_offset, stroke_offset + 1):
            if dx != 0 or dy != 0:
                draw.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 255))

    # Parse hex color
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
        clean_text = clean_text_for_tts(sub.get('text', '')).replace("\n", "\\N")
        if clean_text:
            events.append(f"Dialogue: 0,{format_ass_time(s_sec)},{format_ass_time(e_sec)},Default,,0,0,0,,{clean_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return ass_path


async def export_dubbed_video(
    video_path: str,
    table_data: list,
    subtitles_data: list,
    output_path: str,
    session_id: str = "default",
    bg_music_vol_percent: int = 50,
    aspect_ratio: str = "Original",
    resolution: str = "1080p (Full HD)",
    video_title: str = "",
    title_norm_x: float = 0.35,
    title_norm_y: float = 0.08,
    title_color: str = "#FFEA00",
    title_font_family: str = "Khmer OS Battambang",
    title_font_size: int = 46,
    logo_path: str = "",
    logo_norm_x: float = 0.85,
    logo_norm_y: float = 0.05,
    logo_norm_w: float = 0.15,
    sub_norm_y: float = 0.85,
    sub_color: str = "#FFFFFF",
    sub_font_family: str = "Khmer OS Battambang",
    sub_font_size: int = 18,
    burn_subtitles: bool = True,
    anti_detect: bool = True,
    flip_horizontal: bool = True,
    crop_zoom: bool = True,
    color_grade: bool = True,
    speed_shift: bool = True,
    enable_blur: bool = False,
    blur_norm_x: float = 0.05,
    blur_norm_y: float = 0.05,
    blur_norm_w: float = 0.20,
    blur_norm_h: float = 0.10,
    blur_strength: int = 25,
    blur_tint: str = "#FFFFFF",
    blur_tint_opacity: int = 0,
    progress_callback = None
) -> str:

    if progress_callback:
        progress_callback(5, "វិភាគទំហំ និងរយៈពេលវីដេអូ...")

    orig_w, orig_h, dur_sec = get_video_dimension_and_duration(video_path)
    speed_factor = 1.03 if (anti_detect and speed_shift) else 1.0
    clip_dur_ms = int(dur_sec * 1000)

    # 1. Ultra-Fast Sequential Audio Timeline Stitching (0.2s vs 10min)
    ai_voice_wav = temp_path(f"ai_dubbed_voice_{session_id}_{int(time.time())}.wav")
    has_ai_voices = False

    if AudioSegment and table_data:
        if progress_callback:
            progress_callback(15, "កំពុងច្របាច់សំឡេង AI Dubbed...")

        sorted_items = sorted(table_data, key=lambda x: float(x.get('start_sec', 0)))
        audio_segments = []
        curr_ms = 0

        for item in sorted_items:
            s_ms = max(0, int(float(item.get('start_sec', 0)) * 1000))
            idx = item.get('index', 0)
            v_file = temp_path(f"temp_voice_{session_id}_{idx}.mp3")

            if os.path.exists(v_file) and os.path.getsize(v_file) > 0:
                if s_ms > curr_ms:
                    audio_segments.append(AudioSegment.silent(duration=(s_ms - curr_ms)))
                    curr_ms = s_ms
                try:
                    snd = AudioSegment.from_file(v_file)
                    audio_segments.append(snd)
                    curr_ms += len(snd)
                    has_ai_voices = True
                except Exception as e:
                    print(f"Error reading voice file {v_file}: {e}")

        if curr_ms < clip_dur_ms:
            audio_segments.append(AudioSegment.silent(duration=(clip_dur_ms - curr_ms)))

        if audio_segments and has_ai_voices:
            ai_voice_audio = sum(audio_segments, AudioSegment.empty())
            ai_voice_audio.export(ai_voice_wav, format="wav")

    # 2. Calculate Resolution & Aspect Ratio
    res_presets = {
        "720p (HD)": (1280, 720),
        "1080p (Full HD)": (1920, 1080),
        "2K (1440p)": (2560, 1440),
        "4K (2160p UHD)": (3840, 2160)
    }
    if resolution in res_presets:
        base_w, base_h = res_presets[resolution]
    else:
        base_w, base_h = orig_w, orig_h

    base_w = base_w - (base_w % 2)
    base_h = base_h - (base_h % 2)

    if aspect_ratio == "16:9 (YouTube/Landscape)":
        target_w, target_h = base_w, base_h
    elif "9:16" in aspect_ratio:
        target_w, target_h = base_h, base_w
    else:
        target_w, target_h = base_w, base_h

    # 3. Create Title Image
    title_png_path = ""
    if video_title.strip():
        scaled_title_size = int(title_font_size * (target_h / 1080.0) * 1.8)
        title_png_path = generate_khmer_title_image_pil(
            video_title.strip(), target_w, target_h,
            title_norm_x, title_norm_y, title_color, title_font_family, scaled_title_size
        )

    # 4. Create ASS Subtitle File
    ass_sub_path = ""
    if subtitles_data and burn_subtitles:
        ass_sub_path = create_ass_subtitle_file(
            subtitles_data, target_w, target_h,
            sub_norm_y, sub_color, sub_font_family, sub_font_size,
            speed_factor=speed_factor
        )

    # 5. Build FFmpeg Inputs
    inputs = [
        "-fflags", "+genpts+discardcorrupt",
        "-i", video_path
    ]
    next_idx = 1

    title_idx = -1
    if title_png_path and os.path.exists(title_png_path):
        inputs.extend(["-i", title_png_path])
        title_idx = next_idx
        next_idx += 1

    logo_idx = -1
    if logo_path and os.path.exists(logo_path):
        inputs.extend(["-i", logo_path])
        logo_idx = next_idx
        next_idx += 1

    ai_voice_idx = -1
    if has_ai_voices and os.path.exists(ai_voice_wav) and os.path.getsize(ai_voice_wav) > 0:
        inputs.extend(["-i", ai_voice_wav])
        ai_voice_idx = next_idx
        next_idx += 1

    v_filters = []
    curr_tag = "0:v"

    # Anti-Detection Filters
    if anti_detect:
        trans_filters = []
        if flip_horizontal:
            trans_filters.append("hflip")
        if crop_zoom:
            trans_filters.append("crop=trunc(iw*0.96/2)*2:trunc(ih*0.96/2)*2")
        if color_grade:
            trans_filters.append("eq=contrast=1.05:saturation=1.08:brightness=0.01")
        if speed_shift:
            trans_filters.append(f"setpts=PTS/{speed_factor}")

        if trans_filters:
            v_filters.append(f"[{curr_tag}]{','.join(trans_filters)}[v_anti_det]")
            curr_tag = "v_anti_det"

    # Scaling & Framing
    if "9:16" in aspect_ratio:
        if "Crop" in aspect_ratio:
            v_filters.append(f"[{curr_tag}]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}[v_scaled]")
        else:
            # 9:16 Full Screen with fast boxblur background
            v_filters.append(f"[{curr_tag}]split[fg_raw][bg_raw]")
            v_filters.append(f"[bg_raw]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=20:3[bg_blur]")
            v_filters.append(f"[fg_raw]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg_fit]")
            v_filters.append(f"[bg_blur][fg_fit]overlay=(W-w)/2:(H-h)/2[v_scaled]")
    else:
        v_filters.append(f"[{curr_tag}]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2[v_scaled]")
    
    curr_tag = "v_scaled"

    # Fast Circle / Ellipse Blur
    if enable_blur:
        bx = max(0, min(target_w - 20, int(blur_norm_x * target_w)))
        by = max(0, min(target_h - 20, int(blur_norm_y * target_h)))
        bw = max(20, min(target_w - bx, int(blur_norm_w * target_w)))
        bh = max(20, min(target_h - by, int(blur_norm_h * target_h)))

        bw = bw - (bw % 2)
        bh = bh - (bh % 2)
        blur_rad = max(4, int(blur_strength * (target_h / 1080.0)))

        # Fast boxblur on cropped region
        v_filters.append(f"[{curr_tag}]split[v_base_b][v_crop_src]")
        v_filters.append(f"[v_crop_src]crop={bw}:{bh}:{bx}:{by},boxblur={blur_rad}:2[v_blurred_crop]")
        if blur_tint_opacity > 0:
            t_opacity = max(0.05, min(1.0, blur_tint_opacity / 100.0))
            c_clean = blur_tint.replace("#", "")
            v_filters.append(f"[v_blurred_crop]drawbox=x=0:y=0:w={bw}:h={bh}:color=0x{c_clean}@{t_opacity:.2f}:t=fill[v_tinted_crop]")
            v_filters.append(f"[v_base_b][v_tinted_crop]overlay={bx}:{by}[v_blur_applied]")
        else:
            v_filters.append(f"[v_base_b][v_blurred_crop]overlay={bx}:{by}[v_blur_applied]")
        curr_tag = "v_blur_applied"

    # Title Overlay
    if title_idx != -1:
        v_filters.append(f"[{curr_tag}][{title_idx}:v]overlay=0:0[v_title_applied]")
        curr_tag = "v_title_applied"

    # Logo Overlay
    if logo_idx != -1:
        logo_w = max(40, int(logo_norm_w * target_w))
        logo_w = logo_w - (logo_w % 2)
        v_filters.append(f"[{logo_idx}:v]scale={logo_w}:-1,format=rgba[scaled_logo]")
        logo_x = max(0, int(logo_norm_x * target_w))
        logo_y = max(0, int(logo_norm_y * target_h))
        v_filters.append(f"[{curr_tag}][scaled_logo]overlay={logo_x}:{logo_y}:format=auto[v_logo_applied]")
        curr_tag = "v_logo_applied"

    # Subtitles Burn-in
    if burn_subtitles and ass_sub_path and os.path.exists(ass_sub_path):
        clean_ass = ass_sub_path.replace("\\", "/").replace(":", "\\:")
        v_filters.append(f"[{curr_tag}]ass='{clean_ass}'[v_sub_applied]")
        curr_tag = "v_sub_applied"

    # 6. Audio Filters (Vocal suppression to keep background music + clear AI voice)
    a_filters = []
    curr_a_tag = "a_final"

    vol_factor = max(0.0, min(1.0, bg_music_vol_percent / 100.0))

    if has_ai_voices and ai_voice_idx != -1 and vol_factor > 0:
        # Suppress original dialogue vocal (stereotools mlev=0) and boost AI voice
        a_filters.append(f"[0:a]stereotools=mlev=0.0,volume={vol_factor:.2f}[bg_music]")
        if anti_detect and speed_shift:
            a_filters.append(f"[bg_music]atempo={speed_factor}[bg_spd]")
            a_filters.append(f"[{ai_voice_idx}:a]atempo={speed_factor}[ai_spd]")
            a_filters.append(f"[bg_spd][ai_spd]amix=inputs=2:duration=first:dropout_transition=0:weights=1 2.5[{curr_a_tag}]")
        else:
            a_filters.append(f"[bg_music][{ai_voice_idx}:a]amix=inputs=2:duration=first:dropout_transition=0:weights=1 2.5[{curr_a_tag}]")
    elif has_ai_voices and ai_voice_idx != -1:
        # AI voice only (original spoken voice & audio muted)
        if anti_detect and speed_shift:
            a_filters.append(f"[{ai_voice_idx}:a]atempo={speed_factor}[{curr_a_tag}]")
        else:
            a_filters.append(f"[{ai_voice_idx}:a]anull[{curr_a_tag}]")
    elif vol_factor > 0:
        # Original audio with vocal suppression
        a_filters.append(f"[0:a]stereotools=mlev=0.0,volume={vol_factor:.2f}[bg_music]")
        if anti_detect and speed_shift:
            a_filters.append(f"[bg_music]atempo={speed_factor}[{curr_a_tag}]")
        else:
            a_filters.append(f"[bg_music]anull[{curr_a_tag}]")
    else:
        # Muted
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

    # 7. Run FFmpeg with Real-Time Progress Output (DEVNULL on stderr prevents OS pipe buffer deadlock)
    process = subprocess.Popen(
        ffmpeg_export_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
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
                # Only notify when percentage increments to avoid flooding network
                if render_percent > last_reported_percent:
                    last_reported_percent = render_percent
                    if progress_callback:
                        progress_callback(render_percent, f"កំពុង Render វីដេអូ ({render_percent}%)...")
        elif line == "progress=end":
            if progress_callback:
                progress_callback(99, "កំពុងបញ្ចប់ការ Render (99%)...")

    retcode = process.wait()
    if retcode != 0:
        raise RuntimeError(f"FFmpeg Error (exit code {retcode})")

    if progress_callback:
        progress_callback(100, "នាំចេញវីដេអូជោគជ័យ!")

    return output_path





def split_video_into_chunks(video_path: str, chunk_duration_sec: int, progress_callback=None) -> list:
    """
    Splits video into parts of chunk_duration_sec (e.g. 60s, 180s, 300s).
    """
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
    """
    Cuts highlight scene timecodes (start_sec, end_sec) and merges them into one video.
    """
    if not highlight_segments:
        raise ValueError("ពុំមាន Timecode ឈុត Highlight ឡើយ!")

    temp_clips = []
    total_segs = len(highlight_segments)

    for idx, seg in enumerate(highlight_segments):
        s_sec = seg['start_sec']
        e_sec = seg['end_sec']
        dur = max(0.5, e_sec - s_sec)

        if progress_callback:
            prog = int(((idx + 1) / (total_segs + 1)) * 100)
            progress_callback(prog, f"កំពុងកាត់ឈុត Highlight {idx + 1}/{total_segs}...")

        clip_out = temp_path(f"hl_clip_{idx}_{int(time.time() * 1000)}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{s_sec:.3f}",
            "-i", video_path,
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            clip_out
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        if os.path.exists(clip_out) and os.path.getsize(clip_out) > 0:
            temp_clips.append(clip_out)

    if not temp_clips:
        raise RuntimeError("មិនអាចកាត់ឈុត Highlight បានឡើយ!")

    if progress_callback:
        progress_callback(90, "កំពុងច្របាច់ឈុត Highlight ទាំងអស់បញ្ចូលគ្នា...")

    merge_videos(temp_clips, output_path)

    if progress_callback:
        progress_callback(100, "ច្របាច់ឈុត Highlight ជោគជ័យ!")

    return output_path


def merge_videos(video_files: list, output_path: str) -> str:
    concat_txt = temp_path(f"concat_list_{int(time.time())}.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for v in video_files:
            clean_p = os.path.abspath(v).replace("\\", "/")
            f.write(f"file '{clean_p}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_txt,
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        output_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # Fallback to re-encode concat if codecs differ
        cmd_reencode = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_txt,
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            output_path
        ]
        subprocess.run(cmd_reencode, capture_output=True, text=True)
    return output_path

