import time
from pathlib import Path

import cv2
from ok import Box

from src.lc import packs as pack_data
from src.lc import vision
from src.lc.layout import (PACK_DRAG_FROM_Y, PACK_DRAG_TO_Y, PACK_MODE_ARROW, PACK_OBS_ICON_DX,
                           PACK_OBS_ICON_Y, PACK_OBSERVE_BTN, PACK_REFRESH_BTN,
                           OBSERVE_COL_X0, OBSERVE_COL_DX, OBSERVE_ROW_DY, OBSERVE_ROW_DY0,
                           OBSERVE_TAB_X, OBSERVE_TAB_Y, OBSERVE_TYPES, OBSERVE_VISIBLE_BOTTOM,
                           GIFT_CARD_X, GIFT_CARD_Y, GIFT_KEYWORDS, GIFT_SCROLL_ARROW,
                           GRACE_COL_X, GRACE_NAMES, GRACE_PLUS_DX, GRACE_PLUS_Y,
                           GRACE_PLUSPLUS_DX, GRACE_ROW_Y, TEXT,
                           EVENT_OPTION_GAP, EVENT_SKIP_BTN, NODE_ENTER_BTN,
                           MAP_CENTER, MAP_ZOOM_SCROLLS, NODE_MATCH_THRESHOLD, NODE_TYPES, NODE_UNKNOWN)
from src.tasks.LimbusBaseTask import TEMPLATE_DIR, LimbusBaseTask, TaskFailed
from src.tasks.mirror_shop import SHOP_DEFAULTS, SHOP_DESCRIPTIONS, SHOP_TYPES, MirrorShopMixin

IN_PROGRESS_CONTINUE = '繼續探索'
IN_PROGRESS_ABORT = '終止探索 (放棄獎勵)'

GRACE_LEVELS = ['0', '1', '2']   # 1 = 卡片下的「+」，2 = 「++」
GRACE_DEFAULT = ['1 0', '3 0', '5 0']   # 預設選 1、3、5，0 級
GIFT_PICK_OPTIONS = ['1', '2', '3']
OBSERVE_OFF = '不選'
OBSERVE_TIERS = ['III', 'II', 'I']
OBSERVE_SLOTS = 3
MODE_KEEP, MODE_HARD, MODE_NORMAL = '不切換', '困难', '普通'
NODE_DEFAULT = ['事件', '戰鬥', '異想體']
UNKNOWN_NODE_DIR = Path('screenshots') / 'map_nodes'
EVENT_LOG_DIR = Path('screenshots') / 'event_options'
EVENT_DEFAULT = [vision.EVENT_GIFT, vision.EVENT_CHECK, vision.EVENT_OTHER, vision.EVENT_BATTLE]


def pack_key(floor: int) -> str:
    return f'Pack Priority {floor}F'


def observe_keys(slot: int):
    return f'Observe {slot} Type', f'Observe {slot} Tier', f'Observe {slot} Index'


def parse_grace_line(text: str):
    """「1 1」「起始之星 2」「3」-> (index 0~9, '0' / '1' / '2')；+ / ++ 也接受。看不懂回傳 None。"""
    parts = str(text).replace('：', ' ').replace(':', ' ').split()
    if not parts:
        return None
    head, level = parts[0], (parts[1] if len(parts) > 1 else '0')
    level = {'0級': '0', '0 級': '0', '無': '0', '+': '1', '++': '2'}.get(level, level)
    if level not in GRACE_LEVELS:
        return None
    if head.isdigit() and 1 <= int(head) <= len(GRACE_NAMES):
        return int(head) - 1, level
    if head in GRACE_NAMES:
        return GRACE_NAMES.index(head), level
    return None


class MirrorDungeonTask(MirrorShopMixin, LimbusBaseTask):
    """鏡像迷宮 (目前做到「進入迷宮」為止，迷宮裡的流程之後再加)。

    主畫面 → Drive → 镜像迷宫 → 进入
    - 探索前：「是否进入…?」进入 → 編隊畫面 → 依星芒奖励選隊 → 确认 → 等級警告确认
    - 探索中：「迷宫进度」選继续，或 终止探索 → 确认 → 探索结束奖励「放弃奖励」→ 再重新進入
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '鏡像迷宮'
        self.description = '進入鏡像迷宮：編隊 → 恩惠 → 饰品 → 卡包 → 走第一個節點 (之後尚未完成)'
        self.default_config.update({
            'Min Star Reward': 0,
            'If In Progress': IN_PROGRESS_CONTINUE,
            'Gift Keyword': '呼吸法',
            'Gift Picks': ['1'],
            'Graces': list(GRACE_DEFAULT),
            'Pack Difficulty': MODE_KEEP,
            'Pack Avoid': [],
            'Pack Use Refresh': True,
            'Pack Use Observe': False,
            'Node Priority': list(NODE_DEFAULT),
            'Event Priority': list(EVENT_DEFAULT),
            'Battle Timeout (s)': 400,
        })
        self.config_type['Pack Difficulty'] = {'type': 'drop_down',
                                               'options': [MODE_KEEP, MODE_HARD, MODE_NORMAL]}
        # 每一層一個「想要的卡包」清單，只能從那一層會出現的卡包裡選 (資料：assets/lc/mirror_packs.csv)
        for floor in pack_data.FLOORS:
            key = pack_key(floor)
            self.default_config[key] = []
            self.config_type[key] = {'type': 'drop_down',
                                     'options_available': pack_data.packs_on_floor(floor)}
            self.config_description[key] = (f'第 {floor} 層想要的主題卡包，越上面越優先 '
                                            f'(只列出第 {floor} 層普通或困難會出現的卡包)')
        self.config_type['Pack Avoid'] = {'type': 'drop_down',
                                          'options_available': pack_data.all_packs()}
        self.config_description.update({
            'Pack Difficulty': '卡包畫面右上的難度 (還沒通關困難卡包前可以切換)',
            'Pack Avoid': '不要的卡包，都沒有想要的卡包時會避開這些，也會優先把它們換掉',
            'Pack Use Refresh': '畫面上沒有想要的卡包時，用右上「刷新」(用完為止)',
            'Pack Use Observe': '刷新用完還是沒有時，用「主题卡包观测」把一個卡包換成想要的 (可能花星芒)',
            'Node Priority': '樓層地圖上有好幾條路時，優先走哪種節點，一行一個，越上面越優先。'
                             '可用：' + '、'.join(list(NODE_TYPES) + [NODE_UNKNOWN])
                             + '。沒列到的排最後，一樣優先時走上面那條',
            'Event Priority': '事件選項的優先順序，一行一個，看選項下面的小字分類：'
                              + '、'.join(vision.EVENT_KINDS)
                              + '。「其他」= 沒有小字或沒見過的 (會存到 screenshots/event_options 給你看)',
            'Battle Timeout (s)': '迷宮裡單場戰鬥最多等幾秒',
        })
        for slot in range(1, OBSERVE_SLOTS + 1):
            type_key, tier_key, index_key = observe_keys(slot)
            self.default_config.update({type_key: OBSERVE_OFF, tier_key: 'III', index_key: 1})
            self.config_type[type_key] = {
                'type': 'drop_down', 'options': [OBSERVE_OFF] + OBSERVE_TYPES,
                # 選了類型才顯示等級和第幾個
                'sub_configs': {kind: [tier_key, index_key] for kind in OBSERVE_TYPES},
            }
            self.config_type[tier_key] = {'type': 'drop_down', 'options': OBSERVE_TIERS}
            self.config_description.update({
                type_key: f'E.G.O饰品观测 第 {slot} 個要選的饰品類型。三個都「不選」= 拒绝饰品 (不花星芒)',
                tier_key: '饰品等級 (III 在最上面)',
                index_key: '該等級的第幾個，由左到右、上到下數 (每列 8 個，第 9 個是第二列第 1 個)',
            })
        self.config_type.update({
            'If In Progress': {'type': 'drop_down',
                               'options': [IN_PROGRESS_CONTINUE, IN_PROGRESS_ABORT]},
            'Gift Keyword': {'type': 'drop_down', 'options': GIFT_KEYWORDS},
            'Gift Picks': {'type': 'multi_selection', 'options': GIFT_PICK_OPTIONS},
        })
        self.config_description.update({
            'Min Star Reward': '編隊畫面「星芒奖励」低於這個數字，就依序換名稱有「镜像迷宫」的編隊，'
                               '直到夠高為止 (都不夠就用最高的那隊)。0 = 不換，用目前的編隊',
            'If In Progress': '上次的迷宮還沒結束時：繼續，或終止並放棄獎勵後重新開一場',
            'Gift Keyword': '開局選 E.G.O 饰品時，左邊要選哪一種關鍵字',
            'Gift Picks': '右邊三個饰品要選哪幾個 (由上到下 1~3)。'
                          '實際能選幾個看畫面「选择 0/N」，超過的會依序略過',
            'Graces': '要選的星之恩惠，一行一個，格式「編號 等級」，等級是 0 / 1 / 2 (1 = +，2 = ++)，'
                      '例如「1 0」「2 2」，編號也可以寫名稱「起始之星 1」。編號 (由左到右、上到下)：'
                      + '、'.join(f'{i + 1}.{n}' for i, n in enumerate(GRACE_NAMES)),
        })
        # 設定畫面照流程順序顯示：恩惠 → 饰品观测 → 卡包 (各層想要的 → 避開 → 刷新/觀測)
        pack_keys = (['Pack Difficulty'] + [pack_key(f) for f in pack_data.FLOORS]
                     + ['Pack Avoid', 'Pack Use Refresh', 'Pack Use Observe', 'Node Priority',
                        'Event Priority', 'Battle Timeout (s)'])
        for key in pack_keys:
            self.default_config[key] = self.default_config.pop(key)
        # 商店設定放最後
        self.default_config.update(SHOP_DEFAULTS)
        self.config_type.update(SHOP_TYPES)
        self.config_description.update(SHOP_DESCRIPTIONS)

    def run(self):
        self.open_mirror_dungeon()
        if self.enter_dungeon() == 'continued':
            self.log_info('繼續上次的鏡像迷宮')
            self.explore()
            return
        self.choose_team()
        self.confirm_team()
        self.choose_graces()
        self.choose_start_gifts()
        self.observe_gifts()
        self.choose_pack()
        self.explore()

    def explore(self, max_nodes: int = 80):
        """地圖 → 選節點 → 进入 → 事件 / 戰鬥 → 回到地圖 (每次都重新縮小、重新判斷)。
        到了下一層會先選主題卡包。"""
        for _ in range(max_nodes):
            screen = self.wait_screen(time_out=40)
            if screen == 'pack':
                self.choose_pack()
                continue
            if screen != 'map':
                self.screenshot('fail_unknown_screen')
                raise TaskFailed('不知道現在是什麼畫面 (不是地圖也不是卡包選擇)，請把截圖給我')
            kind = self.choose_node()
            self.enter_node()
            after = self.wait_screen(time_out=20, include_battle=True)
            if after == 'event':
                self.handle_event()
            elif after == 'team':
                if self.fight_node() == 'defeat':
                    self.log_info('戰鬥失敗，停止', notify=True)
                    return
            elif after == 'shop':
                self.handle_shop()
            elif after in ('map', 'pack'):
                continue
            else:
                self.screenshot('fail_after_node')
                raise TaskFailed(f'進入節點 ({kind}) 之後的畫面還沒做，請把截圖給我')
        self.log_info(f'已走過 {max_nodes} 個節點，先停下來', notify=True)

    def wait_screen(self, time_out: float, include_battle: bool = False):
        """等到認得的畫面：'map' 地圖、'pack' 主題卡包、'event' 事件、'team' 戰鬥編隊。途中的獲得饰品都按确认。"""
        start = time.time()
        while time.time() - start < time_out:
            self.next_frame()
            if self.handle_gift_popup():
                continue
            if self.on_map_screen():
                return 'map'
            if self.ocr_roi('pack_title', TEXT['pack_title']):
                return 'pack'
            if self.on_event_screen():
                return 'event'
            if include_battle and self.on_battle_team_screen():
                return 'team'
            if self.on_shop_screen():
                return 'shop'
            confirm = self.ocr_roi('lower_half', TEXT['confirm'])
            if confirm:
                self.click_box(confirm, after_sleep=2)
                continue
            self.sleep(1)
        return None

    # ---------- 進入 ----------

    def on_md_screen(self):
        return self.ocr_roi('md_status')

    def open_mirror_dungeon(self):
        if self.on_md_screen():
            return
        self.go_home()
        self.click_pos('home_drive', after_sleep=1.5)
        entry = self.wait_for(lambda: self.ocr_roi('drive_md', TEXT['mirror_dungeon']),
                              time_out=8, what='Drive 選單的镜像迷宫')
        self.click_box(entry, after_sleep=2)
        self.wait_for(self.on_md_screen, time_out=10, what='鏡像迷宮畫面')

    def dialog(self, key):
        return self.ocr_roi('md_dialog', TEXT[key])

    def click_md_enter(self):
        button = self.wait_for(lambda: self.ocr_roi('md_enter', TEXT['enter']),
                               time_out=5, what='鏡像迷宮的「进入」')
        self.click_box(button, after_sleep=1.5)

    def enter_dungeon(self, attempt: int = 0) -> str:
        """回傳 'new' (開新的一場，接著要選編隊) 或 'continued' (繼續上次的)。"""
        if attempt > 1:
            raise TaskFailed('終止探索後還是沒有回到「探索前」')
        status = ''.join(b.name for b in self.ocr_roi('md_status'))
        self.info_set('探索状态', status)

        if vision.keywords_regex(TEXT['md_not_started']).search(status):
            # 剛放棄獎勵回來時畫面還在動畫，第一次按「进入」常被忽略，所以等不到視窗就再按
            for _ in range(3):
                self.click_md_enter()
                ok = self.wait_until(lambda: self.ocr_roi('md_popup_btn', TEXT['enter']), time_out=4)
                if ok:
                    break
            else:
                self.screenshot('fail_md_enter_popup')
                raise TaskFailed('按了 3 次「进入」都等不到「是否进入」視窗')
            self.click_box(ok, after_sleep=2.5)  # 「是否进入西西弗之镜?」
            self.wait_for(self.on_team_screen, time_out=15, what='鏡像迷宮編隊畫面')
            return 'new'

        self.click_md_enter()

        # 探索中 →「迷宫进度」；探索完成 →「探索结束奖励」
        self.wait_for(lambda: self.dialog('md_continue') or self.dialog('md_give_up'),
                      time_out=8, what='迷宮進度 / 探索結束獎勵視窗')
        if self.dialog('md_give_up'):
            self.give_up_rewards()
            return self.enter_dungeon(attempt + 1)

        if self.config.get('If In Progress') == IN_PROGRESS_CONTINUE:
            self.click_box(self.dialog('md_continue'), after_sleep=3)
            return 'continued'

        self.log_info('終止上次的迷宮探索')
        self.click_box(self.dialog('md_abort'), after_sleep=1.5)
        ok = self.wait_for(lambda: self.dialog('confirm'), time_out=8, what='「要终止…吗?」視窗')
        self.click_box(ok, after_sleep=2)
        self.wait_for(lambda: self.dialog('md_give_up'), time_out=10, what='探索结束奖励')
        self.give_up_rewards()
        return self.enter_dungeon(attempt + 1)

    def give_up_rewards(self):
        self.log_info('探索結束獎勵：放棄獎勵')
        self.click_box(self.dialog('md_give_up'), after_sleep=1.5)
        # 可能再問一次「確定放棄?」
        start = time.time()
        while time.time() - start < 6:
            self.next_frame()
            ok = self.dialog('confirm')
            if ok:
                self.click_box(ok, after_sleep=1.5)
                continue
            if not self.dialog('md_give_up'):
                break
            self.sleep(0.5)
        self.wait_for(lambda: vision.keywords_regex(TEXT['md_not_started']).search(
            ''.join(b.name for b in self.ocr_roi('md_status'))), time_out=10, what='探索前')
        self.sleep(2)  # 等關閉視窗的動畫結束，不然下一次按「进入」會被忽略

    # ---------- 編隊 ----------

    def on_team_screen(self):
        return self.ocr_roi('md_confirm', TEXT['confirm'])

    def read_star(self):
        return vision.parse_stylized_int(''.join(b.name for b in self.ocr_roi('md_star')))

    def current_team(self):
        return ''.join(b.name for b in self.ocr_roi('md_team_title'))

    def choose_team(self):
        self.sleep(1.5)  # 編隊畫面剛出來時還在動畫，數字會讀錯
        self.next_frame()
        minimum = self.config.get('Min Star Reward', 0)
        star = self.read_star()
        self.info_set('編隊', self.current_team())
        self.info_set('星芒奖励', star)
        if not minimum or (star is not None and star >= minimum):
            return

        teams = sorted(self.ocr_roi('md_teams', TEXT['mirror_dungeon']), key=lambda b: b.y)
        if not teams:
            self.log_warning('找不到名稱有「镜像迷宫」的編隊，用目前的編隊')
            return
        # 「最高的那隊」先記成目前選的這隊，換了一圈都沒有更好的就換回來
        title = self.current_team().replace(' ', '')
        original = next((t for t in teams if t.name.replace(' ', '') == title), None)
        best = (star if star is not None else -1, original)
        for team in teams:
            self.click_box(team, after_sleep=1.5)
            self.next_frame()
            star = self.read_star()
            self.log_info(f'{team.name}：星芒奖励 {star}')
            if star is not None and star >= minimum:
                self.info_set('編隊', team.name)
                self.info_set('星芒奖励', star)
                return
            if star is not None and star > best[0]:
                best = (star, team)
        if best[1] is not None:
            self.click_box(best[1], after_sleep=1.5)
            self.info_set('編隊', best[1].name)
        self.info_set('星芒奖励', best[0])
        self.log_warning(f'沒有編隊的星芒奖励達到 {minimum}，改用最高的 ({best[0]})')

    def confirm_team(self):
        """按确认，處理等級警告，直到編隊畫面真的離開 (太快按的話遊戲會忽略)。"""
        self.sleep(1)
        clicks = 0
        last_click = 0.0
        start = time.time()
        while time.time() - start < 25:
            self.next_frame()
            warning = self.ocr_roi('md_popup_btn', TEXT['confirm'])
            if warning:  # 「编队人格当前平均等级低于推荐等级。是否进行战斗?」
                self.log_info('編隊等級低於推薦等級，照樣進入')
                self.click_box(warning, after_sleep=2.5)
                continue
            button = self.on_team_screen()
            if not button:
                if clicks:
                    self.info_set('進入迷宮', '成功')
                    return
            elif time.time() - last_click > 4:  # 按了 4 秒還在編隊畫面就再按一次
                if clicks >= 3:
                    break
                self.click_box(button, after_sleep=2)
                clicks += 1
                last_click = time.time()
                continue
            self.sleep(0.5)
        self.screenshot('fail_md_confirm')
        raise TaskFailed('按了确认還是停在編隊畫面')

    # ---------- 星之恩惠 ----------

    def on_grace_screen(self):
        return self.ocr_roi('grace_title', TEXT['grace_title'])

    def grace_popup(self):
        return self.ocr_roi('grace_popup', TEXT['grace_popup'])

    def choose_graces(self):
        self.wait_for(self.on_grace_screen, time_out=20, what='星之恩惠畫面')
        self.sleep(1.5)
        chosen = []
        for line in self.config.get('Graces', []):
            parsed = parse_grace_line(line)
            if parsed is None:
                self.log_warning(f'看不懂恩惠設定「{line}」，格式要像「1 0」或「2 2」')
                continue
            i, level = parsed
            name = GRACE_NAMES[i]
            col, row = i % 5, i // 5
            x = GRACE_COL_X[col]
            if level == '1':
                x, y = x + GRACE_PLUS_DX, GRACE_PLUS_Y[row]
            elif level == '2':
                x, y = x + GRACE_PLUSPLUS_DX, GRACE_PLUS_Y[row]
            else:
                y = GRACE_ROW_Y[row]
            # 點卡片 / +/ ++ 都是直接選好，不會跳視窗 (確認視窗是按「完成」後才出現)
            self.click_relative(x, y, after_sleep=0.8)
            chosen.append(f'{i + 1}.{name}({level})')
        self.info_set('星之恩惠', '、'.join(chosen) or '沒選')

        done = self.wait_for(lambda: self.ocr_roi('grace_done', TEXT['grace_done']),
                             time_out=5, what='恩惠畫面的「完成」')
        self.click_box(done, after_sleep=1.5)
        # 「完成」後跳出「要选择此效果吗?」→ 确认 (沒選任何恩惠時可能不會跳)
        start = time.time()
        while time.time() - start < 15:
            self.next_frame()
            if self.handle_gift_popup():
                continue
            if self.on_gift_screen():
                return
            if self.grace_popup():
                ok = self.ocr_roi('grace_popup_btn', TEXT['confirm'])
                if ok:
                    self.click_box(ok, after_sleep=2)
                else:
                    self.click_relative(0.585, 0.741, after_sleep=2)
                continue
            ok = self.ocr_roi('center', TEXT['confirm'])
            if ok:
                self.click_box(ok, after_sleep=2)
                continue
            self.sleep(0.5)
        self.screenshot('fail_grace_done')
        raise TaskFailed('按了「完成」之後沒有進到選擇E.G.O饰品')

    # ---------- 開局 E.G.O 饰品 ----------

    def on_gift_screen(self):
        return self.ocr_roi('gift_title', TEXT['gift_title']) and \
            self.ocr_roi('gift_select', TEXT['select'])

    def find_keyword(self, keyword):
        boxes = self.ocr_roi('gift_keywords')
        return next((b for b in boxes if b.name.strip() == keyword), None)

    def gift_limit(self) -> int:
        found = vision.parse_fraction(''.join(b.name for b in self.ocr_roi('gift_count')))
        return found[1] if found else 1

    def choose_start_gifts(self):
        self.wait_for(self.on_gift_screen, time_out=20, what='選擇E.G.O饰品畫面')
        self.sleep(1)
        keyword = self.config.get('Gift Keyword', '呼吸法')
        box = self.find_keyword(keyword)
        if box is None:  # 最後兩種要往下捲
            self.scroll_relative(0.34, 0.55, -5)
            self.sleep(1)
            self.next_frame()
            box = self.find_keyword(keyword)
            if box is None:
                self.click_relative(*GIFT_SCROLL_ARROW, after_sleep=1)
                box = self.find_keyword(keyword)
        if box is None:
            self.screenshot('fail_gift_keyword')
            raise TaskFailed(f'找不到饰品關鍵字「{keyword}」')
        # 點標題下方的饰品區塊
        self.click(box.x + box.width // 2, box.y + int(self.height * 0.12), after_sleep=1.5)

        limit = self.gift_limit()
        self.info_set('可選饰品數', limit)
        picks = sorted({int(p) for p in self.config.get('Gift Picks', ['1'])}) or [1]
        picks = picks[:limit]
        for n in picks:
            self.click_relative(GIFT_CARD_X, GIFT_CARD_Y[n - 1], after_sleep=0.8)
        self.next_frame()
        count = vision.parse_fraction(''.join(b.name for b in self.ocr_roi('gift_count')))
        if count and count[0] != len(picks):
            self.log_warning(f'想選 {len(picks)} 個，畫面上是 {count[0]}/{count[1]}')

        button = self.wait_for(lambda: self.ocr_roi('gift_select', TEXT['select']),
                               time_out=5, what='「选择」按鈕')
        self.click_box(button, after_sleep=2)
        self.collect_gift_popups()

    def handle_gift_popup(self) -> bool:
        """畫面上有「获得E.G.O饰品!」就記下名稱、按确认，回傳 True。任何時候出現都用這個處理。"""
        if not self.ocr_roi('gift_got_title', TEXT['gift_got']):
            return False
        name = ''.join(b.name for b in self.ocr_roi('gift_got_name')).strip() or '(讀不到名稱)'
        gifts = getattr(self, 'acquired_gifts', None)
        if gifts is None:
            gifts = self.acquired_gifts = []
        gifts.append(name)
        self.log_info(f'獲得 E.G.O 饰品：{name}')
        self.info_set('獲得饰品', '、'.join(gifts))
        ok = self.ocr_roi('gift_got_ok', TEXT['confirm'])
        if ok:
            self.click_box(ok, after_sleep=1.5)
        else:
            self.click_relative(0.5, 0.741, after_sleep=1.5)
        return True

    def collect_gift_popups(self, timeout: float = 15):
        """按了「选择」之後，把接連出現的「获得E.G.O饰品!」都按掉。"""
        start = time.time()
        seen_any = False
        while time.time() - start < timeout:
            self.next_frame()
            if self.handle_gift_popup():
                seen_any = True
                continue
            if seen_any:
                break
            self.sleep(0.5)
        if not seen_any:
            self.log_warning('按了「选择」後沒有看到「获得E.G.O饰品」')

    # ---------- E.G.O饰品观测 ----------

    def on_observe_screen(self):
        return self.ocr_roi('observe_title', TEXT['observe_title'])

    def observe_count(self):
        return vision.parse_fraction(''.join(b.name for b in self.ocr_roi('observe_count')))

    def tier_bands(self):
        return vision.find_tier_bands(self.frame)

    def open_observe_tab(self, kind):
        i = OBSERVE_TYPES.index(kind)
        self.click_relative(OBSERVE_TAB_X[i], OBSERVE_TAB_Y, after_sleep=1.2)
        self.next_frame()

    def gift_point(self, tier, index):
        """算出某等級第 index 個饰品的位置 (相對座標)；需要的話往下捲。回傳 None = 找不到。"""
        row, col = (index - 1) // 8, (index - 1) % 8
        x = OBSERVE_COL_X0 + col * OBSERVE_COL_DX
        bands = self.tier_bands()   # 由上到下：III、II、I
        order = 3 - tier            # 從上面數第幾條
        if order < len(bands):
            y = bands[order] + OBSERVE_ROW_DY0 + row * OBSERVE_ROW_DY
            if y <= OBSERVE_VISIBLE_BOTTOM:
                return x, y
        # 往下捲到底，從下面數：I 是最後一條
        self.scroll_relative(0.35, 0.6, -15)
        self.sleep(1)
        self.next_frame()
        bands = self.tier_bands()
        back = tier            # I = 倒數第 1 條、II = 倒數第 2 條 …
        if back <= len(bands):
            y = bands[-back] + OBSERVE_ROW_DY0 + row * OBSERVE_ROW_DY
            if y <= OBSERVE_VISIBLE_BOTTOM:
                return x, y
        return None

    def observe_gifts(self):
        self.wait_for(self.on_observe_screen, time_out=20, what='E.G.O饰品观测畫面')
        self.sleep(1)
        picks = []
        for slot in range(1, OBSERVE_SLOTS + 1):
            type_key, tier_key, index_key = observe_keys(slot)
            kind = self.config.get(type_key, OBSERVE_OFF)
            if kind == OBSERVE_OFF:
                continue
            tier = {'III': 3, 'II': 2, 'I': 1}.get(self.config.get(tier_key, 'III'), 3)
            picks.append((kind, tier, max(1, int(self.config.get(index_key, 1)))))
        if not picks:
            self.log_info('沒有設定要觀測的饰品，拒绝饰品')
            self.click_box(self.wait_for(lambda: self.ocr_roi('observe_reject', TEXT['reject']),
                                         time_out=5, what='「拒绝饰品」'), after_sleep=1.5)
        else:
            chosen = 0
            for kind, tier, index in picks:
                self.open_observe_tab(kind)
                point = self.gift_point(tier, index)
                label = f'{kind} {"I" * tier} 第{index}個'
                if point is None:
                    self.log_warning(f'找不到 {label}，略過')
                    continue
                before = self.observe_count()
                self.click_relative(*point, after_sleep=1)
                self.next_frame()
                after = self.observe_count()
                if before and after and after[0] <= before[0]:
                    self.log_warning(f'{label} 點了沒有選上 (可能已拥有或位置是空的)')
                    continue
                chosen += 1
                self.log_info(f'观测：選了 {label}')
            self.info_set('饰品观测', f'選了 {chosen} 個')
            button = self.wait_for(lambda: self.ocr_roi('observe_select', TEXT['select']),
                                   time_out=5, what='观测的「选择」')
            if chosen == 0:
                self.log_info('一個都沒選上，改按拒绝饰品')
                button = self.ocr_roi('observe_reject', TEXT['reject']) or button
            self.click_box(button, after_sleep=1.5)

        # 「是否要消耗N星芒以进行E.G.O饰品观测?」或拒絕的確認
        start = time.time()
        while time.time() - start < 30:
            self.next_frame()
            if self.ocr_roi('pack_title', TEXT['pack_title']):
                self.info_set('進度', '主題卡包選擇')
                return
            if self.handle_gift_popup():
                continue
            ok = self.ocr_roi('md_popup_btn', TEXT['confirm'])
            if ok:
                self.click_box(ok, after_sleep=2)
                continue
            self.sleep(1)
        self.screenshot('fail_observe')
        raise TaskFailed('饰品观测之後沒有進到主題卡包選擇')

    # ---------- 主題卡包 ----------

    def pack_rules(self, key):
        return [vision.parse_pack_rule(str(line)) for line in self.config.get(key, []) if str(line).strip()]

    def pack_floor(self):
        text = ''.join(b.name for b in self.ocr_roi('pack_title'))
        found = vision.parse_int(text)
        return found if found and found < 20 else 1

    def visible_packs(self):
        return sorted([b for b in self.ocr_roi('pack_names') if len(b.name.strip()) >= 2],
                      key=lambda b: b.x)

    def pack_center_x(self, box):
        return (box.x + box.width / 2) / self.width

    def best_pack(self, packs, rules, floor):
        ranked = [(vision.rule_matches(rules, floor, b.name), b) for b in packs]
        ranked = [(rank, b) for rank, b in ranked if rank is not None]
        return min(ranked, key=lambda r: r[0])[1] if ranked else None

    def set_pack_difficulty(self):
        want = self.config.get('Pack Difficulty', MODE_KEEP)
        if want == MODE_KEEP:
            return
        is_hard = bool(self.ocr_roi('pack_mode', TEXT['hard']))
        if is_hard == (want == MODE_HARD):
            return
        self.log_info(f'卡包難度切換為{want}')
        self.click_relative(*PACK_MODE_ARROW, after_sleep=2)
        self.next_frame()
        if bool(self.ocr_roi('pack_mode', TEXT['hard'])) == is_hard:
            self.log_warning('難度切換沒有反應 (可能已經不能切換了)')

    def read_refresh(self):
        """讀右上「刷新 N/M」，讀不到回傳 None。"""
        found = vision.parse_fraction(''.join(b.name for b in self.ocr_roi('pack_refresh')))
        return found[0] if found else None

    def refreshes_left(self, time_out: float = 10) -> int:
        """剛進卡包畫面時右上角會先冒出一行小字擋住「刷新 N/M」，所以多等一下、重讀幾次。"""
        start = time.time()
        while True:
            self.next_frame()
            left = self.read_refresh()
            if left is not None:
                self.info_set('刷新次數', left)
                return left
            if time.time() - start > time_out:
                self.log_warning('讀不到刷新次數，當作沒有刷新')
                return 0
            self.sleep(0.8)

    def drag_pack(self, box):
        x = self.pack_center_x(box)
        self.log_info(f'選擇主題卡包：{box.name}')
        self.info_set('主題卡包', box.name)
        self.swipe_relative(x, PACK_DRAG_FROM_Y, x, PACK_DRAG_TO_Y, duration=0.8)
        self.sleep(2)
        start = time.time()
        while time.time() - start < 15:
            self.next_frame()
            if not self.ocr_roi('pack_title', TEXT['pack_title']):
                return
            if self.handle_gift_popup():
                continue
            ok = self.ocr_roi('center', TEXT['confirm'])
            if ok:
                self.click_box(ok, after_sleep=2)
                continue
            self.sleep(1)
        self.screenshot('fail_pack_drag')
        raise TaskFailed(f'拖了「{box.name}」還是停在卡包選擇畫面')

    def choose_pack(self):
        self.wait_for(lambda: self.ocr_roi('pack_title', TEXT['pack_title']),
                      time_out=30, what='主題卡包選擇畫面')
        self.sleep(1.5)
        # 等右上的小字消失、讀到「刷新 N/M」再開始
        refreshes = self.refreshes_left(time_out=12)
        self.set_pack_difficulty()
        floor = self.pack_floor()
        want = self.pack_rules(pack_key(floor)) if floor in pack_data.FLOORS else []
        avoid = self.pack_rules('Pack Avoid')
        self.info_set('樓層', f'{floor}F，想要：' + ('、'.join(self.config.get(pack_key(floor), [])) or '無'))

        for _ in range(10):
            self.next_frame()
            packs = self.visible_packs()
            self.info_set('卡包選項', '、'.join(b.name for b in packs))
            best = self.best_pack(packs, want, floor)
            if best is not None:
                return self.drag_pack(best)
            if not want:
                break
            if self.config.get('Pack Use Refresh', True) and refreshes > 0:
                self.log_info(f'沒有想要的卡包，刷新 (剩 {refreshes} 次)')
                button = self.ocr_roi('pack_refresh', TEXT['refresh'])
                if button:
                    self.click_box(button, after_sleep=2.5)
                else:
                    self.click_relative(*PACK_REFRESH_BTN, after_sleep=2.5)
                refreshes = self.refreshes_left(time_out=6)
                continue
            break

        packs = self.visible_packs()
        if want and self.config.get('Pack Use Observe') and packs:
            replaced = self.observe_pack(packs, want, avoid, floor)
            if replaced:
                self.next_frame()
                best = self.best_pack(self.visible_packs(), want, floor)
                if best is not None:
                    return self.drag_pack(best)

        # 沒有想要的：選第一個不在避開清單的
        packs = self.visible_packs()
        if not packs:
            self.screenshot('fail_pack_names')
            raise TaskFailed('讀不到卡包名稱')
        normal = [b for b in packs if vision.rule_matches(avoid, floor, b.name) is None]
        self.drag_pack((normal or packs)[0])

    def observe_pack(self, packs, want, avoid, floor) -> bool:
        """用主题卡包观测把一個卡包換成想要的。回傳 True = 換好了。"""
        self.click_relative(*PACK_OBSERVE_BTN, after_sleep=2)
        self.next_frame()
        ok = self.ocr_roi('md_popup_btn', TEXT['confirm'])   # 可能先問要不要花星芒
        if ok:
            self.click_box(ok, after_sleep=2)
        # 換掉最不想要的那一個：避開清單裡的優先，否則最右邊
        target = next((b for b in packs if vision.rule_matches(avoid, floor, b.name) is not None),
                      packs[-1])
        self.click_relative(self.pack_center_x(target) + PACK_OBS_ICON_DX, PACK_OBS_ICON_Y,
                            after_sleep=2)
        if not self.wait_until(lambda: self.ocr_roi('pack_obs_title', TEXT['pack_obs_title']),
                               time_out=6):
            self.log_warning('沒有打開卡包觀測視窗')
            return False

        for _ in range(4):
            self.next_frame()
            boxes = self.ocr_roi('pack_obs_list')
            blocked = [b for b in boxes if vision.keywords_regex(TEXT['unavailable']).search(b.name)]
            names = [b for b in boxes if b not in blocked and len(b.name.strip()) >= 2]
            usable = [b for b in names
                      if not any(abs((x.x + x.width / 2) - (b.x + b.width / 2)) < self.width * 0.04
                                 and x.y < b.y for x in blocked)]
            best = self.best_pack(usable, want, floor)
            if best is not None:
                self.log_info(f'卡包觀測：把「{target.name}」換成「{best.name}」')
                self.click(best.x + best.width // 2, best.y - int(self.height * 0.1), after_sleep=1)
                self.click_box(self.wait_for(lambda: self.ocr_roi('pack_obs_ok', TEXT['confirm']),
                                             time_out=5, what='卡包觀測的「确认」'), after_sleep=2)
                return self.confirm_pack_replace()
            self.scroll_relative(0.68, 0.55, -5)
            self.sleep(1)
        self.log_warning('卡包觀測裡也沒有想要的卡包，取消')
        cancel = self.ocr_roi('center', ['取消', 'Cancel'])
        if cancel:
            self.click_box(cancel, after_sleep=1.5)
        return False

    def confirm_pack_replace(self) -> bool:
        """「主题卡包"A"将被"B"替换。」(下面是星芒花費) -> 确认。"""
        if not self.wait_until(lambda: self.ocr_roi('pack_replace', TEXT['pack_replace']), time_out=5):
            self.log_warning('沒有看到「…将被…替换」確認視窗')
            return not self.ocr_roi('pack_obs_title', TEXT['pack_obs_title'])
        for _ in range(3):
            ok = self.wait_for(lambda: self.ocr_roi('md_popup_btn', TEXT['confirm']),
                               time_out=5, what='替換確認的「确认」')
            self.click_box(ok, after_sleep=2.5)
            self.next_frame()
            if not self.ocr_roi('pack_replace', TEXT['pack_replace']):
                break
        self.wait_for(lambda: self.ocr_roi('pack_title', TEXT['pack_title'])
                      and not self.ocr_roi('pack_obs_title', TEXT['pack_obs_title']),
                      time_out=10, what='替換後回到卡包選擇畫面')
        self.sleep(1)
        return True

    # ---------- 樓層地圖 ----------

    def on_map_screen(self):
        return self.ocr_roi('map_title', TEXT['map_title'])

    def node_templates(self):
        """assets/lc/map_*.png：檔名 map_xxx -> 設定裡的名稱 (沒有對應名稱就用 xxx)。"""
        names = {tpl: name for name, tpl in NODE_TYPES.items()}
        templates = {}
        for path in sorted(TEMPLATE_DIR.glob('map_*.png')):
            image = self.load_template(path.stem)
            if image is not None:
                templates[names.get(path.stem, path.stem[4:])] = image
        return templates

    def zoom_out_map(self):
        for _ in range(MAP_ZOOM_SCROLLS):
            self.scroll_relative(*MAP_CENTER, -10)
            self.sleep(0.4)
        self.sleep(1)

    def save_unknown_node(self, icon):
        UNKNOWN_NODE_DIR.mkdir(parents=True, exist_ok=True)
        path = UNKNOWN_NODE_DIR / f'unknown_{time.strftime("%m%d_%H%M%S")}_{len(list(UNKNOWN_NODE_DIR.iterdir()))}.png'
        cv2.imencode('.png', icon)[1].tofile(str(path))
        self.log_info(f'不認得的節點圖示已存到 {path}，改名成 assets/lc/map_類型.png 就能辨識 (例如 map_abno.png)')

    def read_map(self):
        """回傳 [(節點, 類型)]，由上到下。"""
        self.next_frame()
        templates = self.node_templates()
        result = []
        for node in vision.find_reachable_nodes(self.frame):
            icon = vision.node_icon(self.frame, node)
            kind, score = vision.classify_node(icon, templates) if templates else (None, 0)
            if kind is None or score < NODE_MATCH_THRESHOLD:
                kind = NODE_UNKNOWN
                self.save_unknown_node(icon)
            result.append((node, kind))
        return result

    def choose_node(self):
        self.wait_for(self.on_map_screen, time_out=30, what='樓層地圖 (正在探索第N层)')
        self.sleep(1.5)
        self.zoom_out_map()
        nodes = self.read_map()
        if not nodes:
            # 沒有亮起的路 = 目前這個節點還沒打完，點自己所在的位置 (紅色火車) 再進去
            train = vision.find_train(self.frame)
            if train is None:
                self.screenshot('fail_map_nodes')
                raise TaskFailed('樓層地圖上找不到可以走的節點，也找不到目前位置 (紅色火車)')
            self.log_info('沒有亮起的路線，目前節點還沒通過，點目前位置')
            self.info_set('選擇節點', '目前位置')
            self.click(*train, after_sleep=2)
            return '目前位置'
        boxes = [Box(n.x - n.size // 2, n.y - n.size // 2, n.size, n.size, name=kind) for n, kind in nodes]
        self.draw_boxes('map_node', boxes, 'green')
        self.info_set('可走節點', '、'.join(kind for _, kind in nodes))

        priority = [str(line).strip() for line in self.config.get('Node Priority', []) if str(line).strip()]
        rank = {kind: i for i, kind in reversed(list(enumerate(priority)))}
        node, kind = min(nodes, key=lambda nk: rank.get(nk[1], len(priority)))
        self.log_info(f'可走節點：{"、".join(k for _, k in nodes)}，選擇：{kind}')
        self.info_set('選擇節點', kind)
        # 點節點中間的圖示 (外框下方有立體的邊，所以往上一點)
        self.click(node.x, int(node.y + node.size * vision.NODE_ICON_DY), after_sleep=2)
        return kind

    def enter_node(self):
        """點了節點後右邊會出現卡包名稱和「进入」。"""
        button = self.wait_until(lambda: self.ocr_roi('node_enter', TEXT['enter']), time_out=6)
        if button:
            self.click_box(button, after_sleep=2)
        else:
            self.log_warning('沒看到「进入」，直接點它的位置')
            self.click_relative(*NODE_ENTER_BTN, after_sleep=2)
        for _ in range(3):   # 確認離開地圖了，沒有就再按一次
            self.next_frame()
            if not self.ocr_roi('node_enter', TEXT['enter']):
                return
            self.click_relative(*NODE_ENTER_BTN, after_sleep=2)
        self.screenshot('fail_node_enter')
        raise TaskFailed('按了「进入」還停在地圖上')

    # ---------- 事件 ----------

    def on_event_screen(self):
        return self.ocr_roi('event_skip', TEXT['skip']) or self.ocr_roi('event_options_title',
                                                                        TEXT['event_options_title'])

    def event_options(self):
        """回傳 [(要點的文字框, 全部文字, 類型)]，由上到下。"""
        boxes = [b for b in self.ocr_roi('event_options') if b.name.strip()]
        groups = vision.group_by_rows(boxes, lambda b: b.y, EVENT_OPTION_GAP * self.height)
        result = []
        for group in groups:
            text = ' '.join(b.name.strip() for b in group)
            result.append((group[0], text, vision.classify_event_option(text)))
        return result

    def log_unknown_option(self, text):
        EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = EVENT_LOG_DIR / 'options.txt'
        seen = path.read_text(encoding='utf-8').splitlines() if path.is_file() else []
        if text in seen:
            return
        with path.open('a', encoding='utf-8') as f:
            f.write(text + '\n')
        self.screenshot('event_option_new')
        self.log_info(f'沒見過的事件選項，已記到 {path}：{text}')

    def choose_event_option(self, options):
        priority = [str(x).strip() for x in self.config.get('Event Priority', EVENT_DEFAULT) if str(x).strip()]
        for _, text, kind in options:
            if kind == vision.EVENT_OTHER:
                self.log_unknown_option(text)
        box, text, kind = min(options, key=lambda o: priority.index(o[2]) if o[2] in priority else len(priority))
        self.log_info('事件選項：' + '、'.join(f'{t} [{k}]' for _, t, k in options) + f'，選擇：{text}')
        self.info_set('事件選項', f'{kind}：{text}')
        self.click_box(box, after_sleep=2)

    def handle_event(self, time_out: float = 90) -> bool:
        """事件：一直點 SKIP (沒亮也點) 直到出現「选项」，依優先順序選一個；
        選完可能還有對話、下一輪選項或獲得饰品，一直處理到回到地圖。不是事件畫面回傳 False。"""
        if not self.wait_until(self.on_event_screen, time_out=8):
            return False
        self.log_info('進入事件')
        start = time.time()
        while time.time() - start < time_out:
            self.next_frame()
            if self.on_map_screen() or self.ocr_roi('pack_title', TEXT['pack_title']):
                self.log_info('事件結束')
                return True
            if self.on_battle_team_screen():   # 選項進了戰鬥
                return self.fight_node() != 'defeat'
            if self.handle_gift_popup():
                continue
            if self.ocr_roi('event_options_title', TEXT['event_options_title']):
                options = self.event_options()
                if options:
                    self.choose_event_option(options)
                    continue
            # 還沒有選項：不管 SKIP 有沒有亮都點 (對話會一段一段跳過)
            self.click_relative(*EVENT_SKIP_BTN, after_sleep=1)
        self.screenshot('fail_event')
        raise TaskFailed('事件處理超時 (可能是判定或戰鬥畫面，還沒做)，請把截圖給我')

    # ---------- 戰鬥節點 (跟經驗本「進入戰鬥」一樣) ----------

    def on_battle_team_screen(self):
        if self.has_template('team_screen') and self.find_template('team_screen'):
            return True
        return self.ocr_roi('to_battle', TEXT['to_battle'])

    def in_input_phase(self):
        return bool(self.ocr_roi('battle_hud', TEXT['win_rate']))

    def fight_node(self):
        """編隊畫面 → 开始战斗 → 出指令階段按 P + Enter → 結算按确认 → 回到地圖。
        回傳 'victory' / 'defeat'。"""
        self.log_info('戰鬥節點：開始戰鬥')
        button = self.ocr_roi('to_battle', TEXT['to_battle'])
        if button:
            self.click_box(button, after_sleep=3)
        else:
            self.click_pos('to_battle', after_sleep=3)
        timeout = self.config.get('Battle Timeout (s)', 400)
        start, result = time.time(), None
        while time.time() - start < timeout:
            self.next_frame()
            if self.on_map_screen() or self.ocr_roi('pack_title', TEXT['pack_title']):
                self.log_info(f'戰鬥結束 ({result or "?"})，用時 {int(time.time() - start)} 秒')
                return result or 'victory'
            got = self.handle_result_screen()
            if got:
                result = got
                if got == 'defeat':
                    return got
                continue
            if self.handle_gift_popup():
                continue
            if self.in_input_phase():
                self.send_key('p', after_sleep=0.5)
                self.send_key('enter', after_sleep=3)
                self.info_incr('回合')
                continue
            if self.on_battle_team_screen():   # 開戰沒反應，再按一次
                self.click_pos('to_battle', after_sleep=3)
                continue
            confirm = self.ocr_roi('lower_half', TEXT['confirm'])
            if confirm:
                self.click_box(confirm, after_sleep=2)
                continue
            self.sleep(1)
        self.screenshot('fail_md_battle')
        raise TaskFailed(f'戰鬥超過 {timeout} 秒沒回到地圖 (可能是戰後獎勵畫面還沒做)，請把截圖給我')
