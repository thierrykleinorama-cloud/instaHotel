# InstaHotel — Environment Setup

Quick setup guide for working on a new machine.

## 1. Clone & Branch

```bash
git clone https://github.com/thierrykleinorama-cloud/instaHotel.git
cd instaHotel
git checkout local
```

## 2. Python Environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### Additional dependencies (if not in requirements.txt)

```bash
pip install streamlit supabase anthropic replicate httpx pillow pillow-heif opencv-python-headless playwright
python -m playwright install chromium
```

## 3. Environment Variables (.env)

Create `.env` in the project root with:

```env
# Supabase (same project as hotelPandL)
SUPABASE_URL=https://lngrockgpnwaizzyvwsk.supabase.co
SUPABASE_KEY=<anon key from Supabase dashboard>
SUPABASE_SERVICE_KEY=<service role key>

# Claude API
ANTHROPIC_API_KEY=<your key>

# Image Enhancement
STABILITY_API_KEY=<from platform.stability.ai>
REPLICATE_API_TOKEN=<from replicate.com>

# Instagram Publishing (NOT YET OBTAINED — see MEMORY.md)
# INSTAGRAM_ACCESS_TOKEN=
# INSTAGRAM_ACCOUNT_ID=
```

## 4. Google Drive Credentials

Two files needed in the project root:
- `.google_token_drive.json` — OAuth token with refresh_token (copy from main machine)
- Google credentials file at `../google_credentials.json` (shared across agents-lab projects)

## 5. FFmpeg (for video+audio compositing)

- **Windows**: Included with ImageMagick at `C:\Program Files\ImageMagick-7.0.10-Q16-HDRI\ffmpeg.exe`, or install separately
- **macOS**: `brew install ffmpeg`
- **Linux/Cloud**: `apt-get install ffmpeg` (handled by `packages.txt` on Streamlit Cloud)
- Auto-detected via `shutil.which("ffmpeg")`

## 6. Streamlit Secrets (optional, for cloud deploy)

`.streamlit/secrets.toml` mirrors `.env` values for Streamlit Cloud.

## 7. Run

```bash
streamlit run app/main.py --server.headless true --server.port 8502
```

## 8. Key API Costs

| Operation | Cost |
|-----------|------|
| Caption generation (Sonnet) | ~$0.013 |
| AI motion prompt (Sonnet) | ~$0.01 |
| Creative scenarios x3 (Sonnet) | ~$0.02 |
| Photo-to-video Kling 5s | $0.30 |
| Photo-to-video Kling 10s | $0.60 |
| MusicGen 10s | ~$0.02 |
| AI Retouch (Replicate) | ~$0.05 |
| Upscale (Stability) | ~$0.05 |

## 9. Current Branch: `local`

All development happens on `local`. Deploy to Streamlit Cloud = merge `local` into `main` and push.
