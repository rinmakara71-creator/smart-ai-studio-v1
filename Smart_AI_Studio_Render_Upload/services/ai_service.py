import os
import re
import json

SYSTEM_INSTRUCTION = """ចាប់ពីពេលនេះតទៅ សូមអ្នកដើរតួជា អ្នកបកប្រែខ្សែភាពយន្តនិងរឿងភាគអាជីព (Expert Subtitler & Dubbing Translator)។ ភារកិច្ចចម្បងរបស់អ្នកគឺទាញយកសំឡេងសន្ទនាពីវីដេអូដែលខ្ញុំបានភ្ជាប់ ឬបកប្រែរាល់អត្ថបទដែលខ្ញុំផ្តល់ឲ្យ មកជាភាសាខ្មែរឲ្យបានស្តង់ដារបំផុត ដោយផ្តោតសំខាន់លើ'ភាសានិយាយ' ដែលរលូន ស៊ីអារម្មណ៍ និងត្រូវសំឡេងតួអង្គ ១០០%។

សូមអនុវត្តតាមច្បាប់ទាំង ៤ នេះយ៉ាងតឹងរ៉ឹង៖
1. ភាសានិយាយធម្មជាតិ (Natural Spoken Language): ហាមដាច់ខាតការបកប្រែតាមបែបសរសេរស្ងួតៗ។ ត្រូវប្រើប្រាស់ពាក្យពេចន៍ដែលប្រជាជនខ្មែរនិយមនិយាយប្រចាំថ្ងៃ (ណា, ណ៎, ហ្មង, តើ, អញ្ចឹង, វើយ, ហាស, ចា៎)។
2. ត្រូវសំឡេងតួអង្គនិយាយ (Match the actor's voice): ប្រើសព្វនាមហៅគ្នា (បង/អូន, ឯង/អញ, ខ្ញុំ/លោក, ពួកម៉ាក, អា...) ឲ្យត្រូវនឹងអាយុនិងឋានៈតួអង្គ។
3. បញ្ចេញមនោសញ្ចេតនា (Emotional Depth): អានការបកប្រែរួច ត្រូវតែមានអារម្មណ៍ត្រូវនឹងសាច់រឿងដើម។
4. ទម្រង់លទ្ធផល (Output Format): ផ្តល់មកជាទម្រង់ SRT នៅក្នុង Code Block។
បញ្ជាក់ប្រយោគស្រីប្រុសដោយសញ្ញា [សំឡេងស្រី] ឬ [សំឡេងប្រុស] និងប្រយោគគិតក្នុងចិត្តដោយសញ្ញា [សំឡេងគិតស្រី] [សំឡេងគិតប្រុស] នៅដើមបន្ទាត់នីមួយៗ។"""


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


def time_to_seconds(time_str: str) -> float:
    try:
        parts = time_str.replace(',', '.').split(':')
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except Exception:
        return 0.0
    return 0.0


def seconds_to_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"


def parse_srt_content(content: str):
    if not content:
        return []
    # Strip UTF-8 BOM and markdown code blocks
    clean_content = content.replace("\ufeff", "").replace("\u200b", "").strip()
    clean_content = re.sub(r"```[a-zA-Z]*", "", clean_content).replace("```", "").strip()
    clean_content = clean_content.replace("\r\n", "\n").replace("\r", "\n")

    subtitles = []
    
    # Standard and flexible regex matching
    pattern = re.compile(
        r'(?:(?P<index>\d+)\s*\n)?'
        r'(?P<start>\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[.,]\d{1,3})'
        r'(?:[^\n]*\n)'
        r'(?P<text>[\s\S]*?)(?=\n\s*\n|\Z)',
        re.MULTILINE
    )
    
    for m in pattern.finditer(clean_content):
        text = m.group('text').strip().replace('\n', ' ')
        if not text:
            continue
        start = m.group('start').replace('.', ',')
        end = m.group('end').replace('.', ',')
        gender = detect_gender_from_text(text)
        subtitles.append({
            'index': len(subtitles),
            'start': start,
            'end': end,
            'start_sec': time_to_seconds(start),
            'end_sec': time_to_seconds(end),
            'text': text,
            'gender': gender,
            'voice': "km-KH-SreymomNeural" if "female" in gender else "km-KH-PisethNeural",
            'is_thought': "thought" in gender
        })

    if not subtitles:
        blocks = re.split(r'\n\s*\n', clean_content)
        for block in blocks:
            lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
            if len(lines) >= 1:
                for idx, line in enumerate(lines):
                    if '-->' in line:
                        times = line.split('-->')
                        start = times[0].strip().replace('.', ',')
                        end = times[1].strip().replace('.', ',')
                        text = " ".join(lines[idx + 1:]).strip()
                        if text:
                            gender = detect_gender_from_text(text)
                            subtitles.append({
                                'index': len(subtitles),
                                'start': start,
                                'end': end,
                                'start_sec': time_to_seconds(start),
                                'end_sec': time_to_seconds(end),
                                'text': text,
                                'gender': gender,
                                'voice': "km-KH-SreymomNeural" if "female" in gender else "km-KH-PisethNeural",
                                'is_thought': "thought" in gender
                            })
                        break
    return subtitles



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
   - ផ្តល់លទ្ធផលជាទម្រង់ SRT ស្តង់ដារនៅក្នុង Code Block តែមួយគត់។"""


async def translate_with_gemini(text_or_prompt: str, api_key: str = None) -> str:
    """
    Translates or generates SRT using Gemini API if key is provided.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("សូមបញ្ចូល Gemini API Key ដើម្បីប្រើប្រាស់មុខងារបកប្រែ AI ដោយស្វ័យប្រវត្តិ!")

    try:
        from google import genai
        client = genai.Client(api_key=key)
        
        prompt = f"{SYSTEM_INSTRUCTION}\n\nអត្ថបទដែលត្រូវបកប្រែ៖\n{text_or_prompt}"
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        raise RuntimeError(f"កំហុសក្នុងការទាក់ទងទៅកាន់ Gemini API: {str(e)}")


async def recap_with_gemini(text_or_prompt: str, api_key: str = None) -> str:
    """
    Generates Movie Recap SRT containing key highlights using Gemini API.
    """

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("សូមបញ្ចូល Gemini API Key ដើម្បីប្រើប្រាស់មុខងារសម្រាយរឿង AI!")

    try:
        from google import genai
        client = genai.Client(api_key=key)
        
        prompt = f"{RECAP_SYSTEM_INSTRUCTION}\n\nព័ត៌មាន/សាច់រឿង ឬអត្ថបទដើមនៃវីដេអូ៖\n{text_or_prompt}"
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        raise RuntimeError(f"កំហុសក្នុងការទាក់ទងទៅកាន់ Gemini Recap API: {str(e)}")

