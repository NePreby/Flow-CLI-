import json
import os
import re
import time
import random
import uuid
import hashlib
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import requests

from config import load_config, get_cookie

FLOW_BASE_URL = "https://flow.google.com"
BATCH_EXECUTE_URL = f"{FLOW_BASE_URL}/_/AiSandboxAngularFrontend/data/batchexecute"

# Các RPC Identifier chính thức của Google Flow
RPC_GET_CREDITS = "nzlxg"                               # /VideoFxService.GetCredits
RPC_GET_CREDIT_STATUS = "DviW9c"                         # /AiSandbox.GetUserVideoCreditStatusAction
RPC_GET_FLOW_APP_CONFIG = "cPZSdc"                       # /VideoFxService.GetFlowAppConfig
RPC_GET_USER_SETTINGS = "gS5h8c"                         # /VideoFxService.GetUserSettings
RPC_GET_PROJECTS = "UpteDb"                              # /FlowService.GetProjects
RPC_CREATE_PROJECT = "jHPbke"                            # /AiSandbox.CreateProject
RPC_GET_PROJECT = "ngNC2"                                # /AiSandbox.GetProject
RPC_BATCH_GENERATE_IMAGES = "ogiZ0b"                     # /FlowService.BatchGenerateImages
RPC_GET_MEDIA = "as29s"                                  # /FlowService.GetMedia
RPC_LIST_MEDIA = "bOKtO"                                 # /FlowService.ListMedia
RPC_UPSAMPLE_IMAGE = "SPrCad"                            # /FlowService.UpsampleImage
RPC_GENERATE_VIDEO_TEXT = "YhhmEf"                       # /VideoFxService.BatchAsyncGenerateVideoText
RPC_GENERATE_VIDEO_START = "eb1hJf"                      # /VideoFxService.BatchAsyncGenerateVideoStartImage
RPC_GENERATE_VIDEO_START_END = "nprQif"                  # /VideoFxService.BatchAsyncGenerateVideoStartAndEndImage
RPC_GENERATE_VIDEO_REFS = "MZZa6b"                       # /VideoFxService.BatchAsyncGenerateVideoReferenceImages
RPC_GENERATE_VIDEO_EDIT = "jIps6"                        # /VideoFxService.BatchAsyncGenerateVideoEditVideo
RPC_CHECK_VIDEO_STATUS = "jwpduf"                        # /VideoFxService.BatchCheckAsyncVideoGenerationStatus

# Aspect Ratio Enums cho ảnh (Protobuf integer codes trong frontend Flow)
# 1: 1:1 (SQUARE), 2: 9:16 (PORTRAIT), 3: 16:9 (LANDSCAPE), 4: 3:4, 5: 4:3
ASPECT_RATIO_CODES_IMAGE = {
    "1:1": 1,
    "SQUARE": 1,
    "9:16": 2,
    "PORTRAIT": 2,
    "16:9": 3,
    "LANDSCAPE": 3,
    "3:4": 4,
    "PORTRAIT_3_4": 4,
    "4:3": 5,
    "LANDSCAPE_4_3": 5
}

ASPECT_RATIOS_IMAGE = {
    "16:9": "LANDSCAPE (16:9)",
    "9:16": "PORTRAIT (9:16)",
    "1:1": "SQUARE (1:1)",
    "4:3": "LANDSCAPE (4:3)",
    "3:4": "PORTRAIT (3:4)"
}

ASPECT_RATIO_CODES_VIDEO = {
    "16:9": 1,
    "LANDSCAPE": 1,
    "9:16": 2,
    "PORTRAIT": 2
}

ASPECT_RATIOS_VIDEO = {
    "16:9": "LANDSCAPE (16:9)",
    "9:16": "PORTRAIT (9:16)"
}

VIDEO_RESOLUTIONS = {
    "720p": 1,
    "360p": 4
}

VIDEO_DURATIONS = [4, 6, 8, 10]

# Supported Models chuẩn Google Flow AI Studio
IMAGE_MODELS = [
    {
        "id": "Nano Banana 2.1",
        "name": "🍌 Nano Banana 2.1",
        "badge": "Mới",
        "desc": "Mô hình tạo ảnh thế hệ 2.1 mới nhất của Google Flow, cân bằng tối ưu giữa chi tiết và tốc độ.",
        "key": "BELUGA"
    },
    {
        "id": "Nano Banana Pro",
        "name": "🍌 Nano Banana Pro",
        "badge": "Pro",
        "desc": "Mô hình Pro cao cấp nhất của Google Flow, chất lượng siêu nét, hỗ trợ upscaling 2K/4K.",
        "key": "GEM_PIX_2"
    },
    {
        "id": "Nano Banana 2 Lite",
        "name": "🍌 Nano Banana 2 Lite",
        "badge": "Lite",
        "desc": "Mô hình siêu nhẹ, tốc độ tạo ảnh cực nhanh, tiết kiệm điểm tín dụng.",
        "key": "HARBOR_SEAL"
    }
]

VIDEO_MODELS = [
    {
        "id": "Omni 1.1 Flash",
        "name": "🔊 Omni 1.1 Flash",
        "badge": "Omni Flash",
        "desc": "Mô hình Gemini Omni 1.1 Flash thế hệ mới, tạo video mượt mà siêu tốc kèm âm thanh sống động.",
        "key": "abra"
    },
    {
        "id": "Veo 3.1 - Fast",
        "name": "🔊 Veo 3.1 - Fast",
        "badge": "Fast",
        "desc": "Mô hình Veo 3.1 tối ưu tốc độ render nhanh chóng, thích hợp tạo mẫu thử.",
        "key": "veo_3_1_fast"
    },
    {
        "id": "Veo 3.1 - Lite",
        "name": "🔊 Veo 3.1 - Lite",
        "badge": "Lite",
        "desc": "Mô hình Veo 3.1 bản rút gọn, tiết kiệm điểm tín dụng tối đa cho tài khoản.",
        "key": "veo_3_1_lite"
    },
    {
        "id": "Veo 3.1 - Quality",
        "name": "🔊 Veo 3.1 - Quality",
        "badge": "Cinematic",
        "desc": "Mô hình Veo 3.1 chất lượng chuẩn điện ảnh cao cấp nhất của Google DeepMind.",
        "key": "veo_3_1_quality"
    }
]

# Mapping chuẩn hóa tên mô hình
MODEL_ALIASES = {
    # Image
    "nano banana 2.1": "Nano Banana 2.1",
    "nano-banana-2.1": "Nano Banana 2.1",
    "nano_banana_2.1": "Nano Banana 2.1",
    "nano banana 2": "Nano Banana 2.1",
    "beluga": "Nano Banana 2.1",
    "beluga_display": "Nano Banana 2.1",
    "nano banana pro": "Nano Banana Pro",
    "nano-banana-pro": "Nano Banana Pro",
    "nano_banana_pro": "Nano Banana Pro",
    "gem_pix_2": "Nano Banana Pro",
    "nano banana 2 lite": "Nano Banana 2 Lite",
    "nano-banana-2-lite": "Nano Banana 2 Lite",
    "nano_banana_2_lite": "Nano Banana 2 Lite",
    "harbor_seal": "Nano Banana 2 Lite",
    "imagen_3": "Nano Banana 2.1",
    "imagen_3_fast": "Nano Banana 2 Lite",
    "imagen_3_5": "Nano Banana Pro",
    # Video
    "omni 1.1 flash": "Omni 1.1 Flash",
    "omni flash": "Omni 1.1 Flash",
    "omni-1.1-flash": "Omni 1.1 Flash",
    "omni_1_1_flash": "Omni 1.1 Flash",
    "abra": "Omni 1.1 Flash",
    "veo 3.1 - fast": "Veo 3.1 - Fast",
    "veo 3.1 fast": "Veo 3.1 - Fast",
    "veo-3.1-fast": "Veo 3.1 - Fast",
    "veo_3_1_fast": "Veo 3.1 - Fast",
    "veo 3.1 - lite": "Veo 3.1 - Lite",
    "veo 3.1 lite": "Veo 3.1 - Lite",
    "veo-3.1-lite": "Veo 3.1 - Lite",
    "veo_3_1_lite": "Veo 3.1 - Lite",
    "veo 3.1 - quality": "Veo 3.1 - Quality",
    "veo 3.1 quality": "Veo 3.1 - Quality",
    "veo-3.1-quality": "Veo 3.1 - Quality",
    "veo_3_1_quality": "Veo 3.1 - Quality",
    "veo-2.0-generate-001": "Veo 3.1 - Fast",
    "veo-3.0": "Veo 3.1 - Quality",
    "veo-3.0-fast": "Veo 3.1 - Fast"
}

# gRPC error descriptions
GRPC_STATUS_MESSAGES = {
    1: "Thao tác đã bị hủy (CANCELLED)",
    2: "Lỗi không xác định từ Google Flow (UNKNOWN)",
    3: "Dữ liệu yêu cầu không hợp lệ (INVALID_ARGUMENT). Kiểm tra mô hình hoặc định dạng tham số.",
    4: "Quá thời gian xử lý từ máy chủ Google (DEADLINE_EXCEEDED)",
    5: "Không tìm thấy tài nguyên (NOT_FOUND)",
    6: "Tài nguyên đã tồn tại (ALREADY_EXISTS)",
    7: "Từ chối quyền truy cập (PERMISSION_DENIED). Tài khoản không có quyền trên mô hình này.",
    8: "Đã hết điểm tín dụng hoặc vượt giới hạn tạo (RESOURCE_EXHAUSTED).",
    9: "Điều kiện tiên quyết không thỏa mãn (FAILED_PRECONDITION)",
    10: "Thao tác bị gián đoạn (ABORTED)",
    11: "Giá trị vượt ngoài phạm vi cho phép (OUT_OF_RANGE)",
    12: "Tính năng chưa được hỗ trợ (UNIMPLEMENTED)",
    13: "Lỗi nội bộ hệ thống Google Flow (INTERNAL)",
    14: "Dịch vụ tạm thời không khả dụng (UNAVAILABLE). Vui lòng thử lại sau.",
    15: "Mất mát dữ liệu (DATA_LOSS)",
    16: "Phiên làm việc hết hạn hoặc không có quyền xác thực (UNAUTHENTICATED). Vui lòng cập nhật Cookie."
}


class GoogleFlowClient:
    def __init__(self, cookie: Optional[str] = None):
        self.cookie = (cookie or get_cookie() or "").strip()
        self.session = requests.Session()
        self.at_token = ""
        self.fsid = ""
        self._cached_project_id: Optional[str] = None
        self.initialized = False
        self._parsed_cookies: Dict[str, str] = {}
        self._setup_session()

    def _setup_session(self):
        """Khởi tạo session với headers tương thích Chrome hiện đại."""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
            "X-Same-Domain": "1",
            "Referer": "https://flow.google.com/",
            "Origin": "https://flow.google.com"
        })
        if self.cookie:
            self._apply_cookie(self.cookie)

    def update_cookie(self, cookie_str: str):
        """Cập nhật cookie mới và làm mới session."""
        self.cookie = cookie_str.strip()
        self._cached_project_id = None
        self.initialized = False
        self._apply_cookie(self.cookie)

    def _apply_cookie(self, cookie_str: str):
        """Phân tích cookie, tính toán Authorization SAPISIDHASH và đưa vào session."""
        cookie_str = cookie_str.strip()
        self._parsed_cookies = {}

        if cookie_str.startswith("[") and cookie_str.endswith("]"):
            try:
                cookie_list = json.loads(cookie_str)
                flat_parts = []
                for c in cookie_list:
                    if isinstance(c, dict) and "name" in c and "value" in c:
                        k, v = c["name"], c["value"]
                        self._parsed_cookies[k] = v
                        flat_parts.append(f"{k}={v}")
                        self.session.cookies.set(k, v, domain=c.get("domain", ".google.com"))
                cookie_str = "; ".join(flat_parts)
            except Exception:
                pass
        else:
            for item in cookie_str.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    self._parsed_cookies[k] = v
                    self.session.cookies.set(k, v, domain=".google.com")

        self.session.headers["Cookie"] = cookie_str

        # Tính toán mã băm Authorization: SAPISIDHASH theo chuẩn Boq Google
        auth_header = self._generate_sapisid_hash()
        if auth_header:
            self.session.headers["Authorization"] = auth_header

    def _generate_sapisid_hash(self, origin: str = "https://flow.google.com") -> Optional[str]:
        """Tạo chuỗi xác thực SAPISIDHASH / SAPISID1PHASH / SAPISID3PHASH."""
        t = int(time.time())
        parts = []

        sapisid = self._parsed_cookies.get("SAPISID")
        if sapisid:
            h = hashlib.sha1(f"{t} {sapisid} {origin}".encode()).hexdigest()
            parts.append(f"SAPISIDHASH {t}_{h}")

        sapisid_1p = self._parsed_cookies.get("__Secure-1PAPISID") or self._parsed_cookies.get("__1PSAPISID")
        if sapisid_1p:
            h1 = hashlib.sha1(f"{t} {sapisid_1p} {origin}".encode()).hexdigest()
            parts.append(f"SAPISID1PHASH {t}_{h1}")

        sapisid_3p = self._parsed_cookies.get("__Secure-3PAPISID") or self._parsed_cookies.get("__3PSAPISID")
        if sapisid_3p:
            h3 = hashlib.sha1(f"{t} {sapisid_3p} {origin}".encode()).hexdigest()
            parts.append(f"SAPISID3PHASH {t}_{h3}")

        return " ".join(parts) if parts else None

    def init_session(self) -> Tuple[bool, str]:
        """Tải trang flow.google.com để trích xuất token CSRF (at) và fsid."""
        if not self.cookie:
            return False, "Chưa cung cấp Google Cookie. Vui lòng cấu hình cookie tài khoản Google Flow."

        try:
            # Luôn cập nhật Authorization header theo thời gian thực
            auth_header = self._generate_sapisid_hash()
            if auth_header:
                self.session.headers["Authorization"] = auth_header

            res = self.session.get(FLOW_BASE_URL, timeout=15)
            if res.status_code != 200:
                return False, f"Không thể kết nối đến Google Flow (HTTP {res.status_code})"

            html = res.text

            # Kiểm tra xem cookie có bị điều hướng đăng nhập không
            if "accounts.google.com/ServiceLogin" in html and 'id="identifierId"' in html:
                self.initialized = False
                return False, "Cookie Google đã hết hạn hoặc không hợp lệ. Vui lòng truy cập flow.google.com và lấy cookie mới."

            # Trích xuất WIZ_global_data
            wiz_match = re.search(r'window\.WIZ_global_data\s*=\s*(\{.*?\});', html, re.DOTALL)
            if wiz_match:
                try:
                    wiz_data = json.loads(wiz_match.group(1))
                    self.at_token = wiz_data.get("SNlM0e", "")
                    self.fsid = wiz_data.get("FdrFJe", "")
                except Exception:
                    pass

            if not self.at_token:
                at_match = re.search(r'\"SNlM0e\":\"([^\"]+)\"', html)
                if at_match:
                    self.at_token = at_match.group(1)

            # Nếu không tìm thấy SNlM0e, thử kiểm tra token phụ trong WIZ_global_data
            if not self.at_token and wiz_match:
                try:
                    wiz_data = json.loads(wiz_match.group(1))
                    # Một số phiên bản web Boq sử dụng WZsZ1e hoặc y83d5b
                    self.at_token = wiz_data.get("WZsZ1e", "")
                except Exception:
                    pass

            self.initialized = True
            return True, "Kết nối Google Flow thành công!"
        except Exception as e:
            return False, f"Lỗi khởi tạo kết nối: {str(e)}"

    def _execute_rpc(self, rpc_id: str, payload: Any) -> Tuple[bool, Any]:
        """Gửi lệnh RPC đến Google Boq batchexecute và xử lý lỗi gRPC."""
        if not self.initialized:
            ok, msg = self.init_session()
            if not ok and not self.at_token:
                return False, msg

        # Luôn làm mới Authorization header
        auth_header = self._generate_sapisid_hash()
        if auth_header:
            self.session.headers["Authorization"] = auth_header

        payload_json = json.dumps(payload, separators=(',', ':')) if not isinstance(payload, str) else payload
        f_req = json.dumps([[[rpc_id, payload_json, None, "generic"]]], separators=(',', ':'))

        data = {"f.req": f_req}
        if self.at_token:
            data["at"] = self.at_token

        params = {
            "rpcids": rpc_id,
            "source-path": "/projects",
            "bl": "boq_labs-ai-sandbox-frontend_20261018.05_p0",
            "hl": "en",
            "rt": "c"
        }
        if self.fsid:
            params["f.sid"] = self.fsid

        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
        }

        try:
            res = self.session.post(BATCH_EXECUTE_URL, params=params, data=data, headers=headers, timeout=35)
            if res.status_code == 401:
                return False, "Lỗi xác thực (401 Unauthorized): Cookie tài khoản không hợp lệ hoặc đã hết hạn. Vui lòng lấy cookie mới."
            if res.status_code != 200:
                return False, f"Lỗi máy chủ Google Flow (HTTP {res.status_code}): {res.text[:200]}"

            parsed, errors = self._parse_batchexecute(res.text)

            # Kiểm tra lỗi gRPC
            if rpc_id in errors:
                err_code = errors[rpc_id]
                err_desc = GRPC_STATUS_MESSAGES.get(err_code, f"Lỗi gRPC mã [{err_code}]")
                return False, f"{err_desc} (RPC: {rpc_id})"

            if rpc_id in parsed:
                return True, parsed[rpc_id]

            # Kiểm tra nếu toàn bộ payload trả về lỗi
            if "error" in parsed:
                return False, parsed["error"]

            return True, parsed
        except Exception as e:
            return False, f"Lỗi kết nối RPC ({rpc_id}): {str(e)}"

    def _parse_batchexecute(self, raw_text: str) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Phân tích dữ liệu chunk JSON từ batchexecute, nhận diện cả kết quả và mã lỗi gRPC."""
        text = raw_text.strip()
        if text.startswith(")]}'"):
            text = text[4:].strip()

        results: Dict[str, Any] = {}
        errors: Dict[str, int] = {}

        lines = text.split('\n')
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                continue
            if line.isdigit():
                idx += 1
                if idx < len(lines):
                    chunk = lines[idx]
                    self._extract_chunks(chunk, results, errors)
            else:
                self._extract_chunks(line, results, errors)
            idx += 1

        return results, errors

    def _extract_chunks(self, chunk_str: str, results: Dict[str, Any], errors: Dict[str, int]):
        """Trích xuất khối dữ liệu wrb.fr hoặc mã lỗi er."""
        try:
            chunk_data = json.loads(chunk_str)
            if isinstance(chunk_data, list):
                for item in chunk_data:
                    if not isinstance(item, list) or len(item) < 2:
                        continue

                    # Khối dữ liệu thành công hoặc lỗi theo RPC
                    if item[0] == "wrb.fr" and len(item) >= 3:
                        rpc_id = item[1]
                        payload_raw = item[2]
                        # Kiểm tra error status ở field 5 (index 5)
                        grpc_status = item[5] if len(item) > 5 else None
                        if grpc_status and isinstance(grpc_status, list) and len(grpc_status) > 0:
                            code = grpc_status[0]
                            if isinstance(code, int) and code != 0:
                                errors[rpc_id] = code
                                continue

                        if payload_raw:
                            try:
                                results[rpc_id] = json.loads(payload_raw)
                            except Exception:
                                results[rpc_id] = payload_raw
                        else:
                            if grpc_status:
                                errors[rpc_id] = grpc_status[0] if isinstance(grpc_status, list) else int(grpc_status)
                            else:
                                results[rpc_id] = None

                    # Khối lỗi tổng thể của batchexecute
                    elif item[0] == "er" and len(item) >= 6:
                        http_code = item[5]
                        if http_code == 401:
                            results["error"] = "Lỗi xác thực (401 Unauthorized): Cookie tài khoản không hợp lệ hoặc đã hết hạn."
                        else:
                            results["error"] = f"Lỗi phản hồi batchexecute (Mã lỗi {http_code})"
        except Exception:
            pass

    def get_or_create_project_id(self) -> str:
        """Lấy Project ID hiện có của tài khoản hoặc tự động tạo mới."""
        if self._cached_project_id:
            return self._cached_project_id

        # 1. Truy vấn danh sách dự án của user thông qua RPC UpteDb
        ok, resp = self._execute_rpc(RPC_GET_PROJECTS, ["projects/*", 100])
        if ok and isinstance(resp, list) and len(resp) > 0:
            try:
                # Cấu trúc: [[[project_id, [title, ...]], ...]]
                projects_list = resp[0] if isinstance(resp[0], list) else resp
                valid_pids = []
                for item in projects_list:
                    if isinstance(item, list) and len(item) >= 1:
                        pid = item[0]
                        if isinstance(pid, str) and len(pid) >= 30 and "-" in pid:
                            # Ưu tiên project chính có nhiều metadata (thường chứa scene/node)
                            if len(item) > 1 and isinstance(item[1], list) and len(item[1]) >= 4:
                                self._cached_project_id = pid
                                return pid
                            valid_pids.append(pid)
                if valid_pids:
                    # Ưu tiên pid "470b517b-51dd-4e0d-99ed-62c55c6a7c01" nếu có
                    for p in valid_pids:
                        if p.startswith("470b517b"):
                            self._cached_project_id = p
                            return p
                    self._cached_project_id = valid_pids[0]
                    return valid_pids[0]
            except Exception:
                pass

        # 2. Nếu chưa có dự án nào, gọi RPC jHPbke để tạo một dự án mới
        create_payload = [
            "projects/*",
            [None, ["Flow AI Creative Studio Workspace"]],
            []
        ]
        ok_create, resp_create = self._execute_rpc(RPC_CREATE_PROJECT, create_payload)
        if ok_create and isinstance(resp_create, list) and len(resp_create) >= 1:
            pid = resp_create[0]
            if isinstance(pid, str):
                self._cached_project_id = pid
                return pid

        # Dự phòng mặc định dự án đã xác thực của người dùng
        default_pid = "470b517b-51dd-4e0d-99ed-62c55c6a7c01"
        self._cached_project_id = default_pid
        return default_pid

    def get_credits(self) -> Dict[str, Any]:
        """Lấy số điểm còn lại (Remaining Credits / Points)."""
        if not self.cookie:
            return {
                "success": False,
                "credits": 0,
                "error": "Chưa nhập Cookie Google Flow",
                "is_mock": True
            }

        ok, resp = self._execute_rpc(RPC_GET_CREDITS, [])
        if ok and isinstance(resp, list):
            credits_val = 0
            tier = "Free"
            try:
                flat_numbers = []
                def extract_numbers(obj):
                    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
                        flat_numbers.append(obj)
                    elif isinstance(obj, list):
                        for el in obj:
                            extract_numbers(el)

                extract_numbers(resp)
                if flat_numbers:
                    credits_val = flat_numbers[0]
                return {
                    "success": True,
                    "credits": credits_val,
                    "raw": resp,
                    "tier": tier
                }
            except Exception as e:
                return {"success": False, "credits": 0, "error": f"Lỗi đọc dữ liệu điểm: {e}"}

        # Thử lấy qua RPC phụ GetUserVideoCreditStatusAction
        ok2, resp2 = self._execute_rpc(RPC_GET_CREDIT_STATUS, [])
        if ok2 and isinstance(resp2, list):
            flat = [x for x in resp2 if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if flat:
                return {"success": True, "credits": flat[0], "raw": resp2, "tier": "Standard"}

        return {
            "success": False,
            "credits": 0,
            "error": resp if isinstance(resp, str) else "Không thể lấy số điểm từ Google Flow"
        }

    def generate_image(self,
                       prompt: str,
                       model: str = "Nano Banana 2.1",
                       aspect_ratio: str = "16:9",
                       count: int = 2,
                       seed: Optional[int] = None,
                       negative_prompt: str = "") -> Dict[str, Any]:
        """Tạo ảnh từ Google Flow sử dụng Native Flow Engine kết hợp đồng bộ hóa phiên."""
        prompt = prompt.strip()
        if not prompt:
            return {"success": False, "error": "Prompt không được để trống"}

        count = max(1, min(count or 1, 4))
        model_clean = model.strip()
        model_name = MODEL_ALIASES.get(model_clean.lower(), model_clean)
        project_id = self.get_or_create_project_id()

        # Tính toán timeout động theo số lượng ảnh (cho phép Google Flow đủ thời gian render song song tất cả các ảnh: ~100-120s mỗi lượt batch)
        dynamic_timeout = max(180, 140 + (count * 60))

        # Thực thi qua Native Flow Engine (vượt qua reCAPTCHA Enterprise và xác thực phiên hoàn chỉnh)
        try:
            from flow_worker import generate_image_native
            res = generate_image_native(
                cookie_str=self.cookie,
                project_id=project_id,
                prompt=prompt,
                model=model_name,
                aspect_ratio=aspect_ratio,
                count=count,
                timeout_sec=dynamic_timeout
            )
            return res
        except Exception as ex:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Lỗi khởi chạy engine tạo ảnh: {str(ex)}"
            }

    def generate_video(self,
                       prompt: str,
                       model: str = "Omni 1.1 Flash",
                       aspect_ratio: str = "16:9",
                       resolution: str = "720p",
                       duration: int = 8,
                       count: int = 1,
                       start_image_url: Optional[str] = None,
                       end_image_url: Optional[str] = None,
                       seed: Optional[int] = None) -> Dict[str, Any]:
        """Tạo video từ Google Flow sử dụng Native Flow Engine kết hợp đồng bộ hóa phiên."""
        prompt = prompt.strip()
        if not prompt and not start_image_url:
            return {"success": False, "error": "Cần nhập prompt hoặc tải ảnh bắt đầu (Start Frame)"}

        model_clean = model.strip()
        model_name = MODEL_ALIASES.get(model_clean.lower(), model_clean)
        count = max(1, min(4, count or 1))
        project_id = self.get_or_create_project_id()

        # Tính toán timeout động theo số lượng video (Google Flow render video 180-300s mỗi đợt)
        dynamic_timeout = max(360, 240 + (count * 100))

        # Thực thi qua Native Flow Engine (vượt qua reCAPTCHA Enterprise và xác thực phiên hoàn chỉnh)
        try:
            from flow_worker import generate_video_native
            res = generate_video_native(
                cookie_str=self.cookie,
                project_id=project_id,
                prompt=prompt,
                model=model_name,
                aspect_ratio=aspect_ratio,
                duration=duration,
                resolution=resolution,
                count=count,
                start_image_url=start_image_url,
                end_image_url=end_image_url,
                timeout_sec=dynamic_timeout
            )
            return res
        except Exception as ex:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Lỗi khởi chạy engine tạo video: {str(ex)}"
            }

    def get_media(self, media_name_or_id: str) -> Optional[Dict[str, Any]]:
        """Truy vấn thông tin chi tiết và URL tải về của media qua RPC as29s."""
        payload = [media_name_or_id]
        ok, resp = self._execute_rpc(RPC_GET_MEDIA, payload)
        if ok and resp:
            urls = []
            def find_urls(obj):
                if isinstance(obj, str) and re.match(r'^https?://', obj):
                    urls.append(obj)
                elif isinstance(obj, list):
                    for el in obj:
                        find_urls(el)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        find_urls(v)
            find_urls(resp)
            if urls:
                u = urls[0]
                ext = ".mp4" if (".mp4" in u or "video" in u.lower()) else ".jpg"
                return {
                    "id": media_name_or_id,
                    "url": u,
                    "type": "video" if ext == ".mp4" else "image",
                    "ext": ext
                }
        return None

    def _extract_media_ids(self, raw_resp: Any) -> List[str]:
        """Trích xuất các mã định danh media dạng UUID hoặc media/."""
        ids = []
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

        def walk(obj):
            if isinstance(obj, str):
                if uuid_pattern.match(obj) or obj.startswith("media/") or obj.startswith("input_files/"):
                    ids.append(obj)
            elif isinstance(obj, list):
                for el in obj:
                    walk(el)
            elif isinstance(obj, dict):
                for v in obj.values():
                    walk(v)

        walk(raw_resp)
        return list(dict.fromkeys(ids))

    def _extract_media_results(self, raw_resp: Any, media_type: str = "image") -> List[Dict[str, Any]]:
        """Trích xuất URL ảnh, video và mã media từ phản hồi protobuf lồng nhau."""
        results = []
        if not raw_resp:
            return results

        found_urls = []
        def find_urls(obj):
            if isinstance(obj, str):
                # Nhận diện link media trực tiếp của Google
                if re.match(r'^https?://', obj):
                    if any(x in obj for x in ["googleusercontent.com", "storage.googleapis.com", ".jpg", ".jpeg", ".png", ".webp", ".mp4"]):
                        found_urls.append(obj)
            elif isinstance(obj, list):
                for item in obj:
                    find_urls(item)
            elif isinstance(obj, dict):
                for v in obj.values():
                    find_urls(v)

        find_urls(raw_resp)

        for u in dict.fromkeys(found_urls):
            ext = ".mp4" if media_type == "video" else ".jpg"
            if ".mp4" in u or "video" in u.lower():
                ext = ".mp4"
            elif ".png" in u:
                ext = ".png"
            elif ".webp" in u:
                ext = ".webp"

            results.append({
                "url": u,
                "type": media_type,
                "ext": ext,
                "id": f"media_{int(time.time())}_{random.randint(100, 999)}"
            })
        return results

    def download_media(self, url: str, output_path: Union[str, Path]) -> Tuple[bool, str]:
        """Tải ảnh hoặc video từ URL trực tiếp về máy với header giả lập trình duyệt chuẩn xác."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            download_url = url
            if "/asb/" in download_url and "=s" not in download_url:
                download_url += "=s1600-rw"

            # Danh sách User-Agent chuẩn (bao gồm HeadlessChrome tương thích với hash eaua của Google Video)
            candidate_user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/149.0.7827.55 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            ]

            last_error = "Unknown error"
            for ua in candidate_user_agents:
                headers = {
                    "User-Agent": ua,
                    "Referer": "https://flow.google.com/",
                    "Origin": "https://flow.google.com",
                    "Accept": "*/*"
                }
                # Thử tải trực tiếp không kèm cookie trước (phù hợp với googlevideo signed URLs)
                try:
                    res = requests.get(download_url, headers=headers, stream=True, timeout=90)
                    if res.status_code in [200, 206]:
                        ct = res.headers.get("content-type", "")
                        if "webp" in ct and output_path.suffix.lower() in [".jpg", ".jpeg"]:
                            output_path = output_path.with_suffix(".webp")
                        with open(output_path, "wb") as f:
                            for chunk in res.iter_content(chunk_size=65536):
                                if chunk:
                                    f.write(chunk)
                        return True, str(output_path)
                    last_error = f"HTTP Error {res.status_code}"
                except Exception as ex:
                    last_error = str(ex)

                # Thử với session cookies nếu cần
                try:
                    res2 = self.session.get(download_url, headers=headers, stream=True, timeout=90)
                    if res2.status_code in [200, 206]:
                        ct = res2.headers.get("content-type", "")
                        if "webp" in ct and output_path.suffix.lower() in [".jpg", ".jpeg"]:
                            output_path = output_path.with_suffix(".webp")
                        with open(output_path, "wb") as f:
                            for chunk in res2.iter_content(chunk_size=65536):
                                if chunk:
                                    f.write(chunk)
                        return True, str(output_path)
                    last_error = f"HTTP Error {res2.status_code}"
                except Exception as ex:
                    last_error = str(ex)

            return False, last_error
        except Exception as e:
            return False, str(e)


# Bộ sinh dữ liệu thử nghiệm Demo/Mock nếu người dùng chưa có cookie
class DemoFlowClient:
    """Mô phỏng đầy đủ chức năng tạo ảnh/video khi người dùng chưa cấu hình cookie."""
    def __init__(self):
        self.credits = 150.0

    def get_credits(self) -> Dict[str, Any]:
        return {
            "success": True,
            "credits": round(self.credits, 1),
            "tier": "Demo / Preview Mode",
            "is_mock": True
        }

    def generate_image(self, prompt: str, model: str = "Nano Banana 2.1", aspect_ratio: str = "16:9", count: int = 2, seed: Optional[int] = None, negative_prompt: str = "") -> Dict[str, Any]:
        cost = 1.0 * count
        self.credits = max(0.0, self.credits - cost)
        images = []
        width, height = 1280, 720
        if aspect_ratio == "9:16":
            width, height = 720, 1280
        elif aspect_ratio == "1:1":
            width, height = 1024, 1024
        elif aspect_ratio == "4:3":
            width, height = 1024, 768
        elif aspect_ratio == "3:4":
            width, height = 768, 1024

        for i in range(count):
            img_seed = (seed or random.randint(1000, 99999)) + i
            img_url = f"https://picsum.photos/seed/{img_seed}/{width}/{height}"
            images.append({
                "id": f"img_{int(time.time())}_{i}",
                "url": img_url,
                "type": "image",
                "ext": ".jpg",
                "width": width,
                "height": height,
                "seed": img_seed
            })

        return {
            "success": True,
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "count": count,
            "images": images,
            "credits_remaining": round(self.credits, 1),
            "is_mock": True
        }

    def generate_video(self, prompt: str, model: str = "Omni 1.1 Flash", aspect_ratio: str = "16:9", resolution: str = "720p", duration: int = 8, count: int = 2, start_image_url: Optional[str] = None, end_image_url: Optional[str] = None, seed: Optional[int] = None) -> Dict[str, Any]:
        cost = 5.0 * count
        self.credits = max(0.0, self.credits - cost)
        sample_videos = [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
        ]

        videos = []
        for i in range(count):
            vid_seed = (seed or random.randint(1000, 99999)) + i
            videos.append({
                "id": f"vid_{int(time.time())}_{i}",
                "url": sample_videos[i % len(sample_videos)],
                "type": "video",
                "ext": ".mp4",
                "resolution": resolution,
                "duration": duration,
                "seed": vid_seed
            })

        return {
            "success": True,
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "duration": duration,
            "count": count,
            "videos": videos,
            "credits_remaining": round(self.credits, 1),
            "is_mock": True
        }

    def download_media(self, url: str, output_path: Union[str, Path]) -> Tuple[bool, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            res = requests.get(url, stream=True, timeout=60)
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                return True, str(output_path)
            with open(output_path, "wb") as f:
                f.write(b"MOCK_FLOW_MEDIA_CONTENT")
            return True, str(output_path)
        except Exception as e:
            return False, str(e)
