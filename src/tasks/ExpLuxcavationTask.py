import time

from ok import Box

from src.lc import vision
from src.lc.layout import REPEAT, TEXT
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed

MODE_SKIP = '跳過戰鬥'
MODE_BATTLE = '進入戰鬥'
STAGE_OPTIONS = ['最右邊 (最高關)', '中間', '最左邊']
LEVEL_OPTIONS = ['最下面 (等級最高)', '中間', '最上面']
MAX_REPEAT = 10  # 遊戲「连续进行」上限
# 彈窗裡出現這些字就停：代表可能要花狂氣或購買東西
DANGER_TEXT = ['Lunacy', '狂气', '购买', 'Purchase', '不足']


class LuxcavationTask(LimbusBaseTask):
    """采光 (Luxcavation) 共用流程，經驗本和纺锤本都繼承它。

    主畫面 → Drive → 采光 → 切到分頁 → 選卡片 → 設定「连续进行」→
    「跳过战斗」或「进入」→ 編隊畫面「开始战斗」→ 自動戰鬥 → 結算按确认。
    關卡按鈕全部用 OCR 找字，不需要模板。
    """

    STAGE_OPTIONS = STAGE_OPTIONS
    TAB_TEXT = TEXT['lux_exp_tab']
    TITLE = '采光'
    ENTER_COST = 0   # 每次消耗的腦啡肽模組
    SKIP_COST = 0
    DEFAULT_RUNS = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_config.update({
            'Mode': MODE_SKIP,
            'Runs': self.DEFAULT_RUNS,
            'Stage': STAGE_OPTIONS[0],
            'Battle Timeout (s)': 400,
        })
        self.config_type.update({
            'Mode': {'type': 'drop_down', 'options': [MODE_SKIP, MODE_BATTLE]},
            'Stage': {'type': 'drop_down', 'options': STAGE_OPTIONS},
        })
        self.config_description.update({
            'Mode': '跳過戰鬥：直接拿獎勵，最穩定\n進入戰鬥：用上次的編隊自動打',
            'Runs': '要打幾次，1~10 (用遊戲的「连续进行」一次設定好)',
            'Stage': '打畫面上哪一張可以打的關卡卡片',
            'Battle Timeout (s)': '進入戰鬥模式下，一場最多等幾秒 (连续进行 N 次就等 N 倍)',
        })

    # 一鍵日常會先設定這個，用日常自己的次數；單獨執行時是 None，用任務自己的 Runs
    runs_override = None
    mode_override = None   # 一鍵日常可以指定跳過戰鬥或進入戰鬥
    current_runs = 1

    # ---------- 給子類別調整 ----------

    def planned_runs(self, runs: int) -> int:
        """實際要打幾次；回傳 0 代表今天不用打。"""
        return runs

    def available_buttons(self, buttons):
        """可以打的卡片按鈕 (預設全部)。"""
        return buttons

    # ---------- 主流程 ----------

    def run(self):
        self.open_luxcavation()
        runs = self.runs_override if self.runs_override is not None else self.config.get('Runs', 1)
        runs = max(1, runs)
        if runs > MAX_REPEAT:
            self.log_warning(f'连续进行最多 {MAX_REPEAT} 次，改成 {MAX_REPEAT}')
            runs = MAX_REPEAT
        runs = self.planned_runs(runs)
        self.current_runs = max(1, runs)
        if runs <= 0:
            self.go_home()
            return

        mode = self.mode_override or self.config.get('Mode', MODE_SKIP)
        skip = mode == MODE_SKIP
        cost = (self.SKIP_COST if skip else self.ENTER_COST) * runs
        before = self.read_modules()
        self.info_set('模組 (開始)', before)
        if cost and before is not None and before < cost:
            raise TaskFailed(f'模組不夠：需要 {cost}，目前 {before}')

        button = self.pick_stage(skip=skip)
        self.set_repeat(button, runs)
        if skip:
            self.skip_battle(button)
        else:
            self.enter_and_fight(button)

        after = self.read_modules()
        self.info_set('模組 (結束)', after)
        if cost and before is not None and after is not None and after >= before:
            self.log_warning(f'模組數量沒有減少 ({before} -> {after})，請確認有沒有真的打到')
        self.go_home()
        self.log_info(f'{self.TITLE}完成 ({runs} 次)', notify=True)

    # ---------- 畫面 ----------

    def stage_buttons(self, skip: bool):
        roi, key = ('lux_skip', 'lux_skip') if skip else ('lux_enter', 'lux_enter')
        return sorted(self.ocr_roi(roi, TEXT[key]), key=lambda box: box.x)

    def on_stage_list(self):
        return self.stage_buttons(skip=False)

    def read_modules(self):
        return vision.parse_int(''.join(b.name for b in self.ocr_roi('lux_modules')))

    def open_luxcavation(self):
        if not self.on_stage_list():
            self.go_home()
            self.click_pos('home_drive', after_sleep=1.5)
            entry = self.wait_for(lambda: self.ocr_roi('luxcavation', TEXT['luxcavation']),
                                  time_out=8, what='Drive 選單的采光')
            self.click_box(entry, after_sleep=2)
            self.wait_for(self.on_stage_list, time_out=10, what='采光關卡列表')
        tab = self.ocr_roi('lux_tabs', self.TAB_TEXT)
        if tab:
            self.click_box(tab, after_sleep=1.5)
        self.next_frame()

    def pick_stage(self, skip: bool):
        buttons = self.wait_for(lambda: self.available_buttons(self.stage_buttons(skip)),
                                time_out=5, what='可以打的關卡')
        choice = self.config.get('Stage', STAGE_OPTIONS[0])
        if choice == STAGE_OPTIONS[2]:
            return buttons[0]
        if choice == STAGE_OPTIONS[1] and len(buttons) >= 3:
            return buttons[len(buttons) // 2]
        return buttons[-1]

    # ---------- 连续进行 ----------

    def repeat_header(self, button):
        """找和 button 同一張卡片上的「连续进行×N」文字框。"""
        cx = button.x + button.width / 2
        for box in self.ocr_roi('lux_repeat', TEXT['lux_repeat']):
            if abs(box.x + box.width / 2 - cx) < self.width * 0.13:
                return box
        return None

    def repeat_count_near(self, button):
        header = self.repeat_header(button)
        return vision.parse_repeat(header.name) if header else None

    def find_toggle(self, header):
        """「连续进行×N」文字右邊的白色 ▲/▼ (像素座標)。"""
        w, h = self.width, self.height
        right = header.x + header.width
        area = (int(right + 0.004 * w), int(header.y - 0.01 * h),
                int(right + REPEAT.toggle_search_dx * w), int(header.y + header.height + 0.01 * h))
        return vision.find_bright_blob(self.frame, area)

    def ocr_px(self, left, top, right, bottom, keywords):
        box = Box(left, top, to_x=right, to_y=bottom)
        return self.ocr(box=box, match=vision.keywords_regex(keywords))

    def panel_buttons(self, header, toggle):
        """展開後的「1«」和綠色「+」(像素座標)。先用 OCR 找，找不到才用位移。"""
        w, h = self.width, self.height
        tx, ty = toggle
        row = self.ocr_px(int(header.x - 0.12 * w), int(ty + 0.015 * h),
                          int(tx + 0.03 * w), int(ty + 0.08 * h), ['《', '«', '+'])
        reset = next((b for b in row if '《' in b.name or '«' in b.name), None)
        plus = next((b for b in row if '+' in b.name), None)
        row_y = ty + REPEAT.row_dy * h
        reset_xy = (reset.x + reset.width / 2, reset.y + reset.height / 2) if reset \
            else (tx + REPEAT.min_dx * w, row_y)
        plus_xy = (plus.x + plus.width / 2, plus.y + plus.height / 2) if plus \
            else (tx + REPEAT.plus_dx * w, row_y)
        return reset_xy, plus_xy

    def click_px(self, xy, after_sleep):
        self.click_relative(xy[0] / self.width, xy[1] / self.height, after_sleep=after_sleep)

    def set_repeat(self, button, runs: int):
        """點 ▲ 展開 → 按「1«」歸 1 → 按綠色 + (runs-1) 次 → 點 ▼ 收起 → 確認數字。"""
        header = self.repeat_header(button)
        if header is None:
            self.log_warning('找不到「连续进行」，只打 1 次')
            return
        if vision.parse_repeat(header.name) == runs:
            self.info_set('连续进行', runs)
            return

        toggle = self.find_toggle(header)
        if toggle is None:
            self.screenshot('fail_repeat_toggle')
            raise TaskFailed('找不到「连续进行」旁邊的 ▲')
        self.click_px(toggle, after_sleep=0.8)                 # ▲ 展開
        self.next_frame()
        reset_xy, plus_xy = self.panel_buttons(header, toggle)
        self.click_px(reset_xy, after_sleep=0.4)               # 1« 歸 1
        for _ in range(runs - 1):
            self.click_px(plus_xy, after_sleep=0.3)            # 綠色 +
        self.click_px(toggle, after_sleep=0.6)                 # ▼ 收起
        self.next_frame()

        current = self.repeat_count_near(button)
        self.info_set('连续进行', current)
        if current != runs:
            self.screenshot('fail_set_repeat')
            raise TaskFailed(f'连续进行想設 {runs} 次，畫面上是 {current}')

    # ---------- 选择关卡 (纺锤本會跳出來) ----------

    def level_popup_open(self):
        return bool(self.ocr_roi('level_title', TEXT['level_title']))

    def choose_level(self, skip: bool):
        """「选择关卡」視窗：依設定點某一列右邊的「跳过战斗」或「进入」。

        列表由上到下等級越來越高，預設點最下面 (等級最高) 那一列。
        """
        key = 'lux_skip' if skip else 'lux_enter'
        rows = sorted(self.ocr_roi('level_actions', TEXT[key]), key=lambda b: b.y)
        if not rows:
            self.screenshot('fail_choose_level')
            raise TaskFailed('「选择关卡」視窗裡找不到按鈕')
        choice = self.config.get('Level', LEVEL_OPTIONS[0])
        if choice == LEVEL_OPTIONS[2]:
            row = rows[0]
        elif choice == LEVEL_OPTIONS[1]:
            row = rows[len(rows) // 2]
        else:
            row = rows[-1]
        self.info_set('关卡', f'第 {rows.index(row) + 1} 列 (共 {len(rows)} 列)')
        self.click_box(row, after_sleep=1.5)

    # ---------- 跳過戰鬥 ----------

    def skip_battle(self, button):
        self.click_box(button, after_sleep=1.5)
        start = time.time()
        clicked_any = False
        while time.time() - start < 30:
            self.next_frame()
            if self.level_popup_open():
                self.choose_level(skip=True)
                continue
            result = self.handle_result_screen()
            if result:
                clicked_any = True
                if result == 'defeat':
                    self.log_warning('跳過戰鬥顯示失敗')
                continue
            confirm = self.ocr_roi('center', TEXT['confirm'])
            if confirm:
                if self.ocr_roi('center', DANGER_TEXT):
                    self.screenshot('fail_skip_popup')
                    raise TaskFailed('彈窗提到狂氣/購買/不足，為了安全先停下來')
                self.click_box(confirm, after_sleep=1.5)
                clicked_any = True
                continue
            cont = self.ocr_roi('lower_half', TEXT['continue'])
            if cont:
                self.click_box(cont, after_sleep=1.5)
                clicked_any = True
                continue
            # 按過結算/確認、而且回到關卡列表 = 結束
            # (只看關卡列表不夠：選關視窗後面那些沒開放的卡片也讀得到「进入」)
            if clicked_any and self.on_stage_list():
                return
            self.sleep(1)
        self.screenshot('fail_skip_battle')
        raise TaskFailed('跳過戰鬥後 30 秒內沒回到關卡列表')

    # ---------- 進入戰鬥 ----------

    def on_team_screen(self):
        if self.has_template('team_screen') and self.find_template('team_screen'):
            return True
        return self.ocr_roi('to_battle', TEXT['to_battle'])

    def enter_and_fight(self, button):
        self.click_box(button, after_sleep=2)
        try:
            self.wait_for(lambda: self.on_team_screen() or self.level_popup_open(),
                          time_out=10, what='編隊畫面')
            if self.level_popup_open():
                self.choose_level(skip=False)
                self.wait_for(self.on_team_screen, time_out=10, what='編隊畫面')
        except TaskFailed:
            raise TaskFailed('點了「进入」卻沒進編隊畫面，可能是模組不足或跳出了提示視窗')
        start_button = self.ocr_roi('to_battle', TEXT['to_battle'])
        if start_button:
            self.click_box(start_button, after_sleep=3)
        else:
            self.click_pos('to_battle', after_sleep=3)
        self.fight()

    def in_input_phase(self):
        """右下角看得到「胜率 / 伤害」按鈕 = 等玩家下指令的階段。

        行動槽變多時這兩個按鈕會往右移，所以用 OCR 在一塊較寬的範圍裡找字。
        """
        return bool(self.ocr_roi('battle_hud', TEXT['win_rate']))

    def fight(self):
        """只在出指令階段按 P(勝率) + Enter(開戰)，演出動畫時不按鍵，直到回到關卡列表。

        连续进行 > 1 時會一場接一場打，全部打完才會回到列表。
        """
        timeout = self.config.get('Battle Timeout (s)', 400) * self.current_runs
        start = time.time()
        while time.time() - start < timeout:
            self.next_frame()
            if self.on_stage_list():
                self.log_info(f'戰鬥結束，用時 {int(time.time() - start)} 秒')
                return
            if self.handle_result_screen():
                continue
            if self.in_input_phase():
                self.send_key('p', after_sleep=0.5)
                self.send_key('enter', after_sleep=3)
                self.info_incr('回合')
                continue
            confirm = self.ocr_roi('lower_half', TEXT['confirm'])
            if confirm:
                self.click_box(confirm, after_sleep=2)
                continue
            self.sleep(1)  # 戰鬥演出中，等一下再看
        self.screenshot('fail_battle_timeout')
        raise TaskFailed(f'戰鬥超過 {timeout} 秒沒結束')


class ExpLuxcavationTask(LuxcavationTask):
    """經驗本：每次花模組 (畫面上「进入 3」「跳过战斗 6」)。"""

    TAB_TEXT = TEXT['lux_exp_tab']
    TITLE = '經驗本'
    ENTER_COST = 3
    SKIP_COST = 6

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '打經驗本'
        self.description = '跳過戰鬥或用上次的隊伍打采光「经验」'
        self.config_description['Mode'] = '跳過戰鬥：每次 6 模組，直接拿獎勵\n進入戰鬥：每次 3 模組，用上次的編隊自動打'
