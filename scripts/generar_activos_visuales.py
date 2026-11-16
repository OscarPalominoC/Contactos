"""Genera los activos visuales de Check Ltda. a partir de la imagen original:
1. Extrae el logotipo circular con canal alfa antialiaseado.
2. Genera favicon.svg, favicon.ico y favicon.png.
3. Genera fondos de aplicación (claro y oscuro) compatibles con Glassmorphism y WCAG 2.1 AA.
"""
import base64
import io
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = Path("C:/Users/Oscar/.gemini/antigravity/brain/9310e9eb-91ed-47de-aabf-466f9e3ded00/.user_uploaded/media_1794707274916_a372ea28.jpg")
PUBLIC = RAIZ / "frontend" / "public"
DIST = RAIZ / "frontend" / "dist"
SKILLS_IMG = RAIZ / "SKILLS" / "images"

# Coordenadas exactas del logo circular en la imagen original
CX = 171.0
CY = 109.0
R = 48.0


def extraer_logo(origen_path: Path) -> Image.Image:
    """Extrae el logo circular con super-sampling y máscara antialiaseada."""
    img = Image.open(origen_path).convert("RGBA")
    pad = 2
    box = (int(CX - R - pad), int(CY - R - pad), int(CX + R + pad), int(CY + R + pad))
    recorte = img.crop(box)
    w, h = recorte.size

    # Máscara circular con supersampling 8x para bordes ultra-suaves
    scale = 8
    mascara = Image.new("L", (w * scale, h * scale), 0)
    draw = ImageDraw.Draw(mascara)
    ccx = (CX - box[0]) * scale
    ccy = (CY - box[1]) * scale
    rr = R * scale
    draw.ellipse((ccx - rr, ccy - rr, ccx + rr, ccy + rr), fill=255)
    mascara = mascara.resize((w, h), Image.Resampling.LANCZOS)
    recorte.putalpha(mascara)

    # Escalar a 512x512 y mejorar contraste/nitidez
    master = recorte.resize((512, 512), Image.Resampling.LANCZOS)
    master = ImageEnhance.Sharpness(master).enhance(1.35)
    master = ImageEnhance.Color(master).enhance(1.15)
    return master


def generar_favicons(logo: Image.Image) -> None:
    """Genera favicon.svg, favicon.ico y favicon.png."""
    # 1. Favicon PNG y master logo
    logo.save(PUBLIC / "logo-check.png", "PNG")
    logo.resize((64, 64), Image.Resampling.LANCZOS).save(PUBLIC / "favicon.png", "PNG")

    # 2. Favicon ICO con múltiples resoluciones
    logo.save(PUBLIC / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # 3. Favicon SVG con imagen incrustada en alta definición y contorno vectorial de marca
    buf = io.BytesIO()
    logo.resize((128, 128), Image.Resampling.LANCZOS).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
  <defs>
    <clipPath id="circle-clip">
      <circle cx="64" cy="64" r="62.5" />
    </clipPath>
    <filter id="subtle-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.25" />
    </filter>
  </defs>
  <circle cx="64" cy="64" r="63" fill="#D32F2F" stroke="#FBC02D" stroke-width="1.5" filter="url(#subtle-shadow)" />
  <g clip-path="url(#circle-clip)">
    <image href="data:image/png;base64,{b64}" x="0" y="0" width="128" height="128" />
  </g>
</svg>
"""
    (PUBLIC / "favicon.svg").write_text(svg_content, encoding="utf-8")
    print("Favicons generados exitosamente.")


def crear_orbe(ancho: int, alto: int, cx: int, cy: int, radio: int, color_rgb: tuple[int, int, int], opacidad: int) -> Image.Image:
    """Crea una capa con un orbe de gradiente radial suave para fondo de vidrio."""
    capa = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    bbox = (cx - radio, cy - radio, cx + radio, cy + radio)
    draw.ellipse(bbox, fill=(*color_rgb, opacidad))
    # Desenfoque gaussiano amplio para simular iluminación ambiental
    return capa.filter(ImageFilter.GaussianBlur(radio * 0.45))


def generar_fondos_glassmorphism(logo: Image.Image) -> None:
    """Genera fondos claro y oscuro con orbes ambientales y marca de agua del logo de Check Ltda."""
    ANCHO, ALTO = 2000, 1818

    # Logo watermark preparado a 800x800
    logo_wm = logo.resize((820, 820), Image.Resampling.LANCZOS)
    wm_x = ANCHO - 880  # Cuadrante derecho para lucir detrás de paneles
    wm_y = (ALTO - 820) // 2

    # -------------------------------------------------------------
    # 1. MODO CLARO (fondo_app_claro.webp)
    # Base: #F4F6F8 (244, 246, 248)
    # Colores: Rojo Automotriz #D32F2F, Azul Técnico #1565C0, Amarillo #FBC02D
    # -------------------------------------------------------------
    fondo_claro = Image.new("RGBA", (ANCHO, ALTO), (244, 246, 248, 255))

    # Orbe Rojo suave superior
    orbe_rojo = crear_orbe(ANCHO, ALTO, ANCHO - 350, 350, 600, (211, 47, 47), 38)
    fondo_claro.alpha_composite(orbe_rojo)

    # Orbe Azul suave inferior
    orbe_azul = crear_orbe(ANCHO, ALTO, 350, ALTO - 450, 700, (21, 101, 192), 35)
    fondo_claro.alpha_composite(orbe_azul)

    # Orbe Amarillo cálido central
    orbe_amarillo = crear_orbe(ANCHO, ALTO, ANCHO // 2, ALTO // 2, 500, (251, 192, 45), 30)
    fondo_claro.alpha_composite(orbe_amarillo)

    # Integrar marca de agua del logo con opacidad sutil (9% alfa)
    wm_claro = logo_wm.copy()
    r, g, b, a = wm_claro.split()
    a = a.point(lambda p: int(p * 0.095))
    wm_claro.putalpha(a)
    fondo_claro.alpha_composite(wm_claro, (wm_x, wm_y))

    # Guardar fondo claro WebP
    fondo_claro_rgb = fondo_claro.convert("RGB")
    fondo_claro_rgb.save(PUBLIC / "fondo_app_claro.webp", "WEBP", quality=92)
    print("fondo_app_claro.webp generado.")

    # -------------------------------------------------------------
    # 2. MODO OSCURO (fondo_app_oscuro.webp)
    # Base: #07080B (7, 8, 11)
    # -------------------------------------------------------------
    fondo_oscuro = Image.new("RGBA", (ANCHO, ALTO), (7, 8, 11, 255))

    # Orbe Rojo profundo
    orbe_rojo_dark = crear_orbe(ANCHO, ALTO, ANCHO - 400, 350, 650, (211, 47, 47), 55)
    fondo_oscuro.alpha_composite(orbe_rojo_dark)

    # Orbe Azul nocturno
    orbe_azul_dark = crear_orbe(ANCHO, ALTO, 300, ALTO - 400, 750, (21, 101, 192), 50)
    fondo_oscuro.alpha_composite(orbe_azul_dark)

    # Orbe Ámbar suave
    orbe_ambar_dark = crear_orbe(ANCHO, ALTO, ANCHO // 2 + 100, ALTO // 2, 550, (251, 192, 45), 45)
    fondo_oscuro.alpha_composite(orbe_ambar_dark)

    # Integrar marca de agua del logo con opacidad y resplandor (14% alfa)
    wm_oscuro = logo_wm.copy()
    r, g, b, a = wm_oscuro.split()
    a = a.point(lambda p: int(p * 0.14))
    wm_oscuro.putalpha(a)
    fondo_oscuro.alpha_composite(wm_oscuro, (wm_x, wm_y))

    # Guardar fondo oscuro WebP
    fondo_oscuro_rgb = fondo_oscuro.convert("RGB")
    fondo_oscuro_rgb.save(PUBLIC / "fondo_app_oscuro.webp", "WEBP", quality=92)
    print("fondo_app_oscuro.webp generado.")


def sincronizar_copias():
    """Copia los activos a dist/ y a SKILLS/images/ para mantener coherencia."""
    archivos = ["fondo_app_claro.webp", "fondo_app_oscuro.webp", "favicon.svg", "logo-check.png"]
    for nombre in archivos:
        src = PUBLIC / nombre
        if src.exists():
            if DIST.exists():
                (DIST / nombre).write_bytes(src.read_bytes())
            if SKILLS_IMG.exists():
                (SKILLS_IMG / nombre).write_bytes(src.read_bytes())
    print("Sincronización a dist/ y SKILLS/images/ completada.")


def main():
    if not ORIGEN.exists():
        raise FileNotFoundError(f"No se encontró la imagen original en {ORIGEN}")
    print(f"Extrayendo logo desde {ORIGEN}...")
    logo = extraer_logo(ORIGEN)
    generar_favicons(logo)
    generar_fondos_glassmorphism(logo)
    sincronizar_copias()
    print("Todos los activos visuales fueron creados y optimizados exitosamente.")


if __name__ == "__main__":
    main()

