import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
DEFAULT_DOWNLOADS_DIR = BASE_DIR / "downloads"

DEFAULT_CONFIG: Dict[str, Any] = {
    "cookie": "",
    "downloads_dir": str(DEFAULT_DOWNLOADS_DIR),
    "auto_download": True,
    "default_image_model": "Nano Banana 2.1",
    "default_video_model": "Omni 1.1 Flash",
    "default_image_aspect_ratio": "16:9",
    "default_video_aspect_ratio": "16:9",
    "default_resolution": "720p",
    "default_duration": 8,
    "default_count": 1,
    "default_video_count": 1,
    "theme": "dark",
    "language": "vi"
}

def load_config() -> Dict[str, Any]:
    """Tải cấu hình từ config.json hoặc khởi tạo mặc định."""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception as e:
            print(f"[Warning] Không thể đọc config.json: {e}")
    
    # Đảm bảo thư mục downloads tồn tại
    downloads_path = Path(config.get("downloads_dir", DEFAULT_DOWNLOADS_DIR))
    downloads_path.mkdir(parents=True, exist_ok=True)
    
    return config

def save_config(new_config: Dict[str, Any]) -> bool:
    """Lưu cấu hình vào config.json."""
    try:
        current = load_config()
        current.update(new_config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Error] Không thể lưu config.json: {e}")
        return False

def get_cookie() -> str:
    """Lấy cookie hiện tại từ config hoặc biến môi trường."""
    env_cookie = os.getenv("GOOGLE_FLOW_COOKIE", "")
    if env_cookie:
        return env_cookie
    cfg = load_config()
    return cfg.get("cookie", "").strip()

def set_cookie(cookie_str: str) -> bool:
    """Cập nhật cookie."""
    return save_config({"cookie": cookie_str.strip()})
