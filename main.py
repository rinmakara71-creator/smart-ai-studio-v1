import os
import sys

# Resource directory (for static assets inside PyInstaller bundle)
RESOURCE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
if RESOURCE_DIR not in sys.path:
    sys.path.insert(0, RESOURCE_DIR)

# Data directory (for user files, downloads, exports next to .exe or in project)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


import uuid
import asyncio
import json
import time
import re
from typing import Optional, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.ai_service import parse_srt_content, translate_with_gemini, recap_with_gemini
from services.audio_service import generate_single_tts, temp_path
from services.video_service import (
    export_dubbed_video, merge_videos, get_video_dimension_and_duration,
    split_video_into_chunks, extract_and_merge_highlights
)
from services.downloader_service import download_batch_videos, download_single_video, extract_links_from_url

TEMP_DIR = os.path.join(BASE_DIR, "temp_dubbing_files")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Downloaded_Videos")
EXPORT_DIR = os.path.join(BASE_DIR, "Exported_Videos")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(RESOURCE_DIR, "static")

for d in [TEMP_DIR, DOWNLOAD_DIR, EXPORT_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="Smart AI Studio Web", description="Khmer AI Video Dubbing & Subtitling Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/media/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/media/temp", StaticFiles(directory=TEMP_DIR), name="temp")
app.mount("/media/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")
app.mount("/media/exports", StaticFiles(directory=EXPORT_DIR), name="exports")


# In-memory store for task statuses and SSE events
active_tasks = {}


class SubtitleItem(BaseModel):
    index: int
    start: str
    end: str
    start_sec: float
    end_sec: float
    text: str
    voice: str = "km-KH-PisethNeural"
    is_thought: bool = False


class BatchTTSRequest(BaseModel):
    session_id: str = "default"
    items: List[SubtitleItem]


class SingleTTSRequest(BaseModel):
    session_id: str = "default"
    item: SubtitleItem


class ExportRequest(BaseModel):
    session_id: str = "default"
    video_path: str
    subtitles: List[SubtitleItem]
    bg_music_vol: int = 50
    aspect_ratio: str = "Original"
    resolution: str = "1080p (Full HD)"
    video_title: str = ""
    title_norm_x: float = 0.35
    title_norm_y: float = 0.08
    title_color: str = "#FFEA00"
    title_font_family: str = "Khmer OS Battambang"
    title_font_size: int = 46
    logo_path: str = ""
    logo_norm_x: float = 0.85
    logo_norm_y: float = 0.05
    logo_norm_w: float = 0.15
    sub_norm_y: float = 0.85
    sub_color: str = "#FFFFFF"
    sub_font_family: str = "Khmer OS Battambang"
    sub_font_size: int = 18
    burn_subtitles: bool = True
    anti_detect: bool = True
    flip_horizontal: bool = True
    crop_zoom: bool = True
    color_grade: bool = True
    speed_shift: bool = True
    enable_blur: bool = False
    blur_norm_x: float = 0.05
    blur_norm_y: float = 0.05
    blur_norm_w: float = 0.20
    blur_norm_h: float = 0.10
    blur_strength: int = 25
    blur_tint: str = "#FFFFFF"
    blur_tint_opacity: int = 0


class MergeRequest(BaseModel):
    video_files: List[str]


class DownloadRequest(BaseModel):
    urls: List[str]


class SingleDownloadRequest(BaseModel):
    url: str


class SplitVideoRequest(BaseModel):
    video_path: str
    chunk_duration_sec: int = 60


class GeminiRequest(BaseModel):
    content: str
    api_key: Optional[str] = None


class RecapRequest(BaseModel):
    content: str
    api_key: Optional[str] = None


class ExportHighlightsRequest(BaseModel):
    video_path: str
    highlights: List[SubtitleItem]
    session_id: str = "default"




@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Smart AI Studio Web - Welcome</h1>"



@app.get("/api/download-file")
async def download_file_endpoint(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="រកមិនឃើញ File នេះទេ!")
    filename = os.path.basename(path)
    return FileResponse(
        path=path,
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):

    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    file_path = os.path.join(UPLOADS_DIR, unique_name)

    # Stream in chunks
    with open(file_path, "wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            buffer.write(chunk)

    w, h, dur = get_video_dimension_and_duration(file_path)
    return {
        "success": True,
        "filename": file.filename,
        "file_path": file_path,
        "file_url": f"/media/uploads/{unique_name}",
        "width": w,
        "height": h,
        "duration": dur
    }


@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    unique_name = f"logo_{uuid.uuid4().hex[:8]}_{safe_filename}"
    file_path = os.path.join(UPLOADS_DIR, unique_name)

    with open(file_path, "wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            buffer.write(chunk)

    return {
        "success": True,
        "filename": file.filename,
        "file_path": file_path,
        "file_url": f"/media/uploads/{unique_name}"
    }


@app.post("/api/parse-srt")
async def parse_srt(file: Optional[UploadFile] = File(None), raw_text: Optional[str] = Form(None)):
    content = ""
    if file:
        content_bytes = await file.read()
        try:
            content = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = content_bytes.decode("utf-8", errors="ignore")
    elif raw_text:
        content = raw_text

    subtitles = parse_srt_content(content)
    return {
        "success": True,
        "count": len(subtitles),
        "subtitles": subtitles
    }



@app.post("/api/gemini-translate")
async def gemini_translate(req: GeminiRequest):
    try:
        response_text = await translate_with_gemini(req.content, req.api_key)
        subtitles = parse_srt_content(response_text)
        return {
            "success": True,
            "raw_response": response_text,
            "subtitles": subtitles
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/gemini-recap")
async def gemini_recap_endpoint(req: RecapRequest):
    try:
        response_text = await recap_with_gemini(req.content, req.api_key)
        subtitles = parse_srt_content(response_text)
        return {
            "success": True,
            "raw_response": response_text,
            "subtitles": subtitles
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/generate-single-tts")
async def generate_single_tts_endpoint(req: SingleTTSRequest):
    item_dict = req.item.model_dump()
    success = await generate_single_tts(item_dict, req.session_id)
    v_file = temp_path(f"temp_voice_{req.session_id}_{req.item.index}.mp3")
    return {
        "success": success,
        "index": req.item.index,
        "audio_url": f"/media/temp/{os.path.basename(v_file)}" if success else None
    }


@app.post("/api/generate-batch-tts")
async def generate_batch_tts_endpoint(req: BatchTTSRequest):
    task_id = str(uuid.uuid4())
    start_t = time.time()
    active_tasks[task_id] = {
        "progress": 0,
        "status": "ចាប់ផ្តើមបង្កើតសំឡេង AI...",
        "start_time": start_t,
        "elapsed_sec": 0,
        "completed": False,
        "results": []
    }

    async def run_batch_tts():
        total = len(req.items)
        results = []
        for idx, item in enumerate(req.items):
            item_dict = item.model_dump()
            success = await generate_single_tts(item_dict, req.session_id)
            v_file = temp_path(f"temp_voice_{req.session_id}_{item.index}.mp3")
            results.append({
                "index": item.index,
                "success": success,
                "audio_url": f"/media/temp/{os.path.basename(v_file)}" if success else None
            })
            prog = int(((idx + 1) / total) * 100)
            elapsed = int(time.time() - start_t)
            active_tasks[task_id]["progress"] = prog
            active_tasks[task_id]["elapsed_sec"] = elapsed
            active_tasks[task_id]["status"] = f"បង្កើតសំឡេង {idx + 1}/{total} រួចរាល់"
            active_tasks[task_id]["results"] = results
            await asyncio.sleep(0.05)

        active_tasks[task_id]["completed"] = True
        active_tasks[task_id]["elapsed_sec"] = int(time.time() - start_t)
        active_tasks[task_id]["status"] = "បង្កើតសំឡេង AI ទាំងអស់រួចរាល់!"

    asyncio.create_task(run_batch_tts())
    return {"success": True, "task_id": task_id}


@app.post("/api/export-video")
async def export_video_endpoint(req: ExportRequest):
    if not os.path.exists(req.video_path):
        raise HTTPException(status_code=404, detail=f"រកមិនឃើញ File វីដេអូ: {req.video_path}")

    task_id = str(uuid.uuid4())
    start_t = time.time()
    active_tasks[task_id] = {
        "progress": 0,
        "status": "រៀបចំ Export វីដេអូ...",
        "start_time": start_t,
        "elapsed_sec": 0,
        "completed": False,
        "output_path": None,
        "output_url": None,
        "error": None
    }

    base_name = os.path.basename(req.video_path)
    clean_name, _ = os.path.splitext(base_name)
    export_filename = f"{clean_name}_Dubbed_{int(uuid.uuid4().hex[:6], 16)}.mp4"
    out_path = os.path.join(EXPORT_DIR, export_filename)

    table_data = [item.model_dump() for item in req.subtitles]
    subtitles_data = [{"start": item.start, "end": item.end, "text": item.text} for item in req.subtitles]

    def update_progress(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["elapsed_sec"] = int(time.time() - start_t)
        active_tasks[task_id]["status"] = msg

    async def run_export():
        try:
            await export_dubbed_video(
                video_path=req.video_path,
                table_data=table_data,
                subtitles_data=subtitles_data,
                output_path=out_path,
                session_id=req.session_id,
                bg_music_vol_percent=req.bg_music_vol,
                aspect_ratio=req.aspect_ratio,
                resolution=req.resolution,
                video_title=req.video_title,
                title_norm_x=req.title_norm_x,
                title_norm_y=req.title_norm_y,
                title_color=req.title_color,
                title_font_family=req.title_font_family,
                title_font_size=req.title_font_size,
                logo_path=req.logo_path,
                logo_norm_x=req.logo_norm_x,
                logo_norm_y=req.logo_norm_y,
                logo_norm_w=req.logo_norm_w,
                sub_norm_y=req.sub_norm_y,
                sub_color=req.sub_color,
                sub_font_family=req.sub_font_family,
                sub_font_size=req.sub_font_size,
                burn_subtitles=req.burn_subtitles,
                anti_detect=req.anti_detect,
                flip_horizontal=req.flip_horizontal,
                crop_zoom=req.crop_zoom,
                color_grade=req.color_grade,
                speed_shift=req.speed_shift,
                enable_blur=req.enable_blur,
                blur_norm_x=req.blur_norm_x,
                blur_norm_y=req.blur_norm_y,
                blur_norm_w=req.blur_norm_w,
                blur_norm_h=req.blur_norm_h,
                blur_strength=req.blur_strength,
                blur_tint=req.blur_tint,
                blur_tint_opacity=req.blur_tint_opacity,
                progress_callback=update_progress
            )
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["elapsed_sec"] = int(time.time() - start_t)
            active_tasks[task_id]["output_path"] = out_path
            active_tasks[task_id]["output_url"] = f"/media/exports/{export_filename}"
            active_tasks[task_id]["download_url"] = f"/api/download-file?path={out_path}"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)


    asyncio.create_task(run_export())
    return {"success": True, "task_id": task_id}


@app.post("/api/split-video")
async def split_video_endpoint(req: SplitVideoRequest):
    if not os.path.exists(req.video_path):
        raise HTTPException(status_code=404, detail=f"រកមិនឃើញ File វីដេអូ: {req.video_path}")

    task_id = str(uuid.uuid4())
    start_t = time.time()
    active_tasks[task_id] = {
        "progress": 0,
        "status": "រៀបចំកាត់វីដេអូជាកង់ៗ...",
        "start_time": start_t,
        "elapsed_sec": 0,
        "completed": False,
        "parts": [],
        "error": None
    }

    def update_progress(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["elapsed_sec"] = int(time.time() - start_t)
        active_tasks[task_id]["status"] = msg

    async def run_split():
        try:
            chunks = split_video_into_chunks(req.video_path, req.chunk_duration_sec, progress_callback=update_progress)
            parts_info = []
            for c in chunks:
                fname = os.path.basename(c)
                parent_dir = os.path.basename(os.path.dirname(c))
                parts_info.append({
                    "filename": fname,
                    "file_path": c,
                    "file_url": f"/media/exports/{parent_dir}/{fname}"
                })
            active_tasks[task_id]["parts"] = parts_info
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["status"] = f"កាត់វីដេអូបានជោគជ័យសរុប {len(chunks)} ភាគ!"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.create_task(run_split())
    return {"success": True, "task_id": task_id}


@app.post("/api/export-highlights")
async def export_highlights_endpoint(req: ExportHighlightsRequest):
    if not os.path.exists(req.video_path):
        raise HTTPException(status_code=404, detail=f"រកមិនឃើញ File វីដេអូ: {req.video_path}")

    task_id = str(uuid.uuid4())
    start_t = time.time()
    active_tasks[task_id] = {
        "progress": 0,
        "status": "រៀបចំកាត់យកឈុត Highlight...",
        "start_time": start_t,
        "elapsed_sec": 0,
        "completed": False,
        "output_path": None,
        "output_url": None,
        "error": None
    }

    base_name = os.path.splitext(os.path.basename(req.video_path))[0]
    out_filename = f"{base_name}_Highlights_{int(uuid.uuid4().hex[:6], 16)}.mp4"
    out_path = os.path.join(EXPORT_DIR, out_filename)

    def update_progress(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["elapsed_sec"] = int(time.time() - start_t)
        active_tasks[task_id]["status"] = msg

    async def run_highlights():
        try:
            hl_data = [item.model_dump() for item in req.highlights]
            extract_and_merge_highlights(req.video_path, hl_data, out_path, progress_callback=update_progress)
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["output_path"] = out_path
            active_tasks[task_id]["output_url"] = f"/media/exports/{out_filename}"
            active_tasks[task_id]["download_url"] = f"/api/download-file?path={out_path}"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.create_task(run_highlights())
    return {"success": True, "task_id": task_id}


@app.post("/api/download-single")
async def download_single_endpoint(req: SingleDownloadRequest):
    task_id = str(uuid.uuid4())
    start_t = time.time()
    active_tasks[task_id] = {
        "progress": 0,
        "status": "ទាញយកវីដេអូ...",
        "start_time": start_t,
        "elapsed_sec": 0,
        "completed": False,
        "video_file": None,
        "error": None
    }

    def update_progress(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["elapsed_sec"] = int(time.time() - start_t)
        active_tasks[task_id]["status"] = msg

    async def run_single_dl():
        try:
            fpath = download_single_video(req.url, progress_callback=update_progress)
            fname = os.path.basename(fpath)
            parent_dir = os.path.basename(os.path.dirname(fpath))
            active_tasks[task_id]["video_file"] = {
                "filename": fname,
                "file_path": fpath,
                "file_url": f"/media/downloads/{parent_dir}/{fname}"
            }
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["status"] = "ទាញយកវីដេអូជោគជ័យ!"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.create_task(run_single_dl())
    return {"success": True, "task_id": task_id}


@app.post("/api/merge-videos")
async def merge_videos_endpoint(req: MergeRequest):
    if len(req.video_files) < 2:
        raise HTTPException(status_code=400, detail="សូមជ្រើសរើសយ៉ាងតិច ២ វីដេអូឡើងទៅ!")

    task_id = str(uuid.uuid4())
    start_t = time.time()
    active_tasks[task_id] = {
        "progress": 20,
        "status": "កំពុងច្របាច់បញ្ចូលវីដេអូទាំងអស់...",
        "start_time": start_t,
        "elapsed_sec": 0,
        "completed": False,
        "output_path": None,
        "output_url": None,
        "download_url": None,
        "error": None
    }

    merge_filename = f"Full_Movie_Merged_{int(uuid.uuid4().hex[:6], 16)}.mp4"
    out_path = os.path.join(EXPORT_DIR, merge_filename)

    async def run_merge():
        try:
            merge_videos(req.video_files, out_path)
            active_tasks[task_id]["progress"] = 100
            active_tasks[task_id]["status"] = "Merge វីដេអូទាំងអស់ជោគជ័យ!"
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["output_path"] = out_path
            active_tasks[task_id]["output_url"] = f"/media/exports/{merge_filename}"
            active_tasks[task_id]["download_url"] = f"/api/download-file?path={out_path}"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)


    asyncio.create_task(run_merge())
    return {"success": True, "task_id": task_id}


@app.post("/api/download-batch")
async def download_batch_endpoint(req: DownloadRequest):
    task_id = str(uuid.uuid4())
    start_t = time.time()
    active_tasks[task_id] = {
        "progress": 0,
        "status": "ស្វែងរក Links ភាគរឿង...",
        "start_time": start_t,
        "elapsed_sec": 0,
        "completed": False,
        "video_files": [],
        "error": None
    }

    def update_progress(prog, msg):
        active_tasks[task_id]["progress"] = prog
        active_tasks[task_id]["elapsed_sec"] = int(time.time() - start_t)
        active_tasks[task_id]["status"] = msg

    async def run_download():
        try:
            all_urls = []
            for u in req.urls:
                extracted = extract_links_from_url(u)
                all_urls.extend(extracted)
            
            # Deduplicate preserving order
            seen = set()
            unique_urls = [x for x in all_urls if not (x in seen or seen.add(x))]

            files = download_batch_videos(unique_urls, progress_callback=update_progress)
            video_data = []
            for f in files:
                fname = os.path.basename(f)
                video_data.append({
                    "filename": fname,
                    "file_path": f,
                    "file_url": f"/media/downloads/{os.path.basename(os.path.dirname(f))}/{fname}"
                })
            active_tasks[task_id]["video_files"] = video_data
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["status"] = f"ទាញយកជោគជ័យសរុប {len(files)} ភាគ!"
        except Exception as e:
            active_tasks[task_id]["completed"] = True
            active_tasks[task_id]["error"] = str(e)

    asyncio.create_task(run_download())
    return {"success": True, "task_id": task_id}



@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="រកមិនឃើញ Task ID នេះទេ!")
    return active_tasks[task_id]


@app.get("/api/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request):
    """
    Server-Sent Events (SSE) for live task progress updates.
    """
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            if task_id in active_tasks:
                task = active_tasks[task_id]
                yield f"data: {json.dumps(task, ensure_ascii=False)}\n\n"
                if task.get("completed", False):
                    break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 កំពុងដំណើរការ Smart AI Studio Web នៅលើ http://0.0.0.0:{port} ...")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)


