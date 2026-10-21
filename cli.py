import argparse
import sys
import os
import time
from pathlib import Path

# Đảm bảo mã hóa UTF-8 cho Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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

def print_header():
    print("=" * 65)
    print("      GOOGLE FLOW AI STUDIO - CLI TOOL (IMAGEN & VEO)")
    print("=" * 65)

def cmd_credits(args):
    cookie = get_cookie()
    if not cookie:
        print("[!] Chưa cấu hình Cookie Google Flow. Đang chạy chế độ Demo.")
        client = DemoFlowClient()
    else:
        client = GoogleFlowClient(cookie=cookie)

    print("[*] Đang truy vấn số điểm từ Google Flow...")
    res = client.get_credits()
    if res.get("success"):
        credits = res.get("credits", 0)
        tier = res.get("tier", "Standard")
        print(f"[✓] Số điểm còn lại: {credits} credits (Gói: {tier})")
    else:
        print(f"[x] Lỗi lấy số điểm: {res.get('error', 'Không xác định')}")

def cmd_models(args):
    print("\n--- DANH SÁCH MÔ HÌNH ẢNH (GOOGLE FLOW) ---")
    for m in IMAGE_MODELS:
        print(f" • {m['name']:<24} [{m['badge']}] | {m['desc']}")

    print("\n--- DANH SÁCH MÔ HÌNH VIDEO (GOOGLE FLOW) ---")
    for m in VIDEO_MODELS:
        print(f" • {m['name']:<24} [{m['badge']}] | {m['desc']}")
    
    print("\n--- THỜI LƯỢNG & ĐỘ PHÂN GIẢI VIDEO ---")
    print(f" • Thời lượng hỗ trợ : {', '.join([str(d) + 's' for d in VIDEO_DURATIONS])} (Mặc định: 8s)")
    print(f" • Độ phân giải      : {', '.join(VIDEO_RESOLUTIONS.keys())} (Mặc định: 720p)")
    print(" • Số lượng sinh     : x1, x2 (Mặc định), x3, x4")

    print("\n--- TỈ LỆ KHUNG HÌNH (ASPECT RATIOS) ---")
    print(" • Ảnh  :", ", ".join(ASPECT_RATIOS_IMAGE.keys()))
    print(" • Video:", ", ".join(ASPECT_RATIOS_VIDEO.keys()))

def cmd_set_cookie(args):
    cookie_str = args.cookie.strip()
    if not cookie_str:
        print("[x] Cookie không được để trống!")
        return
    set_cookie(cookie_str)
    print("[*] Đang kiểm tra cookie với máy chủ Google Flow...")
    client = GoogleFlowClient(cookie=cookie_str)
    ok, msg = client.init_session()
    if ok:
        res = client.get_credits()
        print(f"[✓] Lưu cookie thành công! Số điểm hiện có: {res.get('credits', 0)} credits.")
    else:
        print(f"[!] Cảnh báo: {msg}")

def cmd_image(args):
    cookie = get_cookie()
    client = GoogleFlowClient(cookie=cookie) if cookie else DemoFlowClient()

    print(f"[*] Đang yêu cầu tạo {args.count} ảnh...")
    print(f"    - Prompt: \"{args.prompt}\"")
    print(f"    - Model : {args.model}")
    print(f"    - Tỉ lệ : {args.ratio}")

    res = client.generate_image(
        prompt=args.prompt,
        model=args.model,
        aspect_ratio=args.ratio,
        count=args.count,
        seed=args.seed,
        negative_prompt=args.negative or ""
    )

    if not res.get("success"):
        print(f"[x] Tạo ảnh thất bại: {res.get('error')}")
        return

    images = res.get("images", [])
    if not images:
        print(f"[x] Tạo ảnh thất bại: Không nhận được URL ảnh từ Google Flow.")
        return

    print(f"[✓] Đã tạo thành công {len(images)} ảnh!")

    out_dir = Path(args.output or DEFAULT_DOWNLOADS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, img in enumerate(images):
        url = img.get("url")
        print(f"    [{idx+1}] URL: {url}")
        if args.download:
            filename = f"flow_img_{int(time.time())}_{idx+1}.jpg"
            save_path = out_dir / filename
            dl_ok, path = client.download_media(url, save_path)
            if dl_ok:
                print(f"        -> Đã tải về: {path}")
            else:
                print(f"        -> Lỗi tải: {path}")

    # Cập nhật số điểm
    c_res = client.get_credits()
    print(f"[i] Số điểm còn lại: {c_res.get('credits', 'N/A')} credits")

def cmd_video(args):
    cookie = get_cookie()
    client = GoogleFlowClient(cookie=cookie) if cookie else DemoFlowClient()

    print(f"[*] Đang yêu cầu tạo {args.count} video...")
    print(f"    - Prompt      : \"{args.prompt}\"")
    print(f"    - Model       : {args.model}")
    print(f"    - Tỉ lệ       : {args.ratio}")
    print(f"    - Độ phân giải: {args.resolution}")
    print(f"    - Thời lượng  : {args.duration}s")
    print(f"    - Số lượng    : {args.count}")

    res = client.generate_video(
        prompt=args.prompt,
        model=args.model,
        aspect_ratio=args.ratio,
        resolution=args.resolution,
        duration=args.duration,
        count=args.count,
        start_image_url=args.start_image,
        end_image_url=args.end_image,
        seed=args.seed
    )

    if not res.get("success"):
        print(f"[x] Tạo video thất bại: {res.get('error')}")
        return

    videos = res.get("videos", [])
    if not videos:
        if res.get("status") == "PROCESSING":
            print(f"[✓] Yêu cầu tạo {args.count} video đã được gửi thành công đến Google Flow!")
            print(f"    - Trạng thái: {res.get('message')}")
            print("    - Lưu ý     : Video Veo/Omni đang được render dưới nền trên cụm máy chủ Google.")
            c_res = client.get_credits()
            print(f"[i] Số điểm còn lại: {c_res.get('credits', 'N/A')} credits")
            return
        print(f"[x] Tạo video thất bại: {res.get('error', 'Không nhận được dữ liệu video từ Google Flow')}")
        return

    print(f"[✓] Đã nhận kết quả video từ Google Flow ({len(videos)} video)!")

    out_dir = Path(args.output or DEFAULT_DOWNLOADS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, vid in enumerate(videos):
        url = vid.get("url")
        url_1080 = vid.get("url_1080p")
        mid = vid.get("media_id")
        
        target_url = url
        quality_label = "720p"
        if getattr(args, "quality", "1080p") == "1080p":
            if url_1080:
                target_url = url_1080
                quality_label = "1080p (1K)"
            elif mid and hasattr(client, "get_media"):
                cached = client.get_media(f"{mid}_upsampled")
                if cached and cached.get("url"):
                    target_url = cached["url"]
                    quality_label = "1080p (1K)"

        print(f"    [{idx+1}] URL: {url}")
        if quality_label == "1080p (1K)":
            print(f"        -> Bản 1080p Upscaled: {target_url}")

        if args.download:
            suffix = "_1080p" if quality_label.startswith("1080p") else ""
            filename = f"flow_video_{int(time.time())}_{idx+1}{suffix}.mp4"
            save_path = out_dir / filename
            dl_ok, path = client.download_media(target_url, save_path)
            if dl_ok:
                print(f"        -> [✓] Đã tải về bản {quality_label}: {path}")
            else:
                print(f"        -> [x] Lỗi tải: {path}")

    # Cập nhật số điểm
    c_res = client.get_credits()
    print(f"[i] Số điểm còn lại: {c_res.get('credits', 'N/A')} credits")


def cmd_upscale(args):
    cookie = get_cookie()
    if not cookie:
        print("[x] Cần cấu hình cookie để nâng cấp video 1080p!")
        return

    import re
    mid = args.media_id
    m = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', mid)
    if m:
        mid = m.group(1)

    print(f"[*] Đang yêu cầu Google Flow nâng cấp video {mid[:8]} lên 1080p (1K)...")
    from flow_client import GoogleFlowClient
    from flow_worker import upscale_video_1080p
    fc = GoogleFlowClient(cookie=cookie)
    proj_id = fc.get_or_create_project_id()
    
    url_1080 = upscale_video_1080p(cookie, proj_id, mid)
    if not url_1080:
        print("[x] Không thể lấy video 1080p từ Google Flow.")
        return

    print(f"[✓] Đã nhận stream 1080p: {url_1080[:80]}...")
    out_dir = Path(args.output or DEFAULT_DOWNLOADS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"flow_video_{mid[:8]}_1080p.mp4"
    ok, p = fc.download_media(url_1080, out_file)
    if ok:
        print(f"[✓] Tải thành công video 1080p (1K): {p}")
    else:
        print(f"[x] Lỗi tải: {p}")

def main():
    parser = argparse.ArgumentParser(description="Google Flow AI Studio - Công Cụ Tạo Ảnh & Video AI")
    subparsers = parser.add_subparsers(dest="command", help="Lệnh chức năng")

    # credits
    p_credits = subparsers.add_parser("credits", help="Xem số điểm còn lại")
    p_credits.set_defaults(func=cmd_credits)

    # models
    p_models = subparsers.add_parser("models", help="Xem danh sách mô hình hỗ trợ")
    p_models.set_defaults(func=cmd_models)

    # set-cookie
    p_cookie = subparsers.add_parser("set-cookie", help="Lưu Cookie Google Flow")
    p_cookie.add_argument("cookie", help="Chuỗi cookie Google Flow")
    p_cookie.set_defaults(func=cmd_set_cookie)

    # image
    p_img = subparsers.add_parser("image", help="Tạo ảnh AI từ prompt")
    p_img.add_argument("prompt", help="Mô tả hình ảnh")
    p_img.add_argument("--model", default="Nano Banana 2.1", help="Mô hình (Nano Banana 2.1, Nano Banana Pro, Nano Banana 2 Lite)")
    p_img.add_argument("--ratio", default="16:9", choices=["16:9", "9:16", "1:1", "4:3", "3:4"], help="Tỉ lệ khung hình (16:9, 9:16, 1:1, 4:3, 3:4)")
    p_img.add_argument("--count", type=int, default=2, choices=[1, 2, 3, 4], help="Số lượng ảnh tạo (1, 2, 3, 4 - Mặc định: 2)")
    p_img.add_argument("--seed", type=int, default=None, help="Hạt giống ngẫu nhiên")
    p_img.add_argument("--negative", default="", help="Prompt loại trừ")
    p_img.add_argument("--output", default=None, help="Thư mục lưu trữ")
    p_img.add_argument("--download", action="store_true", default=True, help="Tự động tải về máy")
    p_img.set_defaults(func=cmd_image)

    # video
    p_vid = subparsers.add_parser("video", help="Tạo video AI từ prompt")
    p_vid.add_argument("prompt", help="Mô tả kịch bản video")
    p_vid.add_argument("--model", default="Omni 1.1 Flash", help="Mô hình (Omni 1.1 Flash, Veo 3.1 - Fast, Veo 3.1 - Lite, Veo 3.1 - Quality)")
    p_vid.add_argument("--ratio", default="16:9", choices=["16:9", "9:16"], help="Tỉ lệ khung hình (16:9, 9:16)")
    p_vid.add_argument("--resolution", default="720p", choices=["720p", "360p"], help="Độ phân giải (720p, 360p - Mặc định: 720p)")
    p_vid.add_argument("--quality", default="1080p", choices=["1080p", "720p"], help="Chất lượng tải về máy: 1080p (1K Full HD) hoặc 720p (Mặc định: 1080p)")
    p_vid.add_argument("--duration", type=int, default=8, choices=[4, 6, 8, 10], help="Thời lượng giây (4, 6, 8, 10 - Mặc định: 8)")
    p_vid.add_argument("--count", type=int, default=1, choices=[1, 2, 3, 4], help="Số lượng video tạo (1, 2, 3, 4 - Mặc định: 1)")
    p_vid.add_argument("--start-image", default=None, help="Đường dẫn hoặc URL ảnh bắt đầu (Start Frame)")
    p_vid.add_argument("--end-image", default=None, help="Đường dẫn hoặc URL ảnh kết thúc (End Frame)")
    p_vid.add_argument("--seed", type=int, default=None, help="Hạt giống ngẫu nhiên")
    p_vid.add_argument("--output", default=None, help="Thư mục lưu trữ")
    p_vid.add_argument("--download", action="store_true", default=True, help="Tự động tải về máy")
    p_vid.set_defaults(func=cmd_video)

    # upscale
    p_upscale = subparsers.add_parser("upscale", help="Nâng cấp video lên 1080p (1K Full HD) từ Flow")
    p_upscale.add_argument("media_id", help="UUID của video hoặc URL stream video")
    p_upscale.add_argument("--output", default=None, help="Thư mục lưu trữ")
    p_upscale.set_defaults(func=cmd_upscale)

    args = parser.parse_args()
    if not args.command:
        print_header()
        parser.print_help()
        sys.exit(0)

    args.func(args)

if __name__ == "__main__":
    main()
