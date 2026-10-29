from src.tasks.EnkephalinTask import EnkephalinTask
from src.tasks.ExpLuxcavationTask import ExpLuxcavationTask
from src.tasks.LimbusBaseTask import LimbusBaseTask


class DailyTask(LimbusBaseTask):
    """一鍵日常：依序執行勾選的項目。每個項目的細節在它自己的任務頁面設定。

    經驗本花的是「腦啡肽模組」，所以先把體力換成模組，再去打本。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '一鍵日常'
        self.description = '換體力 → 打經驗本'
        self.default_config.update({
            'Convert Enkephalin': True,
            'Run EXP Luxcavation': True,
        })
        self.config_description.update({
            'Convert Enkephalin': '先把體力換成模組 (經驗本要花模組)',
            'Run EXP Luxcavation': '打經驗本 (模式、次數、關卡在「打經驗本」任務裡設定)',
        })

    def run(self):
        if self.config.get('Convert Enkephalin'):
            self.run_task_by_class(EnkephalinTask)
        if self.config.get('Run EXP Luxcavation'):
            self.run_task_by_class(ExpLuxcavationTask)
        self.go_home()
        self.log_info('日常完成', notify=True)
