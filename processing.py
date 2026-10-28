"""Operações de processamento independentes da interface gráfica."""

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# Nome da operação: (rótulo do ajuste, mínimo, máximo, valor inicial).
OPERATIONS = {
    "Brilho": ("Fator de brilho", 0.0, 3.0, 1.5),
    "Contraste": ("Fator de contraste", 0.0, 3.0, 1.5),
    "Nitidez": ("Fator de nitidez", 0.0, 5.0, 2.0),
    "Tons de cinza": None,
    "Negativo": None,
    "Equalização do histograma": None,
    "Suavização gaussiana": ("Raio de suavização (pixels)", 0.0, 10.0, 2.0),
}


def load_image(path: str | Path) -> Image.Image:
    """Abre uma imagem, corrige sua orientação e compõe transparência sobre branco."""
    with Image.open(path) as source:
        oriented = ImageOps.exif_transpose(source)
        rgba = oriented.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        return Image.alpha_composite(background, rgba).convert("RGB")


def process_image(image: Image.Image, operation: str, factor: float = 1.0) -> Image.Image:
    """Retorna uma nova imagem sem modificar a original."""
    if operation not in OPERATIONS:
        raise ValueError(f"Operação desconhecida: {operation}")

    settings = OPERATIONS[operation]
    if settings is not None and not settings[1] <= factor <= settings[2]:
        raise ValueError(f"O ajuste deve estar entre {settings[1]} e {settings[2]}.")

    rgb = image.convert("RGB")
    if operation == "Brilho":
        return ImageEnhance.Brightness(rgb).enhance(factor)
    if operation == "Contraste":
        return ImageEnhance.Contrast(rgb).enhance(factor)
    if operation == "Nitidez":
        return ImageEnhance.Sharpness(rgb).enhance(factor)
    if operation == "Tons de cinza":
        return ImageOps.grayscale(rgb)
    if operation == "Negativo":
        return ImageOps.invert(rgb)
    if operation == "Equalização do histograma":
        # Equaliza a luminância, preservando os canais de cor (Cb e Cr).
        luminance, cb, cr = rgb.convert("YCbCr").split()
        return Image.merge("YCbCr", (ImageOps.equalize(luminance), cb, cr)).convert("RGB")
    return rgb.filter(ImageFilter.GaussianBlur(radius=factor))


def image_histograms(image: Image.Image) -> list[tuple[str, str, list[int]]]:
    """Retorna nome, cor do gráfico e contagens dos 256 níveis de cada canal."""
    if image.mode == "L":
        return [("Cinza", "#475569", image.histogram())]

    channels = image.convert("RGB").split()
    return [
        (name, color, channel.histogram())
        for name, color, channel in zip(
            ("Vermelho", "Verde", "Azul"), ("#dc2626", "#15803d", "#2563eb"), channels
        )
    ]
