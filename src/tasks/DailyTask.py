from src.tasks.EnkephalinTask import EnkephalinTask
from src.tasks.ExpLuxcavationTask import MODE_BATTLE, MODE_SKIP, ExpLuxcavationTask
from src.tasks.LimbusBaseTask import LimbusBaseTask
from src.tasks.PassTask import PassTask
from src.tasks.ThreadLuxcavationTask import ThreadLuxcavationTask


class DailyTask(LimbusBaseTask):
    """一鍵日常：依序執行勾選的項目。每個項目的細節在它自己的任務頁面設定。

    采光要花「腦啡肽模組」，所以先把體力換成模組，再去打本。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '一鍵日常'
        self.description = '換體力 → 打纺锤本 (每日加成 3 次) → 打經驗本 → 領通行證獎勵'
        self.default_config.update({
            'Convert Enkephalin': True,
            'Run Thread Luxcavation': True,
            'Thread Runs': 3,
            'Run EXP Luxcavation': True,
            'EXP Runs': 1,
            'Skip Battle': True,
            'Claim Pass': True,
        })
        self.config_description.update({
            'Convert Enkephalin': '先把體力換成模組 (采光要花模組)',
            'Run Thread Luxcavation': '打纺锤本 (模式、關卡等其他設定沿用「打纺锤本」任務)',
            'Thread Runs': '日常打纺锤本的次數，1~10 (仍會受每日加成限制)',
            'Run EXP Luxcavation': '打經驗本 (模式、關卡等其他設定沿用「打經驗本」任務)',
            'EXP Runs': '日常打經驗本的次數，1~10',
            'Skip Battle': '日常打采光時用「跳过战斗」；關掉就用上次的編隊進入戰鬥',
            'Claim Pass': '最後領通行證獎勵 (要領哪些在「領通行證獎勵」任務裡設定)',
        })

    def run(self):
        if self.config.get('Convert Enkephalin'):
            self.run_task_by_class(EnkephalinTask)
        if self.config.get('Run Thread Luxcavation'):
            self.run_luxcavation(ThreadLuxcavationTask, self.config.get('Thread Runs', 3))
        if self.config.get('Run EXP Luxcavation'):
            self.run_luxcavation(ExpLuxcavationTask, self.config.get('EXP Runs', 1))
        if self.config.get('Claim Pass'):
            self.run_task_by_class(PassTask)
        self.go_home()
        self.log_info('日常完成', notify=True)

    def run_luxcavation(self, task_class, runs: int):
        """用日常自己的次數和模式跑采光任務，跑完還原，單獨執行時才會用回任務自己的設定。"""
        task = self.get_task_by_class(task_class)
        task.runs_override = runs
        task.mode_override = MODE_SKIP if self.config.get('Skip Battle', True) else MODE_BATTLE
        try:
            self.run_task_by_class(task_class)
        finally:
            task.runs_override = None
            task.mode_override = None
