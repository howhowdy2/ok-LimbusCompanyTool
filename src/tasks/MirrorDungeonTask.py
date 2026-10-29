import time

from src.lc import vision
from src.lc.layout import (OBSERVE_COL_X0, OBSERVE_COL_DX, OBSERVE_ROW_DY, OBSERVE_ROW_DY0,
                           OBSERVE_TAB_X, OBSERVE_TAB_Y, OBSERVE_TYPES, OBSERVE_VISIBLE_BOTTOM,
                           GIFT_CARD_X, GIFT_CARD_Y, GIFT_KEYWORDS, GIFT_SCROLL_ARROW,
                           GRACE_COL_X, GRACE_NAMES, GRACE_PLUS_DX, GRACE_PLUS_Y,
                           GRACE_PLUSPLUS_DX, GRACE_ROW_Y, TEXT)
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed

IN_PROGRESS_CONTINUE = '繼續探索'
IN_PROGRESS_ABORT = '終止探索 (放棄獎勵)'

GRACE_LEVELS = ['0', '1', '2']   # 1 = 卡片下的「+」，2 = 「++」
GRACE_DEFAULT = ['1 0', '3 0', '5 0']   # 預設選 1、3、5，0 級
GIFT_PICK_OPTIONS = ['1', '2', '3']
OBSERVE_OFF = '不選'
OBSERVE_TIERS = ['III', 'II', 'I']
OBSERVE_SLOTS = 3


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


class MirrorDungeonTask(LimbusBaseTask):
    """鏡像迷宮 (目前做到「進入迷宮」為止，迷宮裡的流程之後再加)。

    主畫面 → Drive → 镜像迷宫 → 进入
    - 探索前：「是否进入…?」进入 → 編隊畫面 → 依星芒奖励選隊 → 确认 → 等級警告确认
    - 探索中：「迷宫进度」選继续，或 终止探索 → 确认 → 探索结束奖励「放弃奖励」→ 再重新進入
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '鏡像迷宮'
        self.description = '進入鏡像迷宮並選好編隊 (迷宮內流程尚未完成)'
        self.default_config.update({
            'Min Star Reward': 0,
            'If In Progress': IN_PROGRESS_CONTINUE,
            'Gift Keyword': '呼吸法',
            'Gift Picks': ['1'],
            'Graces': list(GRACE_DEFAULT),
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

    def run(self):
        self.open_mirror_dungeon()
        if self.enter_dungeon() == 'continued':
            self.log_info('繼續上次的鏡像迷宮 (迷宮內流程尚未實作，請手動接手)', notify=True)
            return
        self.choose_team()
        self.confirm_team()
        self.choose_graces()
        self.choose_start_gifts()
        self.observe_gifts()
        self.log_info('已到主題卡包選擇 (之後的流程尚未實作，請手動接手)', notify=True)

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
