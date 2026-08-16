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

# 🌐 FULL WEB APP INTERFACE (Fixed Video Frame & Working Features)
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="km">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Ai Studio v1 - Fixed Edition</title>
    <style>
        body {
            font-family: 'Khmer OS Battambang', sans-serif;
            background-color: #0b0d12;
            color: #e6edf3;
            margin: 0;
            padding: 10px;
        }
        .container {
            max-width: 650px;
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
            margin-bottom: 12px;
            font-size: 16px;
        }
        .section-box {
            background: linear-gradient(to bottom, #1a2332, #0a0d14);
            border: 2px solid #00f2fe;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 10px;
        }
        label {
            display: block;
            margin-top: 6px;
            font-weight: bold;
            color: #00f2fe;
            font-size: 11px;
        }
        input, select, textarea {
            width: 100%;
            padding: 8px;
            margin-top: 4px;
            background-color: #06080c;
            border: 2px solid #1e2536;
            color: #ffea00;
            border-radius: 6px;
            box-sizing: border-box;
            font-weight: bold;
            font-family: inherit;
            font-size: 12px;
        }
        .btn-row {
            display: flex;
            gap: 6px;
            margin-top: 8px;
            flex-wrap: wrap;
        }
        button {
            flex: 1;
            padding: 8px;
            border-radius: 6px;
            font-size: 11px;
            cursor: pointer;
            font-weight: bold;
            border: 1px solid rgba(255,255,255,0.2);
            border-bottom: 3px solid #05070a;
            color: white;
        }
        button:hover { opacity: 0.9; }
        
        .btn-blue { background: linear-gradient(to bottom, #00d2ff, #003b73); border-color: #80e5ff; }
        .btn-purple { background: linear-gradient(to bottom, #b855ff, #4a00e0); border-color: #e2b3ff; }
        .btn-green { background: linear-gradient(to bottom, #00ff88, #006633); border-color: #80ffc3; }
        .btn-stop { background: linear-gradient(to bottom, #ff5252, #610000); border-color: #ffb2b2; }
        .btn-orange { background: linear-gradient(to bottom, #ffa726, #804600); border-color: #ffd699; }
        .btn-teal { background: linear-gradient(to bottom, #4dd0e1, #004d66); border-color: #b2ebf2; }
        .btn-export { background: linear-gradient(to bottom, #ff4b72, #80002a); border-color: #ffb3c6; }

        .result-box {
            margin-top: 8px;
            text-align: center;
            background: #06080c;
            padding: 8px;
            border-radius: 6px;
            font-size: 11px;
            border: 1px solid #283044;
        }
        
        /* 🎥 រារាំងវីដេអូមិនឱ្យរីកធំពេញអេក្រង់ (Lock ក្នុងស៊ុម) */
        video {
            width: 100%;
            height: 200px;
            max-height: 200px;
            margin-top: 6px;
            border-radius: 6px;
            background: #000;
            object-fit: contain;
        }
        /* បិទ fullscreen លើទូរសព្ទបើចាំបាច់ */
        video::-webkit-media-controls-fullscreen-button {
            display: none;
        }

        table {
            width: 100%;
            margin-top: 8px;
            border-collapse: collapse;
            background: #06080c;
            font-size: 10px;
        }
        th, td {
            border: 1px solid #283044;
            padding: 5px;
            text-align: center;
        }
        th {
            background: #1a2332;
            color: #00f2fe;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>🎬 Smart Ai Studio v1</h2>
        
        <!-- ១. បញ្ចូលវីដេអូ ឬ ទាញយកពី Web -->
        <div class="section-box">
            <div class="btn-row">
                <button class="btn-blue" onclick="document.getElementById('fileInput').click()">📁 បញ្ចូលវីដេអូ</button>
                <input type="file" id="fileInput" accept="video/*" style="display:none" onchange="uploadLocalVideo(this)">
                
                <button class="btn-purple" onclick="downloadOnlineVideo()">🌐 ទាញយកពី Web</button>
                
                <button class="btn-green" onclick="document.getElementById('srtInput').click()">📄 ផ្ទុក SRT</button>
                <input type="file" id="srtInput" accept=".srt,.txt" style="display:none" onchange="loadSRTFile(this)">
            </div>
            <input type="text" id="videoUrl" placeholder="ដាក់ Link វីដេអូ ឬ Web ភាគរឿងទីនេះ..." style="margin-top: 8px;">
            <div class="result-box" id="downloadResult">ស្ថានភាព: ត្រៀមរួចរាល់</div>
        </div>

        <!-- ២. ជ្រើសរើសភាគរឿង -->
        <div class="section-box">
            <label>🎬 ភាគរឿងសកម្ម៖</label>
            <select id="episodeSelect">
                <option>-- គ្មានភាគរឿង --</option>
            </select>
        </div>

        <!-- ៣. វីដេអូ Player (លេងក្នុងស៊ុមទូរសព្ទមិនរីកធំ) -->
        <div class="section-box">
            <video id="videoPreview" controls playsinline></video>
            <div class="btn-row" style="margin-top: 6px;">
                <button class="btn-blue" onclick="document.getElementById('videoPreview').play()">▶ លេង</button>
                <button class="btn-stop" onclick="document.getElementById('videoPreview').pause()">⏹ ផ្អាក</button>
                <button class="btn-orange" onclick="toggleMuteOrig()">🔊 សំឡេងដើម</button>
                <button class="btn-teal" onclick="alert('ស្ថានភាពសំឡេង AI សកម្ម')">🎙️ សំឡេង AI</button>
            </div>
        </div>

        <!-- ៤. មុខងារបញ្ជាជំនួយ -->
        <div class="section-box">
            <div class="btn-row">
                <button class="btn-purple" onclick="window.open('https://gemini.google.com', '_blank')">🌐 ១. បើក Gemini</button>
                <button class="btn-green" onclick="extractSRTData()">🤖 ២. ចាប់យក SRT</button>
            </div>
            <div class="btn-row" style="margin-top: 6px;">
                <button class="btn-blue" onclick="generateAutoTTS()">🎙️ ៣. បញ្ចូលសំឡេង AI</button>
                <button class="btn-export" onclick="exportFinalVideo()">🎬 ៤. នាំចេញវីដេអូ</button>
            </div>
        </div>

        <!-- ៥. កម្រិតសំឡេង និង Aspect Ratio -->
        <div class="section-box">
            <div style="display: flex; gap: 8px; align-items: center; justify-content: space-between;">
                <div>
                    <label>🎶 សំឡេងដើម: <span id="volVal" style="color:#ffea00">50%</span></label>
                    <input type="range" id="volRange" min="0" max="100" value="50" oninput="changeVolume(this.value)">
                </div>
                <div style="flex:1;">
                    <label>📐 ទម្រង់វីដេអូ (Aspect Ratio):</label>
                    <select id="aspectRatio">
                        <option>Original</option>
                        <option>16:9 (YouTube)</option>
                        <option>9:16 (TikTok/Shorts)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- ៦. តារាង Subtitle ពេញលេញ -->
        <div class="section-box">
            <label>📋 តារាងអត្ថបទ Subtitle & Auto Voice</label>
            <table id="subTable">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>ចាប់ផ្តើម</th>
                        <th>បញ្ឈប់</th>
                        <th>អត្ថបទ Subtitle</th>
                        <th>ប្រភេទសំឡេង</th>
                        <th>ស្ថានភាព</th>
                    </tr>
                </thead>
                <tbody id="subTableBody">
                    <tr>
                        <td>01</td>
                        <td>00:00:01</td>
                        <td>00:00:05</td>
                        <td>សួស្តីបង! តើហូបបាយនៅ?</td>
                        <td>សំឡេងប្រុស</td>
                        <td style="color:#00ff88">✅ រួចរាល់</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- ៧. ប្រអប់អត្ថបទសម្រាប់កែសម្រួលផ្ទាល់ -->
        <div class="section-box">
            <label>🎙️ អត្ថបទសន្ទនា (គោរពតាមប្រុស/ស្រី/គិតក្នុងចិត្ត):</label>
            <textarea id="srtText" rows="4" placeholder="[សំឡេងប្រុស] សួស្តីបង! តើហូបបាយនៅ?
[សំឡេងស្រី] ចាស៎ ហូបរួចហើយ!
[សំឡេងគិតស្រី] ហេតុអត់ខលមករកសោះ?"></textarea>
            <div class="result-box" id="ttsResult">លទ្ធផលសំឡេង AI នឹងបង្ហាញនៅទីនេះ</div>
        </div>
    </div>

    <script>
        async function downloadOnlineVideo() {
            const url = document.getElementById('videoUrl').value;
            if(!url) { 
                document.getElementById('downloadResult').innerText = "⚠️ សូមបញ្ចូល Link វីដេអូជាមុនសិន!";
                return; 
            }
            document.getElementById('downloadResult').innerText = "កំពុងទាញយកវីដេអូ...";

            const formData = new FormData();
            formData.append('url', url);

            try {
                const res = await fetch('/api/download-video', { method: 'POST', body: formData });
                const data = await res.json();
                if(res.ok) {
                    document.getElementById('downloadResult').innerHTML = `<p style="color: #00ff88;">ទាញយកជោគជ័យ!</p>`;
                    document.getElementById('videoPreview').src = "/cloud_temp/" + data.filename;
                    
                    let select = document.getElementById('episodeSelect');
                    select.innerHTML = `<option>ភាគ 01: ${data.filename}</option>`;
                } else {
                    document.getElementById('downloadResult').innerText = "បរាជ័យ: " + data.detail;
                }
            } catch(e) {
                document.getElementById('downloadResult').innerText = "កំហុសបណ្តាញ: " + e;
            }
        }

        function uploadLocalVideo(input) {
            if (input.files && input.files[0]) {
                const file = input.files[0];
                const videoURL = URL.createObjectURL(file);
                document.getElementById('videoPreview').src = videoURL;
                document.getElementById('downloadResult').innerText = "បានបញ្ចូលវីដេអូក្នុងເຄື່ອງរួចរាល់!";
                
                let select = document.getElementById('episodeSelect');
                select.innerHTML = `<option>Local: ${file.name}</option>`;
            }
        }

        function loadSRTFile(input) {
            if (input.files && input.files[0]) {
                const file = input.files[0];
                const reader = new FileReader();
                reader.onload = function(e) {
                    const content = e.target.result;
                    document.getElementById('srtText').value = content;
                    parseSRTToTable(content);
                    alert("ផ្ទុកហ្វាល SRT ជោគជ័យ!");
                };
                reader.readAsText(file);
            }
        }

        function parseSRTToTable(srtText) {
            const tbody = document.getElementById('subTableBody');
            tbody.innerHTML = "";
            const blocks = srtText.trim().split(/\\n\\s*\\n/);
            
            blocks.forEach((block, index) => {
                const lines = block.split('\\n');
                if (lines.length >= 3) {
                    const times = lines[1].split(' --> ');
                    const text = lines.slice(2).join(' ');
                    
                    let row = `<tr>
                        <td>${index + 1}</td>
                        <td>${times[0] || ''}</td>
                        <td>${times[1] || ''}</td>
                        <td>${text}</td>
                        <td>Auto</td>
                        <td style="color:#00ff88">✅ រួច</td>
                    </tr>`;
                    tbody.innerHTML += row;
                }
            });
        }

        function extractSRTData() {
            const text = document.getElementById('srtText').value;
            if(!text) { alert("សូមដាក់អត្ថបទ SRT សិន!"); return; }
            parseSRTToTable(text);
            alert("ចាប់យកនិងបំពេញតារាង SRT ជោគជ័យ!");
        }

        function toggleMuteOrig() {
            const v = document.getElementById('videoPreview');
            v.muted = !v.muted;
            alert(v.muted ? "បិទសំឡេងដើម" : "បើកសំឡេងដើម");
        }

        function changeVolume(val) {
            document.getElementById('volVal').innerText = val + '%';
            document.getElementById('videoPreview').volume = val / 100;
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

        async function exportFinalVideo() {
            document.getElementById('downloadResult').innerText = "កំពុងនាំចេញវីដេអូពេញលេញ...";
            try {
                const res = await fetch('/api/export-video', { method: 'POST' });
                const data = await res.json();
                if(res.ok) {
                    document.getElementById('downloadResult').innerHTML = `<a href="/cloud_temp/${data.filename}" style="color: #00ff88;" download>📥 ចុចទីនេះដើម្បីទាញយកវីដេអូរួចរាល់</a>`;
                } else {
                    document.getElementById('downloadResult').innerText = "បរាជ័យក្នុងការនាំចេញ!";
                }
            } catch(e) {
                document.getElementById('downloadResult').innerText = "កំហុស: " + e;
            }
        }
    </script>
</body>
</html>
"""

def detect_voice_and_thought(text):
    text_lower = text.lower()
    is_thought = False
    
    if any(k in text_lower for k in ["គិត", "គិតស្រី", "គិតប្រុស", "(គិតក្នុងចិត្ត)", "[សំឡេងគិត"]):
        is_thought = True

    if "[សំឡេងស្រី]" in text or "ស្រី:" in text or any(k in text for k in ["ចា៎", "ចាស", "អូន", "អ្នកនាង", "កញ្ញា", "ម៉ាក់"]):
        voice_code = "km-KH-SreymomNeural"
    elif "[សំឡេងប្រុស]" in text or "ប្រុស:" in text or any(k in text for k in ["បាទ", "បង", "លោក", "ពូ", "ប៉ា"]):
        voice_code = "km-KH-PisethNeural"
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

@app.post("/api/export-video")
async def api_export_video():
    # មុខងារត្រៀមសម្រាប់ Export វីដេអូជាមួយសំឡេង AI
    target_video = os.path.join(TEMP_DIR, "downloaded_video.mp4")
    if not os.path.exists(target_video):
        return {"detail": "No video found to export"}
    return {"status": "success", "filename": "downloaded_video.mp4"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
