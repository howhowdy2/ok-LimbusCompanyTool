"""戰鬥後的獎勵選擇 (純邏輯，可以單元測試)。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.lc.vision import normalize_name

# 遭遇戰獎勵卡：看卡片下面的說明分類
CARD_STAR, CARD_MONEY, CARD_GIFT, CARD_CHANCE_GIFT, CARD_OTHER = '星芒', '經費', '飾品', '機率飾品', '其他'
CARD_KINDS = (CARD_STAR, CARD_MONEY, CARD_GIFT, CARD_CHANCE_GIFT, CARD_OTHER)

BASIS_AFFLICTION, BASIS_GIFT = '苦難', '飾品'

# 苦難優先順序 (越前面越好選)：T0 體力上限/防禦/守備 → T1 攻擊等級/等級提升 → T2 拼點威力
# → T3 基礎威力/最終威力/傷害 → T4 硬幣威力
AFFLICTION_DEFAULT = ['体力上限', '生长', '防御等级', '守备', '攻击等级', '等级提升',
                      '拼点威力', '基础威力', '最终威力', '伤害', '硬币威力']


def classify_card(text: str) -> str:
    text = normalize_name(text)
    if '星芒' in text:
        return CARD_STAR
    if '经费' in text:
        return CARD_MONEY
    if '饰品' in text:
        return CARD_CHANCE_GIFT if ('概率' in text or '几率' in text or '机率' in text) else CARD_GIFT
    return CARD_OTHER


def affliction_rank(text: str, rules) -> int:
    """苦難的順位 (越小越好)。

    一個苦難常有好幾個效果 (「防御等级+1，体力上限+7.5%」)：每一段取它符合的第一條規則，
    整個苦難算最差的那一段；都不符合排最後。
    """
    rules = [normalize_name(r) for r in rules if normalize_name(r)]
    worst = None
    for clause in re.split(r'[，,、;；\s]+', text or ''):
        clause = normalize_name(clause)
        if not clause:
            continue
        for i, rule in enumerate(rules):
            if rule in clause:
                worst = i if worst is None else max(worst, i)
                break
    return len(rules) if worst is None else worst


@dataclass
class GiftReward:
    index: int
    tier: int | None
    keyword: str | None
    affliction: str
    enemy_level: int | None = None


def rank_gift_rewards(cards, basis, rules, keywords):
    """回傳排好的卡片 (最想要的在前)。

    以苦難為準：苦難順位 → 敵方等級增加少的 → 饰品等級高的。
    以饰品為準：關鍵詞符合 (照設定順序) → 饰品等級高的 → 苦難順位。
    """
    kw_rank = {k: i for i, k in enumerate(keywords or [])}

    def key(card):
        aff = affliction_rank(card.affliction, rules)
        tier = -(card.tier or 0)
        level = card.enemy_level if card.enemy_level is not None else 99
        if basis == BASIS_GIFT:
            kw = kw_rank.get(card.keyword, len(kw_rank)) if keywords else 0
            return kw, tier, aff, level
        return aff, level, tier
    return sorted(cards, key=key)
