from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        # تقدر تبعث تاريخ النهاية في الرابط، مثلا: ?end=2026-05-06T20:00:00
        end_str = query_components.get("end", ["2026-06-01T23:59:59"])[0]
        
        try:
            end_date = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        except:
            end_date = datetime.now(timezone.utc)

        now = datetime.now(timezone.utc)
        diff = end_date - now
        seconds_left = max(0, int(diff.total_seconds()))

        # تحميل الخط font.ttf اللي راه معاك في مجلد api
        try:
            font_path = os.path.join(os.path.dirname(__file__), 'font.ttf')
            main_font = ImageFont.truetype(font_path, 80) # خط الساعات كبير
            label_font = ImageFont.truetype(font_path, 22) # خط الكلمات صغير
        except:
            main_font = ImageFont.load_default()
            label_font = ImageFont.load_default()

        frames = []
        for i in range(10):
            # صورة متناسقة مع 3 خانات (Hours, Mins, Secs)
            img = Image.new('RGB', (650, 180), color='#070710')
            d = ImageDraw.Draw(img)
            
            # حساب الساعات مباشرة (حتى لو كانت فوق 24 ساعة تخرج ساعات)
            hours = seconds_left // 3600
            minutes = (seconds_left % 3600) // 60
            seconds = seconds_left % 60
            
            time_text = f"{hours:02d}   :   {minutes:02d}   :   {seconds:02d}"
            labels_text = "HOURS             MINUTES             SECONDS"
            
            # وضع النص في الوسط
            d.text((105, 30), time_text, fill="#81A9D6", font=main_font)
            d.text((125, 120), labels_text, fill="#ffffff", font=label_font)
            
            frames.append(img)
            if seconds_left > 0: seconds_left -= 1

        img_io = BytesIO()
        frames[0].save(img_io, 'GIF', save_all=True, append_images=frames[1:], duration=1000, loop=0)
        img_io.seek(0)

        self.send_response(200)
        self.send_header('Content-type', 'image/gif')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(img_io.getvalue())
