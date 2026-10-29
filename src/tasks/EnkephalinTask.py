from src.lc import vision
from src.lc.layout import TEXT
from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed


class EnkephalinTask(LimbusBaseTask):
    """把目前的腦啡肽(體力)全部換成腦啡肽模組，避免體力溢出浪費。

    只用「制作模块」分頁，不會碰「使用狂气」。
    用面板上「拥有 N」的模組數量確認有沒有換成功：體力的「5/145」字體太花，OCR 常讀錯。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '換體力 (腦啡肽 → 模組)'
        self.description = '回主畫面，打開補充腦啡肽面板，把體力全部做成模組'

    def run(self):
        self.convert()

    def read_owned_modules(self):
        # 不加關鍵字過濾：「拥有」和「287」有時會被拆成兩個框
        text = ''.join(b.name for b in self.ocr_roi('enk_owned'))
        if not vision.keywords_regex(TEXT['enk_owned']).search(text):
            return None
        return vision.parse_int(text)

    def panel_open(self):
        return self.read_owned_modules() is not None

    def close_panel(self):
        self.next_frame()
        if self.panel_open():
            self.click_pos('enk_cancel', after_sleep=1.0)

    def convert(self) -> bool:
        self.go_home()
        self.click_pos('enkephalin_box', after_sleep=1.0)
        self.wait_for(self.panel_open, time_out=8, what='補充腦啡肽面板')

        before = self.read_owned_modules()
        self.info_set('模組 (換之前)', before)

        self.click_pos('enk_max', after_sleep=0.8)   # » 調到最多
        self.next_frame()
        if self.ocr_roi('enk_warning', TEXT['not_enough']):
            self.log_info('體力不足 20，不用換')
            self.close_panel()
            return False

        self.click_pos('enk_confirm', after_sleep=2)
        self.next_frame()
        after = self.read_owned_modules()
        self.info_set('模組 (換之後)', after)
        self.close_panel()

        if after is None or before is None:
            self.log_warning('讀不到模組數量，無法確認有沒有換成功')
            return True
        if after <= before:
            self.screenshot('fail_enkephalin')
            raise TaskFailed(f'按了確認但模組沒有增加 ({before} -> {after})')
        self.log_info(f'換體力完成，模組 {before} → {after} (+{after - before})')
        return True
