import os, re, json, base64, urllib.parse, asyncio, subprocess, requests
from PIL import Image, ImageEnhance
import edge_tts

TITLE = os.environ.get("SHORTS_TITLE", "지니어스만 맞추는 레전드 아재 퀴즈")
QUESTION = os.environ.get("SHORTS_QUESTION", "세상에서 가장 가난한 왕은?")
ANSWER = os.environ.get("SHORTS_ANSWER", "최저임금")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
VOICE = "ko-KR-InJoonNeural"

async def generate_tts(text, raw_file, final_file, rate="+15%", pad=0.25):
    await edge_tts.Communicate(text, VOICE, rate=rate, pitch="-1Hz", volume="+12%").save(raw_file)
    subprocess.run(["ffmpeg", "-y", "-i", raw_file, "-af", f"apad=pad_dur={pad}", "-c:a", "libmp3lame", "-q:a", "2", final_file], check=True)

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

def generate_scene_prompts(question, answer):
    dq = "cute sad king character with empty pockets, 2d korean webtoon flat cartoon illustration, no text"
    dc = "cute nervous detective character looking at a ticking clock, suspenseful funny 2d korean webtoon flat cartoon illustration, no text"
    da = "cute coin character turning an empty wallet upside down, humorous punchline 2d korean webtoon flat cartoon illustration, no text"
    if not GEMINI_KEY: return dq, dc, da
    try:
        url = f"https://googleapis.com{GEMINI_KEY}"
        sys_prompt = f"Korean dad joke riddle: '{question}', Answer: '{answer}'. Create 3 short English image prompts for cute 2D Korean webtoon flat vector cartoon illustrations (strictly NO text/letters). 1) 'q_prompt': humorous cute character illustrating the riddle setup. 2) 'c_prompt': cute nervous detective character with a ticking clock waiting for the answer. 3) 'a_prompt': funny cute character illustrating the wordplay answer. Return ONLY valid JSON: {{\"q_prompt\": \"...\", \"c_prompt\": \"...\", \"a_prompt\": \"...\"}}"
        resp = requests.post(url, json={"contents": [{"parts": [{"text": sys_prompt}]}]}, timeout=25).json()
        txt = resp["candidates"][0]["content"]["parts"][0]["text"].replace("```json", "").replace("```", "").strip()
        p = json.loads(txt)
        return p.get("q_prompt", dq), p.get("c_prompt", dc), p.get("a_prompt", da)
    except Exception as e:
        print("프롬프트 생성 예외:", e)
        return dq, dc, da

def fetch_cartoon_image(prompt, out_path, fallback_color):
    full_prompt = f"{prompt}, cute 2D Korean webtoon flat vector cartoon art style, bright vibrant colors, clean outlines, vertical 9:16 composition, strictly no text, no letters, no words"
    if GEMINI_KEY:
        for m in ["gemini-2.5-flash-image", "gemini-2.0-flash-preview-image-generation", "gemini-2.0-flash-exp-image-generation"]:
            try:
                url = f"https://googleapis.com{m}:generateContent?key={GEMINI_KEY}"
                resp = requests.post(url, json={"contents": [{"parts": [{"text": full_prompt}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}, timeout=40).json()
                for p in resp.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    if "inlineData" in p:
                        with open("tmp_gem.png", "wb") as f: f.write(base64.b64decode(p["inlineData"]["data"]))
                        ImageEnhance.Brightness(Image.open("tmp_gem.png").convert("RGB").resize((1080, 1920))).enhance(0.85).save(out_path, quality=92)
                        print(f"Gemini 2D 카툰 생성 성공 ({m}): {out_path}")
                        return True
            except Exception as e: print(f"{m} 예외:", e)
    try:
        url_p = f"https://pollinations.ai{urllib.parse.quote(full_prompt)}?width=1080&height=1920&nologo=true&seed={abs(hash(full_prompt)) % 999999}"
        resp_p = requests.get(url_p, headers={"User-Agent": "Mozilla/5.0"}, timeout=45)
        if resp_p.status_code == 200 and len(resp_p.content) > 8000:
            with open("tmp_pol.jpg", "wb") as f: f.write(resp_p.content)
            ImageEnhance.Brightness(Image.open("tmp_pol.jpg").convert("RGB").resize((1080, 1920))).enhance(0.85).save(out_path, quality=92)
            print(f"Pollinations 2D 카툰 생성 성공: {out_path}")
            return True
    except Exception as e: print("Pollinations 예외:", e)
    Image.new("RGB", (1080, 1920), color=fallback_color).save(out_path)
    return False

async def main():
    q_p, c_p, a_p = generate_scene_prompts(QUESTION, ANSWER)
    fetch_cartoon_image(q_p, "bg_q.jpg", (28, 38, 64))
    fetch_cartoon_image(c_p, "bg_c.jpg", (44, 34, 58))
    fetch_cartoon_image(a_p, "bg_a.jpg", (54, 28, 64))
    spoken_ans = re.sub(r'\([^)]*\)', '', ANSWER).strip() or ANSWER
    await generate_tts(f"{QUESTION}", "q_raw.mp3", "q.mp3", rate="+15%", pad=0.25)
    await generate_tts("과연 정답은, 삼, 이, 일!", "c_raw.mp3", "c.mp3", rate="+18%", pad=0.45)
    await generate_tts(f"정답은 바로 {spoken_ans}입니다!", "a_raw.mp3", "a.mp3", rate="+15%", pad=0.25)
    await generate_tts("재밌었다면 구독과 좋아요 부탁드려요!", "s_raw.mp3", "s.mp3", rate="+15%", pad=0.35)
    d_q, d_c, d_a, d_s = get_duration("q.mp3"), get_duration("c.mp3"), get_duration("a.mp3"), get_duration("s.mp3")
    t1, t2, t3, total_dur = d_q, d_q + d_c, d_q + d_c + d_a, d_q + d_c + d_a + d_s
    with open("concat.txt", "w") as f: f.write("file 'q.mp3'\nfile 'c.mp3'\nfile 'a.mp3'\nfile 's.mp3'\n")
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
        f"[bg]drawbox=x=80:y=190:w=920:h=125:color=#FFD600:t=fill,"
        f"drawtext=fontfile={font_path}:textfile=title.txt:fontcolor=#111111:fontsize=56:x=(w-text_w)/2:y=225,"
        f"drawbox=x=60:y=350:w=960:h=440:color=#0D1117@0.55:t=fill,"
        f"drawbox=x=60:y=350:w=960:h=440:color=#FFD600@0.85:t=4,"
        f"drawtext=fontfile={font_path}:text='Q.':fontcolor=#FFD600:fontsize=85:borderw=5:bordercolor=black:x=(w-text_w)/2:y=380,"
        f"drawtext=fontfile={font_path}:textfile=question.txt:fontcolor=white:fontsize=84:borderw=6:bordercolor=black:x=(w-text_w)/2:y=495:line_spacing=22,"
        f"drawtext=fontfile={font_path}:text='3... 2... 1...':fontcolor=#00E5FF:fontsize=115:borderw=7:bordercolor=black:x=(w-text_w)/2:y=1030:enable='between(t,{t1},{t2})',"
        f"drawbox=x=90:y=1180:w=900:h=240:color=#0D1117@0.75:t=fill:enable='gte(t,{t2})',"
        f"drawbox=x=90:y=1180:w=900:h=240:color=#00E676:t=5:enable='gte(t,{t2})',"
        f"drawtext=fontfile={font_path}:textfile=answer.txt:fontcolor=#00E676:fontsize=86:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1255:line_spacing=20:enable='gte(t,{t2})',"
        f"drawbox=x=80:y=1500:w=920:h=110:color=#FF1744@0.92:t=fill:enable='gte(t,{t3})',"
        f"drawtext=fontfile={font_path}:textfile=sub.txt:fontcolor=white:fontsize=46:borderw=3:bordercolor=black:x=(w-text_w)/2:y=1532:enable='gte(t,{t3})'"
    )
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", f"{total_dur}", "-i", "bg_q.jpg", "-loop", "1", "-t", f"{total_dur}", "-i", "bg_c.jpg", "-loop", "1", "-t", f"{total_dur}", "-i", "bg_a.jpg", "-i", "full_audio.mp3", "-filter_complex", vf, "-t", f"{total_dur}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "output.mp4"], check=True)
    print("쇼츠 렌더링 완료: output.mp4")

if __name__ == "__main__":
    asyncio.run(main())
