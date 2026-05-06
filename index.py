"""
Nafos Studios — Dynamic Countdown GIF Generator
Vercel Serverless Function

Usage: /api/timer?end=2026-06-01T23:59:59
       /api/timer?end=2026-06-01  (defaults to 00:00:00 UTC)

Returns: animated GIF — dark bg (#070710), light-blue text (#81A9D6)
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from io import BytesIO
import math

# ── Pillow is the only runtime dep ──────────────────────────────────────────
from PIL import Image, ImageDraw, ImageFont


# ── Brand palette ────────────────────────────────────────────────────────────
BG_COLOR   = (7, 7, 16)          # #070710
TEXT_COLOR = (129, 169, 214)     # #81A9D6  main digits
DIM_COLOR  = (60, 90, 120)       # separator / label dim
GLOW_COLOR = (129, 169, 214, 30) # subtle ambient glow (RGBA)

# ── Layout ───────────────────────────────────────────────────────────────────
W, H        = 420, 90            # canvas size (px) — fits nicely in emails
DIGIT_SIZE  = 48                 # font size for HH:MM:SS
LABEL_SIZE  = 11                 # font size for "HOURS  MINUTES  SECONDS"
FRAMES      = 60                 # one full second of animation (fps=10 → 6 s loop)
FRAME_DELAY = 100                # ms between frames (10 fps)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a monospace font; fall back to PIL default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "C:/Windows/Fonts/consola.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def _seconds_remaining(end_iso: str) -> int:
    """Parse ISO-8601 target and return whole seconds remaining (≥ 0)."""
    # Accept "2026-06-01" or "2026-06-01T23:59:59"
    fmt = "%Y-%m-%dT%H:%M:%S" if "T" in end_iso else "%Y-%m-%d"
    target = datetime.strptime(end_iso.strip(), fmt).replace(tzinfo=timezone.utc)
    delta = (target - datetime.now(tz=timezone.utc)).total_seconds()
    return max(0, math.floor(delta))


def _draw_frame(total_secs: int, digit_font, label_font) -> Image.Image:
    """Render one frame for a given number of remaining seconds."""
    hours   = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    seconds = total_secs % 60

    img  = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # ── subtle top-edge glow ─────────────────────────────────────────────────
    for y in range(3):
        alpha = 60 - y * 18
        draw.line([(0, y), (W, y)], fill=(*TEXT_COLOR, alpha), width=1)

    # ── timer string ─────────────────────────────────────────────────────────
    timer_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Center the digit block
    bbox = draw.textbbox((0, 0), timer_str, font=digit_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (W - tw) // 2
    ty = (H - th) // 2 - 8

    # Faint shadow for depth
    draw.text((tx + 2, ty + 2), timer_str, font=digit_font,
              fill=(0, 0, 0, 160))
    # Main text
    draw.text((tx, ty), timer_str, font=digit_font, fill=TEXT_COLOR)

    # ── colons pulse (dim on odd seconds) ────────────────────────────────────
    # Already drawn above; if you want a blinking effect re-draw colons:
    # (skipped for simpler, smoother look)

    # ── label row ────────────────────────────────────────────────────────────
    labels     = ["HOURS", "MINUTES", "SECONDS"]
    seg_width  = W // 3
    label_y    = ty + th + 6

    for i, label in enumerate(labels):
        lbbox = draw.textbbox((0, 0), label, font=label_font)
        lw = lbbox[2] - lbbox[0]
        lx = i * seg_width + (seg_width - lw) // 2
        draw.text((lx, label_y), label, font=label_font, fill=DIM_COLOR)

    return img


def generate_gif(end_iso: str) -> bytes:
    """Build an animated GIF and return raw bytes."""
    digit_font = _load_font(DIGIT_SIZE)
    label_font = _load_font(LABEL_SIZE)

    base_secs = _seconds_remaining(end_iso)
    frames: list[Image.Image] = []

    # Generate FRAMES frames, each representing 1 second
    # We loop 0..FRAMES-1 so the GIF ticks for FRAMES seconds then loops
    for i in range(FRAMES):
        secs = max(0, base_secs - i)
        frames.append(_draw_frame(secs, digit_font, label_font))

    buf = BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        loop=0,                   # infinite loop
        duration=FRAME_DELAY,
        optimize=False,
        disposal=2,               # clear to bg between frames
    )
    return buf.getvalue()


# ── Vercel handler ────────────────────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):

    def do_GET(self):  # noqa: N802  (Vercel expects this casing)
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        end_param = params.get("end", ["2026-12-31T23:59:59"])[0]

        try:
            gif_bytes = generate_gif(end_param)
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Content-Length", str(len(gif_bytes)))
            self.end_headers()
            self.wfile.write(gif_bytes)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).encode()
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def log_message(self, *_):  # silence Vercel logs
        pass