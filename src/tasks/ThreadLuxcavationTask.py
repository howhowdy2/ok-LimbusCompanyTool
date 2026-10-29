from src.lc import vision
from src.lc.layout import TEXT
from src.tasks.ExpLuxcavationTask import LuxcavationTask


class ThreadLuxcavationTask(LuxcavationTask):
    """纺锤本：每天只開一個罪孽的關卡 (其他卡片寫「于周X开放」)，上方有「每日加成 N/3」。

    預設打 3 次，並且只打到每日加成用完為止。
    """

    TAB_TEXT = TEXT['lux_thread_tab']
    TITLE = '纺锤本'
    DEFAULT_RUNS = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '打纺锤本'
        self.description = '跳過戰鬥打采光「纺锤」，預設 3 次 (每日加成)'
        self.default_config.update({'Only Daily Bonus': True})
        self.config_description.update({
            'Runs': '要打幾次，1~10。每日加成一天 3 次',
            'Only Daily Bonus': '只打還剩下的每日加成次數 (例如今天已打 1 次，就只打 2 次)',
        })

    def read_daily_bonus(self):
        """讀「每日加成 0/3」，回傳 (已用, 上限)。"""
        text = ''.join(b.name for b in self.ocr_roi('lux_bonus'))
        if not vision.keywords_regex(TEXT['daily_bonus']).search(text):
            return None
        return vision.parse_daily_bonus(text)

    def planned_runs(self, runs: int) -> int:
        bonus = self.read_daily_bonus()
        self.info_set('每日加成', f'{bonus[0]}/{bonus[1]}' if bonus else '讀不到')
        if not self.config.get('Only Daily Bonus') or bonus is None:
            return runs
        remaining = max(0, bonus[1] - bonus[0])
        if remaining == 0:
            self.log_info('今天的每日加成已經用完，不打纺锤本')
        elif remaining < runs:
            self.log_info(f'每日加成剩 {remaining} 次，改打 {remaining} 次')
        return min(runs, remaining)

    def available_buttons(self, buttons):
        """只留有「连续进行」的卡片：還沒開放的卡片上面是「于周X开放」，沒有连续进行。"""
        headers = self.ocr_roi('lux_repeat', TEXT['lux_repeat'])
        open_cards = []
        for button in buttons:
            cx = button.x + button.width / 2
            if any(abs(h.x + h.width / 2 - cx) < self.width * 0.13 for h in headers):
                open_cards.append(button)
        return open_cards
