from src.tasks.LimbusBaseTask import LimbusBaseTask, TaskFailed


class EnkephalinTask(LimbusBaseTask):
    """把目前的腦啡肽(體力)全部換成腦啡肽模組，避免體力溢出浪費。

    不會使用狂氣(付費貨幣)。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = '換體力 (腦啡肽 → 模組)'
        self.description = '回主畫面，打開換體面板，把體力全部換成模組'
        self.default_config.update({
            'Minimum Enkephalin': 20,
        })
        self.config_description.update({
            'Minimum Enkephalin': '體力少於這個數字就不換 (一個模組需要 20 體力)',
        })

    def run(self):
        self.convert()

    def open_panel(self):
        self.click_pos('enkephalin_box', after_sleep=1.0)
        # 面板打開的判斷：讀得到「目前/上限」，或看得到 >> 按鈕(有模板時)
        self.wait_for(
            lambda: self.read_enkephalin() or (self.has_template('enk_max') and self.find_template('enk_max')),
            time_out=8, what='換體面板')

    def close_panel(self):
        self.click_pos('enk_cancel', after_sleep=1.0)

    def convert(self) -> bool:
        self.go_home()
        self.open_panel()

        before = self.read_enkephalin()
        self.info_set('換體前', f'{before[0]}/{before[1]}' if before else '讀不到')
        minimum = self.config.get('Minimum Enkephalin', 20)
        if before and before[0] < minimum:
            self.log_info(f'體力 {before[0]} 少於 {minimum}，不用換')
            self.close_panel()
            return False

        self.click_pos('enk_max', after_sleep=0.5)
        self.click_pos('enk_confirm', after_sleep=1.5)
        self.next_frame()

        # 換完面板通常還開著，讀一次確認體力真的變少了
        after = self.read_enkephalin()
        self.info_set('換體後', f'{after[0]}/{after[1]}' if after else '讀不到')
        self.close_panel()

        if before and after and after[0] >= before[0]:
            self.screenshot('fail_enkephalin')
            raise TaskFailed(f'換體後體力沒有減少 ({before[0]} -> {after[0]})')
        self.log_info('換體力完成')
        return True
