import sys
import os
import glob
import shutil
import time
import subprocess
import asyncio
import re
import json
import traceback
import threading
import edge_tts

# PyQt6 Imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QLabel, QFileDialog, QComboBox, QFrame, 
    QMessageBox, QSlider, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QProgressBar, QLineEdit, QDialog, QTextEdit,
    QColorDialog, QFontDialog, QCheckBox, QGroupBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QObject, QRect, QPoint, QRectF
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QBrush, QImage, QPen, QPainterPath
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink, QVideoFrame

# Selenium Imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    import pyautogui
    import pyperclip
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False

try:
    from pydub import AudioSegment
    from pydub.effects import normalize
except ImportError:
    AudioSegment = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


# ================= SYSTEM INSTRUCTION =================
SYSTEM_INSTRUCTION = """ចាប់ពីពេលនេះតទៅ សូមអ្នកដើរតួជា អ្នកបកប្រែខ្សែភាពយន្តនិងរឿងភាគអាជីព (Expert Subtitler & Dubbing Translator)។ ភារកិច្ចចម្បងរបស់អ្នកគឺទាញយកសំឡេងសន្ទនាពីវីដេអូដែលខ្ញុំបានភ្ជាប់ ឬបកប្រែរាល់អត្ថបទដែលខ្ញុំផ្តល់ឲ្យ មកជាភាសាខ្មែរឲ្យបានស្តង់ដារបំផុត ដោយផ្តោតសំខាន់លើ'ភាសានិយាយ' ដែលរលូន ស៊ីអារម្មណ៍ និងត្រូវសំឡេងតួអង្គ ១០០%។

សូមអនុវត្តតាមច្បាប់ទាំង ៤ នេះយ៉ាងតឹងរ៉ឹង៖

1. ភាសានិយាយធម្មជាតិ (Natural Spoken Language): ហាមដាច់ខាតការបកប្រែតាមបែបសរសេរស្ងួតៗ (Word-for-word)។ ត្រូវប្រើប្រាស់ពាក្យពេចន៍ដែលប្រជាជនខ្មែរនិយមនិយាយប្រចាំថ្ងៃ។ សូមប្រើកន្ទុយពាក្យបញ្ជាក់អារម្មណ៍ (ឧទាហរណ៍៖ ណា, ណ៎, ហ្មង, តើ, អញ្ចឹង, វើយ, ហាស, ចា៎, ចុះ) ឲ្យសក្ដិសមនឹងបរិបទសន្ទនា។
2. ត្រូវសំឡេងតួអង្គនិយាយ (Match the actor's voice): ត្រូវប្រើសព្វនាមហៅគ្នា (បង/អូន, ឯង/អញ, ខ្ញុំ/លោក, ពួកម៉ាក, សម្លាញ់, អា...) ឲ្យត្រូវនឹងអាយុ ឋានៈ និងទំនាក់ទំនងរបស់តួអង្គដែលខ្ញុំបានប្រាប់នៅក្នុងបរិបទនីមួយៗ។
3. បញ្ចេញមនោសញ្ចេតនា (Emotional Depth): អានការបកប្រែរួច ត្រូវតែមានអារម្មណ៍ (ខឹង, សើច, យំ, ផ្អែមល្ហែម, ចំអក, ភ័យស្លន់ស្លោ) ដូចទៅនឹងអត្ថបទដើម។ បើអត្ថបទដើមមានន័យបង្កប់ ឬការលេងពាក្យ ត្រូវបត់បែនពាក្យខ្មែរឲ្យចេញន័យនោះដោយរលូន។
៤. ទម្រង់លទ្ធផល (Output Format): រាល់លទ្ធផលនៃការបកប្រែទាំងអស់ សូមផ្តល់ឲ្យខ្ញុំជាទម្រង់ហ្វាល SRT ដោយដាក់វានៅក្នុង Code Block ដើម្បីឲ្យខ្ញុំងាយស្រួល Copy យកទៅប្រើប្រាស់បន្ត។
បញ្ជាក់ប្រយោគស្រីប្រុសដោយសញ្ញា [សំឡេងស្រី] ឬ [សំឡេងប្រុស] និងប្រយោគគិតក្នុងចិត្តដោយសញ្ញា [សំឡេងគិតស្រី] [សំឡេងគិតប្រុស] [ក្មេង] [មនុស្សចាស់] [បិសាច] នៅដើមបន្ទាត់នីមួយៗ។"""


# ================= TEMP & EXPORT FOLDERS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp_dubbing_files")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Downloaded_Videos")
EXPORT_DIR = os.path.join(BASE_DIR, "Exported_Videos")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)


def temp_path(filename):
    return os.path.join(TEMP_DIR, filename)


def test_encoder_available(enc_name):
    try:
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.05", "-c:v", enc_name, "-f", "null", "-"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        return res.returncode == 0
    except Exception:
        return False


def detect_gpu_hardware_acceleration():
    """ស្វែងរក Hardware GPU Encoders ដែលអាចដំណើរការបានពិតប្រាកដលើម៉ាស៊ីន (Verified)"""
    return {
        "nvenc": test_encoder_available("h264_nvenc"),
        "qsv": test_encoder_available("h264_qsv"),
        "amf": test_encoder_available("h264_amf")
    }


def get_video_dimension_and_duration(video_path):
    w, h, dur = 1920, 1080, 7200.0
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(res.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            w = int(data["streams"][0].get("width", 1920))
            h = int(data["streams"][0].get("height", 1080))
        if "format" in data:
            dur = float(data["format"].get("duration", 7200.0))
    except Exception:
        pass
    return w, h, dur


def generate_khmer_title_image_qt(text, width, height, norm_x, norm_y, color_hex, font_family, font_size):
    if not text.strip():
        return ""

    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    chosen_family = font_family if font_family else "Khmer OS Battambang"
    font = QFont(chosen_family, font_size, QFont.Weight.Bold)
    painter.setFont(font)

    metrics = painter.fontMetrics()
    th = metrics.height()

    tx = int(norm_x * width)
    ty = int(norm_y * height) + th

    painter.setPen(QColor(0, 0, 0, 255))
    stroke_offset = max(2, int(font_size * 0.08))
    for dx in range(-stroke_offset, stroke_offset + 1):
        for dy in range(-stroke_offset, stroke_offset + 1):
            if dx != 0 or dy != 0:
                painter.drawText(tx + dx, ty + dy, text)

    painter.setPen(QColor(color_hex))
    painter.drawText(tx, ty, text)
    painter.end()

    out_png = temp_path(f"title_qt_{int(time.time())}.png")
    image.save(out_png, "PNG")
    return out_png


def create_ass_subtitle_file(subtitles, target_w, target_h, sub_norm_y, sub_color_hex, font_family, font_size, speed_factor=1.0):
    if not subtitles:
        return ""

    ass_path = temp_path(f"custom_sub_{int(time.time())}.ass")
    c = QColor(sub_color_hex)
    ass_color = f"&H00{c.blue():02X}{c.green():02X}{c.red():02X}&"

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
        s_sec = time_to_seconds(sub['start'])
        e_sec = time_to_seconds(sub['end'])
        clean_text = clean_text_for_tts(sub['text']).replace("\n", "\\N")
        if clean_text:
            events.append(f"Dialogue: 0,{format_ass_time(s_sec)},{format_ass_time(e_sec)},Default,,0,0,0,,{clean_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return ass_path


def create_default_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setBrush(QBrush(QColor("#00F2FE")))
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setBrush(QBrush(QColor("#8E2DE2")))
    painter.drawEllipse(16, 16, 32, 32)
    painter.end()
    return QIcon(pixmap)


# ================= HELPER FUNCTIONS =================
def clean_text_for_tts(text):
    if not text:
        return ""
    text = re.sub(r"\[(សំឡេង)?ស្រី\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(សំឡេង)?ប្រុស\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(សំឡេង)?គិត.*?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[គិត\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[ក្មេង.*?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[ចាស់.*?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[មនុស្សចាស់.*?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[បិសាច.*?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\{.*?\}", "", text)
    text = re.sub(r"[\*\#\_\~\-\>\<]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_thought_voice(text):
    if not text:
        return False
    return bool(re.search(r"\[(សំឡេង)?គិត.*?\]|\[គិត\]|\(គិតក្នុងចិត្ត\)", text, re.IGNORECASE))


# ================= PHASE 2: ADVANCED VOICE ROLES & MODULATION =================
VOICE_PROFILES = {
    "សំឡេងស្រីធម្មតា": {
        "voice": "km-KH-SreymomNeural", "pitch": "+0Hz", "rate": "+0%", "is_thought": False, "effect": "normal"
    },
    "សំឡេងប្រុសធម្មតា": {
        "voice": "km-KH-PisethNeural", "pitch": "+0Hz", "rate": "+0%", "is_thought": False, "effect": "normal"
    },
    "សំឡេងក្មេងស្រី (Pitch +35Hz)": {
        "voice": "km-KH-SreymomNeural", "pitch": "+35Hz", "rate": "+8%", "is_thought": False, "effect": "child"
    },
    "សំឡេងក្មេងប្រុស (Pitch +30Hz)": {
        "voice": "km-KH-PisethNeural", "pitch": "+30Hz", "rate": "+6%", "is_thought": False, "effect": "child"
    },
    "សំឡេងមនុស្សចាស់ (Pitch -25Hz)": {
        "voice": "km-KH-PisethNeural", "pitch": "-25Hz", "rate": "-8%", "is_thought": False, "effect": "elder"
    },
    "សំឡេងយាយចាស់ (Pitch -20Hz)": {
        "voice": "km-KH-SreymomNeural", "pitch": "-20Hz", "rate": "-8%", "is_thought": False, "effect": "elder"
    },
    "សំឡេងបិសាច/ធ្ងន់ (Pitch -50Hz)": {
        "voice": "km-KH-PisethNeural", "pitch": "-50Hz", "rate": "-6%", "is_thought": False, "effect": "monster"
    },
    "សំឡេងគិតស្រី (Reverb)": {
        "voice": "km-KH-SreymomNeural", "pitch": "+5Hz", "rate": "-2%", "is_thought": True, "effect": "thought"
    },
    "សំឡេងគិតប្រុស (Reverb)": {
        "voice": "km-KH-PisethNeural", "pitch": "-5Hz", "rate": "-2%", "is_thought": True, "effect": "thought"
    },
}

VOICE_OPTION_NAMES = list(VOICE_PROFILES.keys())


def detect_voice_role_from_text(text):
    if not text:
        return "សំឡេងប្រុសធម្មតា"
    
    # Check Character / Special Roles First
    if re.search(r"\[(សំឡេង)?បិសាច.*?\]|\[យក្ស.*?\]", text, re.IGNORECASE):
        return "សំឡេងបិសាច/ធ្ងន់ (Pitch -50Hz)"
    if re.search(r"\[(សំឡេង)?ក្មេងស្រី.*?\]", text, re.IGNORECASE):
        return "សំឡេងក្មេងស្រី (Pitch +35Hz)"
    if re.search(r"\[(សំឡេង)?ក្មេង.*?\]|\[កូន.*?\]", text, re.IGNORECASE):
        return "សំឡេងក្មេងប្រុស (Pitch +30Hz)"
    if re.search(r"\[(សំឡេង)?យាយ.*?\]|\[យាយចាស់.*?\]", text, re.IGNORECASE):
        return "សំឡេងយាយចាស់ (Pitch -20Hz)"
    if re.search(r"\[(សំឡេង)?មនុស្សចាស់.*?\]|\[តា.*?\]|\[ចាស់.*?\]", text, re.IGNORECASE):
        return "សំឡេងមនុស្សចាស់ (Pitch -25Hz)"
    
    # Thought voices
    if re.search(r"\[(សំឡេង)?គិតស្រី\]", text, re.IGNORECASE):
        return "សំឡេងគិតស្រី (Reverb)"
    if re.search(r"\[(សំឡេង)?គិតប្រុស\]", text, re.IGNORECASE):
        return "សំឡេងគិតប្រុស (Reverb)"
    if re.search(r"\[(សំឡេង)?គិត.*?\]|\[គិត\]|\(គិតក្នុងចិត្ត\)", text, re.IGNORECASE):
        if any(w in text for w in ["ចា៎", "ចាស", "អូន", "អ្នកនាង", "កញ្ញា", "លោកស្រី", "ម៉ាក់", "នាង"]):
            return "សំឡេងគិតស្រី (Reverb)"
        return "សំឡេងគិតប្រុស (Reverb)"

    # Normal gender tags
    if re.search(r"\[(សំឡេង)?ស្រី\]", text, re.IGNORECASE) or "(ស្រី)" in text or "ស្រី:" in text:
        return "សំឡេងស្រីធម្មតា"
    if re.search(r"\[(សំឡេង)?ប្រុស\]", text, re.IGNORECASE) or "(ប្រុស)" in text or "ប្រុស:" in text:
        return "សំឡេងប្រុសធម្មតា"

    female_keywords = ["ចា៎", "ចាស", "អូន", "អ្នកនាង", "កញ្ញា", "លោកស្រី", "អ្នកម៉ាក់", "ម៉ាក់", "នាង"]
    male_keywords = ["បាទ", "បង", "លោក", "លោកពូ", "ពូ", "តា", "លោកប៉ា", "ប៉ា", "អា"]

    for word in female_keywords:
        if word in text:
            return "សំឡេងស្រីធម្មតា"
    for word in male_keywords:
        if word in text:
            return "សំឡេងប្រុសធម្មតា"

    return "សំឡេងប្រុសធម្មតា"


def time_to_seconds(time_str):
    try:
        parts = time_str.replace(',', '.').split(':')
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except Exception:
        return 0.0
    return 0.0


def parse_srt_content(content):
    if not content:
        return []
    clean_content = re.sub(r"```[a-zA-Z]*", "", content).replace("```", "").strip()
    subtitles = []
    pattern = re.compile(
        r'(?P<index>\d+)\s*\n'
        r'(?P<start>\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*\n'
        r'(?P<text>[\s\S]*?)(?=\n\s*\n\d+|\Z)',
        re.MULTILINE
    )
    for m in pattern.finditer(clean_content):
        subtitles.append({
            'start': m.group('start').replace('.', ','),
            'end': m.group('end').replace('.', ','),
            'text': m.group('text').strip().replace('\n', ' ')
        })

    if not subtitles:
        blocks = re.split(r'\n\s*\n', clean_content)
        for block in blocks:
            lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
            if len(lines) >= 2:
                for idx, line in enumerate(lines):
                    if '-->' in line:
                        times = line.split('-->')
                        subtitles.append({
                            'start': times[0].strip(),
                            'end': times[1].strip(),
                            'text': " ".join(lines[idx + 1:])
                        })
                        break
    return subtitles


def parse_srt_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return parse_srt_content(f.read())


def enhance_voice_clarity(sound):
    if not sound or not AudioSegment:
        return sound
    return normalize(sound).high_pass_filter(80) + 2.0


def add_reverb_thought_effect(sound):
    if not sound or not AudioSegment:
        return sound
    delay_1 = AudioSegment.silent(duration=50) + (sound - 3.5)
    delay_2 = AudioSegment.silent(duration=110) + (sound - 7.0)
    delay_3 = AudioSegment.silent(duration=180) + (sound - 11.0)
    return normalize(sound.overlay(delay_1).overlay(delay_2).overlay(delay_3))


def adjust_audio_speed(input_file, output_file, speed_factor):
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


def get_bypass_chrome_driver(headless=False):
    if not SELENIUM_AVAILABLE:
        return None
    options = webdriver.ChromeOptions()
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    user_data_dir = os.path.join(os.getcwd(), "selenium_chrome_data")
    options.add_argument(f"user-data-dir={user_data_dir}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


# ================= WIDGET សម្រាប់ RETRY =================
class RetryStatusWidget(QWidget):
    def __init__(self, row_index, retry_callback, parent=None):
        super().__init__(parent)
        self.row_index = row_index
        self.retry_callback = retry_callback
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        self.status_label = QLabel("⚠️ បរាជ័យ")
        self.status_label.setStyleSheet("color: #FF3366; font-weight: bold;")

        self.retry_btn = QPushButton("🔄 សាកម្ដងទៀត")
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5252, stop:0.4 #d32f2f, stop:1 #610000);
                color: #ffffff;
                border: 1px solid #ffb2b2;
                border-radius: 5px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
                font-family: 'Khmer OS Battambang', 'Battambang', sans-serif;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d2ff, stop:1 #003b73);
                border-color: #00f2fe;
                color: #ffffff;
            }
        """)
        self.retry_btn.clicked.connect(self.on_retry_clicked)

        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.retry_btn)
        layout.addStretch()
        self.setLayout(layout)

    def on_retry_clicked(self):
        self.status_label.setText("⏳ កំពុងបង្កើត...")
        self.status_label.setStyleSheet("color: #FFEA00; font-weight: bold;")
        self.retry_btn.setEnabled(False)
        self.retry_callback(self.row_index, self.update_status)

    def update_status(self, is_success):
        if is_success:
            self.status_label.setText("✅ រួចរាល់")
            self.status_label.setStyleSheet("color: #00FF99; font-weight: bold;")
            self.retry_btn.hide()
        else:
            self.status_label.setText("⚠️ បរាជ័យ")
            self.status_label.setStyleSheet("color: #FF3366; font-weight: bold;")
            self.retry_btn.setEnabled(True)


class WorkerSignals(QObject):
    finished = pyqtSignal(bool)


# ================= BACKGROUND THREADS =================
class ChromeLauncherThread(QThread):
    driver_loaded_signal = pyqtSignal(object)
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def run(self):
        try:
            self.status_signal.emit("🌐 កំពុងបើក Chrome Browser ក្នុង Background...")
            driver = get_bypass_chrome_driver()
            if driver:
                driver.get("https://gemini.google.com/app")
                self.driver_loaded_signal.emit(driver)
            else:
                self.error_signal.emit("មិនអាចបើក Chrome Driver បានទេ! សូមពិនិត្យមើល Chrome Browser របស់អ្នក។")
        except Exception as e:
            err_msg = str(e).strip() or traceback.format_exc()
            self.error_signal.emit(f"កំហុសក្នុងការបើក Chrome:\n{err_msg}")


class WebScraperThread(QThread):
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, target_url):
        super().__init__()
        self.target_url = target_url

    def run(self):
        if not SELENIUM_AVAILABLE:
            self.error_signal.emit("សូមដំឡើង Selenium ជាមុនសិន!")
            return

        driver = None
        try:
            self.status_signal.emit("🤖 កំពុងបើក Web ដើមដើម្បី Scan រក Links ភាគទាំងអស់...")
            driver = get_bypass_chrome_driver(headless=True)
            if not driver:
                self.error_signal.emit("មិនអាចបើក Web Browser សម្រាប់ Scan បានទេ!")
                return

            driver.set_page_load_timeout(30)
            try:
                driver.get(self.target_url)
            except Exception:
                self.status_signal.emit("⚠️ ផ្ទុកទំព័រវេបសាយយឺត ប៉ុន្តែកំពុងបន្ត Scan...")

            time.sleep(3)

            self.status_signal.emit("📜 កំពុង Auto-Scroll ស្វែងរកភាគរឿងឱ្យអស់ (១-ចប់)...")
            try:
                last_height = driver.execute_script("return document.body.scrollHeight")
                for _ in range(5):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.5)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
            except Exception:
                pass

            self.status_signal.emit("🔎 កំពុងចាប់យក (Scrape) Link វីដេអូភាគទាំងអស់...")
            links_found = []
            elements = driver.find_elements(By.XPATH, "//a[@href] | //button[@data-url] | //li/a")
            
            for el in elements:
                try:
                    href = el.get_attribute("href") or el.get_attribute("data-url")
                    if href and href.startswith("http"):
                        if re.search(r'ep|episode|video|watch|play|part|vlog|\d+', href, re.IGNORECASE):
                            if href not in links_found:
                                links_found.append(href)
                except Exception:
                    pass

            if links_found:
                self.status_signal.emit(f"✅ រកឃើញ links សរុប {len(links_found)} ភាគ!")
                self.finished_signal.emit(links_found)
            else:
                self.finished_signal.emit([self.target_url])

        except Exception as e:
            err_msg = str(e).strip() or f"កើតមានកំហុសក្នុងការ Scrap Web:\n{traceback.format_exc()}"
            self.error_signal.emit(err_msg)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass


class BatchUrlInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 Scrap & Download វីដេអូរឿងភាគ (ភាគ ១ ដល់ចប់)")
        self.setFixedSize(650, 350)
        self.setStyleSheet("""
            QDialog { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121622, stop:1 #06080c); 
                border: 2px solid #00f2fe; 
                border-radius: 14px; 
            }
            QLabel { color: #00f2fe; font-size: 13px; font-weight: bold; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QTextEdit {
                background-color: #06080c; color: #ffea00; border: 2px solid #00f2fe;
                border-radius: 10px; padding: 10px; font-size: 12px; font-weight: bold;
                font-family: 'Khmer OS Battambang', 'Battambang', sans-serif;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d2ff, stop:0.4 #0080ff, stop:0.5 #0059b3, stop:1 #003b73);
                color: #FFFFFF; border: 1px solid #80e5ff; border-bottom: 3px solid #001f3f;
                border-radius: 8px; padding: 8px 18px; font-weight: bold; font-size: 12px;
                font-family: 'Khmer OS Battambang', 'Battambang', sans-serif;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #33d6ff, stop:0.4 #1a8cff, stop:0.5 #0066cc, stop:1 #004080);
                border-color: #00f2fe;
            }
            QPushButton#CancelBtn { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a5975, stop:0.4 #2c384e, stop:1 #141a24); 
                border: 1px solid #7288ad; border-bottom: 3px solid #0a0d14;
            }
            QPushButton#ScrapeBtn { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b855ff, stop:0.4 #8e2de2, stop:0.5 #6a0dad, stop:1 #4a00e0); 
                border: 1px solid #e2b3ff; border-bottom: 3px solid #280080;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("🎬 បិទភ្ជាប់ Web URL ដើមនៃរឿង (វា Scan Scrap យកភាគ១-ចប់ ស្វ័យប្រវត្តិ):")
        layout.addWidget(lbl)

        self.txt_urls = QTextEdit()
        self.txt_urls.setPlaceholderText("ឧទាហរណ៍ ដាក់តែ URL ទំព័រដើមនៃរឿង ឬ Link វីដេអូ...")
        layout.addWidget(self.txt_urls)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("បោះបង់")
        btn_cancel.setObjectName("CancelBtn")
        btn_cancel.clicked.connect(self.reject)

        self.btn_auto_scrape = QPushButton("🔍 Scan & Scrap Links Auto")
        self.btn_auto_scrape.setObjectName("ScrapeBtn")
        self.btn_auto_scrape.clicked.connect(self.accept)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_auto_scrape)
        layout.addLayout(btn_box)

    def get_raw_input(self):
        return self.txt_urls.toPlainText().strip()


class BatchVideoDownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, urls):
        super().__init__()
        self.urls = urls

    def run(self):
        if not yt_dlp:
            self.error_signal.emit("សូមដំឡើង yt-dlp ជាមុនសិន! (pip install yt-dlp)")
            return
        
        if not self.urls:
            self.error_signal.emit("ពុំមាន Link ត្រឹមត្រូវសម្រាប់ទាញយកឡើយ!")
            return

        session_folder_name = f"Series_Batch_{time.strftime('%Y%m%d_%H%M%S')}"
        target_download_folder = os.path.join(DOWNLOAD_DIR, session_folder_name)
        os.makedirs(target_download_folder, exist_ok=True)

        try:
            total_items = len(self.urls)
            for idx, url in enumerate(self.urls):
                ep_num = f"{(idx + 1):02d}"
                self.status_signal.emit(f"កំពុងទាញយកភាគ {ep_num}/{total_items}...")
                output_template = os.path.join(target_download_folder, f"{ep_num}_%(title)s.%(ext)s")
                
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

                prog = int(((idx + 1) / total_items) * 100)
                self.progress_signal.emit(prog)

            mp4_files = glob.glob(os.path.join(target_download_folder, "*.mp4")) + glob.glob(os.path.join(target_download_folder, "*/*.mp4"))
            mp4_files.sort()

            if mp4_files:
                self.finished_signal.emit(mp4_files)
            else:
                self.error_signal.emit(f"yt-dlp មិនអាចទាញយកសាច់វីដេអូបានទេពី Link៖\n{self.urls[0]}")

        except Exception as e:
            err_msg = str(e).strip() or traceback.format_exc()
            self.error_signal.emit(f"yt-dlp មិនអាចទាញយកវីដេអូបានទេ! កំហុស៖\n{err_msg}")


class AutoUploadGeminiWorker(QThread):
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, driver, video_path):
        super().__init__()
        self.driver = driver
        self.video_path = video_path

    def run(self):
        try:
            if not self.driver:
                return

            wait = WebDriverWait(self.driver, 30)

            input_selector = (
                By.CSS_SELECTOR, 
                "rich-textarea p, p[data-placeholder], .ql-editor, div[contenteditable='true'], textarea"
            )
            input_box = wait.until(EC.element_to_be_clickable(input_selector))
            time.sleep(1.5)

            input_box.click()
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].innerText = arguments[1];", input_box, SYSTEM_INSTRUCTION)
            input_box.send_keys(" ")
            time.sleep(0.5)

            if self.video_path and os.path.exists(self.video_path):
                js_trigger_click = """
                (function() {
                    let plusBtn = document.querySelector('button[aria-label*="Add"], button[aria-label*="upload"], button.uploader-button, mat-icon[text="add_circle"]');
                    if (!plusBtn) {
                        let buttons = document.querySelectorAll('button');
                        for (let b of buttons) {
                            if (b.innerText.includes('+') || (b.getAttribute('aria-label') && b.getAttribute('aria-label').includes('Add'))) {
                                plusBtn = b;
                                break;
                            }
                        }
                    }
                    if (plusBtn) plusBtn.click();
                })();
                """
                self.driver.execute_script(js_trigger_click)
                time.sleep(0.8)

                js_click_files = """
                (function() {
                    let allElements = document.querySelectorAll('button, div, span, mat-option');
                    for (let el of allElements) {
                        if (el.innerText && el.innerText.trim() === 'Files') {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                })();
                """
                self.driver.execute_script(js_click_files)

                if AUTOMATION_AVAILABLE:
                    time.sleep(1.2)
                    abs_path = os.path.abspath(self.video_path)
                    pyperclip.copy(abs_path)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.4)
                    pyautogui.press('enter')
                    time.sleep(2.0)
                    pyautogui.press('enter')

            self.finished_signal.emit()

        except Exception as e:
            err_msg = str(e).strip() or traceback.format_exc()
            self.error_signal.emit(f"កំហុសបញ្ចូល Prompt/Video អូតូទៅ Gemini:\n{err_msg}")


class GeminiSeleniumWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, driver):
        super().__init__()
        self.driver = driver

    def run(self):
        try:
            if not self.driver:
                raise RuntimeError("សូមបើក Browser Chrome ជាមុនសិន!")

            responses = self.driver.find_elements(By.CSS_SELECTOR, "message-content, .model-response-text, response-container")
            if responses:
                last_response = responses[-1].text
                self.finished_signal.emit(last_response)
            else:
                self.error_signal.emit("មិនទាន់ឃើញមាន Response ពី Gemini ឡើយ! សូមផ្ទៀងផ្ទាត់លើ Chrome Browser។")

        except Exception as e:
            err_msg = str(e).strip() or traceback.format_exc()
            self.error_signal.emit(f"កំហុសទាញយក Response ពី Chrome:\n{err_msg}")


# ================= TTS HELPER FUNCTION (PHASE 2: PITCH & RATE MODULATION) =================
async def generate_single_tts_async(item):
    real_idx = item['index']
    raw_text = item['text']
    voice_code = item['voice_code']
    pitch_mod = item.get('pitch', "+0Hz")
    rate_mod = item.get('rate', "+0%")
    has_thought = item.get('is_thought', False) or is_thought_voice(raw_text)
    
    clean_tts_text = clean_text_for_tts(raw_text)
    
    start_sec = item['start_sec']
    end_sec = item['end_sec']
    srt_duration = max(0.5, end_sec - start_sec)

    if not clean_tts_text:
        return False

    raw_tts_file = temp_path(f"raw_voice_{real_idx}.mp3")
    final_file = temp_path(f"temp_voice_{real_idx}.mp3")

    try:
        communicate = edge_tts.Communicate(clean_tts_text, voice_code, pitch=pitch_mod, rate=rate_mod)
        await communicate.save(raw_tts_file)
        
        if os.path.exists(raw_tts_file):
            sound = AudioSegment.from_file(raw_tts_file) if AudioSegment else None
            tts_duration = len(sound) / 1000.0 if sound else srt_duration

            if tts_duration > 0:
                speed_factor = tts_duration / srt_duration
                speed_factor = max(0.7, min(speed_factor, 2.2))
                adjust_audio_speed(raw_tts_file, final_file, speed_factor)

            if not os.path.exists(final_file):
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
        print(f"Error generating TTS row {real_idx}: {e}")
        return False

    return False


class AudioGenThread(QThread):
    progress_signal = pyqtSignal(int, int)
    item_started_signal = pyqtSignal(int)
    item_completed_signal = pyqtSignal(int, bool)
    finished_signal = pyqtSignal()

    def __init__(self, table_data):
        super().__init__()
        self.table_data = table_data

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._process_batch())

    async def _process_batch(self):
        total = len(self.table_data)
        for progress_idx, item in enumerate(self.table_data):
            real_idx = item['index']
            self.item_started_signal.emit(real_idx)
            success = await generate_single_tts_async(item)
            self.item_completed_signal.emit(real_idx, success)
            self.progress_signal.emit(progress_idx + 1, total)

        self.finished_signal.emit()


# ================= EXPORT VIDEO THREAD (PHASE 2 & PHASE 3 ACCELERATED) =================
class ExportVideoThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, video_path, table_data, subtitles_data, output_path, bg_music_vol_percent=100, 
                 aspect_ratio="Original", resolution="1080p (Full HD)",
                 video_title="", title_norm_x=0.35, title_norm_y=0.08, title_color="#FFEA00", title_font_family="Khmer OS Battambang", title_font_size=46,
                 logo_path="", logo_norm_x=0.85, logo_norm_y=0.05, logo_norm_w=0.15,
                 sub_norm_y=0.85, sub_color="#FFFFFF", sub_font_family="Khmer OS Battambang", sub_font_size=18,
                 anti_detect=True, flip_horizontal=True, crop_zoom=True, color_grade=True, speed_shift=True,
                 enable_blur=False, blur_norm_x=0.05, blur_norm_y=0.05, blur_norm_w=0.20, blur_norm_h=0.10,
                 blur_strength=25, blur_tint="#FFFFFF", blur_tint_opacity=0,
                 # Phase 2: Audio Ducking parameters
                 enable_audio_ducking=True, ducking_reduction_db=14,
                 # Phase 3: GPU Acceleration parameters
                 encoder_choice="Auto (GPU Best)", encode_preset="Balanced"):
        super().__init__()
        self.video_path = video_path
        self.table_data = table_data
        self.subtitles_data = subtitles_data
        self.output_path = output_path
        self.bg_music_vol_percent = bg_music_vol_percent
        self.aspect_ratio = aspect_ratio
        self.resolution = resolution
        self.video_title = video_title
        self.title_norm_x = title_norm_x
        self.title_norm_y = title_norm_y
        self.title_color = title_color
        self.title_font_family = title_font_family
        self.title_font_size = title_font_size
        self.logo_path = logo_path
        self.logo_norm_x = logo_norm_x
        self.logo_norm_y = logo_norm_y
        self.logo_norm_w = logo_norm_w
        self.sub_norm_y = sub_norm_y
        self.sub_color = sub_color
        self.sub_font_family = sub_font_family
        self.sub_font_size = sub_font_size
        
        # Anti-Detection Filters
        self.anti_detect = anti_detect
        self.flip_horizontal = flip_horizontal
        self.crop_zoom = crop_zoom
        self.color_grade = color_grade
        self.speed_shift = speed_shift

        # Circle/Ellipse Blur Parameters
        self.enable_blur = enable_blur
        self.blur_norm_x = blur_norm_x
        self.blur_norm_y = blur_norm_y
        self.blur_norm_w = blur_norm_w
        self.blur_norm_h = blur_norm_h
        self.blur_strength = blur_strength
        self.blur_tint = blur_tint
        self.blur_tint_opacity = blur_tint_opacity

        # Phase 2 Audio Ducking
        self.enable_audio_ducking = enable_audio_ducking
        self.ducking_reduction_db = ducking_reduction_db

        # Phase 3 Hardware Acceleration
        self.encoder_choice = encoder_choice
        self.encode_preset = encode_preset

    def run(self):
        try:
            self.progress_signal.emit(10)
            orig_w, orig_h, dur_sec = get_video_dimension_and_duration(self.video_path)
            speed_factor = 1.03 if (self.anti_detect and self.speed_shift) else 1.0

            # ១. ស្វែងរកសំឡេង AI Dubbed
            ai_voice_wav = temp_path(f"ai_dubbed_voice_{int(time.time())}.wav")
            has_ai_voices = False

            if AudioSegment and self.table_data:
                clip_dur_ms = int(dur_sec * 1000)
                ai_voice_audio = AudioSegment.silent(duration=clip_dur_ms)
                
                for item in self.table_data:
                    idx = item['index']
                    s_ms = int(item['start_sec'] * 1000)
                    v_file = temp_path(f"temp_voice_{idx}.mp3")

                    if os.path.exists(v_file) and os.path.getsize(v_file) > 0:
                        has_ai_voices = True
                        v_sound = AudioSegment.from_file(v_file)
                        ai_voice_audio = ai_voice_audio.overlay(v_sound, position=s_ms)

                if has_ai_voices:
                    ai_voice_audio.export(ai_voice_wav, format="wav")

            self.progress_signal.emit(35)

            # ២. ទាញយកសំឡេងដើមនៃវីដេអូ (BGM Track)
            bg_music_wav = temp_path(f"bg_music_clean_{int(time.time())}.wav")
            has_bg_music = False

            if self.bg_music_vol_percent > 0:
                audio_filters = []
                vol_factor = self.bg_music_vol_percent / 100.0
                audio_filters.append(f"volume={vol_factor:.2f}")

                if self.anti_detect:
                    audio_filters.append("asetrate=48000*1.02,aresample=48000,equalizer=f=1000:t=q:w=1:g=1.5")

                full_filter = ",".join(audio_filters)

                subprocess.run([
                    "ffmpeg", "-y",
                    "-fflags", "+genpts+discardcorrupt",
                    "-i", self.video_path,
                    "-af", full_filter,
                    "-vn", "-threads", "0", bg_music_wav
                ], capture_output=True, text=True)

                if os.path.exists(bg_music_wav) and os.path.getsize(bg_music_wav) > 0:
                    has_bg_music = True

            self.progress_signal.emit(55)

            # ៣. PHASE 2: REAL SIDECHAIN AUDIO DUCKING
            final_audio_wav = temp_path(f"final_mixed_audio_{int(time.time())}.wav")

            if has_ai_voices and has_bg_music and os.path.exists(ai_voice_wav) and os.path.exists(bg_music_wav):
                if self.enable_audio_ducking:
                    ratio_val = max(4, min(12, int(self.ducking_reduction_db / 2.5)))
                    duck_filter = (
                        f"[0:a][1:a]sidechaincompress=threshold=0.03:ratio={ratio_val}:attack=20:release=350[ducked_bg];"
                        f"[ducked_bg][1:a]amix=inputs=2:weights=1 1.25:dropout_transition=2[a_out]"
                    )
                    duck_cmd = [
                        "ffmpeg", "-y",
                        "-i", bg_music_wav,
                        "-i", ai_voice_wav,
                        "-filter_complex", duck_filter,
                        "-map", "[a_out]",
                        "-ar", "48000",
                        final_audio_wav
                    ]
                    subprocess.run(duck_cmd, capture_output=True, text=True)
                else:
                    bg_sound = AudioSegment.from_file(bg_music_wav)
                    ai_sound = AudioSegment.from_file(ai_voice_wav)
                    if len(bg_sound) < len(ai_sound):
                        bg_sound = bg_sound + AudioSegment.silent(duration=(len(ai_sound) - len(bg_sound)))
                    mixed = bg_sound.overlay(ai_sound)
                    mixed.export(final_audio_wav, format="wav")
            elif has_ai_voices and os.path.exists(ai_voice_wav):
                final_audio_wav = ai_voice_wav
            elif has_bg_music and os.path.exists(bg_music_wav):
                final_audio_wav = bg_music_wav
            else:
                final_audio_wav = None

            self.progress_signal.emit(70)

            # ៤. គណនា Resolution តាមការជ្រើសរើស (720p ដល់ 4K)
            res_presets = {
                "720p (HD)": (1280, 720),
                "1080p (Full HD)": (1920, 1080),
                "2K (1440p)": (2560, 1440),
                "4K (2160p UHD)": (3840, 2160)
            }

            if self.resolution in res_presets:
                base_w, base_h = res_presets[self.resolution]
            else:
                base_w, base_h = orig_w, orig_h

            if self.aspect_ratio == "16:9 (YouTube/Landscape)":
                target_w, target_h = base_w, base_h
            elif self.aspect_ratio == "9:16 (TikTok/Reels/Shorts)":
                target_w, target_h = base_h, base_w
            else:
                target_w, target_h = base_w, base_h

            # ៥. បង្កើត Title PNG
            title_png_path = ""
            if self.video_title.strip():
                scaled_title_size = int(self.title_font_size * (target_h / 1080.0) * 1.8)
                title_png_path = generate_khmer_title_image_qt(
                    self.video_title.strip(), target_w, target_h,
                    self.title_norm_x, self.title_norm_y, self.title_color, self.title_font_family, scaled_title_size
                )

            # ៦. បង្កើត Styled ASS Subtitle File
            ass_sub_path = ""
            if self.subtitles_data:
                ass_sub_path = create_ass_subtitle_file(
                    self.subtitles_data, target_w, target_h,
                    self.sub_norm_y, self.sub_color, self.sub_font_family, self.sub_font_size,
                    speed_factor=speed_factor
                )

            # ៧. រៀបចំ Command Inputs & Filters
            inputs = [
                "-fflags", "+genpts+discardcorrupt",
                "-avoid_negative_ts", "make_zero",
                "-i", self.video_path
            ]
            next_idx = 1

            title_idx = -1
            if title_png_path and os.path.exists(title_png_path):
                inputs.extend(["-i", title_png_path])
                title_idx = next_idx
                next_idx += 1

            logo_idx = -1
            if self.logo_path and os.path.exists(self.logo_path):
                inputs.extend(["-i", self.logo_path])
                logo_idx = next_idx
                next_idx += 1

            audio_idx = -1
            if final_audio_wav and os.path.exists(final_audio_wav) and os.path.getsize(final_audio_wav) > 0:
                inputs.extend(["-i", final_audio_wav])
                audio_idx = next_idx
                next_idx += 1

            v_filters = []
            curr_tag = "0:v"

            # Anti-Detection Filters
            if self.anti_detect:
                trans_filters = []
                if self.flip_horizontal:
                    trans_filters.append("hflip")
                if self.crop_zoom:
                    trans_filters.append("crop=iw*0.96:ih*0.96")
                if self.color_grade:
                    trans_filters.append("eq=contrast=1.05:saturation=1.08:brightness=0.01")
                if self.speed_shift:
                    trans_filters.append(f"setpts=PTS/{speed_factor}")

                if trans_filters:
                    v_filters.append(f"[{curr_tag}]{','.join(trans_filters)}[v_anti_det]")
                    curr_tag = "v_anti_det"

            # Scaling & Aspect Ratio Pad
            v_filters.append(f"[{curr_tag}]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2[v_scaled]")
            curr_tag = "v_scaled"

            # អនុវត្ត Blur រាងពងក្រពើ/រាងមូល (Circle / Ellipse Blur Filter)
            if self.enable_blur:
                bx = max(0, min(target_w - 20, int(self.blur_norm_x * target_w)))
                by = max(0, min(target_h - 20, int(self.blur_norm_y * target_h)))
                bw = max(20, min(target_w - bx, int(self.blur_norm_w * target_w)))
                bh = max(20, min(target_h - by, int(self.blur_norm_h * target_h)))
                
                blur_rad = max(5, int(self.blur_strength * (target_h / 1080.0)))
                rx = bw / 2.0
                ry = bh / 2.0
                cx = rx
                cy = ry

                v_filters.append(f"[{curr_tag}]split[v_base_b][v_crop_src]")
                v_filters.append(f"[v_crop_src]crop={bw}:{bh}:{bx}:{by},boxblur={blur_rad}:{max(2, blur_rad // 3)}[v_blurred_crop]")
                
                mask_expr = f"if(lte(pow((X-{cx})/{rx},2)+pow((Y-{cy})/{ry},2),1),255,0)"
                v_filters.append(f"[v_blurred_crop]format=yuva420p,geq=lum='p(X,Y)':a='{mask_expr}'[v_masked_blur]")

                if self.blur_tint_opacity > 0:
                    t_opacity = max(0.05, min(1.0, self.blur_tint_opacity / 100.0))
                    c_clean = self.blur_tint.replace("#", "")
                    v_filters.append(f"[v_masked_blur]drawbox=x=0:y=0:w={bw}:h={bh}:color=0x{c_clean}@{t_opacity:.2f}:t=fill[v_tinted_blur]")
                    v_filters.append(f"[v_base_b][v_tinted_blur]overlay={bx}:{by}[v_blur_applied]")
                else:
                    v_filters.append(f"[v_base_b][v_masked_blur]overlay={bx}:{by}[v_blur_applied]")
                
                curr_tag = "v_blur_applied"

            if title_idx != -1:
                v_filters.append(f"[{curr_tag}][{title_idx}:v]overlay=0:0[v_title_applied]")
                curr_tag = "v_title_applied"

            if logo_idx != -1:
                logo_w = max(40, int(self.logo_norm_w * target_w))
                v_filters.append(f"[{logo_idx}:v]scale={logo_w}:-1[scaled_logo]")
                logo_x = max(0, int(self.logo_norm_x * target_w))
                logo_y = max(0, int(self.logo_norm_y * target_h))
                v_filters.append(f"[{curr_tag}][scaled_logo]overlay={logo_x}:{logo_y}[v_logo_applied]")
                curr_tag = "v_logo_applied"

            # Overlay Burn-in Subtitles
            if ass_sub_path and os.path.exists(ass_sub_path):
                clean_ass = ass_sub_path.replace("\\", "/").replace(":", "\\:")
                v_filters.append(f"[{curr_tag}]ass='{clean_ass}'[v_sub_applied]")
                curr_tag = "v_sub_applied"

            # Audio Filters
            a_filters = []
            a_source = f"{audio_idx}:a" if audio_idx != -1 else "0:a"
            curr_a_tag = "a_out"

            if self.anti_detect and self.speed_shift:
                a_filters.append(f"[{a_source}]atempo={speed_factor}[{curr_a_tag}]")
            else:
                a_filters.append(f"[{a_source}]anull[{curr_a_tag}]")

            all_filters = v_filters + a_filters

            # ៨. PHASE 3: GPU HARDWARE ACCELERATION SELECTION
            gpu_info = detect_gpu_hardware_acceleration()
            chosen_encoder = "libx264"
            encoder_opts = []

            # Check user preference or Auto
            if "NVENC" in self.encoder_choice or (("Auto" in self.encoder_choice) and gpu_info["nvenc"]):
                chosen_encoder = "h264_nvenc"
                preset_val = "p4" if self.encode_preset == "Fast" else ("p5" if self.encode_preset == "Balanced" else "p6")
                encoder_opts = ["-preset", preset_val, "-rc", "vbr", "-cq", "22"]
            elif "QuickSync" in self.encoder_choice or (("Auto" in self.encoder_choice) and gpu_info["qsv"]):
                chosen_encoder = "h264_qsv"
                preset_val = "veryfast" if self.encode_preset == "Fast" else "balanced"
                encoder_opts = ["-preset", preset_val, "-global_quality", "22"]
            elif "AMF" in self.encoder_choice or (("Auto" in self.encoder_choice) and gpu_info["amf"]):
                chosen_encoder = "h264_amf"
                encoder_opts = ["-quality", "speed" if self.encode_preset == "Fast" else "balanced"]
            else:
                # CPU Fallback
                chosen_encoder = "libx264"
                preset_val = "ultrafast" if self.encode_preset == "Fast" else ("veryfast" if self.encode_preset == "Balanced" else "medium")
                crf_val = "18" if "4K" in self.resolution or "2K" in self.resolution else "22"
                encoder_opts = ["-preset", preset_val, "-crf", crf_val]

            ffmpeg_export_cmd = ["ffmpeg", "-y"] + inputs
            ffmpeg_export_cmd.extend([
                "-filter_complex", ";".join(all_filters),
                "-map", f"[{curr_tag}]",
                "-map", f"[{curr_a_tag}]",
                "-c:v", chosen_encoder
            ])
            ffmpeg_export_cmd.extend(encoder_opts)
            ffmpeg_export_cmd.extend([
                "-threads", "0",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "320k" if "4K" in self.resolution else "256k",
                "-ar", "48000",
                self.output_path
            ])

            res = subprocess.run(ffmpeg_export_cmd, capture_output=True, text=True)
            if res.returncode != 0 and chosen_encoder != "libx264":
                print(f"Hardware encoder {chosen_encoder} failed. Retrying with safe CPU libx264...")
                fallback_cmd = ["ffmpeg", "-y"] + inputs
                fallback_cmd.extend([
                    "-filter_complex", ";".join(all_filters),
                    "-map", f"[{curr_tag}]",
                    "-map", f"[{curr_a_tag}]",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "22",
                    "-threads", "0",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "320k" if "4K" in self.resolution else "256k",
                    "-ar", "48000",
                    self.output_path
                ])
                res = subprocess.run(fallback_cmd, capture_output=True, text=True)

            if res.returncode != 0:
                err_lines = [l for l in res.stderr.splitlines() if any(k in l.lower() for k in ["error", "cannot", "failed", "invalid"])]
                clean_err = "\n".join(err_lines[-5:]) if err_lines else res.stderr[-500:]
                raise RuntimeError(f"FFmpeg Error:\n{clean_err}")

            self.progress_signal.emit(100)
            self.finished_signal.emit(self.output_path)

        except Exception as e:
            err_msg = str(e).strip() or traceback.format_exc()
            self.error_signal.emit(f"កំហុសពេលរៀបចំនាំចេញ (Export) វីដេអូ:\n{err_msg}")


class MergeVideosThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, video_files, output_path):
        super().__init__()
        self.video_files = video_files
        self.output_path = output_path

    def run(self):
        try:
            self.progress_signal.emit(20)
            concat_txt = temp_path(f"concat_list_{int(time.time())}.txt")
            with open(concat_txt, "w", encoding="utf-8") as f:
                for v in self.video_files:
                    clean_p = os.path.abspath(v).replace("\\", "/")
                    f.write(f"file '{clean_p}'\n")

            self.progress_signal.emit(50)
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_txt,
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                self.output_path
            ]
            subprocess.run(cmd, capture_output=True, text=True)
            self.progress_signal.emit(100)
            self.finished_signal.emit(self.output_path)
        except Exception as e:
            err_msg = str(e).strip() or traceback.format_exc()
            self.error_signal.emit(f"កំហុសក្នុងការ Merge វីដេអូ:\n{err_msg}")


# ================= PHASE 4: VISUAL SUBTITLE TIMELINE STRIP WIDGET =================
class SubtitleTimelineStripWidget(QWidget):
    position_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(24)
        self.subtitles = []
        self.duration_ms = 1
        self.current_pos_ms = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_subtitles(self, subtitles):
        self.subtitles = subtitles
        self.update()

    def set_duration(self, dur_ms):
        self.duration_ms = max(1, dur_ms)
        self.update()

    def set_current_position(self, pos_ms):
        self.current_pos_ms = pos_ms
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.duration_ms > 0:
            click_x = event.position().x()
            ratio = max(0.0, min(1.0, click_x / self.width()))
            target_ms = int(ratio * self.duration_ms)
            self.position_clicked.emit(target_ms)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background track
        w = self.width()
        h = self.height()
        painter.fillRect(self.rect(), QColor("#0e131d"))
        painter.setPen(QPen(QColor("#1e2536"), 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        if self.duration_ms <= 0 or not self.subtitles:
            painter.setPen(QColor("#4a5975"))
            font = QFont("Khmer OS Battambang", 9)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "គ្មានទិន្នន័យ Subtitle នៅឡើយ")
            painter.end()
            return

        dur_sec = self.duration_ms / 1000.0

        # គូសបន្ទាត់ Subtitle Block នីមួយៗ
        for idx, sub in enumerate(self.subtitles):
            s_sec = time_to_seconds(sub['start'])
            e_sec = time_to_seconds(sub['end'])
            
            x1 = int((s_sec / dur_sec) * w)
            x2 = int((e_sec / dur_sec) * w)
            bw = max(3, x2 - x1)

            # ពិនិត្យមើល Collision/Overlap ជាមួយបន្ទាត់បន្ទាប់
            is_overlap = False
            if idx < len(self.subtitles) - 1:
                next_start = time_to_seconds(self.subtitles[idx + 1]['start'])
                if e_sec > next_start + 0.05:
                    is_overlap = True

            block_color = QColor("#FF3366") if is_overlap else QColor("#00F2FE")
            block_color.setAlpha(190)
            painter.fillRect(x1, 3, bw, h - 6, block_color)
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            painter.drawRect(x1, 3, bw, h - 6)

        # គូស Playhead Indicator (បន្ទាត់ក្រហមបង្ហាញទីតាំងកំពុងលេង)
        play_x = int((self.current_pos_ms / self.duration_ms) * w)
        painter.setPen(QPen(QColor("#FFEA00"), 2))
        painter.drawLine(play_x, 0, play_x, h)

        painter.end()


# ================= INTERACTIVE DRAGGABLE & RESIZABLE CANVAS (PHASE 4: SAFE-ZONE & SNAPPING) =================
class CustomCanvasVideoWidget(QWidget):
    title_size_changed = pyqtSignal(int)
    subtitle_size_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.current_frame_image = None
        self.video_rect = QRect()
        
        # Title Properties
        self.title_text = ""
        self.title_color = QColor("#FFEA00")
        self.title_font_family = "Khmer OS Battambang"
        self.title_font_size = 22
        self.title_norm_x = 0.35
        self.title_norm_y = 0.08
        self.title_rect = QRect()
        self.title_handle_rect = QRect()

        # Logo Properties
        self.logo_pixmap = None
        self.logo_norm_x = 0.85
        self.logo_norm_y = 0.05
        self.logo_norm_w = 0.15
        self.logo_rect = QRect()
        self.logo_handle_rect = QRect()

        # Subtitle Properties
        self.subtitle_text = ""
        self.sub_color = QColor("#FFFFFF")
        self.sub_font_family = "Khmer OS Battambang"
        self.sub_font_size = 18
        self.sub_norm_x = 0.50
        self.sub_norm_y = 0.85
        self.sub_rect = QRect()
        self.sub_handle_rect = QRect()

        # Circle/Ellipse Blur Properties
        self.enable_blur = False
        self.blur_strength = 25
        self.blur_tint = QColor("#FFFFFF")
        self.blur_tint_opacity = 0
        self.blur_norm_x = 0.05
        self.blur_norm_y = 0.05
        self.blur_norm_w = 0.15
        self.blur_norm_h = 0.15
        self.blur_rect = QRect()
        
        self.blur_handle_se = QRect()
        self.blur_handle_e = QRect()
        self.blur_handle_s = QRect()

        # PHASE 4: Safe Zone & Snapping Features
        self.show_safe_zone = False
        self.is_snapped_center_x = False

        # Interaction states
        self.active_mode = None
        self.drag_offset = QPoint()
        self.resize_start_pos = QPoint()
        self.initial_font_size = 22
        self.initial_sub_font_size = 18
        self.initial_logo_norm_w = 0.15
        self.initial_blur_norm_w = 0.15
        self.initial_blur_norm_h = 0.15

    def get_actual_video_rect(self):
        if not self.current_frame_image or self.current_frame_image.isNull():
            return self.rect()
        
        img_w = self.current_frame_image.width()
        img_h = self.current_frame_image.height()
        
        if img_w <= 0 or img_h <= 0:
            return self.rect()
            
        widget_w = self.width()
        widget_h = self.height()
        
        scale = min(widget_w / img_w, widget_h / img_h)
        target_w = int(img_w * scale)
        target_h = int(img_h * scale)
        target_x = (widget_w - target_w) // 2
        target_y = (widget_h - target_h) // 2
        
        return QRect(target_x, target_y, target_w, target_h)

    def set_video_frame(self, frame: QVideoFrame):
        if frame.isValid():
            image = frame.toImage()
            if not image.isNull():
                self.current_frame_image = image
                self.update()

    def set_title(self, text, color_hex, font_family, font_size):
        self.title_text = text
        self.title_color = QColor(color_hex)
        self.title_font_family = font_family if font_family else "Khmer OS Battambang"
        self.title_font_size = max(10, font_size)
        self.update()

    def set_logo(self, pixmap):
        self.logo_pixmap = pixmap
        self.update()

    def set_subtitle(self, text):
        self.subtitle_text = text
        self.update()

    def set_subtitle_style(self, color_hex, font_family, font_size):
        self.sub_color = QColor(color_hex)
        self.sub_font_family = font_family if font_family else "Khmer OS Battambang"
        self.sub_font_size = max(10, font_size)
        self.update()

    def set_blur_config(self, enabled, strength, tint_hex, tint_opacity):
        self.enable_blur = enabled
        self.blur_strength = strength
        self.blur_tint = QColor(tint_hex)
        self.blur_tint_opacity = tint_opacity
        self.update()

    def set_safe_zone_visible(self, visible):
        self.show_safe_zone = visible
        self.update()

    def wheelEvent(self, event):
        pos = event.position().toPoint()
        delta = event.angleDelta().y()

        if self.enable_blur and self.blur_rect.contains(pos):
            step = 0.015 if delta > 0 else -0.015
            self.blur_norm_w = max(0.02, min(0.95, self.blur_norm_w + step))
            self.blur_norm_h = max(0.02, min(0.95, self.blur_norm_h + step))
            self.update()
            event.accept()
            return

        if self.sub_rect.contains(pos):
            step = 2 if delta > 0 else -2
            self.sub_font_size = max(10, min(70, self.sub_font_size + step))
            self.subtitle_size_changed.emit(self.sub_font_size)
            self.update()
            event.accept()
            return

        if self.title_rect.contains(pos):
            step = 2 if delta > 0 else -2
            self.title_font_size = max(10, min(80, self.title_font_size + step))
            self.title_size_changed.emit(self.title_font_size)
            self.update()
            event.accept()
            return

        if self.logo_rect.contains(pos):
            step = 0.015 if delta > 0 else -0.015
            self.logo_norm_w = max(0.04, min(0.60, self.logo_norm_w + step))
            self.update()
            event.accept()
            return

        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()

            if self.enable_blur:
                if self.blur_handle_se.contains(pos):
                    self.active_mode = 'resize_blur_se'
                    self.resize_start_pos = pos
                    self.initial_blur_norm_w = self.blur_norm_w
                    self.initial_blur_norm_h = self.blur_norm_h
                    return
                elif self.blur_handle_e.contains(pos):
                    self.active_mode = 'resize_blur_e'
                    self.resize_start_pos = pos
                    self.initial_blur_norm_w = self.blur_norm_w
                    return
                elif self.blur_handle_s.contains(pos):
                    self.active_mode = 'resize_blur_s'
                    self.resize_start_pos = pos
                    self.initial_blur_norm_h = self.blur_norm_h
                    return

            if self.title_handle_rect.contains(pos):
                self.active_mode = 'resize_title'
                self.resize_start_pos = pos
                self.initial_font_size = self.title_font_size
                return
            elif self.logo_handle_rect.contains(pos):
                self.active_mode = 'resize_logo'
                self.resize_start_pos = pos
                self.initial_logo_norm_w = self.logo_norm_w
                return
            elif self.sub_handle_rect.contains(pos):
                self.active_mode = 'resize_subtitle'
                self.resize_start_pos = pos
                self.initial_sub_font_size = self.sub_font_size
                return

            if self.enable_blur and self.blur_rect.contains(pos):
                self.active_mode = 'drag_blur'
                self.drag_offset = pos - self.blur_rect.topLeft()
            elif self.title_rect.contains(pos):
                self.active_mode = 'drag_title'
                self.drag_offset = pos - self.title_rect.topLeft()
            elif self.logo_rect.contains(pos):
                self.active_mode = 'drag_logo'
                self.drag_offset = pos - self.logo_rect.topLeft()
            elif self.sub_rect.contains(pos):
                self.active_mode = 'drag_subtitle'
                self.drag_offset = pos - self.sub_rect.topLeft()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        vr = self.get_actual_video_rect()
        vw = max(1, vr.width())
        vh = max(1, vr.height())

        if self.enable_blur and self.blur_handle_se.contains(pos):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self.enable_blur and self.blur_handle_e.contains(pos):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self.enable_blur and self.blur_handle_s.contains(pos):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif self.title_handle_rect.contains(pos) or self.logo_handle_rect.contains(pos) or self.sub_handle_rect.contains(pos):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (self.enable_blur and self.blur_rect.contains(pos)) or self.title_rect.contains(pos) or self.logo_rect.contains(pos) or self.sub_rect.contains(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        self.is_snapped_center_x = False

        if self.active_mode == 'drag_blur':
            new_top_left = pos - self.drag_offset
            self.blur_norm_x = max(0.0, min((new_top_left.x() - vr.left()) / vw, 0.95))
            self.blur_norm_y = max(0.0, min((new_top_left.y() - vr.top()) / vh, 0.95))
            self.update()
        elif self.active_mode == 'resize_blur_se':
            diff_x = pos.x() - self.resize_start_pos.x()
            diff_y = pos.y() - self.resize_start_pos.y()
            self.blur_norm_w = max(0.02, min(0.95, self.initial_blur_norm_w + (diff_x / vw)))
            self.blur_norm_h = max(0.02, min(0.95, self.initial_blur_norm_h + (diff_y / vh)))
            self.update()
        elif self.active_mode == 'resize_blur_e':
            diff_x = pos.x() - self.resize_start_pos.x()
            self.blur_norm_w = max(0.02, min(0.95, self.initial_blur_norm_w + (diff_x / vw)))
            self.update()
        elif self.active_mode == 'resize_blur_s':
            diff_y = pos.y() - self.resize_start_pos.y()
            self.blur_norm_h = max(0.02, min(0.95, self.initial_blur_norm_h + (diff_y / vh)))
            self.update()
        elif self.active_mode == 'drag_title':
            new_top_left = pos - self.drag_offset
            calc_nx = (new_top_left.x() - vr.left()) / vw
            # Magnetic snap to center
            if abs(calc_nx - 0.5) < 0.025:
                calc_nx = 0.5 - (self.title_rect.width() / (2 * vw))
                self.is_snapped_center_x = True
            self.title_norm_x = max(0.0, min(calc_nx, 0.95))
            self.title_norm_y = max(0.0, min((new_top_left.y() - vr.top()) / vh, 0.95))
            self.update()
        elif self.active_mode == 'drag_logo':
            new_top_left = pos - self.drag_offset
            self.logo_norm_x = max(0.0, min((new_top_left.x() - vr.left()) / vw, 0.95))
            self.logo_norm_y = max(0.0, min((new_top_left.y() - vr.top()) / vh, 0.95))
            self.update()
        elif self.active_mode == 'drag_subtitle':
            new_top_left = pos - self.drag_offset
            calc_sub_x = ((new_top_left.x() + self.sub_rect.width() // 2) - vr.left()) / vw
            # Magnetic snap to center
            if abs(calc_sub_x - 0.50) < 0.03:
                calc_sub_x = 0.50
                self.is_snapped_center_x = True
            self.sub_norm_x = max(0.0, min(calc_sub_x, 1.0))
            self.sub_norm_y = max(0.0, min((new_top_left.y() - vr.top()) / vh, 0.95))
            self.update()
        elif self.active_mode == 'resize_title':
            diff = (pos.x() - self.resize_start_pos.x()) + (pos.y() - self.resize_start_pos.y())
            new_size = int(self.initial_font_size + (diff * 0.15))
            self.title_font_size = max(10, min(80, new_size))
            self.title_size_changed.emit(self.title_font_size)
            self.update()
        elif self.active_mode == 'resize_logo':
            diff_x = pos.x() - self.resize_start_pos.x()
            new_norm_w = self.initial_logo_norm_w + (diff_x / vw)
            self.logo_norm_w = max(0.04, min(0.60, new_norm_w))
            self.update()
        elif self.active_mode == 'resize_subtitle':
            diff = (pos.x() - self.resize_start_pos.x()) + (pos.y() - self.resize_start_pos.y())
            new_sub_size = int(self.initial_sub_font_size + (diff * 0.15))
            self.sub_font_size = max(10, min(70, new_sub_size))
            self.subtitle_size_changed.emit(self.sub_font_size)
            self.update()

    def mouseReleaseEvent(self, event):
        self.active_mode = None
        self.is_snapped_center_x = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        painter.fillRect(self.rect(), QColor("#000000"))
        self.video_rect = self.get_actual_video_rect()

        if self.current_frame_image and not self.current_frame_image.isNull():
            painter.drawImage(self.video_rect, self.current_frame_image)

        vx = self.video_rect.left()
        vy = self.video_rect.top()
        vw = self.video_rect.width()
        vh = self.video_rect.height()

        # PHASE 4: TIKTOK / REELS SAFE ZONE GUIDES
        if self.show_safe_zone and vw > 50 and vh > 50:
            top_h = int(0.12 * vh)
            painter.fillRect(vx, vy, vw, top_h, QColor(255, 50, 50, 45))
            painter.setPen(QPen(QColor("#FF5555"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(vx, vy + top_h, vx + vw, vy + top_h)

            bottom_h = int(0.20 * vh)
            bottom_y = vy + vh - bottom_h
            painter.fillRect(vx, bottom_y, vw, bottom_h, QColor(255, 50, 50, 45))
            painter.setPen(QPen(QColor("#FF5555"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(vx, bottom_y, vx + vw, bottom_y)

            right_w = int(0.16 * vw)
            right_x = vx + vw - right_w
            painter.fillRect(right_x, vy + top_h, right_w, vh - top_h - bottom_h, QColor(255, 160, 0, 35))
            painter.setPen(QPen(QColor("#FFAA00"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(right_x, vy + top_h, right_x, bottom_y)

            painter.setPen(QPen(QColor("#00FF99"), 2, Qt.PenStyle.SolidLine))
            painter.drawRect(vx + 10, vy + top_h + 10, vw - right_w - 20, vh - top_h - bottom_h - 20)
            
            painter.setFont(QFont("Khmer OS Battambang", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#00FF99"))
            painter.drawText(vx + 16, vy + top_h + 24, "📱 TikTok Safe Zone (កុំដាក់ Title/Sub ហួសបន្ទាត់ក្រហម)")

        # Center Snap Guide Line
        if self.is_snapped_center_x:
            cx = vx + vw // 2
            painter.setPen(QPen(QColor("#00F2FE"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(cx, vy, cx, vy + vh)

        # ១. គូស Circle/Ellipse Blur Preview ដោយសុវត្ថិភាព (Safe Fast Blur)
        if self.enable_blur:
            bx = int(vx + self.blur_norm_x * vw)
            by = int(vy + self.blur_norm_y * vh)
            bw = max(20, int(self.blur_norm_w * vw))
            bh = max(15, int(self.blur_norm_h * vh))

            self.blur_rect = QRect(bx, by, bw, bh)

            if self.current_frame_image and not self.current_frame_image.isNull():
                img_w = self.current_frame_image.width()
                img_h = self.current_frame_image.height()
                
                img_crop_x = max(0, min(img_w - 5, int(self.blur_norm_x * img_w)))
                img_crop_y = max(0, min(img_h - 5, int(self.blur_norm_y * img_h)))
                img_crop_w = max(5, min(img_w - img_crop_x, int(self.blur_norm_w * img_w)))
                img_crop_h = max(5, min(img_h - img_crop_y, int(self.blur_norm_h * img_h)))
                
                try:
                    cropped_img = self.current_frame_image.copy(img_crop_x, img_crop_y, img_crop_w, img_crop_h)
                    if not cropped_img.isNull() and cropped_img.width() > 0 and cropped_img.height() > 0:
                        sw = max(4, bw // 10)
                        sh = max(4, bh // 10)
                        small = cropped_img.scaled(sw, sh, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
                        blurred_preview = small.scaled(bw, bh, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        
                        path = QPainterPath()
                        path.addEllipse(QRect(bx, by, bw, bh))
                        painter.save()
                        painter.setClipPath(path)
                        painter.drawImage(self.blur_rect, blurred_preview)
                        
                        if self.blur_tint_opacity > 0:
                            alpha_int = int((self.blur_tint_opacity / 100.0) * 255)
                            tint_col = QColor(self.blur_tint)
                            tint_col.setAlpha(alpha_int)
                            painter.fillRect(self.blur_rect, tint_col)
                        painter.restore()
                except Exception:
                    pass

            painter.setPen(QPen(QColor("#00F2FE"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.blur_rect)

            self.blur_handle_se = QRect(self.blur_rect.right() - 8, self.blur_rect.bottom() - 8, 10, 10)
            self.blur_handle_e = QRect(self.blur_rect.right() - 4, by + (bh // 2) - 5, 8, 10)
            self.blur_handle_s = QRect(bx + (bw // 2) - 5, self.blur_rect.bottom() - 4, 10, 8)

            painter.setBrush(QBrush(QColor("#00F2FE")))
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            painter.drawRect(self.blur_handle_se)
            painter.drawRect(self.blur_handle_e)
            painter.drawRect(self.blur_handle_s)
        else:
            self.blur_rect = QRect()
            self.blur_handle_se = QRect()
            self.blur_handle_e = QRect()
            self.blur_handle_s = QRect()

        # ២. គូស Title
        if self.title_text.strip():
            font = QFont(self.title_font_family, self.title_font_size, QFont.Weight.Bold)
            painter.setFont(font)
            metrics = painter.fontMetrics()
            tw = metrics.horizontalAdvance(self.title_text)
            th = metrics.height()

            tx = int(vx + self.title_norm_x * vw)
            ty = int(vy + self.title_norm_y * vh)

            self.title_rect = QRect(tx - 6, ty - th + 4, tw + 12, th + 8)

            painter.setPen(QPen(QColor("#00F2FE"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(0, 0, 0, 140)))
            painter.drawRoundedRect(self.title_rect, 6, 6)

            painter.setPen(QColor(0, 0, 0, 240))
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 2)]:
                painter.drawText(tx + dx, ty + dy, self.title_text)

            painter.setPen(self.title_color)
            painter.drawText(tx, ty, self.title_text)

            hx, hy = self.title_rect.right() - 8, self.title_rect.bottom() - 8
            self.title_handle_rect = QRect(hx, hy, 10, 10)
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            painter.setBrush(QBrush(QColor("#00F2FE")))
            painter.drawRect(self.title_handle_rect)
        else:
            self.title_rect = QRect()
            self.title_handle_rect = QRect()

        # ៣. គូស Logo
        if self.logo_pixmap and not self.logo_pixmap.isNull():
            logo_w = max(30, int(self.logo_norm_w * vw))
            scaled_logo = self.logo_pixmap.scaledToWidth(logo_w, Qt.TransformationMode.SmoothTransformation)
            lw = scaled_logo.width()
            lh = scaled_logo.height()

            lx = int(vx + self.logo_norm_x * vw)
            ly = int(vy + self.logo_norm_y * vh)

            self.logo_rect = QRect(lx - 4, ly - 4, lw + 8, lh + 8)

            painter.setPen(QPen(QColor("#FFEA00"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(0, 0, 0, 80)))
            painter.drawRoundedRect(self.logo_rect, 6, 6)

            painter.drawPixmap(lx, ly, scaled_logo)

            lhx, lhy = self.logo_rect.right() - 8, self.logo_rect.bottom() - 8
            self.logo_handle_rect = QRect(lhx, lhy, 10, 10)
            painter.setPen(QPen(QColor("#FFEA00")))
            painter.drawRect(self.logo_handle_rect)
        else:
            self.logo_rect = QRect()
            self.logo_handle_rect = QRect()

        # ៤. គូស Subtitle
        if self.subtitle_text.strip():
            sub_font = QFont(self.sub_font_family, self.sub_font_size, QFont.Weight.Bold)
            painter.setFont(sub_font)
            metrics = painter.fontMetrics()
            sw = metrics.horizontalAdvance(self.subtitle_text)
            sh = metrics.height()

            rect_w = sw + 28
            rect_h = sh + 14

            rx = int(vx + self.sub_norm_x * vw) - (rect_w // 2)
            ry = int(vy + self.sub_norm_y * vh)

            self.sub_rect = QRect(rx, ry, rect_w, rect_h)

            painter.setBrush(QBrush(QColor(0, 0, 0, 190)))
            painter.setPen(QPen(QColor("#00FF99"), 1, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self.sub_rect, 8, 8)

            painter.setPen(QColor(0, 0, 0, 240))
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 2)]:
                painter.drawText(rx + 14 + dx, ry + sh + dy - 2, self.subtitle_text)

            painter.setPen(self.sub_color)
            painter.drawText(rx + 14, ry + sh - 2, self.subtitle_text)

            shx, shy = self.sub_rect.right() - 8, self.sub_rect.bottom() - 8
            self.sub_handle_rect = QRect(shx, shy, 10, 10)
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            painter.setBrush(QBrush(QColor("#00FF99")))
            painter.drawRect(self.sub_handle_rect)
        else:
            self.sub_rect = QRect()
            self.sub_handle_rect = QRect()

        painter.end()


# ================= PHASE 3: BATCH EXPORT QUEUE MANAGER DIALOG =================
class BatchExportQueueDialog(QDialog):
    def __init__(self, queue_list, start_queue_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 Batch Export Queue Manager (ជួរនាំចេញវីដេអូស្វ័យប្រវត្តិ)")
        self.setFixedSize(720, 450)
        self.queue_list = queue_list
        self.start_queue_callback = start_queue_callback
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog { background: #0c0f17; border: 2px solid #00f2fe; border-radius: 12px; }
            QLabel { color: #00f2fe; font-size: 12px; font-weight: bold; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QTableWidget { background-color: #06080c; border: 1px solid #1e2536; gridline-color: #141a26; color: #ffffff; border-radius: 8px; }
            QHeaderView::section { background-color: #1a2333; color: #00f2fe; border: 1px solid #283044; padding: 5px; font-weight: bold; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d2ff, stop:0.4 #0080ff, stop:1 #003b73);
                color: #FFFFFF; border: 1px solid #80e5ff; border-radius: 6px; padding: 6px 14px; font-weight: bold;
                font-family: 'Khmer OS Battambang', 'Battambang', sans-serif;
            }
            QPushButton#CloseBtn { background: #333d4e; border: 1px solid #5a6b85; }
            QPushButton#StartBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00ff88, stop:1 #006633); border: 1px solid #80ffc3; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        lbl = QLabel("📋 បញ្ជីរាយនាមវីដេអូដែលត្រូវ Export បន្តបន្ទាប់គ្នា (Queue):")
        layout.addWidget(lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ភាគ #", "ឈ្មោះវីដេអូ", "ទំហំ/Resolution", "ស្ថានភាព (Status)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 140)
        layout.addWidget(self.table)

        self.populate_table()

        btn_box = QHBoxLayout()
        self.btn_clear = QPushButton("🗑 សម្អាតបញ្ជី")
        self.btn_clear.setObjectName("CloseBtn")
        self.btn_clear.clicked.connect(self.clear_queue)

        self.btn_start = QPushButton("▶ ចាប់ផ្ដើម Export ទាំងអស់ (Start Queue)")
        self.btn_start.setObjectName("StartBtn")
        self.btn_start.clicked.connect(self.on_start_clicked)

        btn_close = QPushButton("បិទ")
        btn_close.setObjectName("CloseBtn")
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(self.btn_clear)
        btn_box.addStretch()
        btn_box.addWidget(self.btn_start)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def populate_table(self):
        self.table.setRowCount(0)
        for idx, item in enumerate(self.queue_list):
            self.table.insertRow(idx)
            self.table.setItem(idx, 0, QTableWidgetItem(f"{idx+1:02d}"))
            self.table.setItem(idx, 1, QTableWidgetItem(os.path.basename(item['video_path'])))
            self.table.setItem(idx, 2, QTableWidgetItem(f"{item.get('resolution', '1080p')}"))
            
            st_item = QTableWidgetItem(item.get('status', '⏳ រង់ចាំ'))
            st_item.setForeground(QColor("#FFEA00") if "រង់ចាំ" in item.get('status', '') else QColor("#00FF99"))
            self.table.setItem(idx, 3, st_item)

    def clear_queue(self):
        self.queue_list.clear()
        self.table.setRowCount(0)

    def on_start_clicked(self):
        if not self.queue_list:
            QMessageBox.information(self, "ជូនដំណឹង", "ពុំមានវីដេអូនៅក្នុងបញ្ជី Queue ឡើយ!")
            return
        self.start_queue_callback()
        self.accept()


# ================= MAIN APPLICATION WINDOW =================
class SmartVideoEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Smart Ai Studio Pro (Audio Engineering • GPU Acceleration • Advanced Editor)")
        
        if os.path.exists("app_icon.png"):
            self.setWindowIcon(QIcon("app_icon.png"))
        else:
            self.setWindowIcon(create_default_icon())

        self.setGeometry(20, 20, 1600, 960)

        self.current_video_path = ""
        self.current_subtitle_row = -1
        self.selenium_driver = None
        self.subtitles = []
        self.downloaded_series_list = []
        self.selected_logo_path = ""
        self.export_queue = []

        # Title Properties
        self.title_color_hex = "#FFEA00"
        self.title_font_family = "Khmer OS Battambang"
        self.title_font_size = 22

        # Subtitle Properties
        self.sub_color_hex = "#FFFFFF"
        self.sub_font_family = "Khmer OS Battambang"
        self.sub_font_size = 18

        # Circle/Ellipse Blur Properties
        self.blur_strength_val = 25
        self.blur_tint_hex = "#FFFFFF"
        self.blur_tint_opacity_val = 0

        # Hardware GPU Detection
        self.gpu_capabilities = detect_gpu_hardware_acceleration()

        # ================= STYLESHEET =================
        self.setStyleSheet("""
            QMainWindow { background-color: #0b0d12; }
            QWidget { 
                color: #e6edf3; 
                font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; 
                font-size: 11px; 
                font-weight: bold; 
            }
            QFrame#LeftPanel, QFrame#RightPanel { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #161b26, stop:1 #080a0f); border: 1px solid rgba(255, 255, 255, 0.08); }
            QFrame#BoxContainer { background: #000000; border: 2px solid #00f2fe; border-radius: 12px; }
            QFrame#OverlayOptionsBox { background: rgba(22, 27, 38, 0.7); border: 1px solid #00f2fe; border-radius: 8px; padding: 6px; }
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2c384e, stop:0.4 #1c2432, stop:0.5 #141a24, stop:1 #0f131b); 
                color: #ffffff; 
                border: 1px solid rgba(255, 255, 255, 0.2); 
                border-bottom: 3px solid #05070a; 
                border-radius: 8px; 
                padding: 6px 12px; 
                font-weight: bold; 
                font-family: 'Khmer OS Battambang', 'Battambang', sans-serif;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d4e6d, stop:0.4 #283448, stop:0.5 #1e2736, stop:1 #161c28); border-color: #00f2fe; color: #00f2fe; }
            QPushButton#BlueBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d2ff, stop:0.4 #0080ff, stop:0.5 #0059b3, stop:1 #003b73); border: 1px solid #80e5ff; border-bottom: 3px solid #001f3f; }
            QPushButton#GreenBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00ff88, stop:0.4 #00cc66, stop:0.5 #00994d, stop:1 #006633); border: 1px solid #80ffc3; border-bottom: 3px solid #00331a; }
            QPushButton#PurpleBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b855ff, stop:0.4 #8e2de2, stop:0.5 #6a0dad, stop:1 #4a00e0); border: 1px solid #e2b3ff; border-bottom: 3px solid #280080; }
            QPushButton#ExportBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff4b72, stop:0.4 #ff0055, stop:0.5 #cc0044, stop:1 #80002a); border: 1px solid #ffb3c6; border-bottom: 3px solid #4d0019; }
            QPushButton#StopBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5252, stop:0.4 #d32f2f, stop:0.5 #9a0007, stop:1 #610000); border: 1px solid #ffb2b2; border-bottom: 3px solid #330000; }
            QPushButton#OrangeBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffa726, stop:0.4 #ff8c00, stop:0.5 #cc7000, stop:1 #804600); border: 1px solid #ffd699; border-bottom: 3px solid #4d2a00; }
            QPushButton#TealBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4dd0e1, stop:0.4 #00b4db, stop:0.5 #0083b0, stop:1 #004d66); border: 1px solid #b2ebf2; border-bottom: 3px solid #002633; }
            QPushButton#MergeBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff007f, stop:0.4 #d6006c, stop:0.5 #a80055, stop:1 #660033); border: 1px solid #ff80bf; border-bottom: 3px solid #33001a; }
            QTableWidget { background-color: #06080c; border: 2px solid #1e2536; gridline-color: #141a26; color: #ffffff; selection-background-color: #0080ff; border-radius: 10px; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QHeaderView::section { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #25334d, stop:0.5 #162030, stop:1 #0d131d); color: #00f2fe; border: 1px solid #283044; padding: 6px; font-weight: bold; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QComboBox, QLineEdit { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2436, stop:1 #0b1019); border: 2px solid #00f2fe; border-radius: 7px; color: #ffea00; font-size: 11px; font-weight: 900; padding: 3px 6px; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QComboBox:hover, QLineEdit:hover { border-color: #ffea00; }
            QComboBox QAbstractItemView { background-color: #0b1019; color: #ffea00; selection-background-color: #0080ff; selection-color: #ffffff; font-weight: bold; border: 1px solid #00f2fe; outline: none; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QProgressBar { border: 2px solid #283044; border-radius: 8px; text-align: center; color: #ffffff; background-color: #06080c; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0055ff, stop:0.5 #00f2fe, stop:1 #00ff88); border-radius: 6px; }
            QMessageBox { background-color: #121622; border: 2px solid #00f2fe; border-radius: 12px; }
            QMessageBox QLabel { color: #ffffff; font-size: 12px; font-weight: bold; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QMessageBox QPushButton { min-width: 80px; font-family: 'Khmer OS Battambang', 'Battambang', sans-serif; }
            QCheckBox { color: #00FF99; font-size: 11px; font-weight: bold; }
        """)

        self.init_ui()

    def init_ui(self):
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # ================= LEFT PANEL (VIDEO PREVIEW & TIMELINE) =================
        left_widget = QFrame()
        left_widget.setObjectName("LeftPanel")
        left_layout = QVBoxLayout(left_widget)

        video_btn_box = QHBoxLayout()
        self.btn_open_video = QPushButton("📁 បញ្ចូលវីដេអូ")
        self.btn_open_video.setObjectName("BlueBtn")
        self.btn_open_video.clicked.connect(self.load_video)

        self.btn_download_video = QPushButton("🌐 ទាញយកពី Web (ភាគ១-ចប់)")
        self.btn_download_video.setObjectName("PurpleBtn")
        self.btn_download_video.clicked.connect(self.download_online_video)

        self.btn_load_srt = QPushButton("📄 SRT")
        self.btn_load_srt.setObjectName("GreenBtn")
        self.btn_load_srt.clicked.connect(self.load_srt_file)

        video_btn_box.addWidget(self.btn_open_video)
        video_btn_box.addWidget(self.btn_download_video)
        video_btn_box.addWidget(self.btn_load_srt)
        left_layout.addLayout(video_btn_box)

        series_select_box = QHBoxLayout()
        lbl_ep = QLabel("🎬 ជ្រើសរើសភាគរឿង៖")
        lbl_ep.setStyleSheet("color: #FFEA00; font-weight: bold; font-size: 12px;")
        self.combo_series_episodes = QComboBox()
        self.combo_series_episodes.currentIndexChanged.connect(self.on_series_episode_selected)
        series_select_box.addWidget(lbl_ep)
        series_select_box.addWidget(self.combo_series_episodes, 1)
        left_layout.addLayout(series_select_box)

        self.video_container = QFrame()
        self.video_container.setObjectName("BoxContainer")
        self.video_container.setMinimumSize(340, 360)
        v_layout = QVBoxLayout(self.video_container)
        v_layout.setContentsMargins(0, 0, 0, 0)

        # Canvas Video Player
        self.video_widget = CustomCanvasVideoWidget(self.video_container)
        self.video_widget.title_size_changed.connect(self.on_title_size_changed_from_canvas)
        self.video_widget.subtitle_size_changed.connect(self.on_subtitle_size_changed_from_canvas)
        v_layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.video_sink = QVideoSink()
        self.video_sink.videoFrameChanged.connect(self.video_widget.set_video_frame)
        self.media_player.setVideoSink(self.video_sink)

        self.tts_player = QMediaPlayer()
        self.tts_audio_output = QAudioOutput()
        self.tts_player.setAudioOutput(self.tts_audio_output)

        self.media_player.errorOccurred.connect(self.on_media_error)
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)

        left_layout.addWidget(self.video_container, 1)

        # PHASE 4: VISUAL SUBTITLE TIMELINE STRIP
        left_layout.addWidget(QLabel("⏱️ បន្ទាត់ Subtitle Timeline (ចុចដើម្បី Jump ទៅកាន់ចំណុចនោះ):"))
        self.timeline_strip = SubtitleTimelineStripWidget()
        self.timeline_strip.position_clicked.connect(self.set_video_position)
        left_layout.addWidget(self.timeline_strip)

        controls_layout = QVBoxLayout()
        slider_box = QHBoxLayout()
        self.slider_video = QSlider(Qt.Orientation.Horizontal)
        self.slider_video.sliderMoved.connect(self.set_video_position)
        
        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #00F2FE; font-weight: bold;")

        slider_box.addWidget(self.slider_video)
        slider_box.addWidget(self.lbl_time)
        controls_layout.addLayout(slider_box)

        btn_control_box = QHBoxLayout()
        self.btn_play_pause = QPushButton("▶ លេង (Space)")
        self.btn_play_pause.setObjectName("BlueBtn")
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)

        self.btn_stop = QPushButton("⏹ បញ្ឈប់")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.clicked.connect(self.stop_video)

        self.btn_mute_orig = QPushButton("🔊 សំឡេងដើម")
        self.btn_mute_orig.setObjectName("OrangeBtn")
        self.btn_mute_orig.clicked.connect(self.toggle_orig_mute)

        self.btn_mute_tts = QPushButton("🎙️ សំឡេង AI")
        self.btn_mute_tts.setObjectName("TealBtn")
        self.btn_mute_tts.clicked.connect(self.toggle_tts_mute)

        # PHASE 4: Toggle TikTok Safe-Zone
        self.chk_safe_zone = QCheckBox("📱 Safe-Zone (TikTok/Reels)")
        self.chk_safe_zone.setStyleSheet("color: #00FF99; font-weight: bold;")
        self.chk_safe_zone.toggled.connect(self.video_widget.set_safe_zone_visible)

        btn_control_box.addWidget(self.btn_play_pause)
        btn_control_box.addWidget(self.btn_stop)
        btn_control_box.addWidget(self.btn_mute_orig)
        btn_control_box.addWidget(self.btn_mute_tts)
        btn_control_box.addWidget(self.chk_safe_zone)

        controls_layout.addLayout(btn_control_box)
        left_layout.addLayout(controls_layout)

        self.lbl_download_status = QLabel("💡 គន្លឹះ៖ ចុចលើជ្រុងស្តាំ ឬ Mouse Wheel ដើម្បីពង្រីក-បង្រួម | បន្ទាត់ក្រហមលើ Timeline = មាន Subtitle ជាន់គ្នា")
        self.lbl_download_status.setStyleSheet("color: #00F2FE; font-size: 11px;")
        left_layout.addWidget(self.lbl_download_status)

        self.progress_bar = QProgressBar()
        left_layout.addWidget(self.progress_bar, 0)

        # ================= RIGHT PANEL (CONTROLS & TABLE) =================
        right_widget = QFrame()
        right_widget.setObjectName("RightPanel")
        right_layout = QVBoxLayout(right_widget)

        top_ai_box = QHBoxLayout()
        self.btn_open_browser = QPushButton("🌐 ១. បើក Chrome Gemini Auto")
        self.btn_open_browser.setObjectName("PurpleBtn")
        self.btn_open_browser.clicked.connect(self.open_chrome_browser)

        self.btn_extract_srt = QPushButton("🤖 ២. ចាប់យក SRT ពី Gemini")
        self.btn_extract_srt.setObjectName("GreenBtn")
        self.btn_extract_srt.clicked.connect(self.extract_srt_from_chrome)

        self.btn_generate_tts = QPushButton("🎙️ ៣. បញ្ចូលសំឡេង AI")
        self.btn_generate_tts.setObjectName("BlueBtn")
        self.btn_generate_tts.clicked.connect(self.start_audio_generation)

        self.btn_export_video = QPushButton("🎬 ៤. នាំចេញវីដេអូ")
        self.btn_export_video.setObjectName("ExportBtn")
        self.btn_export_video.clicked.connect(self.start_video_export)

        # PHASE 3: Batch Export Queue Button
        self.btn_batch_queue = QPushButton("🚀 ជួរ Export (Batch Queue)")
        self.btn_batch_queue.setObjectName("OrangeBtn")
        self.btn_batch_queue.clicked.connect(self.open_batch_export_queue)

        self.btn_merge_all = QPushButton("🎞️ Merge រួម")
        self.btn_merge_all.setObjectName("MergeBtn")
        self.btn_merge_all.clicked.connect(self.merge_all_dubbed_videos)

        top_ai_box.addWidget(self.btn_open_browser)
        top_ai_box.addWidget(self.btn_extract_srt)
        top_ai_box.addWidget(self.btn_generate_tts)
        top_ai_box.addWidget(self.btn_export_video)
        top_ai_box.addWidget(self.btn_batch_queue)
        top_ai_box.addWidget(self.btn_merge_all)
        right_layout.addLayout(top_ai_box)

        # ================= OVERLAY CONFIGURATION =================
        overlay_frame = QFrame()
        overlay_frame.setObjectName("OverlayOptionsBox")
        overlay_layout = QVBoxLayout(overlay_frame)
        overlay_layout.setContentsMargins(8, 8, 8, 8)
        overlay_layout.setSpacing(6)

        # Row 1: Title
        title_row = QHBoxLayout()
        lbl_title = QLabel("🏷️ ចំណងជើង:")
        lbl_title.setStyleSheet("color: #FFEA00; font-weight: bold;")
        self.txt_video_title = QLineEdit()
        self.txt_video_title.setPlaceholderText("វាយបញ្ចូលចំណងជើងវីដេអូ (ជាភាសាខ្មែរ)...")
        self.txt_video_title.textChanged.connect(self.update_live_canvas)

        self.btn_title_font = QPushButton(f"🔤 {self.title_font_family} ({self.title_font_size}pt)")
        self.btn_title_font.setObjectName("PurpleBtn")
        self.btn_title_font.clicked.connect(self.choose_title_font)

        self.btn_title_color = QPushButton("🎨 ពណ៌ចំណងជើង")
        self.btn_title_color.setObjectName("OrangeBtn")
        self.btn_title_color.clicked.connect(self.choose_title_color)

        self.lbl_color_preview = QLabel("   ")
        self.lbl_color_preview.setStyleSheet(f"background-color: {self.title_color_hex}; border: 1px solid white; border-radius: 4px; min-width: 26px; min-height: 20px;")

        title_row.addWidget(lbl_title)
        title_row.addWidget(self.txt_video_title, 1)
        title_row.addWidget(self.btn_title_font)
        title_row.addWidget(self.btn_title_color)
        title_row.addWidget(self.lbl_color_preview)
        overlay_layout.addLayout(title_row)

        # Row 2: Subtitle Controls & Logo
        sub_row = QHBoxLayout()
        lbl_sub = QLabel("💬 Subtitle:")
        lbl_sub.setStyleSheet("color: #00FF99; font-weight: bold;")

        self.btn_sub_font = QPushButton(f"🔤 {self.sub_font_family} ({self.sub_font_size}pt)")
        self.btn_sub_font.setObjectName("PurpleBtn")
        self.btn_sub_font.clicked.connect(self.choose_subtitle_font)

        self.btn_sub_color = QPushButton("🎨 ពណ៌ Subtitle")
        self.btn_sub_color.setObjectName("GreenBtn")
        self.btn_sub_color.clicked.connect(self.choose_subtitle_color)

        self.lbl_sub_color_preview = QLabel("   ")
        self.lbl_sub_color_preview.setStyleSheet(f"background-color: {self.sub_color_hex}; border: 1px solid white; border-radius: 4px; min-width: 26px; min-height: 20px;")

        lbl_logo = QLabel("🖼️ Logo:")
        lbl_logo.setStyleSheet("color: #00F2FE; font-weight: bold; margin-left: 10px;")
        
        self.btn_select_logo = QPushButton("📁 ជ្រើស Logo PNG/JPG")
        self.btn_select_logo.setObjectName("TealBtn")
        self.btn_select_logo.clicked.connect(self.select_logo_file)

        self.lbl_logo_path = QLabel("មិនទាន់ជ្រើស Logo")
        self.lbl_logo_path.setStyleSheet("color: #aaaaaa; font-weight: normal;")

        sub_row.addWidget(lbl_sub)
        sub_row.addWidget(self.btn_sub_font)
        sub_row.addWidget(self.btn_sub_color)
        sub_row.addWidget(self.lbl_sub_color_preview)
        sub_row.addWidget(lbl_logo)
        sub_row.addWidget(self.btn_select_logo)
        sub_row.addWidget(self.lbl_logo_path, 1)
        overlay_layout.addLayout(sub_row)

        # Row 3: Circle/Ellipse Blur Box Configuration
        blur_row = QHBoxLayout()
        self.chk_blur = QCheckBox("⚪ បើក Blur រាងមូល (Circle/Ellipse)")
        self.chk_blur.setChecked(False)
        self.chk_blur.setStyleSheet("color: #00F2FE; font-weight: bold;")
        self.chk_blur.toggled.connect(self.update_live_canvas)

        lbl_strength = QLabel("កម្រិតព្រាល (Blur):")
        lbl_strength.setStyleSheet("color: #FFEA00; font-weight: bold; margin-left: 8px;")

        self.slider_blur_strength = QSlider(Qt.Orientation.Horizontal)
        self.slider_blur_strength.setRange(5, 60)
        self.slider_blur_strength.setValue(25)
        self.slider_blur_strength.setFixedWidth(100)
        self.slider_blur_strength.valueChanged.connect(self.on_blur_strength_changed)

        self.lbl_blur_strength_val = QLabel("25px")
        self.lbl_blur_strength_val.setStyleSheet("color: #FFEA00; font-weight: bold; width: 35px;")

        self.btn_blur_tint_color = QPushButton("🎨 Tint ពណ៌")
        self.btn_blur_tint_color.setObjectName("OrangeBtn")
        self.btn_blur_tint_color.clicked.connect(self.choose_blur_tint_color)

        self.lbl_blur_tint_preview = QLabel("   ")
        self.lbl_blur_tint_preview.setStyleSheet(f"background-color: {self.blur_tint_hex}; border: 1px solid #00F2FE; border-radius: 4px; min-width: 26px; min-height: 20px;")

        lbl_tint_op = QLabel("Tint %:")
        lbl_tint_op.setStyleSheet("color: #FFFFFF; font-weight: bold; margin-left: 6px;")

        self.slider_blur_tint_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_blur_tint_opacity.setRange(0, 100)
        self.slider_blur_tint_opacity.setValue(0)
        self.slider_blur_tint_opacity.setFixedWidth(80)
        self.slider_blur_tint_opacity.valueChanged.connect(self.on_blur_tint_opacity_changed)

        self.lbl_blur_tint_op_val = QLabel("0%")
        self.lbl_blur_tint_op_val.setStyleSheet("color: #FFEA00; font-weight: bold; width: 30px;")

        blur_row.addWidget(self.chk_blur)
        blur_row.addWidget(lbl_strength)
        blur_row.addWidget(self.slider_blur_strength)
        blur_row.addWidget(self.lbl_blur_strength_val)
        blur_row.addWidget(self.btn_blur_tint_color)
        blur_row.addWidget(self.lbl_blur_tint_preview)
        blur_row.addWidget(lbl_tint_op)
        blur_row.addWidget(self.slider_blur_tint_opacity)
        blur_row.addWidget(self.lbl_blur_tint_op_val)
        blur_row.addStretch()
        overlay_layout.addLayout(blur_row)

        # Row 4: Anti-Copyright Bypass Filters
        anti_row = QHBoxLayout()
        lbl_anti = QLabel("🛡️ Bypass Filters:")
        lbl_anti.setStyleSheet("color: #FF0055; font-weight: bold;")
        
        self.chk_anti_detect = QCheckBox("បើកទាំងអស់")
        self.chk_anti_detect.setChecked(True)
        self.chk_anti_detect.setStyleSheet("color: #00FF99;")

        self.chk_flip = QCheckBox("Flip ឆ្វេង-ស្តាំ")
        self.chk_flip.setChecked(True)

        self.chk_crop = QCheckBox("Crop/Zoom 4%")
        self.chk_crop.setChecked(True)

        self.chk_color = QCheckBox("កែពណ៌/Contrast")
        self.chk_color.setChecked(True)

        self.chk_speed = QCheckBox("បង្កើនល្បឿន 3%")
        self.chk_speed.setChecked(True)

        anti_row.addWidget(lbl_anti)
        anti_row.addWidget(self.chk_anti_detect)
        anti_row.addWidget(self.chk_flip)
        anti_row.addWidget(self.chk_crop)
        anti_row.addWidget(self.chk_color)
        anti_row.addWidget(self.chk_speed)
        anti_row.addStretch()
        overlay_layout.addLayout(anti_row)

        right_layout.addWidget(overlay_frame)

        # ================= PHASE 2 & PHASE 3: AUDIO DUCKING & GPU ENCODER CONTROLS =================
        pro_controls_box = QHBoxLayout()

        # Phase 2: Audio Ducking Checkbox & Sensitivity
        self.chk_audio_ducking = QCheckBox("🦆 Auto Audio Ducking")
        self.chk_audio_ducking.setChecked(True)
        self.chk_audio_ducking.setToolTip("ពេល AI និយាយ ភ្លេងដើមនឹងស្រកចុះស្វ័យប្រវត្តិតាមស្តង់ដារអាជីព")
        self.chk_audio_ducking.setStyleSheet("color: #00F2FE; font-weight: bold;")

        lbl_duck_db = QLabel("កម្រិតស្រក:")
        lbl_duck_db.setStyleSheet("color: #FFEA00; font-weight: bold;")
        self.combo_ducking_level = QComboBox()
        self.combo_ducking_level.addItems(["ស្រាល (-8 dB)", "ស្តង់ដារ (-14 dB)", "ខ្លាំង (-18 dB)"])
        self.combo_ducking_level.setCurrentIndex(1)

        # Phase 3: Hardware Encoder Selector
        lbl_encoder = QLabel("⚡ GPU Acceleration:")
        lbl_encoder.setStyleSheet("color: #00FF88; font-weight: bold; margin-left: 10px;")

        self.combo_encoder = QComboBox()
        encoder_items = ["Auto (GPU Best)"]
        if self.gpu_capabilities["nvenc"]:
            encoder_items.append("NVIDIA NVENC (GPU)")
        if self.gpu_capabilities["qsv"]:
            encoder_items.append("Intel QuickSync (GPU)")
        if self.gpu_capabilities["amf"]:
            encoder_items.append("AMD AMF (GPU)")
        encoder_items.append("CPU (libx264)")
        self.combo_encoder.addItems(encoder_items)

        lbl_enc_preset = QLabel("ល្បឿន Render:")
        lbl_enc_preset.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        self.combo_enc_preset = QComboBox()
        self.combo_enc_preset.addItems(["Fast", "Balanced", "High Quality"])
        self.combo_enc_preset.setCurrentIndex(1)

        pro_controls_box.addWidget(self.chk_audio_ducking)
        pro_controls_box.addWidget(lbl_duck_db)
        pro_controls_box.addWidget(self.combo_ducking_level)
        pro_controls_box.addWidget(lbl_encoder)
        pro_controls_box.addWidget(self.combo_encoder)
        pro_controls_box.addWidget(lbl_enc_preset)
        pro_controls_box.addWidget(self.combo_enc_preset)
        pro_controls_box.addStretch()
        right_layout.addLayout(pro_controls_box)

        # Export Format & Resolution Options
        export_options_box = QHBoxLayout()
        lbl_bg_vol = QLabel("🎶 សំឡេងដើម:")
        lbl_bg_vol.setStyleSheet("color: #00F2FE; font-weight: bold; font-size: 11px;")
        
        self.slider_bg_music_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_bg_music_vol.setRange(0, 100)
        self.slider_bg_music_vol.setValue(50)
        self.slider_bg_music_vol.setFixedWidth(110)

        self.lbl_bg_music_vol_val = QLabel("50%")
        self.lbl_bg_music_vol_val.setStyleSheet("color: #FFEA00; font-weight: bold; width: 35px;")
        self.slider_bg_music_vol.valueChanged.connect(lambda v: self.lbl_bg_music_vol_val.setText(f"{v}%"))

        lbl_res = QLabel("🖥️ Resolution:")
        lbl_res.setStyleSheet("color: #00F2FE; font-weight: bold; font-size: 11px; margin-left: 6px;")

        self.combo_resolution = QComboBox()
        self.combo_resolution.addItems([
            "720p (HD)",
            "1080p (Full HD)",
            "2K (1440p)",
            "4K (2160p UHD)",
            "Original (ទំហំដើម)"
        ])
        self.combo_resolution.setCurrentIndex(1)

        lbl_aspect = QLabel("📐 Aspect Ratio:")
        lbl_aspect.setStyleSheet("color: #00F2FE; font-weight: bold; font-size: 11px; margin-left: 6px;")
        
        self.combo_aspect_ratio = QComboBox()
        self.combo_aspect_ratio.addItems([
            "Original",
            "16:9 (YouTube/Landscape)",
            "9:16 (TikTok/Reels/Shorts)"
        ])
        self.combo_aspect_ratio.currentIndexChanged.connect(self.on_aspect_ratio_changed)

        export_options_box.addWidget(lbl_bg_vol)
        export_options_box.addWidget(self.slider_bg_music_vol)
        export_options_box.addWidget(self.lbl_bg_music_vol_val)
        export_options_box.addWidget(lbl_res)
        export_options_box.addWidget(self.combo_resolution)
        export_options_box.addWidget(lbl_aspect)
        export_options_box.addWidget(self.combo_aspect_ratio)
        export_options_box.addStretch()
        right_layout.addLayout(export_options_box)

        # SUBTITLE TABLE (PHASE 2: RICH CHARACTER VOICES WITH PITCH)
        self.table_subtitles = QTableWidget()
        self.table_subtitles.setColumnCount(6)
        self.table_subtitles.setHorizontalHeaderLabels([
            "#", "ចាប់ផ្តើម", "បញ្ឈប់", "អត្ថបទ Subtitle", "តួអង្គ/សំឡេង (Pitch)", "ស្ថានភាព"
        ])
        self.table_subtitles.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_subtitles.setColumnWidth(4, 210)
        self.table_subtitles.setColumnWidth(5, 140)
        self.table_subtitles.cellClicked.connect(self.on_table_cell_clicked)
        right_layout.addWidget(self.table_subtitles)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([520, 1080])

        self.setCentralWidget(main_splitter)

    # ================= KEYBOARD SHORTCUTS =================
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play_pause()
            event.accept()
        elif event.key() == Qt.Key.Key_Left:
            pos = max(0, self.media_player.position() - 3000)
            self.set_video_position(pos)
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            pos = min(self.media_player.duration(), self.media_player.position() + 3000)
            self.set_video_position(pos)
            event.accept()
        else:
            super().keyPressEvent(event)

    # ================= LIVE UPDATE CANVAS =================
    def on_aspect_ratio_changed(self, idx):
        text = self.combo_aspect_ratio.currentText()
        if "9:16" in text:
            self.chk_safe_zone.setChecked(True)

    def on_blur_strength_changed(self, val):
        self.blur_strength_val = val
        self.lbl_blur_strength_val.setText(f"{val}px")
        self.update_live_canvas()

    def on_blur_tint_opacity_changed(self, val):
        self.blur_tint_opacity_val = val
        self.lbl_blur_tint_op_val.setText(f"{val}%")
        self.update_live_canvas()

    def choose_blur_tint_color(self):
        color = QColorDialog.getColor(QColor(self.blur_tint_hex), self, "ជ្រើសរើសពណ៌ Tint លើ Blur")
        if color.isValid():
            self.blur_tint_hex = color.name().upper()
            self.lbl_blur_tint_preview.setStyleSheet(f"background-color: {self.blur_tint_hex}; border: 1px solid #00F2FE; border-radius: 4px; min-width: 26px; min-height: 20px;")
            self.update_live_canvas()

    def on_title_size_changed_from_canvas(self, new_size):
        self.title_font_size = new_size
        self.btn_title_font.setText(f"🔤 {self.title_font_family} ({self.title_font_size}pt)")

    def on_subtitle_size_changed_from_canvas(self, new_size):
        self.sub_font_size = new_size
        self.btn_sub_font.setText(f"🔤 {self.sub_font_family} ({self.sub_font_size}pt)")

    def update_live_canvas(self):
        text = self.txt_video_title.text().strip()
        self.video_widget.set_title(text, self.title_color_hex, self.title_font_family, self.title_font_size)
        self.video_widget.set_subtitle_style(self.sub_color_hex, self.sub_font_family, self.sub_font_size)
        self.video_widget.set_blur_config(self.chk_blur.isChecked(), self.blur_strength_val, self.blur_tint_hex, self.blur_tint_opacity_val)

        if self.selected_logo_path and os.path.exists(self.selected_logo_path):
            pix = QPixmap(self.selected_logo_path)
            self.video_widget.set_logo(pix)
        else:
            self.video_widget.set_logo(None)

    def choose_title_color(self):
        color = QColorDialog.getColor(QColor(self.title_color_hex), self, "ជ្រើសរើសពណ៌ចំណងជើង")
        if color.isValid():
            self.title_color_hex = color.name().upper()
            self.lbl_color_preview.setStyleSheet(f"background-color: {self.title_color_hex}; border: 1px solid white; border-radius: 4px; min-width: 26px; min-height: 20px;")
            self.update_live_canvas()

    def choose_title_font(self):
        initial_font = QFont(self.title_font_family, self.title_font_size)
        font, ok = QFontDialog.getFont(initial_font, self, "ជ្រើសរើសពុម្ពអក្សរ & ទំហំ ចំណងជើង")
        if ok:
            self.title_font_family = font.family()
            self.title_font_size = font.pointSize() if font.pointSize() > 0 else font.pixelSize()
            self.btn_title_font.setText(f"🔤 {self.title_font_family} ({self.title_font_size}pt)")
            self.update_live_canvas()

    def choose_subtitle_color(self):
        color = QColorDialog.getColor(QColor(self.sub_color_hex), self, "ជ្រើសរើសពណ៌ Subtitle")
        if color.isValid():
            self.sub_color_hex = color.name().upper()
            self.lbl_sub_color_preview.setStyleSheet(f"background-color: {self.sub_color_hex}; border: 1px solid white; border-radius: 4px; min-width: 26px; min-height: 20px;")
            self.update_live_canvas()

    def choose_subtitle_font(self):
        initial_font = QFont(self.sub_font_family, self.sub_font_size)
        font, ok = QFontDialog.getFont(initial_font, self, "ជ្រើសរើសពុម្ពអក្សរ & ទំហំ Subtitle")
        if ok:
            self.sub_font_family = font.family()
            self.sub_font_size = font.pointSize() if font.pointSize() > 0 else font.pixelSize()
            self.btn_sub_font.setText(f"🔤 {self.sub_font_family} ({self.sub_font_size}pt)")
            self.update_live_canvas()

    def select_logo_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើសរូប Logo", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if file_path:
            self.selected_logo_path = file_path
            self.lbl_logo_path.setText(os.path.basename(file_path))
            self.lbl_logo_path.setStyleSheet("color: #00FF99; font-weight: bold;")
            self.update_live_canvas()

    def show_dialog(self, title, message, dialog_type="success"):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if dialog_type == "success":
            msg_box.setIcon(QMessageBox.Icon.Information)
        else:
            msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.exec()

    def set_active_video(self, file_path):
        file_path = os.path.abspath(os.path.normpath(file_path))
        if not os.path.exists(file_path):
            self.show_error(f"រកមិនឃើញ File វីដេអូ៖ {file_path}")
            return

        self.current_video_path = file_path
        self.media_player.stop()
        self.tts_player.stop()
        self.tts_player.setSource(QUrl())
        self.current_subtitle_row = -1

        media_url = QUrl.fromLocalFile(file_path)
        self.media_player.setSource(media_url)
        self.media_player.setPosition(0)
        self.btn_play_pause.setText("▶ លេង (Space)")
        
        self.update_live_canvas()

    def load_video(self):
        files, _ = QFileDialog.getOpenFileNames(self, "ជ្រើសរើសវីដេអូ (មួយ ឬច្រើន)", "", "Video Files (*.mp4 *.mkv *.avi *.mov)")
        if files:
            self.downloaded_series_list = files
            self.combo_series_episodes.clear()
            for idx, fpath in enumerate(files):
                fname = os.path.basename(fpath)
                self.combo_series_episodes.addItem(f"ភាគ {idx+1:02d}: {fname}", fpath)
            self.set_active_video(files[0])

    def download_online_video(self):
        dlg = BatchUrlInputDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            raw_input = dlg.get_raw_input()
            if raw_input:
                lines = [l.strip() for l in raw_input.split('\n') if l.strip().startswith('http')]
                if len(lines) == 1:
                    self.lbl_download_status.setText("កំពុង Scan យក Links វីដេអូ...")
                    self.scraper_thread = WebScraperThread(lines[0])
                    self.scraper_thread.status_signal.connect(self.lbl_download_status.setText)
                    self.scraper_thread.finished_signal.connect(self.start_batch_download)
                    self.scraper_thread.error_signal.connect(self.show_error)
                    self.scraper_thread.start()
                elif len(lines) > 1:
                    self.start_batch_download(lines)
                else:
                    self.show_error("សូមបញ្ចូល Link (URL) ឱ្យបានត្រឹមត្រូវ!")

    def start_batch_download(self, urls):
        self.progress_bar.setValue(0)
        self.downloader_thread = BatchVideoDownloadThread(urls)
        self.downloader_thread.progress_signal.connect(self.progress_bar.setValue)
        self.downloader_thread.status_signal.connect(self.lbl_download_status.setText)
        self.downloader_thread.finished_signal.connect(self.on_batch_download_finished)
        self.downloader_thread.error_signal.connect(self.show_error)
        self.downloader_thread.start()

    def on_batch_download_finished(self, video_files):
        if not video_files:
            self.show_error("មិនមានវីដេអូណាត្រូវបានទាញយកជោគជ័យឡើយ!")
            return

        self.downloaded_series_list = video_files
        self.combo_series_episodes.clear()
        
        for idx, fpath in enumerate(video_files):
            fname = os.path.basename(fpath)
            self.combo_series_episodes.addItem(f"ភាគ {idx+1:02d}: {fname}", fpath)

        self.set_active_video(video_files[0])
        
        save_folder = os.path.dirname(video_files[0])
        self.show_dialog(
            "ជោគជ័យ", 
            f"Scrap & ទាញយកវីដេអូរឿងភាគបានជោគជ័យសរុប {len(video_files)} ភាគ!\n\nរក្សាទុកក្នុង៖\n{save_folder}",
            "success"
        )

    def on_series_episode_selected(self, index):
        if 0 <= index < len(self.downloaded_series_list):
            selected_path = self.downloaded_series_list[index]
            self.set_active_video(selected_path)

    def load_srt_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "ជ្រើសរើស File SRT", "", "SRT Files (*.srt)")
        if file_path:
            subtitles = parse_srt_file(file_path)
            self.populate_subtitles(subtitles)

    def populate_subtitles(self, subtitles):
        self.subtitles = subtitles
        self.table_subtitles.setRowCount(0)
        self.timeline_strip.set_subtitles(subtitles)

        for idx, sub in enumerate(subtitles):
            self.table_subtitles.insertRow(idx)
            self.table_subtitles.setItem(idx, 0, QTableWidgetItem(f"{idx + 1:02d}"))
            self.table_subtitles.setItem(idx, 1, QTableWidgetItem(sub['start']))
            self.table_subtitles.setItem(idx, 2, QTableWidgetItem(sub['end']))
            self.table_subtitles.setItem(idx, 3, QTableWidgetItem(sub['text']))

            # Phase 2: Character Voice Dropdown
            detected_role = detect_voice_role_from_text(sub['text'])
            combo_voice = QComboBox()
            combo_voice.addItems(VOICE_OPTION_NAMES)
            
            if detected_role in VOICE_OPTION_NAMES:
                combo_voice.setCurrentText(detected_role)
            else:
                combo_voice.setCurrentIndex(0)
                
            self.table_subtitles.setCellWidget(idx, 4, combo_voice)

            v_file = temp_path(f"temp_voice_{idx}.mp3")
            if os.path.exists(v_file) and os.path.getsize(v_file) > 0:
                status_item = QTableWidgetItem("✅ រួចរាល់")
                status_item.setForeground(QColor("#00FF99"))
            else:
                status_item = QTableWidgetItem("❌ មិនទាន់រួច")
                status_item.setForeground(QColor("#FF5555"))
                
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_subtitles.setItem(idx, 5, status_item)

    def open_chrome_browser(self):
        if not SELENIUM_AVAILABLE:
            self.show_error("សូមដំឡើង selenium និង webdriver_manager!")
            return
        
        self.lbl_download_status.setText("កំពុងបើក Chrome Browser...")
        self.btn_open_browser.setEnabled(False)

        self.chrome_launcher = ChromeLauncherThread()
        self.chrome_launcher.status_signal.connect(self.lbl_download_status.setText)
        self.chrome_launcher.driver_loaded_signal.connect(self.on_chrome_loaded)
        self.chrome_launcher.error_signal.connect(self.on_chrome_error)
        self.chrome_launcher.start()

    def on_chrome_loaded(self, driver):
        self.selenium_driver = driver
        self.btn_open_browser.setEnabled(True)
        self.lbl_download_status.setText("Chrome បានបើករួចរាល់!")

        self.auto_upload_worker = AutoUploadGeminiWorker(self.selenium_driver, self.current_video_path)
        self.auto_upload_worker.error_signal.connect(self.show_error)
        self.auto_upload_worker.start()

    def on_chrome_error(self, err_msg):
        self.btn_open_browser.setEnabled(True)
        self.lbl_download_status.setText("កំហុសបើក Chrome!")
        self.show_error(err_msg)

    def extract_srt_from_chrome(self):
        if not self.selenium_driver:
            self.show_error("សូមបើក Chrome ជាមុនសិន!")
            return
        self.gemini_worker = GeminiSeleniumWorker(self.selenium_driver)
        self.gemini_worker.finished_signal.connect(self.on_srt_extracted)
        self.gemini_worker.error_signal.connect(self.show_error)
        self.gemini_worker.start()

    def on_srt_extracted(self, response_text):
        subtitles = parse_srt_content(response_text)
        if subtitles:
            self.populate_subtitles(subtitles)
            self.show_dialog("ជោគជ័យ", f"ទទួលបាន {len(subtitles)} Subtitles ពី Gemini!", "success")
        else:
            self.show_error("ពុំមានទិន្នន័យ SRT ត្រឹមត្រូវនៅក្នុង Gemini Response ឡើយ!")

    # ================= PHASE 2: AUDIO GENERATION WITH CHARACTER VOICES =================
    def start_audio_generation(self):
        row_count = self.table_subtitles.rowCount()
        if row_count == 0:
            self.show_error("សូមបញ្ជូល Subtitle ជាមុនសិន!")
            return

        table_data = []
        for row in range(row_count):
            start_str = self.table_subtitles.item(row, 1).text()
            end_str = self.table_subtitles.item(row, 2).text()
            text = self.table_subtitles.item(row, 3).text()
            combo = self.table_subtitles.cellWidget(row, 4)
            
            selected_voice_name = combo.currentText() if combo else "សំឡេងប្រុសធម្មតា"
            prof = VOICE_PROFILES.get(selected_voice_name, VOICE_PROFILES["សំឡេងប្រុសធម្មតា"])

            table_data.append({
                'index': row,
                'start_sec': time_to_seconds(start_str),
                'end_sec': time_to_seconds(end_str),
                'text': text,
                'voice_code': prof['voice'],
                'pitch': prof['pitch'],
                'rate': prof['rate'],
                'is_thought': prof['is_thought']
            })

        self.progress_bar.setValue(0)
        self.audio_gen_thread = AudioGenThread(table_data)
        
        self.audio_gen_thread.item_started_signal.connect(self.on_tts_item_started)
        self.audio_gen_thread.item_completed_signal.connect(self.on_tts_item_completed)
        self.audio_gen_thread.progress_signal.connect(lambda current, total: self.progress_bar.setValue(int(current / total * 100)))
        self.audio_gen_thread.finished_signal.connect(lambda: self.show_dialog("ជោគជ័យ", "បង្កើតសំឡេង AI គ្រប់តួអង្គ (Pitch & Reverb) រួចរាល់!", "success"))
        
        self.audio_gen_thread.start()

    def on_tts_item_started(self, row_idx):
        status_item = QTableWidgetItem("⏳ កំពុងបង្កើត...")
        status_item.setForeground(QColor("#FFEA00"))
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_subtitles.setItem(row_idx, 5, status_item)

    def on_tts_item_completed(self, row_idx, success):
        if success:
            status_item = QTableWidgetItem("✅ រួចរាល់")
            status_item.setForeground(QColor("#00FF99"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_subtitles.setItem(row_idx, 5, status_item)
        else:
            retry_widget = RetryStatusWidget(row_idx, self.handle_single_row_retry)
            self.table_subtitles.setCellWidget(row_idx, 5, retry_widget)

    def handle_single_row_retry(self, row_index, callback_ui_update):
        start_str = self.table_subtitles.item(row_index, 1).text()
        end_str = self.table_subtitles.item(row_index, 2).text()
        text = self.table_subtitles.item(row_index, 3).text()
        combo = self.table_subtitles.cellWidget(row_index, 4)
        
        selected_voice_name = combo.currentText() if combo else "សំឡេងប្រុសធម្មតា"
        prof = VOICE_PROFILES.get(selected_voice_name, VOICE_PROFILES["សំឡេងប្រុសធម្មតា"])

        item_data = {
            'index': row_index,
            'start_sec': time_to_seconds(start_str),
            'end_sec': time_to_seconds(end_str),
            'text': text,
            'voice_code': prof['voice'],
            'pitch': prof['pitch'],
            'rate': prof['rate'],
            'is_thought': prof['is_thought']
        }

        signals = WorkerSignals()
        signals.finished.connect(callback_ui_update)

        def worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(generate_single_tts_async(item_data))
            signals.finished.emit(success)

        threading.Thread(target=worker, daemon=True).start()

    # ================= PHASE 3: BATCH EXPORT QUEUE =================
    def open_batch_export_queue(self):
        if self.current_video_path and not any(q['video_path'] == self.current_video_path for q in self.export_queue):
            clean_name, _ = os.path.splitext(os.path.basename(self.current_video_path))
            out_p = os.path.join(EXPORT_DIR, f"{clean_name}_Dubbed.mp4")
            self.export_queue.append({
                'video_path': self.current_video_path,
                'output_path': out_p,
                'resolution': self.combo_resolution.currentText(),
                'status': '⏳ រង់ចាំ'
            })

        dlg = BatchExportQueueDialog(self.export_queue, self.start_batch_queue_rendering, self)
        dlg.exec()

    def start_batch_queue_rendering(self):
        if not self.export_queue:
            return
        self.lbl_download_status.setText("🚀 កំពុងដំណើរការ Batch Export Queue...")
        self.run_next_queue_item()

    def run_next_queue_item(self):
        next_job = None
        for job in self.export_queue:
            if job['status'] == '⏳ រង់ចាំ':
                next_job = job
                break

        if not next_job:
            self.lbl_download_status.setText("✅ បានបញ្ចប់ការ Render ក្នុង Queue ទាំងអស់!")
            self.show_dialog("ជោគជ័យ", "បានបញ្ចប់ការ Export វីដេអូទាំងអស់ក្នុង Queue!", "success")
            return

        next_job['status'] = '⏳ កំពុង Render...'
        self.current_queue_job = next_job
        self.execute_export_job(next_job['video_path'], next_job['output_path'], is_queue=True)

    # ================= EXPORT VIDEO LOGIC =================
    def start_video_export(self):
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            self.show_error("សូមបញ្ជូលវីដេអូជាមុនសិន!")
            return

        base_name = os.path.basename(self.current_video_path)
        clean_name, _ = os.path.splitext(base_name)

        existing_files = glob.glob(os.path.join(EXPORT_DIR, "*.mp4"))
        next_seq = len(existing_files) + 1
        
        default_export_filename = f"{next_seq:02d}_{clean_name}_Dubbed.mp4"
        default_export_path = os.path.join(EXPORT_DIR, default_export_filename)

        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "រក្សាទុកវីដេអូនាំចេញ (Export)", 
            default_export_path, 
            "Video Files (*.mp4)"
        )
        
        if not save_path:
            return

        self.execute_export_job(self.current_video_path, save_path, is_queue=False)

    def execute_export_job(self, input_video_path, save_path, is_queue=False):
        self.progress_bar.setValue(0)
        row_count = self.table_subtitles.rowCount()
        table_data = []
        subtitles_data = []

        for row in range(row_count):
            start_str = self.table_subtitles.item(row, 1).text()
            end_str = self.table_subtitles.item(row, 2).text()
            text_str = self.table_subtitles.item(row, 3).text()

            table_data.append({
                'index': row,
                'start_sec': time_to_seconds(start_str),
                'end_sec': time_to_seconds(end_str),
            })
            subtitles_data.append({
                'start': start_str,
                'end': end_str,
                'text': text_str
            })

        bg_vol_percent = self.slider_bg_music_vol.value()
        selected_aspect = self.combo_aspect_ratio.currentText()
        selected_res = self.combo_resolution.currentText()
        video_title = self.txt_video_title.text()

        title_nx = self.video_widget.title_norm_x
        title_ny = self.video_widget.title_norm_y
        logo_nx = self.video_widget.logo_norm_x
        logo_ny = self.video_widget.logo_norm_y
        logo_nw = self.video_widget.logo_norm_w
        final_font_size = self.video_widget.title_font_size

        sub_ny = self.video_widget.sub_norm_y
        sub_col = self.sub_color_hex
        sub_ff = self.sub_font_family
        sub_fs = self.sub_font_size

        # Bypass Settings
        anti_detect = self.chk_anti_detect.isChecked()
        flip_h = self.chk_flip.isChecked()
        crop_z = self.chk_crop.isChecked()
        col_g = self.chk_color.isChecked()
        spd_s = self.chk_speed.isChecked()

        # Circle/Ellipse Blur Settings
        enable_blur = self.chk_blur.isChecked()
        blur_nx = self.video_widget.blur_norm_x
        blur_ny = self.video_widget.blur_norm_y
        blur_nw = self.video_widget.blur_norm_w
        blur_nh = self.video_widget.blur_norm_h
        blur_st = self.blur_strength_val
        blur_tint = self.blur_tint_hex
        blur_top = self.blur_tint_opacity_val

        # PHASE 2: Audio Ducking Configuration
        enable_ducking = self.chk_audio_ducking.isChecked()
        duck_choice = self.combo_ducking_level.currentText()
        duck_db = 14
        if "-8" in duck_choice:
            duck_db = 8
        elif "-18" in duck_choice:
            duck_db = 18

        # PHASE 3: GPU Encoder Selection
        encoder_choice = self.combo_encoder.currentText()
        encode_preset = self.combo_enc_preset.currentText()

        self.export_thread = ExportVideoThread(
            input_video_path, table_data, subtitles_data, save_path, 
            bg_music_vol_percent=bg_vol_percent, aspect_ratio=selected_aspect, resolution=selected_res,
            video_title=video_title, title_norm_x=title_nx, title_norm_y=title_ny,
            title_color=self.title_color_hex, title_font_family=self.title_font_family, title_font_size=final_font_size,
            logo_path=self.selected_logo_path, logo_norm_x=logo_nx, logo_norm_y=logo_ny, logo_norm_w=logo_nw,
            sub_norm_y=sub_ny, sub_color=sub_col, sub_font_family=sub_ff, sub_font_size=sub_fs,
            anti_detect=anti_detect, flip_horizontal=flip_h, crop_zoom=crop_z, color_grade=col_g, speed_shift=spd_s,
            enable_blur=enable_blur, blur_norm_x=blur_nx, blur_norm_y=blur_ny, blur_norm_w=blur_nw, blur_norm_h=blur_nh,
            blur_strength=blur_st, blur_tint=blur_tint, blur_tint_opacity=blur_top,
            enable_audio_ducking=enable_ducking, ducking_reduction_db=duck_db,
            encoder_choice=encoder_choice, encode_preset=encode_preset
        )
        self.export_thread.progress_signal.connect(self.progress_bar.setValue)
        
        if is_queue:
            self.export_thread.finished_signal.connect(self.on_queue_item_finished)
            self.export_thread.error_signal.connect(self.on_queue_item_error)
        else:
            self.export_thread.finished_signal.connect(self.on_export_finished)
            self.export_thread.error_signal.connect(self.show_error)

        self.export_thread.start()

    def on_queue_item_finished(self, out_path):
        if hasattr(self, 'current_queue_job') and self.current_queue_job:
            self.current_queue_job['status'] = '✅ រួចរាល់'
        self.run_next_queue_item()

    def on_queue_item_error(self, err_msg):
        if hasattr(self, 'current_queue_job') and self.current_queue_job:
            self.current_queue_job['status'] = '❌ បរាជ័យ'
        self.show_error(err_msg)
        self.run_next_queue_item()

    def on_export_finished(self, output_path):
        self.show_dialog(
            "ជោគជ័យ", 
            f"នាំចេញវីដេអូរួចរាល់ដោយជោគជ័យ!\n• Audio Ducking: សកម្ម\n• GPU Acceleration: បានអនុវត្ត\n\nរក្សាទុកក្នុង៖\n{output_path}", 
            "success"
        )

    def merge_all_dubbed_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "ជ្រើសរើសវីដេអូដែលចង់ Merge ចូលគ្នា (យ៉ាងហោច ២ វីដេអូ)", 
            EXPORT_DIR, 
            "Video Files (*.mp4 *.mkv *.avi)"
        )
        if not files or len(files) < 2:
            self.show_error("សូមជ្រើសរើសយ៉ាងតិច ២ វីដេអូឡើងទៅដើម្បីច្របាច់បញ្ចូលគ្នា!")
            return

        default_merge_path = os.path.join(EXPORT_DIR, f"Full_Movie_Merged_{int(time.time())}.mp4")
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "រក្សាទុកវីដេអូដែល Merge រួច", 
            default_merge_path, 
            "Video Files (*.mp4)"
        )
        if not save_path:
            return

        self.progress_bar.setValue(0)
        self.lbl_download_status.setText("⏳ កំពុង Merge វីដេអូទាំងអស់បញ្ចូលគ្នា...")
        self.merge_thread = MergeVideosThread(files, save_path)
        self.merge_thread.progress_signal.connect(self.progress_bar.setValue)
        self.merge_thread.finished_signal.connect(self.on_merge_completed_and_preview)
        self.merge_thread.error_signal.connect(self.show_error)
        self.merge_thread.start()

    def on_merge_completed_and_preview(self, output_path):
        clean_path = os.path.abspath(os.path.normpath(output_path))
        if not os.path.exists(clean_path):
            self.show_error(f"រកមិនឃើញ File វីដេអូដែលបាន Merge៖\n{clean_path}")
            return

        fname = os.path.basename(clean_path)
        self.lbl_download_status.setText(f"✅ Merge រួចរាល់៖ {fname}")
        
        self.combo_series_episodes.blockSignals(True)
        if clean_path in self.downloaded_series_list:
            self.downloaded_series_list.remove(clean_path)
        self.downloaded_series_list.insert(0, clean_path)
        
        self.combo_series_episodes.insertItem(0, f"🎬 វីដេអូរួម (Full Movie): {fname}", clean_path)
        self.combo_series_episodes.setCurrentIndex(0)
        self.combo_series_episodes.blockSignals(False)
        
        self.set_active_video(clean_path)
        self.media_player.setPosition(0)
        self.media_player.play()
        self.btn_play_pause.setText("⏸ ផ្អាក (Space)")

        self.show_dialog(
            "ជោគជ័យ", 
            f"Merge វីដេអូទាំងអស់បញ្ចូលគ្នារួចរាល់ និងបានចាក់បង្ហាញលើអេក្រង់ស្វ័យប្រវត្តិ!\n\nរក្សាទុកក្នុង៖\n{clean_path}", 
            "success"
        )

    # Player Controls
    def toggle_play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.tts_player.pause()
            self.btn_play_pause.setText("▶ លេង (Space)")
        else:
            self.media_player.play()
            self.btn_play_pause.setText("⏸ ផ្អាក (Space)")

    def stop_video(self):
        self.media_player.stop()
        self.tts_player.stop()
        self.tts_player.setSource(QUrl())
        self.current_subtitle_row = -1
        self.btn_play_pause.setText("▶ លេង (Space)")

    def toggle_orig_mute(self):
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        self.btn_mute_orig.setText("🔇 សំឡេងដើម" if not is_muted else "🔊 សំឡេងដើម")

    def toggle_tts_mute(self):
        is_muted = self.tts_audio_output.isMuted()
        self.tts_audio_output.setMuted(not is_muted)
        self.btn_mute_tts.setText("🔇 សំឡេង AI" if not is_muted else "🎙️ សំឡេង AI")

    def set_video_position(self, position):
        self.media_player.setPosition(position)

    def on_position_changed(self, position):
        self.slider_video.setValue(position)
        self.timeline_strip.set_current_position(position)
        sec_pos = position / 1000.0

        current_text = ""
        current_row = -1
        for row in range(self.table_subtitles.rowCount()):
            s_sec = time_to_seconds(self.table_subtitles.item(row, 1).text())
            e_sec = time_to_seconds(self.table_subtitles.item(row, 2).text())
            if s_sec <= sec_pos <= e_sec:
                current_text = self.table_subtitles.item(row, 3).text()
                current_row = row
                break

        if current_text:
            clean_sub = clean_text_for_tts(current_text)
            self.video_widget.set_subtitle(clean_sub)
        else:
            self.video_widget.set_subtitle("")

        if current_row != -1:
            if current_row != self.current_subtitle_row:
                self.current_subtitle_row = current_row
                
                self.tts_player.stop()
                self.tts_player.setSource(QUrl())
                
                v_file = temp_path(f"temp_voice_{current_row}.mp3")
                if os.path.exists(v_file) and os.path.getsize(v_file) > 0:
                    self.tts_player.setSource(QUrl.fromLocalFile(v_file))
                    self.tts_player.play()
        else:
            if self.current_subtitle_row != -1:
                self.tts_player.stop()
                self.tts_player.setSource(QUrl())
                self.current_subtitle_row = -1

        dur = self.media_player.duration()
        self.lbl_time.setText(f"{self.format_time(position)} / {self.format_time(dur)}")

    def on_duration_changed(self, duration):
        self.slider_video.setRange(0, duration)
        self.timeline_strip.set_duration(duration)

    def on_table_cell_clicked(self, row, col):
        start_str = self.table_subtitles.item(row, 1).text()
        sec = time_to_seconds(start_str)
        self.media_player.setPosition(int(sec * 1000))

    def on_media_error(self, error, error_string):
        if error_string and "ResourceError" in str(error):
            return
        if error_string:
            print(f"Media Player Notice: {error_string}")

    def format_time(self, ms):
        seconds = int(ms / 1000)
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def show_error(self, err):
        msg = str(err).strip() if err else ""
        if not msg:
            msg = "កើតមានកំហុសមិនច្បាស់លាស់!"
        self.show_dialog("កំហុស", msg, "error")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartVideoEditor()
    window.show()
    sys.exit(app.exec())
