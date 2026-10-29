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
    'pass_banner': (0.84, 0.33),        # 主畫面右上「SEASON N LIMBUS PASS」橫幅
    'pass_daily_tab': (0.212, 0.355),   # 通行证任务左邊直排的「日常任务」
    'pass_weekly_tab': (0.212, 0.555),  # 「周常任务」
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
    'lux_repeat': (0.22, 0.28, 0.98, 0.39),       # 每張關卡卡片的「连续进行×N」(纺锤卡片比較高)
    'lux_modules': (0.215, 0.865, 0.265, 0.912),   # 左下角腦啡肽模組數量
    'lux_bonus': (0.36, 0.02, 0.54, 0.09),         # 纺锤上方「每日加成 0/3」(不要包到右邊「剩余11小时」)
    'lux_bonus_num': (0.47, 0.015, 0.545, 0.095),  # 只有「0/3」那幾個字
    # 纺锤點下去後的「选择关卡」視窗
    'level_title': (0.38, 0.12, 0.62, 0.22),
    'level_actions': (0.55, 0.30, 0.72, 0.80),     # 每一列右邊的「跳过战斗」/「进入」
    # 通行證
    'pass_banner': (0.72, 0.24, 0.96, 0.30),       # 橫幅上的「LIMBUS PASS」小字
    'pass_tabs': (0.10, 0.03, 0.36, 0.12),         # 「战斗通行证 / 通行证任务」
    'pass_missions': (0.30, 0.26, 0.44, 0.83),     # 任務名稱 (只取左半邊的字)
    'pass_claim_all': (0.58, 0.77, 0.72, 0.86),    # 「全部领取」
    # 鏡像迷宮
    'drive_md': (0.29, 0.40, 0.41, 0.49),          # Drive 選單的「镜像迷宫」
    'md_status': (0.70, 0.19, 0.90, 0.245),        # 「探索状态  探索前」
    'md_enter': (0.82, 0.64, 0.91, 0.73),          # 右下大顆「进入」
    'md_popup_btn': (0.50, 0.62, 0.70, 0.73),      # 「是否进入…?」/ 等級警告視窗右邊的按鈕
    'md_teams': (0.05, 0.40, 0.15, 0.76),          # 編隊畫面左邊的編隊名稱清單
    'md_team_title': (0.16, 0.14, 0.26, 0.20),     # 目前選到的編隊名稱
    'md_star': (0.875, 0.715, 0.955, 0.78),        # 「星芒奖励 96」的數字
    'md_confirm': (0.84, 0.77, 0.95, 0.86),        # 右下「确认」
    'md_dialog': (0.20, 0.25, 0.75, 0.85),         # 迷宮進度 / 終止確認 / 探索結束獎勵 視窗 (不含右下的进入)
    # 鏡像迷宮：星之恩惠
    'grace_title': (0.08, 0.02, 0.32, 0.10),       # 「西西弗的星之恩惠」
    'grace_popup': (0.40, 0.27, 0.60, 0.34),       # 「要选择此效果吗?」
    'grace_popup_btn': (0.50, 0.70, 0.66, 0.78),   # 彈窗右邊的「确认」
    'grace_done': (0.89, 0.89, 0.97, 0.97),        # 右下「完成」
    # 鏡像迷宮：選擇 E.G.O 饰品
    'gift_title': (0.60, 0.18, 0.76, 0.26),        # 「选择E.G.O饰品」
    'gift_keywords': (0.12, 0.20, 0.56, 0.60),     # 左邊關鍵字分類的標題
    'gift_count': (0.86, 0.78, 0.92, 0.845),       # 「选择 0/1」的數字
    'gift_select': (0.79, 0.78, 0.86, 0.845),      # 「选择」
    'gift_got_title': (0.38, 0.21, 0.62, 0.29),    # 「获得E.G.O饰品!」
    'gift_got_name': (0.25, 0.56, 0.39, 0.68),     # 橘色框裡的饰品名稱
    'gift_got_ok': (0.42, 0.70, 0.58, 0.78),       # 「确认」
    # 鏡像迷宮：E.G.O饰品观测
    'observe_title': (0.09, 0.02, 0.30, 0.10),     # 「E.G.O饰品观测」
    'observe_count': (0.86, 0.765, 0.91, 0.83),    # 「选择 0/3」的數字
    'observe_select': (0.81, 0.765, 0.88, 0.83),   # 「选择」
    'observe_reject': (0.67, 0.765, 0.77, 0.83),   # 「拒绝饰品」
    # 鏡像迷宮：主題卡包
    'pack_title': (0.38, 0.11, 0.62, 0.20),        # 「选择1层主题卡包」
    # 戰鬥中右下角的「胜率 / 伤害」按鈕 (行動槽變多時會往右移，範圍抓寬一點)
    'battle_hud': (0.72, 0.71, 0.90, 0.85),
    # 結算畫面 (战斗胜利)
    'result_title': (0.65, 0.10, 0.98, 0.26),
    'result_confirm': (0.80, 0.72, 0.97, 0.86),
}

# 通行證任務：可以領取的那一列背景是棕橘色，其他是黑色。
# 在任務名稱右邊這塊取樣 (相對座標的 x 範圍)，紅色通道平均 > PASS_CLAIMABLE_MIN_RED 就算可領
PASS_ROW_SAMPLE_X = (0.445, 0.46)
PASS_CLAIMABLE_MIN_RED = 40


# 星之恩惠：由左到右、上到下 1~10
GRACE_NAMES = ['起始之星', '层积星云', '星际旅行', '倾落的流星雨', '双星商店',
               '卫星商店', '星云的宠爱', '星芒的引导', '偶然的彗星', '全面的可能性']
GRACE_COL_X = (0.174, 0.329, 0.484, 0.639, 0.794)   # 卡片中心
GRACE_ROW_Y = (0.274, 0.606)                        # 卡片標題那一列 (點這裡 = 0 級)
GRACE_PLUS_Y = (0.482, 0.813)                       # 「+」「++」按鈕那一列
GRACE_PLUS_DX = -0.027                              # 「+」在卡片中心左邊
GRACE_PLUSPLUS_DX = 0.036                           # 「++」在卡片中心右邊

# E.G.O 饰品關鍵字 (最後兩個要往下捲才看得到)
GIFT_KEYWORDS = ['烧伤', '流血', '震颤', '破裂', '沉沦', '呼吸法', '充能', '斩击', '突刺', '打击']
GIFT_CARD_X = 0.79                                  # 右邊三個饰品卡片的中心
GIFT_CARD_Y = (0.37, 0.52, 0.67)
GIFT_SCROLL_ARROW = (0.341, 0.826)                  # 左邊清單下方的 ▼


# E.G.O饰品观测：上面 11 個分頁，左邊清單依 III / II / I 分區，每列 8 個
OBSERVE_TYPES = GIFT_KEYWORDS + ['泛用']
OBSERVE_TAB_X = (0.088, 0.137, 0.186, 0.234, 0.282, 0.331, 0.379, 0.428, 0.476, 0.524, 0.573)
OBSERVE_TAB_Y = 0.262
OBSERVE_COL_X0 = 0.1025          # 第 1 欄饰品中心
OBSERVE_COL_DX = 0.065           # 每欄間距
OBSERVE_ROW_DY0 = 0.086          # 等級分隔條中心 → 第 1 列饰品中心
OBSERVE_ROW_DY = 0.110           # 每列間距
OBSERVE_VISIBLE_BOTTOM = 0.80    # 饰品中心超過這裡就要往下捲


# 「连续进行」下拉面板
#   ▲/▼ 開關：用 vision.find_bright_blob 在文字右邊找白色三角形
#   展開後那一列 (1« − [數字] + »10) 先用 OCR 找「《」和「+」，找不到才用下面的位移
#   位移都相對於 ▲/▼ 的中心 (用經驗本卡片量的)
class REPEAT:
    toggle_search_dx = 0.08   # ▲ 在文字右邊多遠以內
    row_dy = 0.044            # 展開那一列在 ▲ 下方多少
    min_dx = -0.152           # 1« 在 ▲ 左邊多少
    plus_dx = -0.018          # 綠色 + 在 ▲ 左邊多少


# OCR 關鍵字：英文版和 LLC 簡中漢化都列上去 (繁體會被自動轉成簡體)
TEXT = {
    'luxcavation': ['Luxcavation', '采光'],
    'to_battle': ['To Battle', '开始战斗', '出击'],
    'confirm': ['Confirm', '确认', '确定'],
    'continue': ['Continue', '继续', '点击'],
    'lux_exp_tab': ['EXP', '经验'],
    'lux_thread_tab': ['Thread', '纺锤'],
    'daily_bonus': ['Daily', '每日加成'],
    'level_title': ['Select', '选择关卡'],
    'lux_enter': ['Enter', '进入'],
    'lux_skip': ['Skip', '跳过战斗'],
    'lux_repeat': ['Repeat', '连续进行'],
    'enk_owned': ['拥有', 'Own'],
    'not_enough': ['不足', 'Not enough', 'Insufficient'],
    'win_rate': ['Win Rate', 'WinRate', '胜率'],
    'pass_banner': ['LIMBUS PASS', 'PASS'],
    'pass_missions_tab': ['Pass Missions', '通行证任务'],
    'pass_rewards_tab': ['Battle Pass', '战斗通行证'],
    'claim_all': ['Claim All', '全部领取'],
    'mirror_dungeon': ['Mirror Dungeon', '迷宫', '迷宮'],  # OCR 有時讀成繁體
    'md_not_started': ['探索前', 'Not Started'],
    'md_continue': ['Continue', '继续'],
    'md_abort': ['Abort', '终止探索'],
    'md_give_up': ['Give Up', '放弃奖励'],
    'grace_title': ['Grace', '星之恩惠'],
    'grace_popup': ['要选择此效果', 'Select this'],
    'grace_done': ['Done', '完成'],
    'gift_title': ['E.G.O', '饰品'],
    'gift_got': ['获得', 'Acquired'],
    'select': ['Select', '选择'],
    'reject': ['Refuse', '拒绝'],
    'observe_title': ['Observation', '观测'],
    'pack_title': ['Theme Pack', '主题卡包'],
    'enter': ['Enter', '进入'],
    'victory': ['Victory', '胜利'],
    'defeat': ['Defeat', '失败'],
}

# 可以用「擷取模板」任務自動截的模板：名稱 -> (要截的區域, 說明)
CAPTURABLE_TEMPLATES = {
    'home_window': (ROI['home_window'], '停在主畫面 (下方 Window 按鈕是亮紅色)'),
    'enk_max': (ROI['enk_max'], '打開換體力面板 (看得到 >> 全部換成模組的按鈕)'),
    'team_screen': (ROI['team_screen'], '停在進入關卡後的編隊畫面'),
}
