import subprocess, json, uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

app = FastAPI()
PROXY = "socks5://127.0.0.1:40000"
YT_ARGS = ["--proxy", PROXY, "--extractor-args", "youtube:player_client=tv_downgraded,web_creator,mweb"]

@app.get("/")
def home():
    return {"status": "Online"}

@app.get("/search")
def search(q: str = Query("trending")):
    cmd = ["yt-dlp"] + YT_ARGS + ["--flat-playlist", "--dump-single-json", f"ytsearch10:{q}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(res.stdout)
    return {"videos": [{"id": e.get("id"), "title": e.get("title", "")[:38]} for e in data.get("entries", [])]}

@app.get("/stream_video")
def stream_video(id: str):
    yt = subprocess.Popen(["yt-dlp"] + YT_ARGS + ["-f", "best[height<=360]", "-o", "-", f"https://www.youtube.com/watch?v={id}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    ff = subprocess.Popen(["ffmpeg", "-i", "pipe:0", "-vf", "scale=240:180", "-r", "12", "-q:v", "12", "-f", "mjpeg", "pipe:1"], stdin=yt.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    def gen():
        try:
            while chunk := ff.stdout.read(4096):
                yield chunk
        finally:
            ff.kill(); yt.kill()
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/stream_audio")
def stream_audio(id: str):
    yt = subprocess.Popen(["yt-dlp"] + YT_ARGS + ["-f", "bestaudio", "-o", "-", f"https://www.youtube.com/watch?v={id}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    ff = subprocess.Popen(["ffmpeg", "-i", "pipe:0", "-ar", "16000", "-ac", "1", "-f", "s16le", "pipe:1"], stdin=yt.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    def gen():
        try:
            while chunk := ff.stdout.read(2048):
                yield chunk
        finally:
            ff.kill(); yt.kill()
    return StreamingResponse(gen(), media_type="application/octet-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
