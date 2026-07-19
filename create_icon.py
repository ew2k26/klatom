#!/usr/bin/env python3
"""Generate ew² app icon - dark eye design."""

from PIL import Image, ImageDraw, ImageFilter
import math

def create_icon():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 256))
        draw = ImageDraw.Draw(img)
        cx, cy = size // 2, size // 2

        # Outer eye shape - dark ellipse
        eye_w = int(size * 0.45)
        eye_h = int(size * 0.25)
        draw.ellipse(
            [cx - eye_w, cy - eye_h, cx + eye_w, cy + eye_h],
            fill=(20, 20, 25, 255),
            outline=(50, 50, 60, 200),
            width=max(1, size // 32),
        )

        # Inner white/sclera - subtle
        sclera_w = int(size * 0.32)
        sclera_h = int(size * 0.16)
        draw.ellipse(
            [cx - sclera_w, cy - sclera_h, cx + sclera_w, cy + sclera_h],
            fill=(35, 35, 42, 255),
        )

        # Iris - dark circle
        iris_r = int(size * 0.13)
        draw.ellipse(
            [cx - iris_r, cy - iris_r, cx + iris_r, cy + iris_r],
            fill=(10, 10, 14, 255),
        )

        # Pupil - pure black
        pupil_r = int(size * 0.07)
        draw.ellipse(
            [cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r],
            fill=(0, 0, 0, 255),
        )

        # Light reflections - small white dots
        if size >= 32:
            ref_r = max(1, size // 24)
            # Main reflection
            rx1 = cx + int(size * 0.04)
            ry1 = cy - int(size * 0.04)
            draw.ellipse(
                [rx1 - ref_r, ry1 - ref_r, rx1 + ref_r, ry1 + ref_r],
                fill=(180, 180, 200, 220),
            )
            # Secondary reflection
            if size >= 64:
                ref_r2 = max(1, size // 40)
                rx2 = cx - int(size * 0.06)
                ry2 = cy + int(size * 0.03)
                draw.ellipse(
                    [rx2 - ref_r2, ry2 - ref_r2, rx2 + ref_r2, ry2 + ref_r2],
                    fill=(120, 120, 140, 160),
                )

        # Subtle neutral glow around iris
        if size >= 48:
            glow_r = int(size * 0.18)
            glow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_img)
            glow_draw.ellipse(
                [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
                outline=(80, 80, 90, 60),
                width=max(1, size // 20),
            )
            img = Image.alpha_composite(img, glow_img)

        images.append(img)

    # Save as ICO with multiple sizes
    ico_path = "C:\\Users\\kasu\\Downloads\\Klatom\\ew2.ico"
    images[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1],
    )
    print(f"Icon saved: {ico_path}")

    # Also save PNG version
    png_path = "C:\\Users\\kasu\\Downloads\\Klatom\\ew2_icon.png"
    images[-1].save(png_path, format="PNG")
    print(f"PNG saved: {png_path}")

if __name__ == "__main__":
    create_icon()
