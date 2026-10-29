"""鏡像迷宮主題卡包資料：哪個卡包會出現在哪一層 (普通 / 困難)。

資料在 assets/lc/mirror_packs.csv (卡包名称,普通模式,困难模式)，
樓層寫法像「1F、2F」，「—」= 這個難度不會出現。遊戲改版就更新那個 CSV。
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[2] / 'assets' / 'lc' / 'mirror_packs.csv'
FLOORS = (1, 2, 3, 4, 5)


def parse_floors(text: str) -> tuple[int, ...]:
    return tuple(sorted({int(n) for n in re.findall(r'(\d+)\s*F', text or '')}))


@lru_cache(maxsize=1)
def load_packs(path: str = str(CSV_PATH)) -> dict[str, dict[str, tuple[int, ...]]]:
    """{卡包名称: {'normal': (1, 2), 'hard': (1,)}}，保持 CSV 的順序。"""
    packs: dict[str, dict[str, tuple[int, ...]]] = {}
    try:
        with open(path, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                name = (row.get('卡包名称') or '').strip()
                if name:
                    packs[name] = {'normal': parse_floors(row.get('普通模式', '')),
                                   'hard': parse_floors(row.get('困难模式', ''))}
    except FileNotFoundError:
        pass
    return packs


def packs_on_floor(floor: int, hard: bool | None = None) -> list[str]:
    """這一層會出現的卡包。hard=None = 普通或困難任一種會出現就算。"""
    result = []
    for name, floors in load_packs().items():
        if hard is None:
            ok = floor in floors['normal'] or floor in floors['hard']
        else:
            ok = floor in floors['hard' if hard else 'normal']
        if ok:
            result.append(name)
    return result


def all_packs() -> list[str]:
    return list(load_packs())
