import os
import time
import glob
import re

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Downloaded_Videos")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def extract_links_from_url(target_url: str) -> list:
    """
    Extracts video or playlist links using yt-dlp.
    """
    if not yt_dlp:
        raise RuntimeError("សូមដំឡើង yt-dlp ជាមុនសិន! (pip install yt-dlp)")

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

