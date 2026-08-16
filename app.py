@app.post("/api/generate-auto-tts")
async def api_generate_auto_tts(text_content: str = Form(...)):
    if not AudioSegment:
        return {"detail": "pydub not installed"}

    lines = text_content.split('\n')
    combined_audio = AudioSegment.silent(duration=500)
    success_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # រំលងលេខលំដាប់ SRT និងម៉ោងដោយសុវត្ថិភាព
        if line.isdigit() or "-->" in line or "-->" in line.replace(" ", ""):
            continue
        
        voice_code, is_thought = detect_voice_and_thought(line)
        
        # លុបចោល Tags ផ្សេងៗដូចជា [សំឡេងប្រុស], [សំឡេងស្រី], ម៉ោង ឬលេខកូដផ្សេងៗ
        clean_text = re.sub(r"\[.*?\]|\(.*?\)", "", line).strip()
        if not clean_text or len(clean_text) < 2:
            continue

        temp_audio_file = os.path.join(TEMP_DIR, f"temp_{id(line)}_{success_count}.mp3")
        try:
            communicate = edge_tts.Communicate(clean_text, voice_code)
            await communicate.save(temp_audio_file)
            
            if os.path.exists(temp_audio_file) and os.path.getsize(temp_audio_file) > 100:
                segment = AudioSegment.from_file(temp_audio_file)
                if is_thought:
                    segment = add_reverb_thought_effect(segment)
                
                combined_audio += segment + AudioSegment.silent(duration=300)
                success_count += 1
        except Exception as e:
            print(f"Skipping line due to TTS error: {e}")
            continue

    if success_count == 0:
        return {"detail": "No valid text found to generate speech"}

    output_file = os.path.join(TEMP_DIR, "final_auto_dubbed.mp3")
    combined_audio.export(output_file, format="mp3", bitrate="320k")
    return FileResponse(output_file, media_type="audio/mp3", filename="auto_dubbed.mp3")
