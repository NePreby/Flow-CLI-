import sys
import os
import time
import uuid
import re
import asyncio
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright

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

def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            msg = " ".join(str(a) for a in args)
            print(msg.encode("ascii", errors="replace").decode("ascii"), **kwargs)
        except Exception:
            pass

def _parse_cookie_list(cookie_str: str) -> List[Dict[str, Any]]:
    """Phân tích cookie string thành danh sách cookie hợp lệ cho Playwright."""
    cookies = []
    for item in cookie_str.strip().split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            k, v = k.strip(), v.strip()
            if k:
                cookies.append({
                    "name": k,
                    "value": v,
                    "domain": ".google.com",
                    "path": "/",
                    "secure": True,
                    "sameSite": "None"
                })
    return cookies

def _run_in_thread(func, *args, **kwargs):
    """Đảm bảo hàm chạy trên một OS worker thread độc lập với Proactor policy trên Windows."""
    def _thread_target():
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        return func(*args, **kwargs)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_thread_target)
            return future.result()
    else:
        return _thread_target()

def _find_start_generation_button(page):
    """Tìm chính xác nút Start Generation đang kích hoạt."""
    btns = page.locator('button').all()
    for b in btns:
        try:
            if not b.is_visible() or b.is_disabled():
                continue
            al = (b.get_attribute('aria-label') or '').lower()
            txt = b.inner_text().strip().lower()
            if 'generation' in al or 'arrow_forward' in txt:
                return b
        except Exception:
            continue
    return None

def _generate_image_native_impl(
    cookie_str: str,
    project_id: str,
    prompt: str,
    model: str = "Nano Banana 2.1",
    aspect_ratio: str = "16:9",
    count: int = 1,
    timeout_sec: int = 50
) -> Dict[str, Any]:
    """Tạo ảnh trực tiếp trên Google Flow canvas sử dụng headless browser."""
    if not cookie_str:
        return {"success": False, "error": "Chưa cấu hình Google Flow Cookie"}

    needed = max(1, count)
    captured_map = {}  # base_url -> clean_url
    existing_img_bases = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            context.add_cookies(_parse_cookie_list(cookie_str))

            page = context.new_page()

            project_url = f"https://flow.google.com/project/{project_id}"
            page.goto(project_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            # Thu thập toàn bộ base URL của ảnh đã có sẵn trên canvas
            for img in page.query_selector_all('img'):
                src = img.get_attribute('src') or ''
                if '/asb/' in src:
                    existing_img_bases.add(src.split('=')[0])

            # Cấu hình Settings (Image, Aspect Ratio, Count, Model)
            settings_btn = page.locator('button[aria-label="Settings trigger"]').first
            if settings_btn.is_visible():
                settings_btn.click()
                page.wait_for_timeout(400)

                img_tab = page.locator('.cdk-overlay-container button:has-text("Image")').first
                if img_tab.is_visible():
                    img_tab.click()
                    page.wait_for_timeout(200)

                # Chọn Aspect Ratio
                ratio_clean = aspect_ratio.replace(" ", "")
                ratio_btn = page.locator(f'.cdk-overlay-container flow-toggles[aria-label="Aspect ratio"] button:has-text("{ratio_clean}")').first
                if not ratio_btn.is_visible():
                    ratio_btn = page.locator(f'.cdk-overlay-container button:has-text("{ratio_clean}")').first
                if ratio_btn.is_visible():
                    ratio_btn.click()
                    page.wait_for_timeout(200)

                # Chọn Model nếu được chỉ định
                if model:
                    model_btn = page.locator('.cdk-overlay-container button[aria-label="Select model family"]').first
                    if not model_btn.is_visible():
                        model_btn = page.locator('.cdk-overlay-container button:has-text("Nano Banana"), .cdk-overlay-container button:has-text("🍌")').first
                    if model_btn.is_visible():
                        model_btn.click()
                        page.wait_for_timeout(300)
                        target_model_btn = page.locator(f'[role="menuitem"]:has-text("{model}"), .mat-mdc-menu-item:has-text("{model}")').first
                        if target_model_btn.is_visible():
                            target_model_btn.click()
                            page.wait_for_timeout(200)
                        else:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(200)

                # Chọn số lượng ảnh (x1, x2, x3, x4)
                count_str = f"x{max(1, min(4, count))}"
                count_btn = page.locator(f'.cdk-overlay-container flow-toggles[aria-label="Output count"] button:has-text("{count_str}")').first
                if not count_btn.is_visible():
                    count_btn = page.locator(f'.cdk-overlay-container button:has-text("{count_str}")').first
                if count_btn.is_visible():
                    count_btn.click()
                    page.wait_for_timeout(200)

                page.keyboard.press("Escape")
                page.wait_for_timeout(400)

            # Lắng nghe response network cho ảnh mới
            def on_response(resp):
                url = resp.url
                if "/asb/" in url and resp.status == 200:
                    base = url.split("=")[0]
                    if base not in existing_img_bases and base not in captured_map:
                        clean_url = f"{base}=s1600-rw"
                        captured_map[base] = clean_url

            page.on("response", on_response)

            # Điền prompt vào ô ProseMirror
            pm = page.locator("div.ProseMirror").first
            pm.click()
            pm.fill(prompt)
            page.wait_for_timeout(400)

            # Bấm nút Start generation
            gen_btn = _find_start_generation_button(page)
            if not gen_btn:
                gen_btn = page.locator('button[aria-label*="generation" i]').first
            gen_btn.click()

            # Chờ ảnh render xong với cơ chế đồng bộ hóa canvas (reload polling)
            start_time = time.time()
            last_log_time = 0

            while time.time() - start_time < timeout_sec:
                page.wait_for_timeout(2000)
                elapsed = int(time.time() - start_time)
                if elapsed - last_log_time >= 15:
                    last_log_time = elapsed
                    _safe_print(f"[*] Dang cho Google Flow render ({elapsed}s / {timeout_sec}s)... (Da nhan {len(captured_map)}/{needed} anh)")

                # 1. Quét tìm các thẻ tile ở hàng đầu (vị trí mới nhất trên canvas)
                try:
                    footers = page.locator('.footer-left')
                    total_f = footers.count()
                    for i in range(min(needed * 2, total_f)):
                        f = footers.nth(i)
                        # Bỏ qua nếu là video tile
                        is_vid = f.evaluate('''el => {
                            const icon = el.querySelector("mat-icon")?.textContent?.trim() || "";
                            return icon === "videocam" || icon === "play_circle" || icon === "play_arrow";
                        }''')
                        if is_vid:
                            continue

                        img_src = f.evaluate('''el => {
                            const card = el.closest("flow-tile-container") || el.closest("flow-image-tile") || el.parentElement.parentElement.parentElement;
                            const im = card ? card.querySelector("img") : null;
                            return (im && im.src && im.src.includes("/asb/")) ? im.src : null;
                        }''')
                        if img_src and '/asb/' in img_src:
                            base = img_src.split('=')[0]
                            if base not in existing_img_bases and base not in captured_map:
                                captured_map[base] = f"{base}=s1600-rw"
                except Exception:
                    pass

                # 2. Quét bổ sung toàn bộ thẻ img mới trên DOM
                try:
                    for img in page.query_selector_all('img'):
                        src = img.get_attribute('src') or ''
                        if '/asb/' in src:
                            base = src.split('=')[0]
                            if base not in existing_img_bases and base not in captured_map:
                                captured_map[base] = f"{base}=s1600-rw"
                except Exception:
                    pass

                # Thoát ngay khi đã thu thập ĐỦ số lượng ảnh độc lập
                if len(captured_map) >= needed:
                    break

                # 3. Sau 12s đầu, định kỳ làm mới trang mỗi 12s để đồng bộ trạng thái mới nhất từ server
                if elapsed >= 12 and (elapsed % 12) < 3:
                    try:
                        page.goto(project_url, wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(2500)
                    except Exception:
                        pass

            # Nếu chưa đủ số lượng ảnh, chờ thêm 3s và quét lại lần cuối
            if len(captured_map) < needed:
                page.wait_for_timeout(3000)
                try:
                    for img in page.query_selector_all('img'):
                        src = img.get_attribute('src') or ''
                        if '/asb/' in src:
                            base = src.split('=')[0]
                            if base not in existing_img_bases and base not in captured_map:
                                captured_map[base] = f"{base}=s1600-rw"
                except Exception:
                    pass

            # Kiểm tra kết quả thu được
            results = list(captured_map.values())[:needed]

            browser.close()
            if results:
                return {
                    "success": True,
                    "prompt": prompt,
                    "model": model,
                    "aspect_ratio": aspect_ratio,
                    "count": len(results),
                    "images": [{"url": u, "media_id": str(uuid.uuid4())} for u in results]
                }
            else:
                return {
                    "success": False,
                    "error": "Google Flow chưa hoàn thành sinh ảnh mới trong thời gian quy định (Timeout). Vui lòng thử lại với prompt khác hoặc giảm số lượng ảnh."
                }

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            with open("scratch/worker_last_error.log", "w", encoding="utf-8") as f:
                f.write(f"{type(e).__name__}: {repr(e)}\n{tb}")
        except Exception:
            pass
        return {"success": False, "error": f"Lỗi thực thi native Flow worker: {type(e).__name__}: {str(e)}"}

def _resolve_local_image_path(img_ref: Optional[str]) -> Optional[str]:
    """Chuyển đổi URL, tên file hoặc đường dẫn ảnh về đường dẫn file cục bộ thực tế."""
    if not img_ref:
        return None
    img_ref = str(img_ref).strip()
    if not img_ref:
        return None

    # 1. Đường dẫn file cục bộ trực tiếp
    p = Path(img_ref)
    if p.exists() and p.is_file():
        return str(p.resolve())

    # 2. Kiểm tra trong các thư mục mặc định (uploads, downloads)
    clean_name = Path(img_ref.lstrip("/\\")).name
    for parent in [".", "uploads", "downloads"]:
        cand = Path(parent) / clean_name
        if cand.exists() and cand.is_file():
            return str(cand.resolve())

    try:
        from config import UPLOADS_DIR, DOWNLOADS_DIR
        for d in [UPLOADS_DIR, DOWNLOADS_DIR]:
            cand = Path(d) / clean_name
            if cand.exists() and cand.is_file():
                return str(cand.resolve())
    except Exception:
        pass

    # 3. Tải từ HTTP/HTTPS URL về thư mục scratch tạm
    if img_ref.startswith("http://") or img_ref.startswith("https://"):
        try:
            import requests
            ext = ".png"
            if ".webp" in img_ref: ext = ".webp"
            elif ".jpg" in img_ref or ".jpeg" in img_ref: ext = ".jpg"
            temp_path = Path("scratch") / f"frame_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            r = requests.get(img_ref, timeout=30)
            if r.status_code == 200:
                with open(temp_path, "wb") as f:
                    f.write(r.content)
                return str(temp_path.resolve())
        except Exception:
            pass

    return None

def _upload_frame_to_chip(page, chip_label: str, file_path: str) -> bool:
    """Mở chip (Start hoặc End), kích hoạt file chooser, chờ upload hoàn tất, chọn item và bấm Add to prompt."""
    try:
        chip = page.locator(f'button.empty-chip:has-text("{chip_label}")').first
        if not chip.is_visible():
            chip = page.locator(f'button:has-text("{chip_label}")').first
        if not chip.is_visible():
            _safe_print(f"[!] Khong tim thay chip {chip_label}")
            return False
        chip.click()
        page.wait_for_timeout(800)

        up_btn = page.locator('.cdk-overlay-container button:has-text("Upload media")').first
        if not up_btn.is_visible():
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            return False

        with page.expect_file_chooser(timeout=5000) as fc_info:
            up_btn.click()
        fc = fc_info.value
        fc.set_files(file_path)

        # Chờ file hoàn tất tải lên Google Flow và xuất hiện ở đầu danh sách asset
        start_w = time.time()
        uploaded_item = None
        while time.time() - start_w < 35.0:
            items = page.locator('.cdk-overlay-container button.asset-item').all()
            if items:
                it0 = items[0]
                has_sp = it0.evaluate('el => !!el.querySelector("mat-spinner, .mat-mdc-progress-spinner")')
                txt = it0.text_content().strip()
                is_upl = "Uploading" in txt
                if not has_sp and not is_upl:
                    uploaded_item = it0
                    break
            page.wait_for_timeout(400)

        if not uploaded_item:
            _safe_print(f"[!] Upload file {Path(file_path).name} qua han thoi gian (timeout)")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            return False

        # Bắt buộc click vào item vừa upload để kích hoạt chọn (Google Flow không tự chọn file mới)
        uploaded_item.click()
        page.wait_for_timeout(600)

        add_btn = page.locator('.cdk-overlay-container button:has-text("Add to prompt")').first
        if add_btn.is_visible() and not add_btn.is_disabled():
            add_btn.click()
            page.wait_for_timeout(1200)
            _safe_print(f"[✓] Da them thanh cong {chip_label} Frame vao prompt: {Path(file_path).name}")
            return True
        else:
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            return False
    except Exception as e:
        _safe_print(f"[!] Loi khi upload frame {chip_label}: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False

def _generate_video_native_impl(
    cookie_str: str,
    project_id: str,
    prompt: str,
    model: str = "Omni 1.1 Flash",
    aspect_ratio: str = "16:9",
    duration: int = 8,
    resolution: str = "720p",
    count: int = 1,
    start_image_url: Optional[str] = None,
    end_image_url: Optional[str] = None,
    timeout_sec: int = 160
) -> Dict[str, Any]:
    """Thực thi tạo video qua Playwright với logic bắt ĐÚNG video mới của prompt."""
    if not cookie_str:
        return {"success": False, "error": "Chưa cấu hình Google Flow Cookie"}

    needed = max(1, count)
    captured_video_map = {}  # base_uuid_url -> full_presigned_url
    existing_video_bases = set()
    start_local_path = _resolve_local_image_path(start_image_url)
    end_local_path = _resolve_local_image_path(end_image_url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            context = browser.new_context(viewport={"width": 1400, "height": 900}, user_agent=user_agent)
            context.add_cookies(_parse_cookie_list(cookie_str))

            page = context.new_page()

            # Lắng nghe và thu thập video stream URL đã có sẵn khi nạp trang
            def on_initial_response(resp):
                u = resp.url
                if ("flow-content.google/video" in u or "googlevideo.com/videoplayback" in u) and resp.status in [200, 206]:
                    existing_video_bases.add(u.split("?")[0])

            page.on("response", on_initial_response)

            project_url = f"https://flow.google.com/project/{project_id}"
            page.goto(project_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3500)

            # Ngừng thu thập video cũ, chuyển sang theo dõi video mới
            page.remove_listener("response", on_initial_response)

            def on_new_response(resp):
                u = resp.url
                if ("flow-content.google/video" in u or "googlevideo.com/videoplayback" in u) and resp.status in [200, 206]:
                    base = u.split("?")[0]
                    if base not in existing_video_bases and base not in captured_video_map:
                        captured_video_map[base] = u
                        _safe_print(f"[✓] Da bat duoc stream video: {base[:60]}")

            page.on("response", on_new_response)

            # Cấu hình Settings (Video, Duration, Resolution, Count)
            settings_btn = page.locator('button[aria-label="Settings trigger"]').first
            if settings_btn.is_visible():
                settings_btn.click()
                page.wait_for_timeout(400)

                vid_tab = page.locator('.cdk-overlay-container button:has-text("Video")').first
                if vid_tab.is_visible():
                    vid_tab.click()
                    page.wait_for_timeout(400)

                ratio_clean = aspect_ratio.replace(" ", "")
                ratio_btn = page.locator(f'.cdk-overlay-container flow-toggles[aria-label="Aspect ratio"] button:has-text("{ratio_clean}")').first
                if not ratio_btn.is_visible():
                    ratio_btn = page.locator(f'.cdk-overlay-container button:has-text("{ratio_clean}")').first
                if ratio_btn.is_visible():
                    ratio_btn.click()
                    page.wait_for_timeout(200)

                dur_str = f"{duration}s"
                dur_btn = page.locator(f'.cdk-overlay-container flow-toggles[aria-label="Video duration"] button:has-text("{dur_str}")').first
                if not dur_btn.is_visible():
                    dur_btn = page.locator(f'.cdk-overlay-container button:has-text("{dur_str}")').first
                if dur_btn.is_visible():
                    dur_btn.click()
                    page.wait_for_timeout(200)

                res_btn = page.locator(f'.cdk-overlay-container flow-toggles[aria-label="Video resolution"] button:has-text("{resolution}")').first
                if not res_btn.is_visible():
                    res_btn = page.locator(f'.cdk-overlay-container button:has-text("{resolution}")').first
                if res_btn.is_visible():
                    res_btn.click()
                    page.wait_for_timeout(200)

                # Chọn Model nếu được chỉ định
                if model:
                    model_btn = page.locator('.cdk-overlay-container button[aria-label="Select model family"]').first
                    if model_btn.is_visible():
                        model_btn.click()
                        page.wait_for_timeout(300)
                        target_model_btn = page.locator(f'[role="menuitem"]:has-text("{model}"), .mat-mdc-menu-item:has-text("{model}")').first
                        if target_model_btn.is_visible():
                            target_model_btn.click()
                            page.wait_for_timeout(200)
                        else:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(200)

                # Chọn chế độ Video Type (Frames hoặc Text)
                if start_local_path or end_local_path:
                    frames_btn = page.locator('.cdk-overlay-container flow-toggles[aria-label="Video type"] button:has-text("Frames")').first
                    if not frames_btn.is_visible():
                        frames_btn = page.locator('.cdk-overlay-container button:has-text("Frames")').first
                    if frames_btn.is_visible():
                        frames_btn.click()
                        page.wait_for_timeout(300)
                else:
                    text_mode_btn = page.locator('.cdk-overlay-container flow-toggles[aria-label="Video type"] button:has-text("Text")').first
                    if not text_mode_btn.is_visible():
                        text_mode_btn = page.locator('.cdk-overlay-container button:has-text("Text")').first
                    if text_mode_btn.is_visible():
                        text_mode_btn.click()
                        page.wait_for_timeout(300)

                count_str = f"x{max(1, min(4, count))}"
                count_btn = page.locator(f'.cdk-overlay-container flow-toggles[aria-label="Output count"] button:has-text("{count_str}")').first
                if not count_btn.is_visible():
                    count_btn = page.locator(f'.cdk-overlay-container button:has-text("{count_str}")').first
                if count_btn.is_visible():
                    count_btn.click()
                    page.wait_for_timeout(200)

                page.keyboard.press("Escape")
                page.wait_for_timeout(400)

            # Dọn dẹp chip ảnh cũ nếu có trong thanh prompt trước khi nạp frame mới
            if start_local_path or end_local_path:
                try:
                    for c in page.locator('flow-image-ingredient-chip').all():
                        rm = c.locator('button[aria-label*="Remove" i], button:has-text("cancel"), mat-icon:has-text("cancel")').first
                        if rm.is_visible():
                            rm.click()
                            page.wait_for_timeout(300)
                except Exception:
                    pass

            # Đính kèm Start Frame (Ảnh bắt đầu) nếu có
            if start_local_path:
                _safe_print(f"[*] Dang tai Start Frame len Google Flow: {Path(start_local_path).name}...")
                _upload_frame_to_chip(page, "Start", start_local_path)

            # Đính kèm End Frame (Ảnh kết thúc) nếu có
            if end_local_path:
                _safe_print(f"[*] Dang tai End Frame len Google Flow: {Path(end_local_path).name}...")
                _upload_frame_to_chip(page, "End", end_local_path)

            # Điền prompt nếu có
            if prompt:
                pm = page.locator("div.ProseMirror").first
                if pm.is_visible():
                    pm.click()
                    pm.fill(prompt)
                    page.wait_for_timeout(400)

            # Bấm Start generation
            gen_btn = _find_start_generation_button(page)
            if not gen_btn:
                gen_btn = page.locator('button[aria-label*="generation" i]').first
            if gen_btn and gen_btn.is_visible():
                gen_btn.click()

            # Chờ tile mới ứng với prompt xuất hiện và hoàn thành render
            start_time = time.time()
            clicked_tiles = set()
            last_log_time = 0

            while time.time() - start_time < timeout_sec:
                page.wait_for_timeout(3000)
                elapsed = int(time.time() - start_time)
                if elapsed - last_log_time >= 15:
                    last_log_time = elapsed
                    _safe_print(f"[*] Dang cho Google Flow render video ({elapsed}s / {timeout_sec}s)... (Da nhan {len(captured_video_map)}/{needed} video)")

                # Quét trực tiếp các tile flow-tile-container trên canvas
                try:
                    tiles = page.locator('flow-tile-container').all()
                    for i in range(min(needed * 2, len(tiles))):
                        if i in clicked_tiles:
                            continue
                        t = tiles[i]
                        # Kiểm tra xem có icon video không
                        is_vid = t.locator('mat-icon:has-text("play_arrow"), mat-icon:has-text("play_circle"), mat-icon:has-text("videocam")').count() > 0
                        if not is_vid:
                            continue

                        # Kiểm tra thumbnail video đã render hoàn tất
                        has_thumb = t.evaluate('''el => {
                            const im = el.querySelector("img");
                            return !!(im && im.src && im.src.includes("/asb/"));
                        }''')
                        if has_thumb:
                            t.scroll_into_view_if_needed()
                            page.wait_for_timeout(300)
                            b = t.bounding_box()
                            if b:
                                prev_count = len(captured_video_map)
                                # Click ngay giữa tile để phát video và kích hoạt stream network
                                page.mouse.click(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
                                click_start = time.time()
                                while time.time() - click_start < 4.0:
                                    if len(captured_video_map) > prev_count:
                                        break
                                    page.wait_for_timeout(300)

                                # Kích hoạt lôi tùy chọn 1080p Upscaled qua menu Download trên modal video
                                try:
                                    dl_btn = page.locator('button[aria-label*="download" i], button:has(mat-icon:has-text("download"))').first
                                    if dl_btn.is_visible():
                                        dl_btn.click()
                                        page.wait_for_timeout(400)
                                        opt_1080 = page.locator('.cdk-overlay-container [role="menuitem"]:has-text("1080p"), .cdk-overlay-container button:has-text("1080p")').first
                                        if opt_1080.is_visible():
                                            _safe_print("[*] Dang kich hoat 1080p Upscaled tren Google Flow...")
                                            opt_1080.click()
                                            up_st = time.time()
                                            while time.time() - up_st < 6.0:
                                                if any("_upsampled" in u for u in captured_video_map.values()):
                                                    break
                                                page.wait_for_timeout(300)
                                except Exception:
                                    pass

                                page.keyboard.press("Escape")
                                page.wait_for_timeout(500)
                                if len(captured_video_map) > prev_count:
                                    clicked_tiles.add(i)
                except Exception:
                    pass

                if len(captured_video_map) >= needed:
                    break

                # Định kỳ làm mới trang mỗi 45s sau 60s đầu để đồng bộ video tiles mới nhất từ server nếu chưa nhận được
                if elapsed >= 60 and (elapsed % 45) < 4 and len(captured_video_map) < needed:
                    try:
                        page.goto(project_url, wait_until="domcontentloaded", timeout=25000)
                        page.wait_for_timeout(3000)
                        clicked_tiles.clear()
                    except Exception:
                        pass

            browser.close()

            # Phân loại video gốc và phiên bản 1080p upsampled
            video_map_by_id = {}
            for base, full_url in captured_video_map.items():
                clean_base = base.split("?")[0]
                if "_upsampled" in clean_base:
                    mid = clean_base.split("/")[-1].replace("_upsampled", "")
                    if mid not in video_map_by_id:
                        video_map_by_id[mid] = {}
                    video_map_by_id[mid]["url_1080p"] = full_url
                else:
                    mid = clean_base.split("/")[-1]
                    if mid not in video_map_by_id:
                        video_map_by_id[mid] = {}
                    video_map_by_id[mid]["url"] = full_url

            video_items = []
            for mid, info in video_map_by_id.items():
                u_main = info.get("url") or info.get("url_1080p")
                video_items.append({
                    "media_id": mid,
                    "url": u_main,
                    "url_720p": info.get("url") or u_main,
                    "url_1080p": info.get("url_1080p")
                })

            if video_items:
                return {
                    "success": True,
                    "prompt": prompt,
                    "model": model,
                    "aspect_ratio": aspect_ratio,
                    "duration": duration,
                    "resolution": resolution,
                    "count": len(video_items[:needed]),
                    "videos": video_items[:needed]
                }
            else:
                # Video đã được gửi thành công và đang render async trên Google server
                return {
                    "success": True,
                    "status": "PROCESSING",
                    "prompt": prompt,
                    "model": model,
                    "aspect_ratio": aspect_ratio,
                    "duration": duration,
                    "resolution": resolution,
                    "count": count,
                    "message": "Yêu cầu tạo video đã được gửi thành công đến Google Flow. Video đang được xử lý trên máy chủ Google (khoảng 1 - 2 phút).",
                    "videos": []
                }

    except Exception as e:
        return {"success": False, "error": f"Lỗi thực thi native Video worker: {str(e)}"}

def generate_image_native(*args, **kwargs) -> Dict[str, Any]:
    """Hàm bọc an toàn chạy ngoài asyncio loop cho generate_image."""
    return _run_in_thread(_generate_image_native_impl, *args, **kwargs)

def generate_video_native(*args, **kwargs) -> Dict[str, Any]:
    """Hàm bọc an toàn chạy ngoài asyncio loop cho generate_video."""
    return _run_in_thread(_generate_video_native_impl, *args, **kwargs)

def _sync_canvas_videos_impl(cookie_str: str, project_id: str, max_videos: int = 4) -> List[Dict[str, Any]]:
    """Quét canvas và lấy link stream của các video mới nhất trong dự án."""
    if not cookie_str:
        return []
    videos = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            context = browser.new_context(viewport={"width": 1400, "height": 900}, user_agent=user_agent)
            context.add_cookies(_parse_cookie_list(cookie_str))
            page = context.new_page()

            captured = {}
            def on_resp(resp):
                u = resp.url
                if ("flow-content.google/video" in u or "googlevideo.com/videoplayback" in u) and resp.status in [200, 206]:
                    base = u.split("?")[0]
                    if base not in captured:
                        captured[base] = u

            page.on("response", on_resp)
            page.goto(f"https://flow.google.com/project/{project_id}", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3500)

            tiles = page.locator('flow-tile-container').all()
            for i, t in enumerate(tiles[:min(max_videos * 2, len(tiles))]):
                is_vid = t.locator('mat-icon:has-text("play_arrow"), mat-icon:has-text("play_circle"), mat-icon:has-text("videocam")').count() > 0
                if not is_vid:
                    continue
                prompt_txt = ""
                try:
                    f = t.locator('.footer-left').first
                    if f.count() > 0:
                        prompt_txt = f.text_content().strip().lstrip("play_circle").lstrip("videocam").strip()
                except Exception:
                    pass

                b = t.bounding_box()
                if b:
                    prev_c = len(captured)
                    page.mouse.click(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
                    st = time.time()
                    while time.time() - st < 3.5:
                        if len(captured) > prev_c:
                            break
                        page.wait_for_timeout(200)
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                    if len(captured) > prev_c:
                        new_urls = [u for u in captured.values()]
                        videos.append({
                            "url": new_urls[-1],
                            "prompt": prompt_txt or f"Video_{i+1}"
                        })
                if len(videos) >= max_videos:
                    break

            browser.close()
    except Exception as e:
        _safe_print(f"[!] Loi sync canvas videos: {e}")
    return videos

def sync_canvas_videos(*args, **kwargs) -> List[Dict[str, Any]]:
    """Hàm bọc an toàn chạy ngoài asyncio loop cho sync_canvas_videos."""
    return _run_in_thread(_sync_canvas_videos_impl, *args, **kwargs)


def _upscale_video_1080p_impl(cookie_str: str, project_id: str, media_id: str) -> Optional[str]:
    """Lấy hoặc kích hoạt stream 1080p Upscaled thật từ Google Flow."""
    if not cookie_str or not media_id:
        return None

    _safe_print(f"[*] Dang ket noi Google Flow kich hoat 1080p cho media {media_id[:8]}...")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    captured_1080_url = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1366, "height": 850}, user_agent=user_agent)
            context.add_cookies(_parse_cookie_list(cookie_str))
            page = context.new_page()

            def on_resp(r):
                nonlocal captured_1080_url
                u = r.url
                if ("flow-content.google/video" in u or "googlevideo.com/videoplayback" in u) and "_upsampled" in u and r.status in [200, 206]:
                    captured_1080_url = u

            page.on("response", on_resp)
            page.goto(f"https://flow.google.com/project/{project_id}", wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3500)

            tiles = page.locator('flow-tile-container').all()
            target_tile = None
            for t in tiles[:12]:
                is_vid = t.locator('mat-icon:has-text("play_arrow"), mat-icon:has-text("play_circle"), mat-icon:has-text("videocam")').count() > 0
                if not is_vid:
                    continue
                html = t.evaluate("el => el.innerHTML")
                if media_id in html:
                    target_tile = t
                    break
                if not target_tile:
                    target_tile = t

            if target_tile:
                b = target_tile.bounding_box()
                if b:
                    page.mouse.click(b['x'] + b['width']/2, b['y'] + b['height']/2)
                    page.wait_for_timeout(2000)
                    dl_btn = page.locator('button[aria-label*="download" i], button:has(mat-icon:has-text("download"))').first
                    if dl_btn.is_visible():
                        dl_btn.click()
                        page.wait_for_timeout(500)
                        opt_1080 = page.locator('.cdk-overlay-container [role="menuitem"]:has-text("1080p"), .cdk-overlay-container button:has-text("1080p")').first
                        if opt_1080.is_visible():
                            opt_1080.click()
                            st = time.time()
                            while time.time() - st < 12.0:
                                if captured_1080_url:
                                    break
                                page.wait_for_timeout(300)
            browser.close()
    except Exception as e:
        _safe_print(f"[!] Loi upscale video 1080p: {e}")

    return captured_1080_url

def upscale_video_1080p(*args, **kwargs) -> Optional[str]:
    """Hàm bọc an toàn chạy ngoài asyncio loop cho upscale_video_1080p."""
    return _run_in_thread(_upscale_video_1080p_impl, *args, **kwargs)
