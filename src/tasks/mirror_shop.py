"""鏡像迷宮商店：買饰品 → 強化 → 合成 → 离开。給 MirrorDungeonTask 繼承用。"""

import re
import time

import cv2

from src.lc import shop, vision
from src.lc.layout import (ENHANCE_BTN, ENHANCE_CONFIRM, ENHANCE_GRID, ENHANCE_PLUS, ENHANCE_PLUSPLUS,
                           FUSE_BTN, FUSE_CENTER, FUSE_GRID, GIFT_KEYWORDS, GIFT_LIT_VALUE,
                           KEYWORD_MATCH_THRESHOLD, KEYWORD_TEMPLATES, KW_CELL_X, KW_CELL_Y, KW_CONFIRM,
                           OWNED_COLS, OWNED_ROWS, SHOP_BUY_BTN, SHOP_CLOSE_BTN, SHOP_ENHANCE_BTN,
                           SHOP_FUSE_BTN, SHOP_ITEM_X, SHOP_ITEM_Y, SHOP_LEAVE_BTN, SHOP_PRICE_DY,
                           SHOP_REFRESH_BTN, TEXT)
from src.tasks.LimbusBaseTask import TaskFailed

TIER_NAMES = ['I', 'II', 'III', 'IV']
ENHANCE_LEVELS = ['+', '++']
FUSE_TIER_OPTIONS = ['1', '2', '3', '4']

SHOP_DEFAULTS = {
    'Shop Enable': True,
    'Shop Min Money': 100,
    'Shop Keywords': [],
    'Shop Tiers': [],
    'Shop Refreshes': 1,
    'Shop Enhance': True,
    'Enhance Level': '+',
    'Shop Fuse': False,
    'Fuse Keyword': GIFT_KEYWORDS[0],
    'Fuse Tiers': ['3', '4'],
    'Fuse Material Tiers': ['1', '2'],
    'Fuse Skip Enhanced': True,
}
SHOP_TYPES = {
    'Shop Keywords': {'type': 'drop_down', 'options_available': GIFT_KEYWORDS},   # 清單，可排順序
    'Shop Tiers': {'type': 'multi_selection', 'options': TIER_NAMES},
    'Enhance Level': {'type': 'drop_down', 'options': ENHANCE_LEVELS},
    'Fuse Keyword': {'type': 'drop_down', 'options': GIFT_KEYWORDS},
    'Fuse Tiers': {'type': 'multi_selection', 'options': FUSE_TIER_OPTIONS},
    'Fuse Material Tiers': {'type': 'multi_selection', 'options': FUSE_TIER_OPTIONS},
}
SHOP_DESCRIPTIONS = {
    'Shop Enable': '走到商店時要不要買 / 強化 / 合成 (關掉就直接离开)',
    'Shop Min Money': '最低保留經費：買、強化、刷新前經費低於這個數字就不做，直接离开',
    'Shop Keywords': '要買哪些關鍵詞的饰品 (看饰品右下角的圖示)，越上面越優先；空的 = 不限',
    'Shop Tiers': '要買哪些等級的饰品 (左上角的羅馬數字)，不勾 = 不限',
    'Shop Refreshes': '沒有想買的饰品時，最多按幾次右上「刷新」',
    'Shop Enhance': '買完後用「强化饰品」強化亮起的饰品 (符合 Shop Keywords 的先強化)',
    'Enhance Level': '強化選 + 還是 ++',
    'Shop Fuse': '用「合成饰品」把低等級饰品合成高等級 (會消耗材料饰品)',
    'Fuse Keyword': '合成出來的饰品關鍵詞',
    'Fuse Material Tiers': '哪些等級的饰品可以拿去當合成材料 (預設 1、2 級)',
    'Fuse Skip Enhanced': '不拿強化過 (右上角有 +) 的饰品當材料',
    'Fuse Tiers': '想合成的等級 (做得到最高的優先)，例如勾 3、4。點數：I=3 II=6 III=10 IV=15；'
                  '合計 ≤10→1級、11~16→2級、17~24→3級、≥25→4級 (最多 3 個材料)',
}


class MirrorShopMixin:

    # ---------- 共用 ----------

    def on_shop_screen(self):
        return self.ocr_roi('shop_title', TEXT['shop_title']) and self.ocr_roi('shop_leave', TEXT['leave'])

    def keyword_templates(self):
        result = {}
        for name, file in KEYWORD_TEMPLATES.items():
            image = self.load_template(file)
            if image is not None:
                result[name] = image
        return result

    def read_number(self, roi):
        """經費、價格：取最長的一串數字 (前面的硬幣圖示常被讀成奇怪的字)。"""
        text = ''.join(b.name for b in self.ocr_roi(roi))
        return longest_number(text)

    def money_ok(self, money, what):
        minimum = self.config.get('Shop Min Money', 100)
        if money is None:
            self.log_warning(f'讀不到經費，不{what}')
            return False
        if money < minimum:
            self.log_info(f'經費 {money} 低於設定的 {minimum}，不{what}')
            return False
        return True

    def gift_center(self, grid, index):
        x0, dx, y0, dy = grid
        return int((x0 + dx * (index % OWNED_COLS)) * self.width), int((y0 + dy * (index // OWNED_COLS)) * self.height)

    def lit_gifts(self, grid):
        """強化 / 合成畫面右邊亮起的饰品：[(索引, 等級, 關鍵詞, 強化過嗎)]。"""
        self.next_frame()
        templates = self.keyword_templates()
        half = int(0.045 * self.height)
        result = []
        for index in range(OWNED_COLS * OWNED_ROWS):
            cx, cy = self.gift_center(grid, index)
            if cy + half >= self.height:
                break
            region = self.frame[cy - half:cy + half, cx - half:cx + half]
            if region.size == 0:
                continue
            value = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)[:, :, 2].mean()
            if value < GIFT_LIT_VALUE:
                continue
            tier = vision.gift_tier(self.frame, (cx, cy))
            kw, score = vision.gift_keyword(self.frame, (cx, cy), templates)
            result.append((index, tier, kw if score >= KEYWORD_MATCH_THRESHOLD else None,
                           vision.gift_enhanced(self.frame, (cx, cy))))
        return result

    def close_sub_screen(self):
        self.click_relative(*SHOP_CLOSE_BTN, after_sleep=1.5)
        self.wait_for(self.on_shop_screen, time_out=8, what='關掉強化 / 合成後回到商店')

    # ---------- 主流程 ----------

    def handle_shop(self):
        self.log_info('進入商店')
        if self.config.get('Shop Enable', True):
            self.shop_buy()
            if self.config.get('Shop Enhance', True):
                self.shop_enhance()
            if self.config.get('Shop Fuse', False):
                self.shop_fuse()
        self.leave_shop()

    def leave_shop(self):
        for _ in range(5):
            self.next_frame()
            if self.handle_gift_popup():
                continue
            ok = self.ocr_roi('md_popup_btn', TEXT['confirm'])   # 「要离开商店吗?」→ 确认 (要先檢查，商店畫面還在後面)
            if ok:
                self.click_box(ok, after_sleep=2.5)
                continue
            if self.on_shop_screen():
                self.click_relative(*SHOP_LEAVE_BTN, after_sleep=2)
                continue
            self.log_info('離開商店')
            return
        self.screenshot('fail_shop_leave')
        raise TaskFailed('按了「离开」還在商店')

    # ---------- 買 ----------

    def shop_items(self):
        """讀 8 格饰品：等級、關鍵詞、價格、名稱。"""
        self.next_frame()
        templates = self.keyword_templates()
        boxes = self.ocr_roi('shop_items')
        items = []
        for row, y in enumerate(SHOP_ITEM_Y):
            for col, x in enumerate(SHOP_ITEM_X):
                index = row * len(SHOP_ITEM_X) + col
                center = (int(x * self.width), int(y * self.height))
                tier = vision.gift_tier(self.frame, center)
                kw, score = vision.gift_keyword(self.frame, center, templates)
                price, name = None, ''
                for b in boxes:
                    bx = (b.x + b.width / 2) / self.width
                    by = (b.y + b.height / 2) / self.height
                    if abs(bx - x) > 0.055:
                        continue
                    if y + SHOP_PRICE_DY[0] <= by <= y + SHOP_PRICE_DY[1]:
                        price = longest_number(b.name)
                    elif y + SHOP_PRICE_DY[1] < by <= y + 0.14:
                        name = b.name.strip()
                items.append(shop.ShopItem(index, tier, kw if score >= KEYWORD_MATCH_THRESHOLD else None,
                                           price, name))
        return items

    def shop_buy(self):
        keywords = list(self.config.get('Shop Keywords', []))
        tiers = [TIER_NAMES.index(t) + 1 for t in self.config.get('Shop Tiers', []) if t in TIER_NAMES]
        refreshes = int(self.config.get('Shop Refreshes', 1))
        tried = set()
        for _ in range(20):
            money = self.read_number('shop_money')
            if not self.money_ok(money, '買'):
                return
            items = self.shop_items()
            self.info_set('商店', '、'.join(f'{it.name or "?"}({TIER_NAMES[it.tier - 1] if it.tier else "?"}/'
                                           f'{it.keyword or "?"}/{it.price})' for it in items if it.tier or it.price))
            wanted = [it for it in shop.wanted_items(items, keywords, tiers, money)
                      if (it.name, it.price) not in tried]
            if wanted:
                item = wanted[0]
                tried.add((item.name, item.price))
                self.buy_item(item)
                continue
            if refreshes <= 0:
                return
            cost = self.read_number('shop_refresh_cost') or 0
            if not self.money_ok(money - cost, '刷新'):
                return
            self.log_info(f'沒有想買的饰品，刷新 (花 {cost})')
            refreshes -= 1
            self.click_relative(*SHOP_REFRESH_BTN, after_sleep=2.5)

    def buy_item(self, item):
        x = SHOP_ITEM_X[item.index % len(SHOP_ITEM_X)]
        y = SHOP_ITEM_Y[item.index // len(SHOP_ITEM_X)]
        self.log_info(f'購買饰品：{item.name} ({TIER_NAMES[item.tier - 1]} {item.keyword or ""}，{item.price})')
        self.click_relative(x, y, after_sleep=1.5)
        if not self.wait_until(lambda: self.ocr_roi('shop_buy_title', TEXT['buy']), time_out=5):
            self.log_warning('點了饰品沒有出現購買視窗')
            return
        button = self.ocr_roi('shop_buy_btn', TEXT['buy'])
        if button:
            self.click_box(button, after_sleep=2)
        else:
            self.click_relative(*SHOP_BUY_BTN, after_sleep=2)
        self.wait_until(self.handle_gift_popup, time_out=6)
        self.wait_for(self.on_shop_screen, time_out=8, what='買完回到商店')
        self.info_incr('購買饰品')

    # ---------- 強化 ----------

    def shop_enhance(self):
        keywords = list(self.config.get('Shop Keywords', []))
        self.click_relative(*SHOP_ENHANCE_BTN, after_sleep=2)
        if not self.wait_until(lambda: self.ocr_roi('shop_sub_title', TEXT['enhance_title']), time_out=6):
            self.log_warning('沒有打開強化畫面')
            return
        tried = set()
        for _ in range(OWNED_COLS * OWNED_ROWS):
            money = self.read_number('enhance_money')
            if not self.money_ok(money, '強化'):
                break
            # 符合關鍵詞的先強化 (照清單順序)，其他的之後
            rank = {k: i for i, k in enumerate(keywords)}
            gifts = sorted((g for g in self.lit_gifts(ENHANCE_GRID) if g[0] not in tried),
                           key=lambda g: rank.get(g[2], len(rank)))
            if not gifts:
                break
            index, tier, kw, _ = gifts[0]
            tried.add(index)
            self.enhance_gift(index, kw)
        self.close_sub_screen()

    def enhance_gift(self, index, kw):
        cx, cy = self.gift_center(ENHANCE_GRID, index)
        self.click(cx, cy, after_sleep=1)
        self.click_relative(*ENHANCE_BTN, after_sleep=2)
        if not self.wait_until(lambda: self.ocr_roi('enhance_cost', TEXT['enhance_cost']), time_out=5):
            self.log_warning(f'第 {index + 1} 個饰品沒辦法強化')
            return
        level = self.config.get('Enhance Level', '+')
        self.click_relative(*(ENHANCE_PLUSPLUS if level == '++' else ENHANCE_PLUS), after_sleep=1)
        self.log_info(f'強化第 {index + 1} 個饰品 ({kw or "?"}) → {level}')
        self.click_relative(*ENHANCE_CONFIRM, after_sleep=2.5)
        for _ in range(4):   # 回到強化清單 (途中的確認視窗都按掉)
            self.next_frame()
            if self.ocr_roi('shop_sub_title', TEXT['enhance_title']) and not self.ocr_roi(
                    'enhance_cost', TEXT['enhance_cost']):
                break
            ok = self.ocr_roi('center', TEXT['confirm'])
            if ok:
                self.click_box(ok, after_sleep=1.5)
            else:
                self.sleep(1)
        self.info_incr('強化饰品')

    # ---------- 合成 ----------

    def shop_fuse(self):
        keyword = self.config.get('Fuse Keyword', GIFT_KEYWORDS[0])
        targets = {int(t) for t in self.config.get('Fuse Tiers', ['4'])}
        self.click_relative(*SHOP_FUSE_BTN, after_sleep=2)
        if not self.wait_until(lambda: self.ocr_roi('shop_sub_title', TEXT['fuse_title']), time_out=6):
            self.log_warning('沒有打開合成畫面')
            return
        for _ in range(3):
            if not self.choose_fuse_keyword(keyword):
                break
            materials = {int(t) for t in self.config.get('Fuse Material Tiers', ['1', '2'])}
            skip_enhanced = self.config.get('Fuse Skip Enhanced', True)
            gifts = [g for g in self.lit_gifts(FUSE_GRID)
                     if g[1] in materials and not (skip_enhanced and g[3])]
            combo = shop.best_fuse_combo([g[1] for g in gifts], targets)
            if combo is None:
                self.log_info('材料不夠合成想要的等級')
                break
            picked = [gifts[i] for i in combo]
            total = sum(shop.FUSE_POINTS[g[1]] for g in picked)
            self.log_info(f'合成{keyword}：材料 ' + '、'.join(TIER_NAMES[g[1] - 1] for g in picked)
                          + f' (共 {total} 點 → {shop.fuse_result_tier(total)} 級)')
            for index, _, _, _ in picked:
                self.click(*self.gift_center(FUSE_GRID, index), after_sleep=1)
            self.click_relative(*FUSE_BTN, after_sleep=2.5)
            for _ in range(6):   # 確認 / 獲得饰品
                self.next_frame()
                if self.handle_gift_popup():
                    break
                ok = self.ocr_roi('center', TEXT['confirm'])
                if ok:
                    self.click_box(ok, after_sleep=2)
                else:
                    self.sleep(1)
            self.info_incr('合成饰品')
        self.close_sub_screen()

    def choose_fuse_keyword(self, keyword) -> bool:
        self.click_relative(*FUSE_CENTER, after_sleep=1.5)
        if not self.wait_until(lambda: self.ocr_roi('shop_sub_title', TEXT['kw_select']), time_out=5):
            self.log_warning('沒有出現「合成 - 关键词选择」')
            return False
        i = GIFT_KEYWORDS.index(keyword)
        self.click_relative(KW_CELL_X[i % 5], KW_CELL_Y[i // 5], after_sleep=0.8)
        self.click_relative(*KW_CONFIRM, after_sleep=2)
        return bool(self.wait_until(lambda: self.ocr_roi('shop_sub_title', TEXT['fuse_title']), time_out=5))


def longest_number(text):
    found = re.findall(r'\d+', (text or '').translate(str.maketrans({'O': '0', 'o': '0'})))
    return int(max(found, key=len)) if found else None
