"""Provides a simple API for your basic OCR client

Drive the API to complete "interprocess communication"

Requirements
"""

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi import Response
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from library_basics import CodingVideo
import shutil


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "videos"

app.mount("/resources", StaticFiles(directory="resources"), name="resources")

# We'll create a lightweight "database" for our videos
# You can add uploads later (not required for assessment)
# For now, we will just hardcode are samples
VIDEOS: dict[str, Path] = {
    "demo": Path("resources/oop.mp4"),
}

class VideoMetaData(BaseModel):
    fps: float
    frame_count: int
    duration_seconds: float
    _links: dict | None = None

@app.get("/", response_class=HTMLResponse)
def main_page():
    html_content = f"""
    <html>
        <head>
            <title>Title Test</title>
            <link rel="stylesheet" href="/resources/styles.css">
        </head>
        <body>
            <header>
                <div class="help">
                    <h1 class="help_symbol">?</h1>
                    <h1>ALT+H</h1>
                </div>
            
                <form action="/upload/" method="POST" enctype="multipart/form-data">
                    <div class="upload">
                        <img class="upload_img" src="/resources/upload.png" alt="Upload">
                        <h1>ALT+U</h1>
                        <!-- Added onChange to auto-submit the form when a file is picked -->
                        <input type="file" id="file-upload" class="visually-hidden" 
                               name="uploaded_file" accesskey="u" onchange="this.form.submit()">
                    </div>
                </form>
            </header>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.post("/upload/")
async def upload_video(uploaded_file: UploadFile = File(...)):
    # Create required directory hierarchy mappings cleanly
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Combine directory paths with source filename strings securely
    destination_path = UPLOAD_DIR / uploaded_file.filename

    # Stream file binary directly to disk
    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)

    VIDEOS[uploaded_file.filename] = destination_path

    return RedirectResponse(url=f"/video/{uploaded_file.filename}/frame/0", status_code=303)


def _open_vid_or_404(vid: str) -> CodingVideo:
    path = VIDEOS.get(vid)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")
    try:
        return CodingVideo(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Could not open video {e}")

def _meta(video: CodingVideo) -> VideoMetaData:
    return VideoMetaData(
            fps=video.fps,
            frame_count=video.frame_count,
            duration_seconds=video.duration
    )

#UNFINISHED HERE
# MODIFY IT TO GIVE A HTML RESPONSE AND BE SORTA SIMILAR TO THE WIREFRAME
@app.get("/video/{vid}/frame/{t}", response_class=Response)
def video_frame(vid: str, t: float):
    try:
        video = _open_vid_or_404(vid)
        video.save_as_image(t)
        text = video.get_text_from_image()
        return text
    finally:
      video.capture.release()