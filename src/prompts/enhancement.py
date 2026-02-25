"""
Prompts: Image Enhancement
Prompts sent to Stability AI upscale (conservative/creative) and Replicate retouch APIs.
"""

# ---------------------------------------------------------------------------
# Stability AI — Conservative / Creative Upscale
# ---------------------------------------------------------------------------

UPSCALE_PROMPT = (
    "High quality, highly detailed photograph of a boutique hotel. "
    "Sharp focus, natural lighting, professional photography."
)

UPSCALE_NEGATIVE_PROMPT = (
    "blurry, noisy, low quality, artifacts, watermark, text overlay"
)

# ---------------------------------------------------------------------------
# Replicate — Nano Banana Pro (AI Retouch)
# ---------------------------------------------------------------------------

RETOUCH_PROMPT = (
    "Enhance this hotel photograph for a luxury hospitality marketing portfolio. "
    "If the image contains scan artifacts — such as uneven margins, scanner edges, "
    "or visible borders that are not part of the original photo — remove them and "
    "reconstruct a clean, full-bleed image. "
    "Improve natural lighting, boost color vibrancy, increase sharpness and clarity, "
    "fix white balance, and make it look professionally shot. "
    "Keep the exact same scene, composition, and all objects — only improve the visual quality."
)
