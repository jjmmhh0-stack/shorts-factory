import os, re, asyncio, subprocess
import edge_tts

TITLE = os.environ.get("SHORTS_TITLE", "지니어스만 맞추는 레전드 아재 퀴즈")
QUESTION = os.environ.get("SHORTS_QUESTION", "세상에서 가장 가난한 왕은?")
ANSWER = os.environ.get("SHORTS_ANSWER", "최저임금")
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

async def main():
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
        f"drawbox=x=60:y=420:w=960:h=1050:color=#161B22@0.95:t=fill,"
        f"drawbox=x=60:y=420:w=960:h=1050:color=#30363D:t=4,"
        f"drawbox=x=80:y=220:w=920:h=130:color=#FFD600:t=fill,"
        f"drawtext=fontfile={font_path}:textfile=title.txt:fontcolor=#111111:fontsize=56:x=(w-text_w)/2:y=258,"
        f"drawtext=fontfile={font_path}:text='Q.':fontcolor=#FFD600:fontsize=95:borderw=4:bordercolor=black:x=(w-text_w)/2:y=500,"
        f"drawtext=fontfile={font_path}:textfile=question.txt:fontcolor=white:fontsize=88:borderw=5:bordercolor=black:x=(w-text_w)/2:y=650:line_spacing=24,"
        f"drawtext=fontfile={font_path}:text='3... 2... 1...':fontcolor=#00E5FF:fontsize=95:borderw=5:bordercolor=black:x=(w-text_w)/2:y=1020:enable='between(t,{t1},{t2})',"
        f"drawbox=x=110:y=1010:w=860:h=240:color=#21262D:t=fill:enable='gte(t,{t2})',"
        f"drawbox=x=110:y=1010:w=860:h=240:color=#00E676:t=4:enable='gte(t,{t2})',"
        f"drawtext=fontfile={font_path}:textfile=answer.txt:fontcolor=#00E676:fontsize=86:borderw=4:bordercolor=black:x=(w-text_w)/2:y=1085:line_spacing=20:enable='gte(t,{t2})',"
        f"drawbox=x=80:y=1520:w=920:h=110:color=#FF1744@0.92:t=fill:enable='gte(t,{t3})',"
        f"drawtext=fontfile={font_path}:textfile=sub.txt:fontcolor=white:fontsize=46:borderw=3:bordercolor=black:x=(w-text_w)/2:y=1552:enable='gte(t,{t3})'"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#0D1117:s=1080x1920:d={total_dur}",
        "-i", "full_audio.mp3",
        "-vf", vf,
        "-t", f"{total_dur}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        "output.mp4"
    ], check=True)
    print("깔끔한 원래 배경 + 최적화된 음성 쇼츠 완료: output.mp4", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
