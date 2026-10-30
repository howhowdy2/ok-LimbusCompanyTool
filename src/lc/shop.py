"""鏡像迷宮商店的純邏輯 (挑要買的、合成材料怎麼配)，不碰遊戲，可以單元測試。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

# 合成：饰品等級 -> 點數；總點數 -> 合成出來的等級 (普通商店)
FUSE_POINTS = {1: 3, 2: 6, 3: 10, 4: 15, 5: 30}
FUSE_TIER_MIN_POINTS = ((25, 4), (17, 3), (11, 2), (0, 1))
FUSE_MIN_ITEMS, FUSE_MAX_ITEMS = 2, 3


def fuse_result_tier(total: int) -> int:
    for minimum, tier in FUSE_TIER_MIN_POINTS:
        if total >= minimum:
            return tier
    return 1


def best_fuse_combo(tiers, targets):
    """tiers：可以當材料的饰品等級 (依畫面順序)；targets：想合成的等級 (例如 {3, 4})。

    回傳要放進去的材料索引 (tuple)，做不到回傳 None。
    挑法：能做出的最高目標等級優先 → 總點數最少 (不浪費) → 材料最少；
    不會拿「等級 >= 目標」的饰品當材料 (拿 IV 去合 IV 沒意義)。
    """
    best, best_key = None, None
    usable = [(i, t) for i, t in enumerate(tiers) if t in FUSE_POINTS]
    for count in range(FUSE_MIN_ITEMS, FUSE_MAX_ITEMS + 1):
        for combo in combinations(usable, count):
            total = sum(FUSE_POINTS[t] for _, t in combo)
            result = fuse_result_tier(total)
            if result not in targets or any(t >= result for _, t in combo):
                continue
            key = (-result, total, count)
            if best_key is None or key < best_key:
                best, best_key = tuple(i for i, _ in combo), key
    return best


@dataclass
class ShopItem:
    index: int          # 第幾格 (0~7，由左到右、上到下)
    tier: int | None
    keyword: str | None
    price: int | None
    name: str = ''


def wanted_items(items, keywords, tiers, money, wanted=None):
    """要買的饰品，依優先順序：「想要的饰品」清單裡的 (照清單順序) → 關鍵詞在設定裡的順序 → 等級高的 → 便宜的。

    keywords / tiers 空的 = 不限；想要清單裡的饰品不受關鍵詞 / 等級限制。
    讀不到價格的不買，買不起的不買。
    """
    from src.lc import gifts
    result = []
    for item in items:
        if item.price is None or item.price > money:
            continue
        if gifts.wanted_rank(item.name, wanted) is not None:
            result.append(item)
            continue
        if item.tier is None:
            continue
        if keywords and item.keyword not in keywords:
            continue
        if tiers and item.tier not in tiers:
            continue
        result.append(item)
    rank = {k: i for i, k in enumerate(keywords or [])}

    def key(it):
        w = gifts.wanted_rank(it.name, wanted)
        return (0 if w is not None else 1, w or 0, rank.get(it.keyword, 0), -(it.tier or 0), it.price)
    return sorted(result, key=key)


def fuse_materials(gifts_on_screen, material_tiers, avoid_keywords, skip_enhanced):
    """可以拿去合成的饰品：等級在 material_tiers、不是要保留的關鍵詞、(可選) 沒強化過。

    gifts_on_screen: [(索引, 等級, 關鍵詞, 強化過)]
    """
    return [g for g in gifts_on_screen
            if g[1] in material_tiers and g[2] not in avoid_keywords and not (skip_enhanced and g[3])]
