import os
import base64
import asyncio
import subprocess
import requests
from PIL import Image, ImageEnhance
import edge_tts

TITLE = os.environ.get("SHORTS_TITLE", "지니어스만 맞추는 레전드 아재 퀴즈")
QUESTION = os.environ.get("SHORTS_QUESTION", "세상에서 가장 가난한 왕은?")
ANSWER = os.environ.get("SHORTS_ANSWER", "최저임금")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

VOICE = "ko-KR-InJoonNeural"

async def generate_tts(text, filename, rate="+10%"):
    communicate = edge_tts.Communicate(text, VOICE, rate=rate, pitch="-2Hz", volume="+15%")
    await communicate.save(filename)

def get_duration(filename):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def wrap_text(text, max_chars=11):
    words = text.split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 <= max_chars:
            current = (current + " " + w).strip()
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return "\n".join(lines)

def fetch_ai_image(prompt, out_path, fallback_color):
    if GEMINI_KEY:
        try:
            url = f"https://googleapis.com{GEMINI_KEY}"
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": "9:16"}
            }
            resp = requests.post(url, json=payload, timeout=35)
            data = resp.json()
            if "predictions" in data and len(data["predictions"]) > 0:
                b64 = data["predictions"][0]["bytesBase64Encoded"]
                with open("tmp.png", "wb") as f:
                    f.write(base64.b64decode(b64))
                img = Image.open("tmp.png").convert("RGB").resize((1080, 1920))
                img = ImageEnhance.Brightness(img).enhance(0.82)
                img.save(out_path, quality=92)
                print(f"Imagen 2D 카툰 생성 성공: {out_path}")
                return True
        except Exception as e:
            print("Imagen 1차 시도 예외:", e)

        try:
            url2 = f"https://googleapis.com{GEMINI_KEY}"
            payload2 = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]}
            }
            resp2 = requests.post(url2, json=payload2, timeout=35)
            data2 = resp2.json()
            parts = data2.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            for p in parts:
                if "inlineData" in p:
                    b64 = p["inlineData"]["data"]
                    with open("tmp2.png", "wb") as f:
                        f.write(base64.b64decode(b64))
                    img = Image.open("tmp2.png").convert("RGB").resize((1080, 1920))
                    img = ImageEnhance.Brightness(img).enhance(0.82)
                    img.save(out_path, quality=92)
                    print(f"Gemini Flash 2D 카툰 생성 성공: {out_path}")
                    return True
        except Exception as e:
            print("Gemini Flash 이미지 생성 예외:", e)

    try:
        import urllib.parse
        encoded = urllib.parse.quote(prompt)
        url3 = f"https://pollinations.ai{encoded}?width=1080&height=1920&nologo=true&seed={abs(hash(prompt)) % 100000}"
        resp3 = requests.get(url3, timeout=45)
        if resp3.status_code == 200 and len(resp3.content) > 5000:
            with open("tmp3.jpg", "wb") as f:
                f.write(resp3.content)
            img = Image.open("tmp3.jpg").convert("RGB").resize((1080, 1920))
            img = ImageEnhance.Brightness(img).enhance(0.82)
            img.save(out_path, quality=92)
            print(f"Pollinations 2D 카툰 생성 성공: {out_path}")
            return True
    except Exception as e:
        print("Pollinations 예외:", e)

    img = Image.new("RGB", (1080, 1920), color=fallback_color)
    img.save(out_path)
    return False

async def main():
    q_prompt = (
        f"Cute 2D Korean webtoon style flat cartoon illustration, humorous expressive character thinking or puzzled about: '{QUESTION}'. "
        "Vibrant colorful vector art, clean outlines, vertical 9:16 composition, strictly NO text, NO letters, NO speech bubbles."
    )
    a_prompt = (
        f"Cute 2D Korean webtoon style flat cartoon illustration, funny punchline comedy scene revealing the answer: '{ANSWER}' for '{QUESTION}'. "
        "Bright cheerful vibrant colors, expressive laughing or surprised reaction, vertical 9:16 composition, strictly NO text, NO letters, NO speech bubbles."
    )

    fetch_ai_image(q_prompt, "bg_q.jpg", (24, 34, 56))
    fetch_ai_image(a_prompt, "bg_a.jpg", (38, 24, 56))

    q_text = f"{QUESTION} 과연 정답은 무엇일까요?"
    c_text = "3, 2, 1"
    a_text = f"정답은 바로 {ANSWER}입니다!"
    sub_text = "재밌었다면 구독과 좋아요 부탁드려요!"

    await generate_tts(q_text, "q.mp3", rate="+10%")
    await generate_tts(c_text, "c.mp3", rate="+10%")
    await generate_tts(a_text, "a.mp3", rate="+10%")
    await generate_tts(sub_text, "s.mp3", rate="+10%")

    d_q = get_duration("q.mp3")
    d_c = get_duration("c.mp3")
    d_a = get_duration("a.mp3")
    d_s = get_duration("s.mp3")

    t1 = d_q
    t2 = d_q + d_c
    t3 = d_q + d_c + d_a
    total_dur = t3 + d_s + 0.4

    with open("concat.txt", "w") as f:
        f.write("file 'q.mp3'\nfile 'c.mp3'\nfile 'a.mp3'\nfile 's.mp3'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "raw_audio.mp3"], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", "raw_audio.mp3",
        "-filter:a", "loudnorm=I=-16:TP=-1.5:LRA=11,volume=1.15",
        "full_audio.mp3"
    ], check=True)

    font_path = "/usr/share/fonts/truetype/nanum/NanumSquareRoundEB.ttf"
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf"
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"

    clean_title = TITLE.replace("#Shorts", "").replace("#넌센스퀴즈", "").strip()
    if len(clean_title) > 15:
        clean_title = clean_title[:15]

    with open("title.txt", "w", encoding="utf-8") as f:
        f.write(clean_title)
    with open("question.txt", "w", encoding="utf-8") as f:
        f.write(wrap_text(QUESTION, 11))
    with open("answer.txt", "w", encoding="utf-8") as f:
        f.write(f"정답 : {wrap_text(ANSWER, 10)}")
    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write("재밌었다면 구독 & 좋아요 부탁드려요!")

    vf = (
        f"[0:v]scale=1080:1920,setsar=1[bg0];"
        f"[1:v]scale=1080:1920,setsar=1[bg1];"
        f"[bg0][bg1]overlay=enable='gte(t,{t2})'[bg];"
        f"[bg]drawbox=x=80:y=190:w=920:h=125:color=#FFD600:t=fill,"
        f"drawtext=fontfile={font_path}:textfile=title.txt:fontcolor=#111111:fontsize=56:x=(w-text_w)/2:y=225,"
        f"drawbox=x=60:y=360:w=960:h=460:color=#0D1117@0.62:t=fill,"
        f"drawbox=x=60:y=360:w=960:h=460:color=#FFD600@0.85:t=4,"
        f"drawtext=fontfile={font_path}:text='Q.':fontcolor=#FFD600:fontsize=85:borderw=5:bordercolor=black:x=(w-text_w)/2:y=395,"
        f"drawtext=fontfile={font_path}:textfile=question.txt:fontcolor=white:fontsize=84:borderw=6:bordercolor=black:x=(w-text_w)/2:y=515:line_spacing=22,"
        f"drawtext=fontfile={font_path}:text='3... 2... 1...':fontcolor=#00E5FF:fontsize=115:borderw=7:bordercolor=black:x=(w-text_w)/2:y=1020:enable='between(t,{t1},{t2})',"
        f"drawbox=x=90:y=1180:w=900:h=240:color=#0D1117@0.82:t=fill:enable='gte(t,{t2})',"
        f"drawbox=x=90:y=1180:w=900:h=240:color=#00E676:t=5:enable='gte(t,{t2})',"
        f"drawtext=fontfile={font_path}:textfile=answer.txt:fontcolor=#00E676:fontsize=86:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1255:line_spacing=20:enable='gte(t,{t2})',"
        f"drawbox=x=80:y=1500:w=920:h=110:color=#FF1744@0.92:t=fill:enable='gte(t,{t3})',"
        f"drawtext=fontfile={font_path}:textfile=sub.txt:fontcolor=white:fontsize=46:borderw=3:bordercolor=black:x=(w-text_w)/2:y=1532:enable='gte(t,{t3})'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{total_dur}", "-i", "bg_q.jpg",
        "-loop", "1", "-t", f"{total_dur}", "-i", "bg_a.jpg",
        "-i", "full_audio.mp3",
        "-filter_complex", vf,
        "-t", f"{total_dur}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        "output.mp4"
    ]
    subprocess.run(cmd, check=True)
    print("문제/정답 2D 카툰 배경 전환 + 깔끔한 오디오 쇼츠 완료: output.mp4")

if __name__ == "__main__":
    asyncio.run(main())
