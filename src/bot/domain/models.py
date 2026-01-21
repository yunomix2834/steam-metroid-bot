from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class Deal:
    appid: int
    name: str
    discount_pct: int
    price_final: str
    price_original: Optional[str]
    url: str
    image_url: Optional[str] = None
    tags: Sequence[str] = ()
