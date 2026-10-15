from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 1024

img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ===== КРУГ С ТЁПЛЫМ ГРАДИЕНТОМ =====
center = SIZE // 2
radius = SIZE // 2 - 20

for y in range(SIZE):
    for x in range(SIZE):
        dx = x - center
        dy = y - center
        dist = (dx * dx + dy * dy) ** 0.5

        if dist <= radius:
            t = dist / radius
            t = t ** 0.5

            # Тёплый градиент: сверху ярко-жёлтый → снизу тёмно-оранжевый
            vy = (y - center) / radius
            warm = (vy + 1) / 2

            r = int(255 * (1 - warm) + 193 * warm) - int(t * 30)
            g = int(217 * (1 - warm) + 68 * warm) - int(t * 20)
            b = int(61 * (1 - warm) + 14 * warm) - int(t * 10)

            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            img.putpixel((x, y), (r, g, b, 255))
        else:
            img.putpixel((x, y), (0, 0, 0, 0))

draw = ImageDraw.Draw(img)

# ===== ШРИФТ =====
font_bold_paths = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

def find_font(paths, size):
    for fp in paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

# Огромная буква "С"
font_letter = find_font(font_bold_paths, 620)

# ===== БУКВА "С" =====
text = "С"
bbox = draw.textbbox((0, 0), text, font=font_letter)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
x = (SIZE - tw) / 2 - bbox[0]
y = (SIZE - th) / 2 - bbox[1] - 20   # чуть выше центра (оптически по центру)

# Тёплая тень (коричневая)
draw.text((x + 8, y + 8), text, font=font_letter, fill=(80, 30, 0, 130))
# Белая буква
draw.text((x, y), text, font=font_letter, fill=(255, 250, 240, 255))

# ===== СОХРАНЯЕМ =====
img.save('static/icon-1024.png')
print("✅ static/icon-1024.png создан!")

for size in [512, 192]:
    resized = img.resize((size, size), Image.LANCZOS)
    resized.save(f'static/icon-{size}.png')
    print(f"✅ static/icon-{size}.png создан!")

print("\n🎉 Все иконки готовы!")