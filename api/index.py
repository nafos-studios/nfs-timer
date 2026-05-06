from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query_components = parse_qs(urlparse(self.path).query)
        
        now = datetime.now(timezone.utc)
        # إذا ما بعثتش وقت في الرابط، السكريبت يمدلك 12 ساعة من دبا أوتوماتيكياً
        default_time = (now + timedelta(hours=12)).isoformat()
        end_str = query_components.get("end", [default_time])[0]
        
        try:
            # تنظيف السلسلة النصية وإزالة حرف Z إذا وجد
            end_str = end_str.replace('Z', '')
            end_date = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
        except Exception as e:
            end_date = now + timedelta(hours=12)

        diff = end_date - now
        seconds_left = max(0, int(diff.total_seconds()))

        try:
            font_path = os.path.join(os.path.dirname(__file__), 'font.ttf')
            main_font = ImageFont.truetype(font_path, 90) 
            label_font = ImageFont.truetype(font_path, 20)
        except:
            main_font = ImageFont.load_default()
            label_font = ImageFont.load_default()

        frames = []
        for i in range(10):
            # مساحة الصورة مريكلة باش يجي كلش في الوسط
            img = Image.new('RGB', (600, 200), color='#070710')
            d = ImageDraw.Draw(img)
            
            hours = seconds_left // 3600
            minutes = (seconds_left % 3600) // 60
            seconds = seconds_left % 60
            
            time_text = f"{hours:02d}  :  {minutes:02d}  :  {seconds:02d}"
            labels_text = "HOURS            MINUTES            SECONDS"
            
            # التمركز (Centering)
            d.text((110, 40), time_text, fill="#81A9D6", font=main_font)
            d.text((135, 140), labels_text, fill="#ffffff", font=label_font)
            
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
