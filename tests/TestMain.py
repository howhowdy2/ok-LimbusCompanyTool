"""確認任務可以被 ok-script 載入 (需要 Windows + 已安裝的依賴)：
python -m unittest tests.TestMain
"""
import importlib
import unittest

from ok.test.TaskTestCase import TaskTestCase

from src.config import config
from src.tasks.ExpLuxcavationTask import ExpLuxcavationTask


class TestRegisteredTasks(unittest.TestCase):
    def test_every_registered_task_imports(self):
        for module_name, class_name in config['onetime_tasks']:
            module = importlib.import_module(module_name)
            self.assertTrue(hasattr(module, class_name), f'{module_name}.{class_name}')


class TestExpLuxcavationTask(TaskTestCase):
    task_class = ExpLuxcavationTask
    config = config

    def test_default_config(self):
        self.assertEqual(1, self.task.default_config['Runs'])
        self.assertIn(self.task.default_config['Stage'], ExpLuxcavationTask.STAGE_OPTIONS)


if __name__ == '__main__':
    unittest.main()
