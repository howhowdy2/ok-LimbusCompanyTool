import time

from src.lc import vision
from src.lc.layout import REPEAT_UP_OFFSET_X, REPEAT_UP_Y, TEXT
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed

MODE_SKIP = '跳過戰鬥'
MODE_BATTLE = '進入戰鬥'
STAGE_OPTIONS = ['最右邊 (最高關)', '中間', '最左邊']
# 每次消耗的腦啡肽模組 (畫面上「进入 3」「跳过战斗 6」)
ENTER_COST = 3
SKIP_COST = 6
# 彈窗裡出現這些字就停：代表可能要花狂氣或購買東西
DANGER_TEXT = ['Lunacy', '狂气', '购买', 'Purchase', '不足']


class ExpLuxcavationTask(LimbusBaseTask):
    """打經驗本 (Luxcavation EXP)。

    主畫面 → Drive → 采光 → 经验分頁 → 設定「连续进行」次數 →
    「跳过战斗」(預設) 或「进入」→ 編隊畫面「开始战斗」→ 自動戰鬥。
    關卡按鈕全部用 OCR 找字，不需要模板。
    """

    STAGE_OPTIONS = STAGE_OPTIONS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '打經驗本'
        self.description = '跳過戰鬥或用上次的隊伍打 Luxcavation EXP'
        self.default_config.update({
            'Mode': MODE_SKIP,
            'Runs': 1,
            'Stage': STAGE_OPTIONS[0],
            'Battle Timeout (s)': 300,
        })
        self.config_type.update({
            'Mode': {'type': 'drop_down', 'options': [MODE_SKIP, MODE_BATTLE]},
            'Stage': {'type': 'drop_down', 'options': STAGE_OPTIONS},
        })
        self.config_description.update({
            'Mode': '跳過戰鬥：花較多模組直接拿獎勵，最穩定\n進入戰鬥：用上次的編隊自動打',
            'Runs': '要打幾次 (用遊戲的「连续进行」一次設定好)',
            'Stage': '打畫面上哪一張關卡卡片',
            'Battle Timeout (s)': '進入戰鬥模式下，一場最多等幾秒',
        })

    def run(self):
        self.open_luxcavation()
        runs = max(1, self.config.get('Runs', 1))
        skip = self.config.get('Mode') == MODE_SKIP
        before = self.read_modules()
        self.info_set('模組 (開始)', before)
        need = (SKIP_COST if skip else ENTER_COST) * runs
        if before is not None and before < need:
            raise TaskFailed(f'模組不夠：需要 {need}，目前 {before}')

        button = self.pick_stage(skip=skip)
        self.set_repeat(button, runs)
        if self.config.get('Mode') == MODE_SKIP:
            self.skip_battle(button)
        else:
            self.enter_and_fight(button)

        after = self.read_modules()
        self.info_set('模組 (結束)', after)
        if before is not None and after is not None and after >= before:
            self.log_warning(f'模組數量沒有減少 ({before} -> {after})，請確認有沒有真的打到')
        self.go_home()
        self.log_info(f'經驗本完成 ({runs} 次)', notify=True)

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
        # 上次停在「纺锤」的話切回「经验」
        tab = self.ocr_roi('lux_tabs', TEXT['lux_exp_tab'])
        if tab:
            self.click_box(tab, after_sleep=1.5)

    def pick_stage(self, skip: bool):
        buttons = self.wait_for(lambda: self.stage_buttons(skip), time_out=5,
                                what='跳过战斗按鈕' if skip else '进入按鈕')
        choice = self.config.get('Stage', STAGE_OPTIONS[0])
        if choice == STAGE_OPTIONS[2]:
            return buttons[0]
        if choice == STAGE_OPTIONS[1] and len(buttons) >= 3:
            return buttons[len(buttons) // 2]
        return buttons[-1]

    def repeat_count_near(self, button):
        """讀出和 button 同一張卡片上的「连续进行×N」。"""
        cx = button.x + button.width / 2
        for box in self.ocr_roi('lux_repeat', TEXT['lux_repeat']):
            if abs(box.x + box.width / 2 - cx) < self.width * 0.13:
                return vision.parse_repeat(box.name)
        return None

    def set_repeat(self, button, runs: int):
        """按 ▲ 直到「连续进行」等於 runs (到上限就停)。"""
        cx = (button.x + button.width / 2) / self.width
        current = self.repeat_count_near(button)
        for _ in range(20):
            if current is None or current >= runs:
                break
            self.click_relative(cx + REPEAT_UP_OFFSET_X, REPEAT_UP_Y, after_sleep=0.4)
            self.next_frame()
            new = self.repeat_count_near(button)
            if new == current:  # 已經到上限
                self.log_warning(f'连续进行最多只能設到 {current}')
                break
            current = new
        self.info_set('连续进行', current)

    # ---------- 跳過戰鬥 ----------

    def skip_battle(self, button):
        self.click_box(button, after_sleep=1.5)
        start = time.time()
        clicked_any = False
        while time.time() - start < 30:
            self.next_frame()
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
            # 沒有彈窗、又回到關卡列表 = 結束
            if (clicked_any or time.time() - start > 5) and self.on_stage_list():
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
        enter = self.stage_buttons(skip=False)
        # 找和選到的「跳过战斗」同一張卡片的「进入」(pick_stage 用的是 enter 按鈕時就是它本身)
        target = min(enter, key=lambda b: abs(b.x - button.x)) if enter else button
        self.click_box(target, after_sleep=2)
        try:
            self.wait_for(self.on_team_screen, time_out=10, what='編隊畫面')
        except TaskFailed:
            raise TaskFailed('點了「进入」卻沒進編隊畫面，可能是模組不足或跳出了提示視窗')
        start_button = self.ocr_roi('to_battle', TEXT['to_battle'])
        if start_button:
            self.click_box(start_button, after_sleep=3)
        else:
            self.click_pos('to_battle', after_sleep=3)
        self.fight()

    def fight(self):
        """每隔一段時間按 P(勝率) 和 Enter(開戰)，直到回到關卡列表。

        连续进行 > 1 時會一場接一場打，全部打完才會回到列表。
        """
        timeout = self.config.get('Battle Timeout (s)', 300) * max(1, self.config.get('Runs', 1))
        start = time.time()
        while time.time() - start < timeout:
            self.next_frame()
            if self.on_stage_list():
                self.log_info(f'戰鬥結束，用時 {int(time.time() - start)} 秒')
                return
            if self.handle_result_screen():
                continue
            confirm = self.ocr_roi('lower_half', TEXT['confirm'])
            if confirm:
                self.click_box(confirm, after_sleep=2)
                continue
            self.send_key('p', after_sleep=0.3)
            self.send_key('enter', after_sleep=2)
        self.screenshot('fail_battle_timeout')
        raise TaskFailed(f'戰鬥超過 {timeout} 秒沒結束')
