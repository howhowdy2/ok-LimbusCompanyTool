"""Limbus Company 畫面上固定元素的位置。

全部用「相對座標」(0~1)，所以 1080p、1440p、4K 都能用同一組數字，
前提是遊戲畫面是 16:9。

數字是按鈕在 16:9 畫面上的位置量出來的。如果遊戲改版後位置跑掉，
在 ok-script 的 debug 模式截一張圖、量出新位置，改這裡就好。
"""

# 按鈕中心點 (x, y)：拿來點擊
POS = {
    'home_window': (0.645, 0.883),      # 下方選單「Window」(回主畫面)
    'home_drive': (0.766, 0.878),       # 下方選單「Drive」(出擊選單)
    'enkephalin_box': (0.246, 0.890),   # 主畫面的腦啡肽(體力)圖示，點開換體面板
    'enk_max': (0.630, 0.456),          # 換體面板：全部換成模組(>>)
    'enk_confirm': (0.562, 0.740),      # 換體面板：勾勾確認
    'enk_cancel': (0.380, 0.740),       # 換體面板：叉叉關閉
    'luxcavation': (0.352, 0.278),      # Drive 選單裡的「Luxcavation / 采光」
    'to_battle': (0.896, 0.815),        # 編隊畫面「To Battle!」
    'back': (0.075, 0.062),             # 左上返回鍵
}

# 區域 (x0, y0, x1, y1)：拿來做 OCR 或限制模板比對的搜尋範圍
ROI = {
    'home_window': (0.624, 0.863, 0.665, 0.903),
    'enk_max': (0.619, 0.435, 0.641, 0.478),
    'enk_owned': (0.56, 0.36, 0.66, 0.42),         # 補充腦啡肽面板「拥有 N」(模組數量)
    'enk_warning': (0.40, 0.65, 0.60, 0.71),       # 面板上的紅字「脑啡肽不足。」
    'luxcavation': (0.28, 0.24, 0.43, 0.32),
    'to_battle': (0.83, 0.77, 0.96, 0.86),
    'team_screen': (0.924, 0.227, 0.951, 0.266),   # 編隊畫面右上角的圖示
    'lower_half': (0.0, 0.5, 1.0, 1.0),
    'center': (0.2, 0.2, 0.8, 0.85),
    # 經驗本列表 (用實際遊戲截圖量的)
    'lux_tabs': (0.04, 0.30, 0.20, 0.50),          # 左邊「经验 / 纺锤」分頁
    'lux_enter': (0.22, 0.63, 0.98, 0.69),         # 每張關卡卡片的「进入」
    'lux_skip': (0.22, 0.685, 0.98, 0.745),        # 每張關卡卡片的「跳过战斗」
    'lux_repeat': (0.22, 0.31, 0.98, 0.39),       # 每張關卡卡片的「连续进行×N」
    'lux_modules': (0.215, 0.865, 0.265, 0.912),   # 左下角腦啡肽模組數量
    # 結算畫面 (战斗胜利)
    'result_title': (0.65, 0.10, 0.98, 0.26),
    'result_confirm': (0.80, 0.72, 0.97, 0.86),
}

# 「连续进行」的 ▲ 按鈕，相對於同一張卡片「进入」按鈕中心的位置
REPEAT_UP_OFFSET_X = 0.100
REPEAT_UP_Y = 0.353

# OCR 關鍵字：英文版和 LLC 簡中漢化都列上去 (繁體會被自動轉成簡體)
TEXT = {
    'luxcavation': ['Luxcavation', '采光'],
    'to_battle': ['To Battle', '开始战斗', '出击'],
    'confirm': ['Confirm', '确认', '确定'],
    'continue': ['Continue', '继续', '点击'],
    'lux_exp_tab': ['EXP', '经验'],
    'lux_enter': ['Enter', '进入'],
    'lux_skip': ['Skip', '跳过战斗'],
    'lux_repeat': ['Repeat', '连续进行'],
    'enk_owned': ['拥有', 'Own'],
    'not_enough': ['不足', 'Not enough', 'Insufficient'],
    'victory': ['Victory', '胜利'],
    'defeat': ['Defeat', '失败'],
}

# 可以用「擷取模板」任務自動截的模板：名稱 -> (要截的區域, 說明)
CAPTURABLE_TEMPLATES = {
    'home_window': (ROI['home_window'], '停在主畫面 (下方 Window 按鈕是亮紅色)'),
    'enk_max': (ROI['enk_max'], '打開換體力面板 (看得到 >> 全部換成模組的按鈕)'),
    'team_screen': (ROI['team_screen'], '停在進入關卡後的編隊畫面'),
}
