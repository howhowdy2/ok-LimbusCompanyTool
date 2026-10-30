import cv2

from src.lc import vision
from src.lc.layout import ROI, TEXT
from src.tasks.ExpLuxcavationTask import LEVEL_OPTIONS, LuxcavationTask


class ThreadLuxcavationTask(LuxcavationTask):
    """纺锤本：每天只開一個罪孽的關卡 (其他卡片寫「于周X开放」)。

    上方「每日加成 N/3」的 N 是「今天還剩幾次」：3/3 = 還沒打，0/3 = 用完了。
    預設打 3 次，並且只打到每日加成用完為止。
    """

    TAB_TEXT = TEXT['lux_thread_tab']
    TITLE = '纺锤本'
    DEFAULT_RUNS = 3
    SKIP_COST = 4    # 连续进行×3 時「选择关卡」顯示「跳过战斗 -12」= 每次 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '打纺锤本'
        self.description = '跳過戰鬥打采光「纺锤」，預設 3 次 (每日加成)'
        self.default_config.update({'Only Daily Bonus': True, 'Level': LEVEL_OPTIONS[0]})
        self.config_type.update({'Level': {'type': 'drop_down', 'options': LEVEL_OPTIONS}})
        self.config_description.update({
            'Level': '點下去後「选择关卡」視窗要選哪一列 (越下面等級越高)',
            'Runs': '要打幾次，1~10。每日加成一天 3 次',
            'Only Daily Bonus': '只打還剩下的每日加成次數 (例如顯示 2/3，就只打 2 次；0/3 就不打)',
        })

    def read_daily_bonus(self):
        """讀「每日加成 N/3」，回傳 (剩餘次數, 上限)。

        斜線那幾個字很花，OCR 常讀錯：先讀整塊，讀不到再把數字部分加框、放大重讀幾次。
        """
        text = ''.join(b.name for b in self.ocr_roi('lux_bonus'))
        if not vision.keywords_regex(TEXT['daily_bonus']).search(text):
            return None  # 不在纺锤分頁
        found = vision.parse_daily_bonus(text)
        if found:
            return found
        crop = vision.crop_rel(self.frame, ROI['lux_bonus_num'])
        for scale in (1, 3, 2):
            image = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            image = cv2.copyMakeBorder(image, 20, 20, 20, 20, cv2.BORDER_REPLICATE)
            boxes = self.ocr(frame=image, threshold=0.3)
            found = vision.parse_daily_bonus(''.join(b.name for b in boxes))
            if found:
                return found
        return None

    def read_daily_bonus_retry(self, time_out: float = 5):
        """剛切到纺锤分頁時上方的字還在淡入，多讀幾次。"""
        import time
        start = time.time()
        while time.time() - start < time_out:
            self.next_frame()
            found = self.read_daily_bonus()
            if found:
                return found
            self.sleep(0.7)
        return None

    def bonus_from_panel(self):
        """展開第一張開放卡片的「连续进行」，讀下面的「可适用N次每日加成」，再收起來。"""
        buttons = self.available_buttons(self.stage_buttons(skip=True))
        if not buttons:
            return None
        header = self.repeat_header(buttons[0])
        toggle = self.find_toggle(header) if header else None
        if toggle is None:
            return None
        self.click_px(toggle, after_sleep=0.8)
        self.next_frame()
        w, h = self.width, self.height
        boxes = self.ocr_px(int(header.x - 0.12 * w), int(toggle[1] + 0.08 * h),
                            int(toggle[0] + 0.03 * w), int(toggle[1] + 0.2 * h), ['次', '加成'])
        self.click_px(toggle, after_sleep=0.6)
        for b in boxes:
            n = vision.parse_bonus_hint(b.name)
            if n is not None:
                return n, 3
        return None

    def planned_runs(self, runs: int) -> int:
        bonus = self.read_daily_bonus_retry()
        if bonus is None:
            bonus = self.bonus_from_panel()
            if bonus:
                self.log_info(f'上方讀不到，從「可适用{bonus[0]}次每日加成」讀到')
        self.info_set('每日加成', f'{bonus[0]}/{bonus[1]}' if bonus else '讀不到')
        if not self.config.get('Only Daily Bonus') or bonus is None:
            return runs
        remaining = bonus[0]  # N/3 的 N 就是剩下的次數
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
