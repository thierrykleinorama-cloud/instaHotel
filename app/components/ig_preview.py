"""
Instagram Post Preview Component

Renders a realistic IG feed-style post mockup as HTML/CSS.
Must be rendered via st.components.v1.html() — NOT st.markdown(),
because Streamlit sanitizes <img> tags in markdown mode.
"""

HOTEL_NAME = "Hôtel Noucentista"
HOTEL_HANDLE = "hotel_noucentista_sitges"
HOTEL_LOCATION = "Sitges, Barcelona"


def render_ig_preview(
    image_b64: str,
    caption: str,
    hashtags: str,
    hotel_name: str = HOTEL_NAME,
    hotel_handle: str = HOTEL_HANDLE,
    is_reel: bool = False,
) -> tuple[str, int]:
    """Return (html_string, estimated_height) for an Instagram feed post mockup.

    Render with: st.components.v1.html(html, height=height)

    Args:
        image_b64: Base64-encoded image (JPEG or PNG, no data URI prefix).
        caption: The caption text (already chosen by language/variant).
        hashtags: Space-separated hashtag string (e.g. "#sitges #hotel").
        hotel_name: Display name for the profile header.
        hotel_handle: Instagram handle (no @ prefix).
        is_reel: If True, renders 9:16 aspect ratio with play overlay and "Reels" label.

    Returns:
        Tuple of (html_string, estimated_pixel_height).
    """
    caption_safe = (caption or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    hashtags_safe = (hashtags or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    avatar_letter = (hotel_name or "H")[0].upper()

    aspect_ratio = "9/16" if is_reel else "4/5"
    # 9:16 at 468px width = 832px image height; 4:5 at 468px = 585px
    image_height = 832 if is_reel else 585

    caption_lines = max(1, len(caption_safe) // 60 + 1) if caption_safe else 1
    hashtag_lines = max(1, len(hashtags_safe) // 60 + 1) if hashtags_safe else 0
    text_height = (caption_lines + hashtag_lines) * 20 + 30
    estimated_height = 52 + image_height + 40 + text_height + 40 + 30

    # Reel-specific overlay elements
    reel_overlay_css = ""
    reel_overlay_html = ""
    if is_reel:
        reel_overlay_css = """
  .ig-image-wrap {
    position: relative;
  }
  .ig-reel-play {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 60px;
    height: 60px;
    background: rgba(0,0,0,0.5);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .ig-reel-play::after {
    content: '';
    display: block;
    width: 0;
    height: 0;
    border-style: solid;
    border-width: 12px 0 12px 22px;
    border-color: transparent transparent transparent #fff;
    margin-left: 4px;
  }
  .ig-reel-label {
    position: absolute;
    top: 12px;
    right: 12px;
    background: rgba(0,0,0,0.55);
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 4px;
    letter-spacing: 0.5px;
  }"""
        reel_overlay_html = """
    <div class="ig-reel-play"></div>
    <div class="ig-reel-label">Reels</div>"""

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: transparent;
    display: flex;
    justify-content: center;
    padding: 8px 0;
  }}
  .ig-card {{
    max-width: 468px;
    width: 100%;
    background: #000;
    border: 1px solid #262626;
    border-radius: 8px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #f5f5f5;
    overflow: hidden;
    font-size: 14px;
    line-height: 1.4;
  }}
  .ig-header {{
    display: flex;
    align-items: center;
    padding: 10px 12px;
  }}
  .ig-avatar {{
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; color: #fff;
    flex-shrink: 0;
  }}
  .ig-profile {{
    margin-left: 10px;
    line-height: 1.3;
  }}
  .ig-handle {{
    font-weight: 600;
    font-size: 13px;
  }}
  .ig-location {{
    font-size: 11px;
    color: #a8a8a8;
  }}
  .ig-more {{
    margin-left: auto;
    color: #f5f5f5;
    font-size: 16px;
  }}
  .ig-image-wrap {{
    width: 100%;
    aspect-ratio: {aspect_ratio};
    overflow: hidden;
    background: #1a1a1a;
  }}
  .ig-image-wrap img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}
  .ig-actions {{
    display: flex;
    align-items: center;
    padding: 8px 12px 4px;
    gap: 14px;
  }}
  .ig-actions .spacer {{
    margin-left: auto;
  }}
  .ig-caption {{
    padding: 4px 12px 6px;
  }}
  .ig-caption .handle {{
    font-weight: 700;
  }}
  .ig-caption .text {{
    white-space: pre-wrap;
  }}
  .ig-hashtags {{
    color: #0095f6;
    margin-top: 2px;
    white-space: pre-wrap;
  }}
  .ig-footer {{
    padding: 2px 12px 10px;
    color: #a8a8a8;
    font-size: 11px;
  }}
  .ig-footer .time {{
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.5px;
    margin-top: 2px;
  }}{reel_overlay_css}
</style>
</head>
<body>
<div class="ig-card">
  <div class="ig-header">
    <div class="ig-avatar">{avatar_letter}</div>
    <div class="ig-profile">
      <div class="ig-handle">{hotel_handle}</div>
      <div class="ig-location">{HOTEL_LOCATION}</div>
    </div>
    <div class="ig-more">&middot;&middot;&middot;</div>
  </div>

  <div class="ig-image-wrap">
    <img src="data:image/jpeg;base64,{image_b64}" alt="Post image" />{reel_overlay_html}
  </div>

  <div class="ig-actions">
    <span style="font-size:22px;">&#9825;</span>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f5f5f5" stroke-width="1.8"><path d="M20.656 17.008a9.993 9.993 0 1 0-3.59 3.615L22 22l-1.344-4.992z"/></svg>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f5f5f5" stroke-width="1.8"><line x1="22" y1="3" x2="9.218" y2="10.083"/><polygon points="22 3 15 22 11 13 2 9"/></svg>
    <span class="spacer"></span>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f5f5f5" stroke-width="1.8"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
  </div>

  <div class="ig-caption">
    <div>
      <span class="handle">{hotel_handle}</span>&nbsp;
      <span class="text">{caption_safe}</span>
    </div>
    <div class="ig-hashtags">{hashtags_safe}</div>
  </div>

  <div class="ig-footer">
    <div>View all 12 comments</div>
    <div class="time">2 hours ago</div>
  </div>
</div>
</body>
</html>'''

    return html, estimated_height


def render_ig_preview_carousel(
    images_b64: list[str],
    caption: str,
    hashtags: str,
    hotel_name: str = HOTEL_NAME,
    hotel_handle: str = HOTEL_HANDLE,
) -> tuple[str, int]:
    """Return (html_string, estimated_height) for an Instagram carousel post mockup.

    Shows first image with dot indicators and slide counter. JavaScript-based
    left/right arrows to navigate between slides.

    Args:
        images_b64: List of base64-encoded images (2-10).
        caption: The caption text.
        hashtags: Space-separated hashtag string.

    Returns:
        Tuple of (html_string, estimated_pixel_height).
    """
    if not images_b64:
        return "<p>No images</p>", 50

    caption_safe = (caption or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    hashtags_safe = (hashtags or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    avatar_letter = (hotel_name or "H")[0].upper()
    total = len(images_b64)

    image_height = 585  # 4:5 aspect
    caption_lines = max(1, len(caption_safe) // 60 + 1) if caption_safe else 1
    hashtag_lines = max(1, len(hashtags_safe) // 60 + 1) if hashtags_safe else 0
    text_height = (caption_lines + hashtag_lines) * 20 + 30
    estimated_height = 52 + image_height + 40 + text_height + 40 + 50

    # Build image elements
    img_tags = ""
    for i, b64 in enumerate(images_b64):
        display = "block" if i == 0 else "none"
        img_tags += f'    <img id="slide-{i}" src="data:image/jpeg;base64,{b64}" alt="Slide {i+1}" style="display:{display};" />\n'

    # Dot indicators
    dots_html = ""
    for i in range(total):
        active = "active" if i == 0 else ""
        dots_html += f'<span class="dot {active}" id="dot-{i}"></span>'

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: transparent;
    display: flex;
    justify-content: center;
    padding: 8px 0;
  }}
  .ig-card {{
    max-width: 468px;
    width: 100%;
    background: #000;
    border: 1px solid #262626;
    border-radius: 8px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #f5f5f5;
    overflow: hidden;
    font-size: 14px;
    line-height: 1.4;
  }}
  .ig-header {{
    display: flex;
    align-items: center;
    padding: 10px 12px;
  }}
  .ig-avatar {{
    width: 32px; height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; color: #fff;
    flex-shrink: 0;
  }}
  .ig-profile {{
    margin-left: 10px;
    line-height: 1.3;
  }}
  .ig-handle {{
    font-weight: 600;
    font-size: 13px;
  }}
  .ig-location {{
    font-size: 11px;
    color: #a8a8a8;
  }}
  .ig-more {{
    margin-left: auto;
    color: #f5f5f5;
    font-size: 16px;
  }}
  .ig-image-wrap {{
    width: 100%;
    aspect-ratio: 4/5;
    overflow: hidden;
    background: #1a1a1a;
    position: relative;
  }}
  .ig-image-wrap img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    position: absolute;
    top: 0;
    left: 0;
  }}
  .ig-counter {{
    position: absolute;
    top: 12px;
    right: 12px;
    background: rgba(0,0,0,0.6);
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 12px;
  }}
  .ig-arrow {{
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 28px;
    height: 28px;
    background: rgba(255,255,255,0.85);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 14px;
    color: #333;
    border: none;
    z-index: 2;
  }}
  .ig-arrow:hover {{ background: #fff; }}
  .ig-arrow-left {{ left: 8px; }}
  .ig-arrow-right {{ right: 8px; }}
  .ig-dots {{
    display: flex;
    justify-content: center;
    gap: 4px;
    padding: 8px 0;
  }}
  .dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #555;
  }}
  .dot.active {{
    background: #0095f6;
  }}
  .ig-actions {{
    display: flex;
    align-items: center;
    padding: 8px 12px 4px;
    gap: 14px;
  }}
  .ig-actions .spacer {{
    margin-left: auto;
  }}
  .ig-caption {{
    padding: 4px 12px 6px;
  }}
  .ig-caption .handle {{
    font-weight: 700;
  }}
  .ig-caption .text {{
    white-space: pre-wrap;
  }}
  .ig-hashtags {{
    color: #0095f6;
    margin-top: 2px;
    white-space: pre-wrap;
  }}
  .ig-footer {{
    padding: 2px 12px 10px;
    color: #a8a8a8;
    font-size: 11px;
  }}
  .ig-footer .time {{
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.5px;
    margin-top: 2px;
  }}
</style>
</head>
<body>
<div class="ig-card">
  <div class="ig-header">
    <div class="ig-avatar">{avatar_letter}</div>
    <div class="ig-profile">
      <div class="ig-handle">{hotel_handle}</div>
      <div class="ig-location">{HOTEL_LOCATION}</div>
    </div>
    <div class="ig-more">&middot;&middot;&middot;</div>
  </div>

  <div class="ig-image-wrap" id="carousel">
{img_tags}
    <div class="ig-counter" id="counter">1/{total}</div>
    <button class="ig-arrow ig-arrow-left" onclick="prev()" id="arrow-left" style="display:none;">&#8249;</button>
    <button class="ig-arrow ig-arrow-right" onclick="next()" id="arrow-right">&#8250;</button>
  </div>

  <div class="ig-dots" id="dots">
    {dots_html}
  </div>

  <div class="ig-actions">
    <span style="font-size:22px;">&#9825;</span>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f5f5f5" stroke-width="1.8"><path d="M20.656 17.008a9.993 9.993 0 1 0-3.59 3.615L22 22l-1.344-4.992z"/></svg>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f5f5f5" stroke-width="1.8"><line x1="22" y1="3" x2="9.218" y2="10.083"/><polygon points="22 3 15 22 11 13 2 9"/></svg>
    <span class="spacer"></span>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f5f5f5" stroke-width="1.8"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
  </div>

  <div class="ig-caption">
    <div>
      <span class="handle">{hotel_handle}</span>&nbsp;
      <span class="text">{caption_safe}</span>
    </div>
    <div class="ig-hashtags">{hashtags_safe}</div>
  </div>

  <div class="ig-footer">
    <div>View all 12 comments</div>
    <div class="time">2 hours ago</div>
  </div>
</div>

<script>
  let current = 0;
  const total = {total};

  function show(idx) {{
    for (let i = 0; i < total; i++) {{
      document.getElementById('slide-' + i).style.display = i === idx ? 'block' : 'none';
      const dot = document.getElementById('dot-' + i);
      if (dot) dot.className = i === idx ? 'dot active' : 'dot';
    }}
    document.getElementById('counter').textContent = (idx + 1) + '/' + total;
    document.getElementById('arrow-left').style.display = idx > 0 ? 'flex' : 'none';
    document.getElementById('arrow-right').style.display = idx < total - 1 ? 'flex' : 'none';
    current = idx;
  }}

  function next() {{ if (current < total - 1) show(current + 1); }}
  function prev() {{ if (current > 0) show(current - 1); }}
</script>
</body>
</html>'''

    return html, estimated_height
