import os, re, io, json, math, urllib.parse, asyncio, subprocess, requests
from PIL import Image, ImageDraw, ImageEnhance
import edge_tts

TITLE = os.environ.get("SHORTS_TITLE", "지니어스만 맞추는 레전드 아재 퀴즈")
QUESTION = os.environ.get("SHORTS_QUESTION", "세상에서 가장 가난한 왕은?")
ANSWER = os.environ.get("SHORTS_ANSWER", "최저임금")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
VOICE = "ko-KR-InJoonNeural"

async def generate_tts(text, raw_file, final_file, rate="+16%", end_pad=0.12):
    await edge_tts.Communicate(text, VOICE, rate=rate, pitch="-1Hz", volume="+12%").save(raw_file)
    af = f"silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,areverse,apad=pad_dur={end_pad}"
    subprocess.run(["ffmpeg", "-y", "-i", raw_file, "-af", af, "-c:a", "libmp3lame", "-q:a", "2", final_file], check=True)

def get_duration(filename):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename]
    return float(subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)

def wrap_text(text, max_chars=11):
    words, lines, current = text.split(), [], ""
    for w in words:
        if len(current) + len(w) + 1 <= max_chars: current = (current + " " + w).strip()
        else: lines.append(current); current = w
    if current: lines.append(current)
    return "\n".join(lines)

def get_caricature_data(question, answer):
    dq = "funny exaggerated 2d caricature cartoon of a bewildered person scratching head colorful background no text"
    dc = "funny exaggerated 2d caricature cartoon of a nervous detective holding giant ticking clock colorful background no text"
    da = "funny exaggerated 2d caricature cartoon of a hilarious laughing character with lightbulb idea colorful background no text"
    q_hex, a_hex = "1f914", "1f606"
    if not GEMINI_KEY: return dq, dc, da, q_hex, a_hex
    try:
        url = f"https://googleapis.com{GEMINI_KEY}"
        prompt = f"Korean riddle: '{question}', Answer: '{answer}'. 1) Write 3 simple English descriptions (letters and spaces ONLY) for funny exaggerated 2D caricature cartoon illustrations: 'q' (riddle character), 'c' (nervous detective with clock), 'a' (punchline answer character). 2) Also pick 2 lowercase Unicode hex emoji codes ('q_hex', 'a_hex') matching the riddle and answer objects. Return ONLY JSON: {{\"q\": \"...\", \"c\": \"...\", \"a\": \"...\", \"q_hex\": \"...\", \"a_hex\": \"...\"}}"
        resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15).json()
        first_cand = resp.get("candidates", [{}]).pop(0)
        first_part = first_cand.get("content", {}).get("parts", [{}]).pop(0)
        txt = first_part.get("text", "").replace("```json", "").replace("```", "").strip()
        d = json.loads(txt)
        clean = lambda s: re.sub(r'[^a-zA-Z0-9 ]', '', s)
        return clean(d.get("q", dq)), clean(d.get("c", dc)), clean(d.get("a", da)), d.get("q_hex", "1f914").lower(), d.get("a_hex", "1f606").lower()
    except Exception as e:
        print("프롬프트 생성 예외:", e, flush=True)
        return dq, dc, da, q_hex, a_hex

def fetch_openmoji(hex_code, size=500):
    for code in (hex_code, "1f604"):
        try:
            url = f"https://githubusercontent.com{code.upper()}.png"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return Image.open(io.BytesIO(r.content)).convert("RGBA").resize((size, size), Image.LANCZOS)
        except Exception:
            pass
    return None

def fetch_caricature(prompt_words, hex_code, theme, out_path):
    style = "funny exaggerated 2d caricature illustration expressive big head cartoon art vibrant colors clean outlines no text"
    full = f"{prompt_words} {style}"
    encoded = urllib.parse.quote(full)
    seed = abs(hash(full + theme)) % 999999
    for attempt in range(2):
        try:
            url = f"https://pollinations.ai{encoded}?width=768&height=1344&model=flux&nologo=true&seed={seed + attempt}"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"}, timeout=50)
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", "") and len(r.content) > 15000:
                img = Image.open(io.BytesIO(r.content)).convert("RGB").resize((1080, 1920), Image.LANCZOS)
                ImageEnhance.Brightness(img).enhance(0.90).save(out_path, quality=92)
                print(f"2D 캐리커쳐 AI 이미지 생성 성공: {out_path}", flush=True)
                return True
        except Exception as e:
            print(f"AI 캐리커쳐 재시도({attempt+1}):", e, flush=True)
    w, h = 1080, 1920
    pal = {"q": ((36, 59, 85), (20, 30, 48)), "c": ((142, 45, 226), (74, 0, 224)), "a": ((17, 153, 142), (56, 239, 125))}
    c1, c2 = pal[theme]
    r1, g1, b1 = c1
    r2, g2, b2 = c2
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        draw.line([(0, y), (w, y)], fill=(int(r1+(r2-r1)*y/h), int(g1+(g2-g1)*y/h), int(b1+(b2-b1)*y/h), 255))
    cx, cy = 540, 1050
    for deg in range(0, 360, 15):
        rad1, rad2 = math.radians(deg), math.radians(deg + 7)
        draw.polygon([(cx, cy), (cx + int(1400*math.cos(rad1)), cy + int(1400*math.sin(rad1))), (cx + int(1400*math.cos(rad2)), cy + int(1400*math.sin(rad2)))], fill=(255, 255, 255, 25))
    draw.ellipse([cx-310, cy-310, cx+310, cy+310], fill=(255, 255, 255, 50), outline=(255, 255, 255, 130), width=8)
    icon = fetch_openmoji(hex_code, 480)
    if icon:
        img.paste(icon, (cx-240, cy-240), icon)
    ImageEnhance.Brightness(img.convert("RGB")).enhance(0.92).save(out_path, quality=92)
    print(f"캐리커쳐 백업 캐릭터 합성 완료: {out_path}", flush=True)
    return False

async def main():
    qp, cp, ap, q_hex, a_hex = get_caricature_data(QUESTION, ANSWER)
    fetch_caricature(qp, q_hex, "q", "bg_q.jpg")
    fetch_caricature(cp, "23f0", "c", "bg_c.jpg")
    fetch_caricature(ap, a_hex, "a", "bg_a.jpg")
    spoken_ans = re.sub(r'\([^)]*\)', '', ANSWER).strip() or ANSWER
    await generate_tts(f"{QUESTION}", "q_raw.mp3", "q.mp3", rate="+16%", end_pad=0.12)
    await generate_tts("과연 정답은 삼 이 일", "c_raw.mp3", "c.mp3", rate="+18%", end_pad=0.10)
    await generate_tts(f"정답은 바로 {spoken_ans}", "a_raw.mp3", "a.mp3", rate="+16%", end_pad=0.15)
    await generate_tts("재밌었다면 구독과 좋아요 부탁드려요", "s_raw.mp3", "s.mp3", rate="+16%", end_pad=0.25)

    d_q, d_c, d_a, d_s = get_duration("q.mp3"), get_duration("c.mp3"), get_duration("a.mp3"), get_duration("s.mp3")
    t1, t2, t3, total_dur = d_q, d_q + d_c, d_q + d_c + d_a, d_q + d_c + d_a + d_s

    with open("concat.txt", "w") as f:
        f.write("file 'q.mp3'\nfile 'c.mp3'\nfile 'a.mp3'\nfile 's.mp3'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "raw_audio.mp3"], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", "raw_audio.mp3", "-filter:a", "loudnorm=I=-15:TP=-1.5:LRA=11", "full_audio.mp3"], check=True)

    font_path = next((p for p in ["/usr/share/fonts/truetype/nanum/NanumSquareRoundEB.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"] if os.path.exists(p)), "")
    with open("title.txt", "w", encoding="utf-8") as f: f.write(TITLE.replace("#Shorts", "").replace("#넌센스퀴즈", "").strip()[:15])
    with open("question.txt", "w", encoding="utf-8") as f: f.write(wrap_text(QUESTION, 11))
    with open("answer.txt", "w", encoding="utf-8") as f: f.write(f"정답 : {wrap_text(ANSWER, 10)}")
    with open("sub.txt", "w", encoding="utf-8") as f: f.write("재밌었다면 구독 & 좋아요 부탁드려요!")

    vf = (
        f"[0:v]scale=1080:1920,setsar=1[bg0];[1:v]scale=1080:1920,setsar=1[bg1];[2:v]scale=1080:1920,setsar=1[bg2];"
        f"[bg0][bg1]overlay=enable='between(t,{t1},{t2})'[tmp1];[tmp1][bg2]overlay=enable='gte(t,{t2})'[bg];"
        f"[bg]drawbox=x=80:y=180:w=920:h=120:color=#FFD600:t=fill,"
        f"drawtext=fontfile={font_path}:textfile=title.txt:fontcolor=#111111:fontsize=56:x=(w-text_w)/2:y=212,"
        f"drawbox=x=60:y=330:w=960:h=410:color=#0D1117@0.65:t=fill,"
        f"drawbox=x=60:y=330:w=960:h=410:color=#FFD600@0.9:t=4,"
        f"drawtext=fontfile={font_path}:text='Q.':fontcolor=#FFD600:fontsize=80:borderw=5:bordercolor=black:x=(w-text_w)/2:y=355,"
        f"drawtext=fontfile={font_path}:textfile=question.txt:fontcolor=white:fontsize=82:borderw=6:bordercolor=black:x=(w-text_w)/2:y=465:line_spacing=20,"
        f"drawtext=fontfile={font_path}:text='3... 2... 1...':fontcolor=#00E5FF:fontsize=115:borderw=7:bordercolor=black:x=(w-text_w)/2:y=1360:enable='between(t,{t1},{t2})',"
        f"drawbox=x=90:y=1380:w=900:h=210:color=#0D1117@0.85:t=fill:enable='gte(t,{t2})',"
        f"drawbox=x=90:y=1380:w=900:h=210:color=#00E676:t=5:enable='gte(t,{t2})',"
        f"drawtext=fontfile={font_path}:textfile=answer.txt:fontcolor=#00E676:fontsize=82:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1445:line_spacing=18:enable='gte(t,{t2})',"
        f"drawbox=x=80:y=1630:w=920:h=105:color=#FF1744@0.92:t=fill:enable='gte(t,{t3})',"
        f"drawtext=fontfile={font_path}:textfile=sub.txt:fontcolor=white:fontsize=46:borderw=3:bordercolor=black:x=(w-text_w)/2:y=1660:enable='gte(t,{t3})'"
    )
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", f"{total_dur}", "-i", "bg_q.jpg", "-loop", "1", "-t", f"{total_dur}", "-i", "bg_c.jpg", "-loop", "1", "-t", f"{total_dur}", "-i", "bg_a.jpg", "-i", "full_audio.mp3", "-filter_complex", vf, "-t", f"{total_dur}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "output.mp4"], check=True)
    print("쇼츠 렌더링 완료: output.mp4", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
