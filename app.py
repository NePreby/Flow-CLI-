import os
import sys
import json
import time
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, List

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import load_config, save_config, get_cookie, set_cookie, DEFAULT_DOWNLOADS_DIR
from flow_client import (
    GoogleFlowClient,
    DemoFlowClient,
    IMAGE_MODELS,
    VIDEO_MODELS,
    ASPECT_RATIOS_IMAGE,
    ASPECT_RATIOS_VIDEO,
    VIDEO_RESOLUTIONS,
    VIDEO_DURATIONS
)

# Reload trigger 3
app = FastAPI(title="Google Flow AI Studio - Generator Tool", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
WEB_DIR = BASE_DIR / "web"

# Mount static files
app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")
if (WEB_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

# Quản lý client Flow
def get_client() -> GoogleFlowClient:
    cookie = get_cookie()
    return GoogleFlowClient(cookie=cookie)

demo_client = DemoFlowClient()

# Pydantic Schemas
class CookieUpdateRequest(BaseModel):
    cookie: str

class GenerateImageRequest(BaseModel):
    prompt: str
    model: str = "Nano Banana 2.1"
    aspect_ratio: str = "16:9"
    count: int = 2
    seed: Optional[int] = None
    negative_prompt: str = ""
    auto_download: bool = True

class GenerateVideoRequest(BaseModel):
    prompt: str
    model: str = "Omni 1.1 Flash"
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    duration: int = 8
    count: int = 1
    start_image_url: Optional[str] = None
    end_image_url: Optional[str] = None
    seed: Optional[int] = None
    auto_download: bool = True

class DownloadRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    media_type: str = "image"


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Google Flow AI Tool is Running! (Vui lòng tạo web/index.html)</h1>"


@app.get("/api/config")
async def api_get_config():
    cfg = load_config()
    # Ẩn bớt độ dài cookie vì lý do hiển thị
    cookie = cfg.get("cookie", "")
    masked_cookie = (cookie[:15] + "..." + cookie[-15:]) if len(cookie) > 30 else cookie
    return {
        "cookie_set": bool(cookie),
        "masked_cookie": masked_cookie,
        "downloads_dir": cfg.get("downloads_dir", str(DOWNLOADS_DIR)),
        "auto_download": cfg.get("auto_download", True),
        "default_image_model": cfg.get("default_image_model", "Nano Banana 2.1"),
        "default_video_model": cfg.get("default_video_model", "Omni 1.1 Flash"),
        "default_duration": cfg.get("default_duration", 8),
        "default_count": cfg.get("default_count", 2)
    }


@app.post("/api/cookie")
async def api_set_cookie(req: CookieUpdateRequest):
    cookie_str = req.cookie.strip()
    set_cookie(cookie_str)
    
    # Thử kết nối kiểm tra
    client = GoogleFlowClient(cookie=cookie_str)
    ok, msg = client.init_session()
    credits_info = client.get_credits()
    
    return {
        "success": ok,
        "message": msg,
        "credits": credits_info.get("credits", 0),
        "credits_info": credits_info
    }


@app.get("/api/credits")
async def api_get_credits():
    cookie = get_cookie()
    if not cookie:
        return {
            "success": False,
            "credits": 0,
            "error": "Chưa cấu hình Cookie Google Flow. Vui lòng dán cookie vào phần Cấu hình."
        }
    
    client = get_client()
    res = client.get_credits()
    if not res.get("success"):
        return {
            "success": False,
            "credits": 0,
            "error": res.get("error", "Không thể lấy số điểm từ Google Flow")
        }
    return res


@app.get("/api/models")
async def api_get_models():
    return {
        "image_models": IMAGE_MODELS,
        "video_models": VIDEO_MODELS,
        "aspect_ratios_image": list(ASPECT_RATIOS_IMAGE.keys()),
        "aspect_ratios_video": list(ASPECT_RATIOS_VIDEO.keys()),
        "video_resolutions": list(VIDEO_RESOLUTIONS.keys()),
        "video_durations": VIDEO_DURATIONS,
        "batch_counts": [1, 2, 3, 4]
    }


@app.post("/api/generate/image")
async def api_generate_image(req: GenerateImageRequest):
    cookie = get_cookie()
    cfg = load_config()
    target_dir = Path(cfg.get("downloads_dir", DOWNLOADS_DIR))
    target_dir.mkdir(parents=True, exist_ok=True)

    if not cookie:
        return {
            "success": False,
            "error": "Chưa cấu hình Cookie Google Flow. Vui lòng vào mục Cấu hình để dán cookie tài khoản Google."
        }

    client = get_client()
    result = await asyncio.to_thread(
        client.generate_image,
        prompt=req.prompt,
        model=req.model,
        aspect_ratio=req.aspect_ratio,
        count=req.count,
        seed=req.seed,
        negative_prompt=req.negative_prompt
    )

    # Tự động tải về nếu được yêu cầu
    if result.get("success") and req.auto_download:
        for idx, img in enumerate(result.get("images", [])):
            url = img.get("url")
            if url:
                timestamp = int(time.time())
                safe_prompt = "".join([c if c.isalnum() else "_" for c in req.prompt[:30]]).strip("_")
                filename = f"flow_img_{timestamp}_{idx+1}_{safe_prompt}.webp"
                save_path = target_dir / filename
                
                # Thực hiện tải
                client_to_download = get_client() if cookie else demo_client
                dl_ok, dl_path = await asyncio.to_thread(client_to_download.download_media, url, save_path)
                if dl_ok:
                    img["local_file"] = Path(dl_path).name
                    img["local_url"] = f"/downloads/{Path(dl_path).name}"

    # Lấy lại số điểm sau khi tạo
    credits_info = (get_client() if cookie else demo_client).get_credits()
    result["credits_remaining"] = credits_info.get("credits", 0)
    return result


@app.post("/api/generate/video")
async def api_generate_video(req: GenerateVideoRequest):
    cookie = get_cookie()
    cfg = load_config()
    target_dir = Path(cfg.get("downloads_dir", DOWNLOADS_DIR))
    target_dir.mkdir(parents=True, exist_ok=True)

    if not cookie:
        return {
            "success": False,
            "error": "Chưa cấu hình Cookie Google Flow. Vui lòng vào mục Cấu hình để dán cookie tài khoản Google."
        }

    client = get_client()
    result = await asyncio.to_thread(
        client.generate_video,
        prompt=req.prompt,
        model=req.model,
        aspect_ratio=req.aspect_ratio,
        resolution=req.resolution,
        duration=req.duration,
        count=req.count,
        start_image_url=req.start_image_url,
        end_image_url=req.end_image_url,
        seed=req.seed
    )

    # Tự động tải về nếu được yêu cầu
    if result.get("success") and req.auto_download:
        for idx, vid in enumerate(result.get("videos", [])):
            url = vid.get("url")
            if url:
                timestamp = int(time.time())
                safe_prompt = "".join([c if c.isalnum() else "_" for c in req.prompt[:30]]).strip("_")
                filename = f"flow_video_{timestamp}_{idx+1}_{safe_prompt}.mp4"
                save_path = target_dir / filename
                
                client_to_download = get_client() if cookie else demo_client
                dl_ok, dl_path = await asyncio.to_thread(client_to_download.download_media, url, save_path)
                if dl_ok:
                    vid["local_file"] = Path(dl_path).name
                    vid["local_url"] = f"/downloads/{Path(dl_path).name}"

    # Lấy lại số điểm sau khi tạo
    credits_info = (get_client() if cookie else demo_client).get_credits()
    result["credits_remaining"] = credits_info.get("credits", 0)
    return result


@app.post("/api/download")
async def api_download_media(req: DownloadRequest):
    cfg = load_config()
    target_dir = Path(cfg.get("downloads_dir", DOWNLOADS_DIR))
    target_dir.mkdir(parents=True, exist_ok=True)

    ext = ".mp4" if req.media_type == "video" else ".jpg"
    filename = req.filename or f"flow_download_{int(time.time())}{ext}"
    if not filename.endswith(ext):
        filename += ext
    save_path = target_dir / filename

    cookie = get_cookie()
    client = get_client() if cookie else demo_client
    ok, path_or_err = client.download_media(req.url, save_path)
    
    if ok:
        return {
            "success": True,
            "filename": filename,
            "path": str(path_or_err),
            "local_url": f"/downloads/{filename}"
        }
    return {
        "success": False,
        "error": path_or_err
    }


@app.get("/api/gallery")
async def api_get_gallery():
    """Lấy danh sách các tệp đã tải trong thư mục downloads."""
    cfg = load_config()
    target_dir = Path(cfg.get("downloads_dir", DOWNLOADS_DIR))
    if not target_dir.exists():
        return {"items": []}

    items = []
    files = sorted(target_dir.glob("*"), key=os.path.getmtime, reverse=True)
    for f in files:
        if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm"]:
            media_type = "video" if f.suffix.lower() in [".mp4", ".webm"] else "image"
            stat = f.stat()
            items.append({
                "filename": f.name,
                "url": f"/downloads/{f.name}",
                "type": media_type,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            })
    return {"items": items, "count": len(items)}


@app.post("/api/open-folder")
async def api_open_folder():
    """Mở thư mục lưu trữ tải về trực tiếp trên máy tính Windows."""
    cfg = load_config()
    target_dir = Path(cfg.get("downloads_dir", DOWNLOADS_DIR))
    try:
        if sys.platform == "win32":
            os.startfile(str(target_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(target_dir)])
        else:
            subprocess.run(["xdg-open", str(target_dir)])
        return {"success": True, "message": f"Đã mở thư mục {target_dir}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/upload-frame")
async def api_upload_frame(file: UploadFile = File(...)):
    """Tải ảnh tham chiếu / Start Frame từ máy lên."""
    ext = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"frame_{int(time.time())}_{file.filename}"
    save_path = UPLOADS_DIR / filename
    
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "success": True,
        "filename": filename,
        "url": f"/uploads/{filename}",
        "path": str(save_path)
    }

# Mount uploads static files
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=7860, reload=True)
