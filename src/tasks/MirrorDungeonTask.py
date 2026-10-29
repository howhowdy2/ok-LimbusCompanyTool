import time

from src.lc import vision
from src.lc.layout import TEXT
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed

IN_PROGRESS_CONTINUE = '繼續探索'
IN_PROGRESS_ABORT = '終止探索 (放棄獎勵)'


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
        })
        self.config_type.update({
            'If In Progress': {'type': 'drop_down',
                               'options': [IN_PROGRESS_CONTINUE, IN_PROGRESS_ABORT]},
        })
        self.config_description.update({
            'Min Star Reward': '編隊畫面「星芒奖励」低於這個數字，就依序換名稱有「镜像迷宫」的編隊，'
                               '直到夠高為止 (都不夠就用最高的那隊)。0 = 不換，用目前的編隊',
            'If In Progress': '上次的迷宮還沒結束時：繼續，或終止並放棄獎勵後重新開一場',
        })

    def run(self):
        self.open_mirror_dungeon()
        if self.enter_dungeon() == 'continued':
            self.log_info('繼續上次的鏡像迷宮 (迷宮內流程尚未實作，請手動接手)', notify=True)
            return
        self.choose_team()
        self.confirm_team()
        self.log_info('已進入鏡像迷宮 (迷宮內流程尚未實作，請手動接手)', notify=True)

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
        self.click_md_enter()

        if vision.keywords_regex(TEXT['md_not_started']).search(status):
            # 「是否进入西西弗之镜?」
            ok = self.wait_for(lambda: self.ocr_roi('md_popup_btn', TEXT['enter']),
                               time_out=8, what='「是否进入」視窗')
            self.click_box(ok, after_sleep=2.5)
            self.wait_for(self.on_team_screen, time_out=15, what='鏡像迷宮編隊畫面')
            return 'new'

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
