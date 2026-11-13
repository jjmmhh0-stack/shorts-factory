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
    communicate = edge_tts.Communicate(text, VOICE, rate=rate, pitch="-2Hz", volume="+45%")
    await communicate.save(filename)

def get_duration(filename):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def make_silence(duration, filename):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{duration}", "-q:a", "9", "-acodec", "libmp3lame", filename
    ], check=True)

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

def generate_cartoon_bg(question, answer, out_path="bg.jpg"):
    prompt = f"Cute 2D Korean webtoon flat cartoon illustration, humorous bright colorful scene illustrating the joke: '{question}' and '{answer}'. Clean vector line art, expressive characters, vertical 9:16 composition, strictly NO text, NO letters, NO speech bubbles."
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
                with open("raw_bg.png", "wb") as f:
                    f.write(base64.b64decode(b64))
                img = Image.open("raw_bg.png").convert("RGB").resize((1080, 1920))
                img = ImageEnhance.Brightness(img).enhance(0.78)
                img.save(out_path, quality=92)
                print("Gemini Imagen 2D 카툰 배경 생성 성공!")
                return True
            else:
                print("Imagen 응답 확인:", data)
        except Exception as e:
            print("Imagen 예외:", e)

    try:
        import urllib.parse
        encoded = urllib.parse.quote(prompt)
        url = f"https://pollinations.ai{encoded}?width=1080&height=1920&model=flux&nologo=true&seed={abs(hash(question)) % 100000}"
        resp = requests.get(url, timeout=45)
        if resp.status_code == 200 and len(resp.content) > 5000:
            with open("raw_bg.jpg", "wb") as f:
                f.write(resp.content)
            img = Image.open("raw_bg.jpg").convert("RGB").resize((1080, 1920))
            img = ImageEnhance.Brightness(img).enhance(0.78)
            img.save(out_path, quality=92)
            print("Pollinations 2D 카툰 배경 생성 성공!")
            return True
    except Exception as e:
        print("Pollinations 예외:", e)

    img = Image.new("RGB", (1080, 1920), color=(24, 34, 56))
    img.save(out_path)
    return False

async def main():
    generate_cartoon_bg(QUESTION, ANSWER, "bg.jpg")

    q_text = f"{QUESTION} 과연 정답은 무엇일까요?"
    a_text = f"정답은 바로 {ANSWER}입니다!"
    sub_text = "재밌었다면 구독과 좋아요 부탁드려요!"

    await generate_tts(q_text, "q.mp3", rate="+10%")
    await generate_tts("삼!", "c3.mp3", rate="+0%")
    await generate_tts("이!", "c2.mp3", rate="+0%")
    await generate_tts("일!", "c1.mp3", rate="+0%")
    await generate_tts(a_text, "a.mp3", rate="+10%")
    await generate_tts(sub_text, "s.mp3", rate="+10%")

    make_silence(0.35, "gap_short.mp3")
    make_silence(0.65, "gap_long.mp3")

    d_q = get_duration("q.mp3")
    d_c3 = get_duration("c3.mp3")
    d_c2 = get_duration("c2.mp3")
    d_c1 = get_duration("c1.mp3")
    d_gs = get_duration("gap_short.mp3")
    d_gl = get_duration("gap_long.mp3")
    d_a = get_duration("a.mp3")
    d_s = get_duration("s.mp3")

    t_c3_start = d_q
    t_c2_start = d_q + d_c3 + d_gs
    t_c1_start = t_c2_start + d_c2 + d_gs
    t_ans_start = t_c1_start + d_c1 + d_gl
    t_sub_start = t_ans_start + d_a
    total_dur = t_sub_start + d_s + 0.3

    with open("concat.txt", "w") as f:
        f.write(
            "file 'q.mp3'\n"
            "file 'c3.mp3'\nfile 'gap_short.mp3'\n"
            "file 'c2.mp3'\nfile 'gap_short.mp3'\n"
            "file 'c1.mp3'\nfile 'gap_long.mp3'\n"
            "file 'a.mp3'\nfile 's.mp3'\n"
        )
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "raw_audio.mp3"], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", "raw_audio.mp3", "-filter:a", "volume=1.9", "full_audio.mp3"], check=True)

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
        f"drawbox=x=80:y=190:w=920:h=125:color=#FFD600:t=fill,"
        f"drawtext=fontfile={font_path}:textfile=title.txt:fontcolor=#111111:fontsize=56:x=(w-text_w)/2:y=225,"
        f"drawbox=x=60:y=360:w=960:h=470:color=#0D1117@0.68:t=fill,"
        f"drawbox=x=60:y=360:w=960:h=470:color=#FFD600@0.85:t=4,"
        f"drawtext=fontfile={font_path}:text='Q.':fontcolor=#FFD600:fontsize=85:borderw=5:bordercolor=black:x=(w-text_w)/2:y=395,"
        f"drawtext=fontfile={font_path}:textfile=question.txt:fontcolor=white:fontsize=84:borderw=6:bordercolor=black:x=(w-text_w)/2:y=515:line_spacing=22,"
        f"drawtext=fontfile={font_path}:text='3...':fontcolor=#00E5FF:fontsize=125:borderw=7:bordercolor=black:x=(w-text_w)/2:y=1020:enable='between(t,{t_c3_start},{t_c2_start})',"
        f"drawtext=fontfile={font_path}:text='3... 2...':fontcolor=#00E5FF:fontsize=125:borderw=7:bordercolor=black:x=(w-text_w)/2:y=1020:enable='between(t,{t_c2_start},{t_c1_start})',"
        f"drawtext=fontfile={font_path}:text='3... 2... 1...':fontcolor=#00E5FF:fontsize=125:borderw=7:bordercolor=black:x=(w-text_w)/2:y=1020:enable='between(t,{t_c1_start},{t_ans_start})',"
        f"drawbox=x=90:y=1180:w=900:h=240:color=#0D1117@0.85:t=fill:enable='gte(t,{t_ans_start})',"
        f"drawbox=x=90:y=1180:w=900:h=240:color=#00E676:t=5:enable='gte(t,{t_ans_start})',"
        f"drawtext=fontfile={font_path}:textfile=answer.txt:fontcolor=#00E676:fontsize=86:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1255:line_spacing=20:enable='gte(t,{t_ans_start})',"
        f"drawbox=x=80:y=1500:w=920:h=110:color=#FF1744@0.92:t=fill:enable='gte(t,{t_sub_start})',"
        f"drawtext=fontfile={font_path}:textfile=sub.txt:fontcolor=white:fontsize=46:borderw=3:bordercolor=black:x=(w-text_w)/2:y=1532:enable='gte(t,{t_sub_start})'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", "bg.jpg",
        "-i", "full_audio.mp3",
        "-vf", vf,
        "-t", f"{total_dur}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        "output.mp4"
    ]
    subprocess.run(cmd, check=True)
    print("2D 카툰 배경 + 3-2-1 호흡 완성 쇼츠 렌더링 완료: output.mp4")

if __name__ == "__main__":
    asyncio.run(main())
