"""Provides a simple API for your basic OCR client

Drive the API to complete "interprocess communication"

Requirements
"""
import os
import urllib.parse

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from library_basics import CodingVideo
import shutil
import pyttsx3

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "videos"


RESOURCES_DIR = BASE_DIR.parent / "resources"

app.mount("/resources", StaticFiles(directory=str(RESOURCES_DIR)), name="resources")
app.mount("/preliminary", StaticFiles(directory=str(BASE_DIR)), name="preliminary")

# We'll create a lightweight "database" for our videos
# You can add uploads later (not required for assessment)
# For now, we will just hardcode are samples
VIDEOS: dict[str, Path] = {
    "demo": Path("videos/oop.mp4"),
}

class VideoMetaData(BaseModel):
    fps: float
    frame_count: int
    duration_seconds: float
    _links: dict | None = None

#startup_help_text = "To hear all available hotkeys for this page. Press Alt H"
#help_text_upload = "You are on the Upload Page. Press Alt U and enter a video from your file explorer to upload."
#help_text = "You are on the Video Page. To Play or Pause. Press Alt Comma. To listen to the Text currently shown in the video. Press Alt Full stop while the video is paused. If you want to go back to the upload page. Press Alt Minus"


def text_to_speech(text, file_path = 'output.wav'):
    engine = pyttsx3.init()
    engine.save_to_file(text, file_path)
    engine.runAndWait()

@app.get("/", response_class=HTMLResponse)
def main_page():
    #text_to_speech(help_text_upload, "preliminary/help_text_upload.wav")
    #text_to_speech(help_text, "preliminary/help_text.wav")
    #text_to_speech(startup_help_text, "preliminary/startup_help_text.wav")
    html_content = f"""
    <html>
        <head>
            <title>Upload Page</title>
            <link rel="stylesheet" href="/resources/styles.css">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible&display=swap" rel="stylesheet">
        </head>
        <body>
            <header>
                <div class="help_home">
                    <h1 class="help_symbol_home">?</h1>
                    <h1>ALT+H</h1>
                </div>
                
                <button accesskey="h" onclick="document.getElementById('help_text_upload').play()" style="display:none;"></button>
                <audio id="help_text_upload" src="/preliminary/help_text_upload.wav"></audio>
                
                <br>
            
                <form action="/upload/" method="POST" enctype="multipart/form-data">
                    <div class="upload">
                        <img class="upload_img" src="/resources/upload.png" alt="Upload">
                        <h1>ALT+U</h1>
                        <!-- Added onChange to auto-submit the form when a file is picked -->
                        <input type="file" id="file-upload" class="visually-hidden" 
                               name="uploaded_file" accesskey="u" accept="video/mp4" onchange="this.form.submit()">
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

    return RedirectResponse(url=f"/video/{uploaded_file.filename}", status_code=303)

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

def savevideo_gettext_generatettsfile(vid, time):
    try:
        video = _open_vid_or_404(vid)
        video.save_as_image(time)
        text_in_frame = video.get_text_from_image()
        if text_in_frame.replace(" ", "") == "":
            text_in_frame = f"There is no text detected onscreen at {time} seconds"
        text_to_speech(text_in_frame, "preliminary/text_in_frame.wav")
        return video, text_in_frame
    finally:
        video.capture.release()


#UNFINISHED HERE
@app.get("/video/{vid}", response_class=HTMLResponse)
def video_frame(vid: str):
    video, text_in_frame = savevideo_gettext_generatettsfile(vid, 0)

    html_content = f"""
            <html>
                <head>
                    <title>Video Page</title>
                    <link rel="stylesheet" href="/resources/styles.css">
                    <link rel="preconnect" href="https://fonts.googleapis.com">
                    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                    <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible&display=swap" rel="stylesheet">
                </head>
                <body>
                    <header>
                        <form hidden action="/go-back/" method="POST">
                            <button accesskey="-"></button>
                        </form>

                        <div class="help">
                            <h1 class="help_symbol">?</h1>
                            <h1>ALT+H</h1>
                        </div>

                        <button accesskey="h" onclick="document.getElementById('help_text').play()" style="display:none;"></button>
                        <audio id="help_text" src="/preliminary/help_text.wav"></audio>

                        <br>

                        <video class="videoplayer" id="mainVideo" width="800px">
                            <source src="/preliminary/videos/{vid}" type="video/mp4">
                        </video>
                        <div class="controls">
                            <button id="pause_and_update_button" accesskey="," onclick="pauseAndSyncOrPlay()"></button>
                        </div>

                        <h1> TEXT ON SCREEN: </h1>
                        <textarea class="output_text" id="currentTextOnScreen"> {text_in_frame} </textarea>

                        <audio id="text_in_frame" src="/preliminary/text_in_frame.wav?t=${{new Date().getTime()}}"></audio>
                        <button accesskey="." onclick="document.getElementById('text_in_frame').play()" style="display:none;"></button>

                    </header>
                </body>

                <script>
                    async function pauseAndSyncOrPlay() {{
                        const video = document.getElementById('mainVideo');
                        const audioEngine = document.getElementById('text_in_frame');
                        if (!video.paused) {{
                            // Pause the Video
                            const textBox = document.getElementById('currentTextOnScreen');
                            
                            video.pause();
                            const timestamp = Math.floor(video.currentTime);
                            
                            const queryUrl = `/process-frame?vid={vid}&time=${{timestamp}}`;
                            
                            try {{
                                const response = await fetch(queryUrl);
                                if (!response.ok) throw new Error("Server error");
                                
                                const payloadText = response.headers.get("X-Detected-Text");
                                textBox.value = decodeURIComponent(payloadText || "");
                                
                                // Discard audio cache and reload source
                                audioEngine.src = `/preliminary/text_in_frame.wav?t=${{new Date().getTime()}}`;
                                audioEngine.load();
                                
                            }} catch (err) {{
                                console.error(err);
                            }}
                        }} else {{ 
                            // Play the Video
                            video.play();
                        }}
                    }}
                </script>
            </html>
            """
    print(text_in_frame)
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/process-frame")
async def process_frame(vid: str, time: int):
    try:
        # Validate that the file exists
        video_path = f"preliminary/videos/{vid}"
        if not os.path.exists(video_path):
            print(f"[ERROR] Target video not found at path: {video_path}")
            raise HTTPException(status_code=404, detail=f"Video file '{vid}' not found on server.")

        # Run processing logic script
        _, detected_text = savevideo_gettext_generatettsfile(vid, time)
        audio_path = "preliminary/text_in_frame.wav"

        if not os.path.exists(audio_path):
            raise HTTPException(status_code=500, detail="Audio generation failed.")

        safe_header_text = urllib.parse.quote(detected_text)
        # have text inside custom headers with binary wave stream
        headers = {
            "X-Detected-Text": safe_header_text,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            # Forces the browser to load the NEW audio file every time
            "Pragma": "no-cache",
            "Expires": "0"
        }
        return FileResponse(audio_path, media_type="audio/wav", headers=headers)

    except HTTPException as http_ex:
        # Pass through 404 errors instead of turning into 500s
        raise http_ex

    except Exception as e:
        # Print exact traceback in terminal screen
        import traceback
        print("[CRITICAL ENGINE CRASH TRACEBACK]:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/go-back/")
def go_back():
    return RedirectResponse(url="/", status_code=303)