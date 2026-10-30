"""E.G.O 饰品資料：名稱、等級、關鍵詞 (assets/lc/ego_gifts.csv，欄位：饰品名称,等级,关键词)。

設定畫面的選項會寫成「名稱（IV·突刺）」，比對時只看括號前的名稱。遊戲改版就更新 CSV。
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from src.lc.vision import names_match, normalize_name

CSV_PATH = Path(__file__).resolve().parents[2] / 'assets' / 'lc' / 'ego_gifts.csv'
TIERS = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'EX': 6}
TIER_NAMES = {v: k for k, v in TIERS.items()}
GENERIC = '泛用'


@lru_cache(maxsize=1)
def load_gifts(path: str = str(CSV_PATH)) -> dict[str, tuple[int, str]]:
    """{名稱: (等級 1~6, 關鍵詞)}，保持 CSV 順序 (等級 → 關鍵詞)。"""
    gifts = {}
    try:
        with open(path, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                name = (row.get('饰品名称') or '').strip()
                if name:
                    gifts[name] = (TIERS.get((row.get('等级') or '').strip(), 0), (row.get('关键词') or '').strip())
    except FileNotFoundError:
        pass
    return gifts


def label(name: str) -> str:
    tier, kw = load_gifts().get(name, (0, ''))
    return f'{name}（{TIER_NAMES.get(tier, "?")}·{kw or "?"}）'


def name_of(option: str) -> str:
    """「名稱（IV·突刺）」-> 「名稱」；舊設定直接寫名稱也可以。"""
    return str(option).split('（')[0].split('(')[0].strip()


def all_labels() -> list[str]:
    return [label(n) for n in load_gifts()]


def fuse_target_labels() -> list[str]:
    """合成做得出來的：2~4 級、有關鍵詞 (泛用的不能選關鍵詞合成)。"""
    return [label(n) for n, (tier, kw) in load_gifts().items() if 2 <= tier <= 4 and kw and kw != GENERIC]


def info(name: str):
    """(等級, 關鍵詞)；不認得回傳 None。"""
    return load_gifts().get(name_of(name))


@lru_cache(maxsize=2048)
def match(text: str) -> str | None:
    """OCR 讀到的名稱 -> 資料裡的名稱 (容許少一個字)；認不出來回傳 None。"""
    target = normalize_name(text)
    if len(target) < 2:
        return None
    for name in load_gifts():
        if names_match(normalize_name(name), target):
            return name
    return None


def wanted_rank(name: str | None, wanted_options) -> int | None:
    """name 在「想要的饰品」清單第幾個 (越小越優先)，不在清單回傳 None。"""
    if not name:
        return None
    for i, option in enumerate(wanted_options or []):
        if name_of(option) == name:
            return i
    return None
