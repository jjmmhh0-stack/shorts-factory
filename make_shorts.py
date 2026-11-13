import os
import urllib.parse
import asyncio
import subprocess
import requests
from PIL import Image, ImageEnhance
import edge_tts

TITLE = os.environ.get("SHORTS_TITLE", "지니어스만 맞추는 레전드 아재 퀴즈")
QUESTION = os.environ.get("SHORTS_QUESTION", "세상에서 가장 가난한 왕은?")
ANSWER = os.environ.get("SHORTS_ANSWER", "최저임금")

VOICE = "ko-KR-InJoonNeural"

async def generate_tts(text, filename):
    communicate = edge_tts.Communicate(text, VOICE, rate="+10%", pitch="-2Hz", volume="+45%")
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

def generate_cartoon_bg(question, answer, out_path="bg.jpg"):
    prompt = f"cute 2d korean webtoon flat cartoon illustration, humorous minimal scene representing {question} {answer}, vibrant colors, clean vector art style, no text, no letters, vertical 9:16"
    encoded = urllib.parse.quote(prompt)
    url = f"https://pollinations.ai{encoded}?width=1080&height=1920&nologo=true&seed={abs(hash(question)) % 100000}"
    try:
        resp = requests.get(url, timeout=35)
        if resp.status_code == 200 and len(resp.content) > 5000:
            with open("raw_bg.jpg", "wb") as f:
                f.write(resp.content)
            img = Image.open("raw_bg.jpg").convert("RGB").resize((1080, 1920))
            img = ImageEnhance.Brightness(img).enhance(0.55)
            img.save(out_path, quality=92)
            return True
    except Exception as e:
        print("배경 생성 예외(기본 배경 사용):", e)
    img = Image.new("RGB", (1080, 1920), color=(18, 24, 38))
    img.save(out_path)
    return False

async def main():
    generate_cartoon_bg(QUESTION, ANSWER, "bg.jpg")

    q_text = f"{QUESTION} 과연 정답은 무엇일까요?"
    c_text = "3, 2, 1"
    a_text = f"정답은 바로 {ANSWER}입니다!"
    sub_text = "재밌었다면 구독과 좋아요 부탁드려요!"

    await generate_tts(q_text, "q.mp3")
    await generate_tts(c_text, "c.mp3")
    await generate_tts(a_text, "a.mp3")
    await generate_tts(sub_text, "s.mp3")

    d_q = get_duration("q.mp3")
    d_c = get_duration("c.mp3")
    d_a = get_duration("a.mp3")
    d_s = get_duration("s.mp3")
    total_dur = d_q + d_c + d_a + d_s + 0.4

    with open("concat.txt", "w") as f:
        f.write("file 'q.mp3'\nfile 'c.mp3'\nfile 'a.mp3'\nfile 's.mp3'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "raw_audio.mp3"], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", "raw_audio.mp3", "-filter:a", "volume=1.8", "full_audio.mp3"], check=True)

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

    t1 = d_q
    t2 = d_q + d_c
    t3 = d_q + d_c + d_a

    vf = (
        f"drawbox=x=60:y=400:w=960:h=1020:color=#0D1117@0.72:t=fill,"
        f"drawbox=x=60:y=400:w=960:h=1020:color=#FFD600@0.8:t=4,"
        f"drawbox=x=80:y=210:w=920:h=130:color=#FFD600:t=fill,"
        f"drawtext=fontfile={font_path}:textfile=title.txt:fontcolor=#111111:fontsize=56:x=(w-text_w)/2:y=248,"
        f"drawtext=fontfile={font_path}:text='Q.':fontcolor=#FFD600:fontsize=95:borderw=5:bordercolor=black:x=(w-text_w)/2:y=470,"
        f"drawtext=fontfile={font_path}:textfile=question.txt:fontcolor=white:fontsize=88:borderw=6:bordercolor=black:x=(w-text_w)/2:y=615:line_spacing=24,"
        f"drawtext=fontfile={font_path}:text='3... 2... 1...':fontcolor=#00E5FF:fontsize=95:borderw=6:bordercolor=black:x=(w-text_w)/2:y=980:enable='between(t,{t1},{t2})',"
        f"drawbox=x=100:y=970:w=880:h=240:color=#161B22@0.9:t=fill:enable='gte(t,{t2})',"
        f"drawbox=x=100:y=970:w=880:h=240:color=#00E676:t=5:enable='gte(t,{t2})',"
        f"drawtext=fontfile={font_path}:textfile=answer.txt:fontcolor=#00E676:fontsize=86:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1045:line_spacing=20:enable='gte(t,{t2})',"
        f"drawbox=x=80:y=1490:w=920:h=110:color=#FF1744@0.92:t=fill:enable='gte(t,{t3})',"
        f"drawtext=fontfile={font_path}:textfile=sub.txt:fontcolor=white:fontsize=46:borderw=3:bordercolor=black:x=(w-text_w)/2:y=1522:enable='gte(t,{t3})'"
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
    print("2D 카툰 배경 + 볼륨 증폭 + 구독 자막 쇼츠 완료: output.mp4")

if __name__ == "__main__":
    asyncio.run(main())
