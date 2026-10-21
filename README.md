<div align="center">

# 🎬 Flow-CLI | Google Flow AI Studio

**A production-ready CLI, Web Studio, and Automation Engine for Google Flow (`flow.google.com`).**  
*Generate next-generation AI images and cinematic videos with real-time credit tracking, batch generation, and automated media downloading.*

[![GitHub Repo](https://img.shields.io/badge/GitHub-NePreby%2FFlow--CLI--blue?logo=github&style=for-the-badge)](https://github.com/NePreby/Flow-CLI-.git)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white&style=for-the-badge)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white&style=for-the-badge)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

[Features](#-key-features) • [Installation](#-quick-start) • [Cookie Setup](#-google-flow-cookie-setup) • [CLI Usage](#-cli-usage-guide) • [Web Studio](#-web-studio-ui) • [Supported Models](#-supported-models--specifications) • [REST API](#-api-endpoints)

---

</div>

## 🌟 Key Features

- **⚡ Real-Time Credit Synchronization**:
  - Live queries to Google Flow's `/VideoFxService.GetCredits` (`nzlxg`) and `/AiSandbox.GetUserVideoCreditStatusAction` (`DviW9c`).
  - Real-time balance badges, dynamic tier detection, and automatic credit deductions after each generation.

- **🎨 Multi-Model AI Image Engine**:
  - Powered by Google's latest image architectures: **Nano Banana 2.1** (*Beluga*), **Nano Banana Pro** (*Gemini Pix 2*), and **Nano Banana 2 Lite** (*Harbor Seal* / Imagen 3 variants).
  - Multiple aspect ratios: `16:9` (Landscape), `9:16` (Story/Reels), `1:1` (Square), `4:3`, and `3:4`.
  - Batch generation (1 to 4 images per prompt), negative prompts, and seed reproducibility.

- **🎥 Cinematic AI Video Engine**:
  - Integration with **Gemini Omni 1.1 Flash** (*Abra* - ultra-fast video rendering with synchronized audio) and **Veo 3.1** series (*Fast*, *Lite*, *Quality*).
  - **3 Flexible Generation Modes**:
    1. **Text-to-Video**: Direct prompt-to-video cinematic rendering.
    2. **Image-to-Video**: Animate starting images (Start Frame).
    3. **Start & End Frame Interpolation**: Generate smooth transitions between two keyframe images.
  - Configurable video durations (`4s`, `6s`, `8s`, `10s`), resolutions (`720p`, `360p`), and aspect ratios (`16:9`, `9:16`).

- **💾 Automated Asset Pipeline**:
  - Automatically downloads generated images and videos directly to local storage (`downloads/`).
  - Built-in Gallery browser with one-click folder exploration.

- **🖥️ Dual Interface (CLI & Web Studio)**:
  - **Modern Web Studio**: Dark-mode, glassmorphism UI built with FastAPI, TailwindCSS, and Alpine.js.
  - **Powerful CLI Tool**: Direct terminal workflows, automation scripting, and batch job processing.

- **🚀 Hybrid High-Performance Architecture**:
  - Direct reverse-engineered Google Boq RPC / `batchexecute` client (`flow_client.py`) for lightweight, low-latency execution.
  - Optional headless Playwright automation worker (`flow_worker.py`) for browser canvas fallback.

---

## 📋 Supported Models & Specifications

### 1. Image Generation Models

| Model Name | Internal Key | Badge | Description |
| :--- | :--- | :--- | :--- |
| **Nano Banana 2.1** | `BELUGA` | 🍌 Latest | Balanced next-generation model with high fidelity and prompt adherence. |
| **Nano Banana Pro** | `GEM_PIX_2` | 🍌 Pro | Flagship high-detail model supporting upscaling and ultra-sharp textures. |
| **Nano Banana 2 Lite** | `HARBOR_SEAL` | 🍌 Lite | Ultra-fast lightweight model, minimal credit consumption. |

**Supported Aspect Ratios**: `16:9`, `9:16`, `1:1`, `4:3`, `3:4`  
**Batch Output**: 1 to 4 images per generation  

---

### 2. Video Generation Models

| Model Name | Internal Key | Badge | Audio Support | Description |
| :--- | :--- | :--- | :---: | :--- |
| **Omni 1.1 Flash** | `abra` | 🔊 Omni Flash | **Yes** | High-speed Gemini Omni model generating fluid motion and audio. |
| **Veo 3.1 - Fast** | `veo_3_1_fast` | 🔊 Fast | **Yes** | Quick rendering speed, ideal for rapid iterations and testing. |
| **Veo 3.1 - Lite** | `veo_3_1_lite` | 🔊 Lite | **Yes** | Resource-efficient variant with reduced credit consumption. |
| **Veo 3.1 - Quality** | `veo_3_1_quality` | 🔊 Cinematic | **Yes** | Google DeepMind's flagship cinematic video generation engine. |

**Video Specifications**:
- **Aspect Ratios**: `16:9` (Horizontal) or `9:16` (Vertical Reels/TikTok)
- **Durations**: `4s`, `6s`, `8s` (Default), `10s`
- **Resolutions**: `720p` (Default), `360p`
- **Generation Modes**: Text-to-Video, Image-to-Video (Start Frame), Transition (Start & End Frame)

---

## 🚀 Quick Start

### 1. Clone Repository & Setup Environment

```bash
# Clone the repository
git clone https://github.com/NePreby/Flow-CLI-.git
cd Flow-CLI-

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# Windows (cmd/PowerShell):
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

*(Optional: If utilizing Playwright browser worker fallback)*
```bash
playwright install chromium
```

---

## 🔑 Google Flow Cookie Setup

To access your Google Flow credits and authentic generation pipeline, configure your session cookie:

1. Open your browser and navigate to [https://flow.google.com](https://flow.google.com).
2. Log into your Google account.
3. Press `F12` (or Right-click -> **Inspect**) to open Developer Tools.
4. Go to the **Network** tab and refresh the page (`F5`).
5. Select the first network request to `flow.google.com`.
6. In **Request Headers**, locate the `Cookie:` entry and copy its entire string.
7. Save the cookie using either the Web UI or CLI:

**Via CLI:**
```bash
python cli.py set-cookie "YOUR_COPIED_COOKIE_STRING"
```

**Via Web UI:**
Navigate to the **Cookie Settings** tab in the Web Dashboard, paste the cookie, and click **Save & Test Connection**.

---

## 💻 CLI Usage Guide

Run commands directly from your terminal using `cli.py`:

### Check Account Balance & Credits
```bash
python cli.py credits
```

### List Available Models & Formats
```bash
python cli.py models
```

### Generate Images
```bash
# Basic image generation (2 images, 16:9 ratio)
python cli.py image "Cyberpunk cityscape with neon reflections on wet asphalt, 8k cinematic"

# Advanced customization
python cli.py image "A majestic mechanical tiger in an overgrown botanical greenhouse" \
  --model "Nano Banana Pro" \
  --ratio 16:9 \
  --count 4 \
  --seed 42 \
  --negative "blurry, low quality, artifacts" \
  --output ./my_renders \
  --download
```

### Generate Videos
```bash
# Text-to-Video
python cli.py video "FPV drone cinematic flythrough of a glowing crystal cave" \
  --model "Omni 1.1 Flash" \
  --ratio 16:9 \
  --resolution 720p \
  --duration 8 \
  --count 1 \
  --download

# Image-to-Video (Start Frame)
python cli.py video "The camera orbits around the character as wind blows gently" \
  --start-image "https://example.com/start_frame.jpg" \
  --duration 6

# Start and End Frame Interpolation
python cli.py video "Smooth morph transition from sunrise to twilight" \
  --start-image "https://example.com/day.jpg" \
  --end-image "https://example.com/night.jpg" \
  --duration 8
```

---

## 🌐 Web Studio UI

### Launch the Web Interface

**Windows 1-Click Launch:**
Double-click `run_web.bat`, or execute:
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 7860 --reload
```

The Web Studio will be accessible at: **`http://localhost:7860`**

### Highlights of the Web Studio:
- **Interactive Prompt Canvas**: Select models, aspect ratios, seeds, and image counts with visual badges.
- **Visual Drag-and-Drop Uploader**: Effortlessly upload Start Frame and End Frame images for video generation.
- **Live Output Player & Gallery**: Preview videos with audio, inspect high-res images, and trigger immediate downloads.
- **Native File Explorer Integration**: Open local download folders directly via native system calls.

---

## 🔌 API Endpoints

The FastAPI server (`app.py`) exposes full RESTful endpoints for integration into third-party applications:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/credits` | Fetch live Google Flow balance and account tier. |
| `GET` | `/api/models` | List all available image & video models with configurations. |
| `GET` | `/api/config` | Retrieve current application configuration and masked cookie. |
| `POST` | `/api/cookie` | Update and test Google Flow session cookie. |
| `POST` | `/api/generate/image` | Submit an image generation request. |
| `POST` | `/api/generate/video` | Submit a video generation request (Text/Image/Keyframe). |
| `POST` | `/api/upload` | Upload local images for Start/End frame video generation. |
| `POST` | `/api/download` | Download remote media assets to the local server storage. |
| `GET` | `/api/gallery` | Retrieve metadata of locally stored assets in `downloads/`. |
| `POST` | `/api/open-downloads` | Launch the local file explorer at the download directory. |

---

## 📁 Project Architecture

```
Flow-CLI/
├── app.py                # FastAPI application & RESTful routing
├── cli.py                # Command-line interface with argparse & Rich formatting
├── flow_client.py        # Core reverse-engineered Google Flow RPC / Boq client
├── flow_worker.py        # Playwright headless browser fallback worker
├── config.py             # Settings, credential storage, and directory management
├── config.json           # Local persistent configuration file
├── requirements.txt      # Python dependencies
├── run_web.bat           # 1-Click launcher script for Windows
├── web/
│   └── index.html        # Modern dark-mode Web Studio interface
├── downloads/            # Local directory for generated and downloaded media
└── uploads/              # Local storage for uploaded keyframe references
```

---

## ⚙️ Configuration File (`config.json`)

The application automatically persists configuration in `config.json`:

```json
{
  "cookie": "YOUR_FLOW_COOKIE",
  "downloads_dir": "downloads",
  "auto_download": true,
  "default_image_model": "Nano Banana 2.1",
  "default_video_model": "Omni 1.1 Flash",
  "default_duration": 8,
  "default_count": 2
}
```

---

## ⚠️ Disclaimer & Notes

- **Disclaimer**: This tool is an independent open-source project intended for research, personal automation, and educational purposes. It is not affiliated with, endorsed by, or sponsored by Google.
- **Account Safety**: Keep your session cookies private and never commit `config.json` containing sensitive cookies to public repositories.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.
