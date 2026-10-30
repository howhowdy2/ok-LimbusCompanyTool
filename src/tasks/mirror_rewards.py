"""戰鬥後的獎勵：遭遇戰獎勵卡、選 E.G.O 饰品 (附帶苦難)。給 MirrorDungeonTask 繼承用。"""

from src.lc import gifts, rewards, vision
from src.lc.layout import (GIFT_KEYWORDS, GIFT_REWARD_CLICK_Y, GIFT_TAG_TO_CENTER, KEYWORD_TEMPLATES, GIFT_REWARD_KEYWORD, GIFT_REWARD_SELECT,
                           GIFT_REWARD_TIER, GIFT_REWARD_X, KEYWORD_MATCH_THRESHOLD, REWARD_CARD_CONFIRM,
                           REWARD_CARD_Y, TEXT)

REWARD_DEFAULTS = {
    'Wanted Gifts': [],
    'Reward Card Priority': list(rewards.CARD_KINDS),
    'Reward Gift Basis': rewards.BASIS_AFFLICTION,
    'Affliction Priority': list(rewards.AFFLICTION_DEFAULT),
    'Reward Keywords': [],
}
REWARD_TYPES = {
    'Wanted Gifts': {'type': 'drop_down', 'options_available': gifts.all_labels()},
    'Reward Card Priority': {'type': 'drop_down', 'options_available': list(rewards.CARD_KINDS)},
    'Affliction Priority': {'type': 'drop_down', 'options_available': list(rewards.AFFLICTION_DEFAULT)},
    'Reward Gift Basis': {'type': 'drop_down', 'options': [rewards.BASIS_AFFLICTION, rewards.BASIS_GIFT]},
    'Reward Keywords': {'type': 'drop_down', 'options_available': GIFT_KEYWORDS},
}
REWARD_DESCRIPTIONS = {
    'Wanted Gifts': '想要的 E.G.O 饰品 (越上面越優先)：戰後獎勵和商店看到名稱符合的會最先拿 / 買，'
                    '不受關鍵詞、等級、苦難的限制',
    'Reward Card Priority': '「选择遭遇战奖励卡」的優先順序，一行一個：' + '、'.join(rewards.CARD_KINDS),
    'Reward Gift Basis': '戰鬥後選 E.G.O 饰品 (每張附帶一個苦難) 時，以苦難還是以饰品為準',
    'Affliction Priority': '以苦難為準時，苦難說明含這些字的優先 (越上面越好)，都不含的排最後。'
                           '預設：體力上限/防禦/守備 > 攻擊等級 > 拼點威力 > 基礎/最終威力/傷害 > 硬幣威力',
    'Reward Keywords': '以饰品為準時想要的關鍵詞 (越上面越優先)，之後看等級高的',
}


class MirrorRewardMixin:

    def card_names(self):
        """饰品卡上方的名稱：[(中心 x 相對座標, 資料裡的名稱)]，認不出來的略過。"""
        result = []
        for b in self.ocr_roi('gift_name_row'):
            name = gifts.match(b.name)
            if name:
                result.append(((b.x + b.width / 2) / self.width, name))
        return result

    @staticmethod
    def name_near(names, cx, limit=0.09):
        near = [(abs(x - cx), n) for x, n in names if abs(x - cx) < limit]
        return min(near)[1] if near else ''

    def handle_rewards(self) -> bool:
        """畫面是獎勵選擇就處理掉，回傳 True。"""
        if self.ocr_roi('reward_card_title', TEXT['reward_card_title']):
            self.choose_reward_cards()
            return True
        if self.ocr_roi('gift_reward_marker', TEXT['gift_reward_marker']):
            self.choose_gift_rewards()
            return True
        if self.ocr_roi('gift_reward_btns', TEXT['reject']):
            self.choose_plain_gifts()
            return True
        return False

    def picks_left(self, roi, default=1):
        found = vision.parse_fraction(''.join(b.name for b in self.ocr_roi(roi)).replace(' ', ''))
        return max(0, found[1] - found[0]) if found else default

    # ---------- 遭遇戰獎勵卡 ----------

    def choose_reward_cards(self):
        self.sleep(1)
        self.next_frame()
        boxes = sorted((b for b in self.ocr_roi('reward_card_text') if b.name.strip()), key=lambda b: b.x)
        cards = []   # [(中心 x 相對座標, 說明)]
        for b in boxes:
            cx = (b.x + b.width / 2) / self.width
            if cards and abs(cx - cards[-1][0]) < 0.06:
                cards[-1] = ((cards[-1][0] + cx) / 2, cards[-1][1] + b.name)
            else:
                cards.append((cx, b.name))
        n = self.picks_left('reward_card_count')
        priority = [str(x).strip() for x in self.config.get('Reward Card Priority', rewards.CARD_KINDS)]
        ranked = sorted(cards, key=lambda c: priority.index(rewards.classify_card(c[1]))
                        if rewards.classify_card(c[1]) in priority else len(priority))
        self.log_info('獎勵卡：' + '、'.join(f'{t} [{rewards.classify_card(t)}]' for _, t in cards)
                      + f'，選 {n} 張')
        for x, text in ranked[:n]:
            self.info_set('獎勵卡', text)
            self.click_relative(x, REWARD_CARD_Y, after_sleep=0.8)
        if not cards:
            self.screenshot('fail_reward_cards')
            self.log_warning('讀不到獎勵卡說明，直接按确认')
        self.click_relative(*REWARD_CARD_CONFIRM, after_sleep=2)

    # ---------- 選饰品 (附帶苦難) ----------

    def gift_reward_cards(self):
        self.next_frame()
        templates = self.keyword_templates()
        names = self.card_names()
        aff_boxes = self.ocr_roi('gift_reward_aff')
        level_boxes = self.ocr_roi('gift_reward_level')
        cards = []
        for i, x in enumerate(GIFT_REWARD_X):
            near = lambda b: abs((b.x + b.width / 2) / self.width - x) < 0.1
            text = ' '.join(b.name for b in aff_boxes if near(b))
            if not text.strip():
                continue    # 這格沒有卡片 (只有 2、3 張的時候)
            level = None
            for b in level_boxes:
                if near(b) and '+' in b.name:
                    level = vision.parse_int(b.name)
            tx0, ty0, tx1, ty1 = GIFT_REWARD_TIER
            kx0, ky0, kx1, ky1 = GIFT_REWARD_KEYWORD
            tier = vision.tier_in_roi(self.frame, (x + tx0, ty0, x + tx1, ty1))
            kw, score = vision.keyword_in_roi(self.frame, (x + kx0, ky0, x + kx1, ky1), templates)
            name = self.name_near(names, x)
            kw = kw if score >= KEYWORD_MATCH_THRESHOLD else None
            if name:
                tier, kw = gifts.info(name)
            cards.append(rewards.GiftReward(i, tier, kw, text, level, name))
        return cards

    def choose_gift_rewards(self):
        self.sleep(1)
        cards = self.gift_reward_cards()
        n = self.picks_left('gift_reward_btns')
        basis = self.config.get('Reward Gift Basis', rewards.BASIS_AFFLICTION)
        rules = [str(x).strip() for x in self.config.get('Affliction Priority', rewards.AFFLICTION_DEFAULT)
                 if str(x).strip()]
        ranked = rewards.rank_gift_rewards(cards, basis, rules, list(self.config.get('Reward Keywords', [])),
                                           self.config.get('Wanted Gifts', []))
        self.log_info(f'選饰品獎勵 (以{basis}為準，選 {n} 個)：' + '、'.join(
            f'{c.index + 1}:{c.name or "?"}/{gifts.TIER_NAMES.get(c.tier, "?")}/{c.keyword or "?"}/{c.affliction}'
            f'/+{c.enemy_level}' for c in ranked))
        for card in ranked[:n]:
            self.click_relative(GIFT_REWARD_X[card.index], GIFT_REWARD_CLICK_Y, after_sleep=0.8)
        if not cards:
            self.screenshot('fail_gift_rewards')
            self.log_warning('讀不到饰品獎勵卡')
        button = self.ocr_roi('gift_reward_btns', TEXT['select'])
        if button:
            self.click_box(button[-1], after_sleep=2)
        else:
            self.click_relative(*GIFT_REWARD_SELECT, after_sleep=2)
        self.info_incr('戰後饰品')

    # ---------- 選饰品 (沒有苦難，特殊戰鬥後) ----------

    def plain_gift_cards(self):
        """用每張卡右上的「获得E.G.O饰品」標籤找卡片 (1~4 張、位置不固定)。"""
        self.next_frame()
        templates = self.keyword_templates()
        cards = []
        names = self.card_names()
        tags = sorted(self.ocr_roi('gift_tag_row', TEXT['gift_got']), key=lambda b: b.x)
        for i, tag in enumerate(tags):
            cx = (tag.x + tag.width / 2) / self.width + GIFT_TAG_TO_CENTER
            tx0, ty0, tx1, ty1 = GIFT_REWARD_TIER
            kx0, ky0, kx1, ky1 = GIFT_REWARD_KEYWORD
            tier = vision.tier_in_roi(self.frame, (cx + tx0, ty0, cx + tx1, ty1))
            kw, score = vision.keyword_in_roi(self.frame, (cx + kx0, ky0, cx + kx1, ky1), templates)
            name = self.name_near(names, cx)
            kw = kw if score >= KEYWORD_MATCH_THRESHOLD else None
            if name:
                tier, kw = gifts.info(name)
            cards.append((cx, tier, kw, name))
        return cards

    def plain_gift_screen(self):
        return (self.ocr_roi('gift_reward_btns', TEXT['reject'])
                and not self.ocr_roi('gift_reward_marker', TEXT['gift_reward_marker']))

    def choose_plain_gifts(self):
        """等級高的優先，同等級時看 Reward Keywords。只有一張卡時通常已經選好，先直接按「选择」。"""
        self.sleep(1)
        cards = self.plain_gift_cards()
        keywords = list(self.config.get('Reward Keywords', []))
        rank = {k: i for i, k in enumerate(keywords)}
        wanted = self.config.get('Wanted Gifts', [])

        def key(c):
            w = gifts.wanted_rank(c[3], wanted)
            return (0, w) if w is not None else (1, 0), -(c[1] or 0), rank.get(c[2], len(rank))
        cards.sort(key=key)
        n = self.picks_left('gift_reward_btns')
        self.log_info('饰品獎勵：' + '、'.join(
            f'{nm or "?"}/{gifts.TIER_NAMES.get(t, "?")}/{k or "?"}' for _, t, k, nm in cards) + f'，選 {n} 個')
        for attempt in range(3):
            if attempt > 0 or len(cards) > 1:
                for cx, _, _, _ in cards[:n]:
                    self.click_relative(cx, GIFT_REWARD_CLICK_Y, after_sleep=0.8)
            button = [b for b in self.ocr_roi('gift_reward_btns', TEXT['select'])
                      if not vision.keywords_regex(TEXT['reject']).search(b.name)]
            if button:
                self.click_box(button[-1], after_sleep=2)
            else:
                self.click_relative(*GIFT_REWARD_SELECT, after_sleep=2)
            self.next_frame()
            if not self.plain_gift_screen():
                self.info_incr('戰後饰品')
                return
        self.screenshot('fail_plain_gift')
        self.log_warning('選了饰品還停在選擇畫面')
