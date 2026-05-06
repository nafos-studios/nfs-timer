from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import math

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        end_str = query_components.get("end", ["2026-06-01T23:59:59"])[0]
        
        try:
            end_date = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        except:
            end_date = datetime.now(timezone.utc)

        now = datetime.now(timezone.utc)
        diff = end_date - now
        seconds_left = max(0, int(diff.total_seconds()))

        # Create GIF
        frames = []
        for i in range(10):  # 10 frames
            img = Image.new('RGB', (400, 100), color='#070710')
            d = ImageDraw.Draw(img)
            
            days = seconds_left // 86400
            hours = (seconds_left % 86400) // 3600
            minutes = (seconds_left % 3600) // 60
            seconds = seconds_left % 60
            
            text = f"{days:02d}:{hours:02d}:{minutes:02d}:{seconds:02d}"
            d.text((100, 35), text, fill="#81A9D6")
            frames.append(img)
            if seconds_left > 0: seconds_left -= 1

        img_io = BytesIO()
        frames[0].save(img_io, 'GIF', save_all=True, append_images=frames[1:], duration=1000, loop=0)
        img_io.seek(0)

        self.send_response(200)
        self.send_header('Content-type', 'image/gif')
        self.end_headers()
        self.wfile.write(img_io.getvalue())
