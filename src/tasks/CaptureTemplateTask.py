import cv2

from src.lc import vision
from src.lc.layout import CAPTURABLE_TEMPLATES, MANUAL_TEMPLATES
from src.tasks.LimbusBaseTask import TEMPLATE_DIR, LimbusBaseTask, TaskFailed

FULL_SCREENSHOT = '整張截圖 (自己裁 exp_enter 用)'


class CaptureTemplateTask(LimbusBaseTask):
    """從目前的遊戲畫面擷取模板圖片，存到 assets/lc/。

    固定位置的模板：先在遊戲裡切到對應畫面，選好名稱，按開始就會自動裁好存檔。
    位置不固定的模板 (exp_enter)：選「整張截圖」，再用小畫家裁出需要的部分。
    所有圖片都會換算成 1080p 大小存檔，之後換解析度不用重截。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '擷取模板'
        self.description = '先在遊戲切到對應畫面，再選模板名稱按開始'
        options = list(CAPTURABLE_TEMPLATES) + [FULL_SCREENSHOT]
        self.default_config.update({'Template': options[0]})
        self.config_type.update({'Template': {'type': 'drop_down', 'options': options}})
        lines = [f'{name}：{hint}' for name, (_, hint) in CAPTURABLE_TEMPLATES.items()]
        lines += [f'{name}：{hint}（用整張截圖自己裁）' for name, hint in MANUAL_TEMPLATES.items()]
        self.config_description.update({'Template': '\n'.join(lines)})

    @staticmethod
    def save_png(path, image):
        path.parent.mkdir(parents=True, exist_ok=True)
        ok, data = cv2.imencode('.png', image)
        if not ok:
            raise TaskFailed(f'存檔失敗 {path}')
        data.tofile(str(path))  # 用 tofile 才支援中文路徑

    def run(self):
        frame = self.next_frame()
        if frame is None:
            raise TaskFailed('抓不到遊戲畫面')
        height = frame.shape[0]
        choice = self.config.get('Template')

        if choice == FULL_SCREENSHOT:
            path = TEMPLATE_DIR / '_screen.png'
            self.save_png(path, vision.to_base_scale(frame, height))
            self.log_info(
                f'已存整張截圖到 {path.resolve()}。用小畫家打開，框選要的圖示 → 裁剪 → '
                f'另存成同資料夾的 exp_enter.png (只裁門的圖示，不要包含背景太多)',
                notify=True)
            return

        roi, hint = CAPTURABLE_TEMPLATES[choice]
        crop = vision.crop_rel(frame, roi)
        path = self.template_path(choice)
        self.save_png(path, vision.to_base_scale(crop, height))
        self.log_info(f'已存模板 {path.resolve()}（{hint}）', notify=True)
