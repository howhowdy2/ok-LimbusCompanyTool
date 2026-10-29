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


def wanted_items(items, keywords, tiers, money):
    """要買的饰品，依優先順序：關鍵詞在設定裡的順序 → 等級高的先 → 便宜的先。

    keywords / tiers 空的 = 不限。讀不到價格或等級 (例如「替换…的技能」) 的不買，買不起的不買。
    """
    result = []
    for item in items:
        if item.price is None or item.tier is None or item.price > money:
            continue
        if keywords and item.keyword not in keywords:
            continue
        if tiers and item.tier not in tiers:
            continue
        result.append(item)
    rank = {k: i for i, k in enumerate(keywords or [])}
    return sorted(result, key=lambda it: (rank.get(it.keyword, 0), -it.tier, it.price))
