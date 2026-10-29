from __future__ import annotations

from pathlib import Path

import cv2

from ok import BaseTask, Box

from src.lc import vision
from src.lc.layout import POS, ROI

TEMPLATE_DIR = Path('assets') / 'lc'


class TaskFailed(Exception):
    """畫面不對、等不到預期狀態時丟出，任務會停下來而不是繼續亂點。"""


class LimbusBaseTask(BaseTask):
    """所有 Limbus Company 任務共用的工具。

    原則：每一步都「確認畫面 -> 動作 -> 確認畫面變了」，認不出來就停。
    """

    _template_cache: dict[str, tuple[float, object]] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ---------- 模板 ----------

    @staticmethod
    def template_path(name: str) -> Path:
        return TEMPLATE_DIR / f'{name}.png'

    def has_template(self, name: str) -> bool:
        return self.template_path(name).is_file()

    def load_template(self, name: str):
        path = self.template_path(name)
        if not path.is_file():
            return None
        mtime = path.stat().st_mtime
        cached = self._template_cache.get(name)
        if cached and cached[0] == mtime:
            return cached[1]
        # cv2.imread 讀不了中文路徑，改用 imdecode
        import numpy as np
        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        self._template_cache[name] = (mtime, image)
        return image

    def find_template(self, name: str, roi=None, threshold: float = 0.8,
                      max_results: int = 1) -> list[Box]:
        template = self.load_template(name)
        frame = self.frame
        if template is None or frame is None:
            return []
        if roi is None:
            roi = ROI.get(name)
        matches = vision.find_template(frame, template, roi=roi, threshold=threshold,
                                       max_results=max_results)
        boxes = [Box(m.x, m.y, m.width, m.height, confidence=m.score, name=name) for m in matches]
        if boxes:
            self.draw_boxes(name, boxes, 'green')
        return boxes

    def require_template(self, name: str):
        if not self.has_template(name):
            raise TaskFailed(
                f'缺少模板 {self.template_path(name)}，請先用「擷取模板」任務建立它')

    # ---------- 點擊 / OCR ----------

    def click_pos(self, name: str, after_sleep: float = 1.0):
        x, y = POS[name]
        self.click_relative(x, y, after_sleep=after_sleep, name=name)

    def ocr_roi(self, roi_name: str, keywords=None):
        x0, y0, x1, y1 = ROI[roi_name]
        match = vision.keywords_regex(keywords) if keywords else None
        return self.ocr(x0, y0, x1, y1, match=match, name=roi_name)

    def wait_for(self, condition, time_out: float, what: str):
        """等某個條件成立；超時就丟 TaskFailed 並截圖留證據。"""
        result = self.wait_until(condition, time_out=time_out)
        if not result:
            self.screenshot(f'fail_{what}')
            raise TaskFailed(f'等不到：{what}')
        return result

    # ---------- 畫面判斷 ----------

    def is_home(self) -> bool:
        return bool(self.find_template('home_window', threshold=0.8))

    def go_home(self):
        """回到主畫面。有 home_window 模板時會確認，沒有就只點 Window 按鈕。"""
        if not self.has_template('home_window'):
            self.log_warning('沒有 home_window 模板，無法確認是否在主畫面，只點 Window 按鈕')
            self.click_pos('home_window', after_sleep=2)
            return
        for _ in range(6):
            self.next_frame()
            if self.is_home():
                return
            # 不在主畫面才按 ESC；在主畫面按 ESC 會跳出「離開遊戲」
            self.send_key('esc', after_sleep=1.5)
            self.next_frame()
            if self.is_home():
                return
            # 下方選單看得到時，直接點 Window 比較快
            self.click_pos('home_window', after_sleep=2)
        self.next_frame()
        if not self.is_home():
            self.screenshot('fail_go_home')
            raise TaskFailed('回不到主畫面')
