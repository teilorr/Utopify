from __future__ import annotations
import typing as t

from io import BytesIO
from PIL import Image

if t.TYPE_CHECKING:
    RGBAColor: t.TypeAlias = t.Tuple[int, int, int, int]
    ColorsType: t.TypeAlias = t.List[t.Tuple[int, RGBAColor]]


# https://stackoverflow.com/a/52879133
def _predominant_color_on(img: Image.Image) -> RGBAColor:
    width, height = (150, 150)
    img = img.resize((width, height), resample=0)

    pixels: ColorsType = img.getcolors(width * height)  # type: ignore # PIL stub file broken i hate this library

    sorted_pixels = sorted(pixels, key=lambda t: t[0])
    dominant_color = sorted_pixels[-1][1]
    return dominant_color


def predominant_color_on(img: t.Union[str, bytes]) -> RGBAColor:
    img_io = BytesIO(img) if isinstance(img, bytes) else img
    return _predominant_color_on(Image.open(img_io))
