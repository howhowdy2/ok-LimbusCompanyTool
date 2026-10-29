from src.lc import vision
from src.lc.layout import TEXT
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed


class MirrorDungeonTask(LimbusBaseTask):
    """鏡像迷宮 (目前做到「選好編隊、進入迷宮」為止，迷宮裡的流程之後再加)。

    主畫面 → Drive → 镜像迷宫 → 进入 → 「是否进入…?」进入 → 編隊畫面
    → 看「星芒奖励」，太少就換一個名稱有「镜像迷宫」的編隊 → 确认 → 等級警告按确认。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '鏡像迷宮'
        self.description = '進入鏡像迷宮並選好編隊 (迷宮內流程尚未完成)'
        self.default_config.update({
            'Min Star Reward': 0,
        })
        self.config_description.update({
            'Min Star Reward': '編隊畫面「星芒奖励」低於這個數字，就依序換名稱有「镜像迷宫」的編隊，'
                               '直到夠高為止 (都不夠就用最高的那隊)。0 = 不換，用目前的編隊',
        })

    def run(self):
        self.open_mirror_dungeon()
        self.enter_dungeon()
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

    def enter_dungeon(self):
        status = ''.join(b.name for b in self.ocr_roi('md_status'))
        self.info_set('探索状态', status)
        if not vision.keywords_regex(TEXT['md_not_started']).search(status):
            raise TaskFailed(f'鏡像迷宮不是「探索前」({status})，正在進行中的迷宮目前不處理')
        button = self.wait_for(lambda: self.ocr_roi('md_enter', TEXT['enter']),
                               time_out=5, what='鏡像迷宮的「进入」')
        self.click_box(button, after_sleep=1.5)
        # 「是否进入西西弗之镜?」
        ok = self.wait_for(lambda: self.ocr_roi('md_popup_btn', TEXT['enter']),
                           time_out=8, what='「是否进入」視窗')
        self.click_box(ok, after_sleep=2.5)
        self.wait_for(self.on_team_screen, time_out=15, what='鏡像迷宮編隊畫面')

    # ---------- 編隊 ----------

    def on_team_screen(self):
        return self.ocr_roi('md_confirm', TEXT['confirm'])

    def read_star(self):
        return vision.parse_stylized_int(''.join(b.name for b in self.ocr_roi('md_star')))

    def current_team(self):
        return ''.join(b.name for b in self.ocr_roi('md_team_title'))

    def choose_team(self):
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
            self.click_box(team, after_sleep=1.2)
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
            self.click_box(best[1], after_sleep=1.2)
            self.info_set('編隊', best[1].name)
        self.info_set('星芒奖励', best[0])
        self.log_warning(f'沒有編隊的星芒奖励達到 {minimum}，改用最高的 ({best[0]})')

    def confirm_team(self):
        button = self.wait_for(self.on_team_screen, time_out=5, what='編隊畫面的「确认」')
        self.click_box(button, after_sleep=2)
        # 可能跳「编队人格当前平均等级低于推荐等级。是否进行战斗?」
        self.next_frame()
        warning = self.ocr_roi('md_popup_btn', TEXT['confirm'])
        if warning:
            self.log_info('編隊等級低於推薦等級，照樣進入')
            self.click_box(warning, after_sleep=2)
