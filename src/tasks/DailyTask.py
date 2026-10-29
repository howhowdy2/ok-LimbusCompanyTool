from src.tasks.EnkephalinTask import EnkephalinTask
from src.tasks.ExpLuxcavationTask import ExpLuxcavationTask
from src.tasks.LimbusBaseTask import LimbusBaseTask


class DailyTask(LimbusBaseTask):
    """一鍵日常：依序執行勾選的項目。每個項目的細節在它自己的任務頁面設定。

    順序是「先打經驗本、再換體力」：經驗本要花體力，先換的話就沒體力打本了。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '一鍵日常'
        self.description = '打經驗本 → 把剩下的體力換成模組'
        self.default_config.update({
            'Run EXP Luxcavation': True,
            'Convert Enkephalin': True,
        })
        self.config_description.update({
            'Run EXP Luxcavation': '打經驗本 (次數、關卡在「打經驗本」任務裡設定)',
            'Convert Enkephalin': '最後把剩下的體力換成模組',
        })

    def run(self):
        if self.config.get('Run EXP Luxcavation'):
            self.run_task_by_class(ExpLuxcavationTask)
        if self.config.get('Convert Enkephalin'):
            self.run_task_by_class(EnkephalinTask)
        self.go_home()
        self.log_info('日常完成', notify=True)
