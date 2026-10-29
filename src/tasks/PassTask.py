import time

from src.lc.layout import PASS_CLAIMABLE_MIN_RED, PASS_ROW_SAMPLE_X, TEXT
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed


class PassTask(LimbusBaseTask):
    """領通行證獎勵。

    主畫面右上「LIMBUS PASS」橫幅 → 通行证任务 → 日常任务 / 周常任务 裡可以領的列一個一個點
    → 战斗通行证 → 全部领取 (可關掉)。
    可以領的任務列背景是棕橘色，用顏色判斷，不用模板。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '領通行證獎勵'
        self.description = '領通行證日常 / 周常任務，再到战斗通行证按全部领取'
        self.default_config.update({
            'Claim Daily Missions': True,
            'Claim Weekly Missions': True,
            'Claim All Pass Rewards': True,
        })
        self.config_description.update({
            'Claim Daily Missions': '領「通行证任务 → 日常任务」裡完成的任務',
            'Claim Weekly Missions': '領「通行证任务 → 周常任务」裡完成的任務',
            'Claim All Pass Rewards': '最後到「战斗通行证」按「全部领取」',
        })

    def run(self):
        self.open_pass()
        if self.config.get('Claim Daily Missions') or self.config.get('Claim Weekly Missions'):
            self.click_tab('pass_missions_tab')
            if self.config.get('Claim Daily Missions'):
                self.info_set('日常任務領取', self.claim_missions('pass_daily_tab'))
            if self.config.get('Claim Weekly Missions'):
                self.info_set('周常任務領取', self.claim_missions('pass_weekly_tab'))
        if self.config.get('Claim All Pass Rewards'):
            self.claim_all_rewards()
        self.go_home()
        self.log_info('通行證獎勵領取完成', notify=True)

    # ---------- 畫面 ----------

    def on_pass_screen(self):
        return self.ocr_roi('pass_tabs', TEXT['pass_missions_tab'])

    def open_pass(self):
        if self.on_pass_screen():
            return
        self.go_home()
        banner = self.ocr_roi('pass_banner', TEXT['pass_banner'])
        self.click_pos('pass_banner', after_sleep=2)
        if not banner:
            self.log_warning('沒讀到「LIMBUS PASS」字樣，直接點橫幅位置')
        self.wait_for(self.on_pass_screen, time_out=10, what='通行證畫面')

    def click_tab(self, key):
        tab = self.wait_for(lambda: self.ocr_roi('pass_tabs', TEXT[key]), time_out=5,
                            what=f'通行證分頁 {TEXT[key][-1]}')
        self.click_box(tab, after_sleep=1.5)

    # ---------- 通行證任務 ----------

    def row_claimable(self, box) -> bool:
        """任務名稱右邊那塊背景是棕橘色 = 可以領。"""
        frame = self.frame
        h, w = frame.shape[:2]
        cy = box.y + box.height / 2
        x0, x1 = (int(PASS_ROW_SAMPLE_X[0] * w), int(PASS_ROW_SAMPLE_X[1] * w))
        patch = frame[int(cy - 0.012 * h):int(cy + 0.012 * h), x0:x1, :3]
        return patch.size > 0 and patch[:, :, 2].mean() > PASS_CLAIMABLE_MIN_RED

    def claimable_rows(self):
        titles = [b for b in self.ocr_roi('pass_missions') if len(b.name) >= 4]
        return [b for b in titles if self.row_claimable(b)]

    def claim_missions(self, tab_pos) -> int:
        self.click_pos(tab_pos, after_sleep=1.5)
        claimed = 0
        last = None
        for _ in range(10):
            self.next_frame()
            rows = self.claimable_rows()
            if not rows:
                break
            row = rows[0]
            if row.name == last:  # 點了還是可以領 = 點擊沒有作用，別一直點
                self.screenshot('fail_pass_claim')
                raise TaskFailed(f'任務「{row.name}」點了沒有領到')
            last = row.name
            self.log_info(f'領取任務：{row.name}')
            self.click_box(row, after_sleep=1.5)
            self.dismiss_popups()
            claimed += 1
        return claimed

    # ---------- 战斗通行证 ----------

    def claim_all_rewards(self):
        self.click_tab('pass_rewards_tab')
        button = self.ocr_roi('pass_claim_all', TEXT['claim_all'])
        if not button:
            self.log_info('沒有「全部领取」按鈕 (可能沒有可以領的獎勵)')
            return
        self.click_box(button, after_sleep=2)
        self.dismiss_popups()
        self.info_set('全部领取', '已按')

    def dismiss_popups(self, timeout: float = 6):
        """領獎後的彈窗：看到确认 / 点击继续就按，畫面安靜下來就結束。"""
        start = time.time()
        while time.time() - start < timeout:
            self.next_frame()
            button = self.ocr_roi('center', TEXT['confirm']) or \
                self.ocr_roi('lower_half', TEXT['continue'])
            if not button:
                return
            self.click_box(button, after_sleep=1.5)
        self.screenshot('fail_pass_popup')
        raise TaskFailed('領獎後的彈窗一直關不掉')
