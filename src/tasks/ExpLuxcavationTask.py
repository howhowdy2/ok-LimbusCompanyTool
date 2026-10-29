import time

from src.lc.layout import TEXT
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed


class ExpLuxcavationTask(LimbusBaseTask):
    """打經驗本 (Luxcavation EXP)。

    流程：主畫面 → Drive → Luxcavation → 選關卡的門 → 編隊畫面 To Battle!
    → 戰鬥中一直按 P(勝率) + Enter(開戰) → 回到關卡列表 → 重複。
    使用上次的隊伍，不會改編隊。
    """

    STAGE_OPTIONS = ['最高關', '1', '2', '3', '4', '5', '6', '7', '8', '9']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '打經驗本'
        self.description = '用上次的隊伍打 Luxcavation EXP，需要先擷取 exp_enter 模板'
        self.default_config.update({
            'Runs': 1,
            'Stage': '最高關',
            'Battle Timeout (s)': 300,
        })
        self.config_type.update({
            'Stage': {'type': 'drop_down', 'options': self.STAGE_OPTIONS},
        })
        self.config_description.update({
            'Runs': '要打幾次',
            'Stage': '打哪一關，從左邊數第幾個入口；「最高關」= 最右邊那個',
            'Battle Timeout (s)': '一場戰鬥最多等幾秒，超過就停止',
        })

    def run(self):
        self.require_template('exp_enter')
        runs = self.config.get('Runs', 1)
        for i in range(runs):
            self.info_set('經驗本', f'{i + 1}/{runs}')
            self.run_once()
        self.go_home()
        self.log_info(f'經驗本完成 {runs} 次', notify=True)

    # ---------- 各步驟 ----------

    def stage_doors(self):
        doors = self.find_template('exp_enter', threshold=0.8, max_results=12)
        return sorted(doors, key=lambda box: box.x)

    def open_luxcavation(self):
        if self.stage_doors():  # 已經在關卡列表
            return
        self.go_home()
        self.click_pos('home_drive', after_sleep=1.5)
        entry = self.wait_for(lambda: self.ocr_roi('luxcavation', TEXT['luxcavation']),
                              time_out=8, what='Drive 選單的 Luxcavation')
        self.click_box(entry, after_sleep=2)
        self.wait_for(self.stage_doors, time_out=10, what='經驗本關卡列表')

    def pick_stage(self):
        doors = self.stage_doors()
        if not doors:
            raise TaskFailed('找不到關卡入口')
        stage = self.config.get('Stage', '最高關')
        if stage == '最高關':
            return doors[-1]
        index = int(stage) - 1
        if index >= len(doors):
            self.log_warning(f'只找到 {len(doors)} 個關卡入口，改打最高關')
            return doors[-1]
        return doors[index]

    def on_team_screen(self):
        if self.has_template('team_screen') and self.find_template('team_screen'):
            return True
        return self.ocr_roi('to_battle', TEXT['to_battle'])

    def enter_battle(self):
        door = self.pick_stage()
        self.click_box(door, after_sleep=2)
        try:
            self.wait_for(self.on_team_screen, time_out=10, what='編隊畫面')
        except TaskFailed:
            raise TaskFailed('點了關卡卻沒進編隊畫面，可能是體力不足或跳出了提示視窗')
        button = self.ocr_roi('to_battle', TEXT['to_battle'])
        if button:
            self.click_box(button, after_sleep=3)
        else:
            self.click_pos('to_battle', after_sleep=3)

    def fight(self):
        """戰鬥：每隔一段時間按 P(勝率) 和 Enter(開戰)，直到回到關卡列表或主畫面。"""
        timeout = self.config.get('Battle Timeout (s)', 300)
        start = time.time()
        while time.time() - start < timeout:
            self.next_frame()
            if self.stage_doors() or (self.has_template('home_window') and self.is_home()):
                self.log_info(f'戰鬥結束，用時 {int(time.time() - start)} 秒')
                return
            confirm = self.ocr_roi('lower_half', TEXT['confirm'])
            if confirm:  # 結算畫面的確認鍵
                self.click_box(confirm, after_sleep=2)
                continue
            self.send_key('p', after_sleep=0.3)
            self.send_key('enter', after_sleep=2)
        self.screenshot('fail_battle_timeout')
        raise TaskFailed(f'戰鬥超過 {timeout} 秒沒結束')

    def run_once(self):
        self.open_luxcavation()
        self.enter_battle()
        self.fight()
        self.info_incr('經驗本完成次數')
