import os
import asyncio
import subprocess
import edge_tts

TITLE = os.environ.get("SHORTS_TITLE", "지니어스만 맞추는 레전드 아재 퀴즈")
QUESTION = os.environ.get("SHORTS_QUESTION", "세상에서 가장 가난한 왕은?")
ANSWER = os.environ.get("SHORTS_ANSWER", "최저임금")

VOICE = "ko-KR-InJoonNeural"

async def generate_tts(text, filename):
    communicate = edge_tts.Communicate(text, VOICE, rate="+10%", pitch="-2Hz")
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

async def main():
    q_text = f"{QUESTION} 과연 정답은 무엇일까요?"
    c_text = "3, 2, 1"
    a_text = f"정답은 바로 {ANSWER}입니다! 재밌었다면 구독과 좋아요 부탁드려요."

    await generate_tts(q_text, "q.mp3")
    await generate_tts(c_text, "c.mp3")
    await generate_tts(a_text, "a.mp3")

    d_q = get_duration("q.mp3")
    d_c = get_duration("c.mp3")
    d_a = get_duration("a.mp3")
    total_dur = d_q + d_c + d_a + 0.5

    with open("concat.txt", "w") as f:
        f.write("file 'q.mp3'\nfile 'c.mp3'\nfile 'a.mp3'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "full_audio.mp3"], check=True)

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

    t1 = d_q
    t2 = d_q + d_c

    vf = (
        f"drawbox=x=60:y=420:w=960:h=1050:color=#161B22@0.95:t=fill,"
        f"drawbox=x=60:y=420:w=960:h=1050:color=#30363D:t=4,"
        f"drawbox=x=80:y=220:w=920:h=130:color=#FFD600:t=fill,"
        f"drawtext=fontfile={font_path}:textfile=title.txt:fontcolor=#111111:fontsize=56:x=(w-text_w)/2:y=258,"
        f"drawtext=fontfile={font_path}:text='Q.':fontcolor=#FFD600:fontsize=95:borderw=4:bordercolor=black:x=(w-text_w)/2:y=500,"
        f"drawtext=fontfile={font_path}:textfile=question.txt:fontcolor=white:fontsize=88:borderw=5:bordercolor=black:x=(w-text_w)/2:y=650:line_spacing=24,"
        f"drawtext=fontfile={font_path}:text='3... 2... 1...':fontcolor=#00E5FF:fontsize=92:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1020:enable='between(t,{t1},{t2})',"
        f"drawbox=x=110:y=1010:w=860:h=240:color=#21262D:t=fill:enable='gte(t,{t2})',"
        f"drawbox=x=110:y=1010:w=860:h=240:color=#00E676:t=4:enable='gte(t,{t2})',"
        f"drawtext=fontfile={font_path}:textfile=answer.txt:fontcolor=#00E676:fontsize=86:borderw=4:bordercolor=black:x=(w-text_w)/2:y=1085:line_spacing=20:enable='gte(t,{t2})'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#0D1117:s=1080x1920:d={total_dur}",
        "-i", "full_audio.mp3",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        "output.mp4"
    ]
    subprocess.run(cmd, check=True)
    print("업그레이드 쇼츠 렌더링 완료: output.mp4")

if __name__ == "__main__":
    asyncio.run(main())
