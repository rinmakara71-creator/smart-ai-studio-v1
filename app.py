import os
import glob
import asyncio
import re
import edge_tts
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from pydub import AudioSegment
    from pydub.effects import normalize
except ImportError:
    AudioSegment = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "cloud_temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# 📱 ឌីសាញស្ទីលបែប Desktop Dark Theme ស្រដៀងក្នុងរូបភាព ប៉ុន្តែសម្របតាមទូរសព្ទដៃ
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="km">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Ai Studio v1 - Mobile Edition</title>
    <style>
        body {
            font-family: 'Khmer OS Battambang', sans-serif;
            background-color: #0b0d12;
            color: #e6edf3;
            margin: 0;
            padding: 10px;
        }
        .container {
            max-width: 600px;
            margin: auto;
            background: linear-gradient(135deg, #161b26, #080a0f);
            border: 2px solid #00f2fe;
            border-radius: 14px;
            padding: 15px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.8);
        }
        h2 {
            text-align: center;
            color: #00f2fe;
            margin-bottom: 15px;
            font-size: 18px;
        }
        .section-box {
            background: linear-gradient(to bottom, #1a2332, #0a0d14);
            border: 2px solid #00f2fe;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 12px;
        }
        label {
            display: block;
            margin-top: 8px;
            font-weight: bold;
            color: #00f2fe;
            font-size: 12px;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            background-color: #06080c;
            border: 2px solid #1e2536;
            color: #ffea00;
            border-radius: 8px;
            box-sizing: border-box;
            font-weight: bold;
            font-family: inherit;
            font-size: 13px;
        }
        .btn-row {
            display: flex;
            gap: 8px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        button {
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            font-size: 12px;
            cursor: pointer;
            font-weight: bold;
            border: 1px solid rgba(255,255,255,0.2);
            border-bottom: 3px solid #05070a;
            color: white;
        }
        button:hover { opacity: 0.9; }
        
        /* ពណ៌ប៊ូតុងស្ដារតាម Desktop */
        .btn-blue { background: linear-gradient(to bottom, #00d2ff, #003b73); border-color: #80e5ff; }
        .btn-purple { background: linear-gradient(to bottom, #b855ff, #4a00e0); border-color: #e2b3ff; }
        .btn-green { background: linear-gradient(to bottom, #00ff88, #006633); border-color: #80ffc3; }
        .btn-stop { background: linear-gradient(to bottom, #ff5252, #610000); border-color: #ffb2b2; }
        .btn-orange { background: linear-gradient(to bottom, #ffa726, #804600); border-color: #ffd699; }
        .btn-teal { background: linear-gradient(to bottom, #4dd0e1, #004d66); border-color: #b2ebf2; }
        .btn-export { background: linear-gradient(to bottom, #ff4b72, #80002a); border-color: #ffb3c6; }

        .result-box {
            margin-top: 10px;
            text-align: center;
            background: #06080c;
            padding: 10px;
            border-radius: 8px;
            font-size: 12px;
            border: 1px solid #283044;
        }
        audio, video {
            width: 100%;
            margin-top: 8px;
            border-radius: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>🎬 Smart Ai Studio v1 (Mobile Edition)</h2>
        
        <!-- ១. ផ្នែកទាញយកវីដេអូ និងបញ្ចូល URL -->
        <div class="section-box">
            <label>🌐 ទាញយកវីដេអូរឿងភាគ (ពី Web / YouTube)</label>
            <input type="text" id="videoUrl" placeholder="ដាក់ Link វីដេអូនៅទីនេះ...">
            <div class="btn-row">
                <button class="btn-purple" onclick="downloadVideo()">🌐 ទាញយកវីដេអូអូតូ</button>
            </div>
            <div class="result-box" id="downloadResult">ស្ថានភាព: ត្រៀមរួចរាល់</div>
        </div>

        <!-- ២. ផ្នែកបញ្ជាចាក់វីដេអូ និងការគ្រប់គ្រងសំឡេង -->
        <div class="section-box">
            <label>🎥 ត្រួតពិនិត្យវីដេអូនិងសំឡេង</label>
            <video id="videoPreview" controls style="background:#000; height: 200px; object-fit: contain;"></video>
            
            <div class="btn-row">
                <button class="btn-blue" onclick="playVideo()">▶ លេង</button>
                <button class="btn-stop" onclick="stopVideo()">⏹ បញ្ឈប់</button>
            </div>
        </div>

        <!-- 3. ផ្នែកបង្កើតសំឡេង AI អូតូតាមតួអង្គ -->
        <div class="section-box">
            <label>🎙️ បញ្ចូលសំឡេង AI (Auto Gender & Thought Detection)</label>
            <textarea id="srtText" rows="5" placeholder="សួស្តីបង! តើហូបបាយនៅ?
ចាស៎ ហូបរួចហើយ!
(គិតក្នុងចិត្ត) ហេតុអត់ខលមករកសោះ?"></textarea>
            
            <div class="btn-row">
                <button class="btn-green" onclick="generateAutoTTS()">🎙️ ៣. បង្កើតសំឡេង AI</button>
            </div>
            <div class="result-box" id="ttsResult">លទ្ធផលសំឡេង AI នឹងបង្ហាញនៅទីនេះ</div>
        </div>
    </div>

    <script>
        async function downloadVideo() {
            const url = document.getElementById('videoUrl').value;
            if(!url) { alert('សូមបញ្ចូល Link វីដេអូ!'); return; }
            document.getElementById('downloadResult').innerText = "កំពុងទាញយកវីដេអូ...";

            const formData = new FormData();
            formData.append('url', url);

            try {
                const res = await fetch('/api/download-video', { method: 'POST', body: formData });
                const data = await res.json();
                if(res.ok) {
                    document.getElementById('downloadResult').innerHTML = `<p style="color: #00ff88;">ទាញយកជោគជ័យ!</p>`;
                    document.getElementById('videoPreview').src = "/cloud_temp/" + data.filename;
                } else {
                    document.getElementById('downloadResult').innerText = "បរាជ័យ: " + data.detail;
                }
            } catch(e) {
                document.getElementById('downloadResult').innerText = "កំហុសបណ្តាញ: " + e;
            }
        }

        function playVideo() {
            document.getElementById('videoPreview').play();
        }

        function stopVideo() {
            const v = document.getElementById('videoPreview');
            v.pause();
            v.currentTime = 0;
        }

        async function generateAutoTTS() {
            const textContent = document.getElementById('srtText').value;
            if(!textContent) { alert('សូមបញ្ចូលអត្ថបទសិន!'); return; }
            document.getElementById('ttsResult').innerText = "កំពុងវិភាគ និងច្នៃសំឡេង AI អូតូ...";

            const formData = new FormData();
            formData.append('text_content', textContent);

            try {
                const res = await fetch('/api/generate-auto-tts', { method: 'POST', body: formData });
                if(res.ok) {
                    const blob = await res.blob();
                    const audioUrl = URL.createObjectURL(blob);
                    document.getElementById('ttsResult').innerHTML = `
                        <p style="color: #00ff88;">បង្កើតសំឡេង AI ជោគជ័យ!</p>
                        <audio controls src="${audioUrl}"></audio>
                    `;
                } else {
                    document.getElementById('ttsResult').innerText = "មានបញ្ហាពេលបង្កើតសំឡេង!";
                }
            } catch(e) {
                document.getElementById('ttsResult').innerText = "កំហុស: " + e;
            }
        }
    </script>
</body>
</html>
"""

def detect_voice_and_thought(text):
    text_lower = text.lower()
    is_thought = False
    
    if any(k in text_lower for k in ["គិត", "(គិតក្នុងចិត្ត)", "[គិត]"]):
        is_thought = True

    female_keywords = ["ចា៎", "ចាស", "អូន", "អ្នកនាង", "កញ្ញា", "លោកស្រី", "ម៉ាក់", "នាង", "ស្រី"]
    
    if any(k in text for k in female_keywords) or "[សំឡេងស្រី]" in text:
        voice_code = "km-KH-SreymomNeural"
    else:
        voice_code = "km-KH-PisethNeural"

    return voice_code, is_thought

def add_reverb_thought_effect(sound):
    if not sound or not AudioSegment:
        return sound
    delay_1 = AudioSegment.silent(duration=50) + (sound - 3.5)
    delay_2 = AudioSegment.silent(duration=110) + (sound - 7.0)
    reverb_sound = sound.overlay(delay_1).overlay(delay_2)
    return normalize(reverb_sound)

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_INTERFACE

@app.get("/cloud_temp/{filename}")
async def get_temp_file(filename: str):
    file_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"detail": "File not found"}

@app.post("/api/download-video")
async def api_download_video(url: str = Form(...)):
    if not yt_dlp:
        return {"detail": "yt_dlp not installed"}
    
    output_tmpl = os.path.join(TEMP_DIR, "downloaded_video.mp4")
    if os.path.exists(output_tmpl):
        os.remove(output_tmpl)

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_tmpl,
        'quiet': True,
        'nocheckcertificate': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return {"status": "success", "filename": "downloaded_video.mp4"}
    except Exception as e:
        return {"detail": str(e)}

@app.post("/api/generate-auto-tts")
async def api_generate_auto_tts(text_content: str = Form(...)):
    if not AudioSegment:
        return {"detail": "pydub not installed"}

    lines = text_content.split('\n')
    combined_audio = AudioSegment.silent(duration=500)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        voice_code, is_thought = detect_voice_and_thought(line)
        clean_text = re.sub(r"\[.*?\]|\(.*?\)", "", line).strip()
        if not clean_text:
            continue

        temp_audio_file = os.path.join(TEMP_DIR, f"temp_{id(line)}.mp3")
        try:
            communicate = edge_tts.Communicate(clean_text, voice_code)
            await communicate.save(temp_audio_file)
            
            if os.path.exists(temp_audio_file):
                segment = AudioSegment.from_file(temp_audio_file)
                if is_thought:
                    segment = add_reverb_thought_effect(segment)
                
                combined_audio += segment + AudioSegment.silent(duration=300)
        except Exception:
            pass

    output_file = os.path.join(TEMP_DIR, "final_auto_dubbed.mp3")
    combined_audio.export(output_file, format="mp3", bitrate="320k")
    return FileResponse(output_file, media_type="audio/mp3", filename="auto_dubbed.mp3")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
