"""Ícone da Jarvis na bandeja do Windows."""

from __future__ import annotations

from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw, ImageFont


def icon_image(size: int = 64) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, size - 2, size - 2), fill=(15, 18, 22, 255), outline=(76, 194, 255, 255), width=4)
    font = ImageFont.load_default(size=int(size * 0.55))
    draw.text((size / 2, size / 2), "J", font=font, fill=(76, 194, 255, 255), anchor="mm")
    return image


def create(
    on_open: Callable[[], None],
    on_quit: Callable[[], None],
    voice=None,
    on_talk: Callable[[], None] | None = None,
) -> pystray.Icon:
    items = [pystray.MenuItem("Abrir Jarvis", lambda: on_open(), default=True)]
    if voice is not None:
        items += [
            pystray.MenuItem("Falar agora", lambda: on_talk() if on_talk else voice.listen_now()),
            pystray.MenuItem(
                "Pausar escuta (“Hey Jarvis”)",
                lambda: voice.set_paused(not voice.paused.is_set()),
                checked=lambda _item: voice.paused.is_set(),
            ),
        ]
    items.append(pystray.MenuItem("Sair", lambda: on_quit()))
    return pystray.Icon("SuperJarvis", icon_image(), "Jarvis", pystray.Menu(*items))
