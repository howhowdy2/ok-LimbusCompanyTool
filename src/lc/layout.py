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
    'pack_names': (0.08, 0.58, 0.92, 0.68),        # 五個卡包下方的名稱
    'pack_mode': (0.69, 0.03, 0.79, 0.10),         # 右上「HARD」(普通模式時不是 HARD)
    'pack_refresh': (0.80, 0.03, 0.91, 0.10),      # 「刷新 3/3」
    'pack_observe_btn': (0.10, 0.03, 0.21, 0.10),  # 左上「主题卡包观测」
    'pack_obs_title': (0.20, 0.13, 0.45, 0.22),    # 「观测第1阶层主题卡包」
    'pack_obs_list': (0.44, 0.25, 0.93, 0.83),     # 觀測視窗右邊的卡包清單
    'pack_obs_ok': (0.53, 0.76, 0.71, 0.85),       # 觀測視窗「确认」
    'pack_replace': (0.33, 0.33, 0.67, 0.42),      # 「主题卡包"A"将被"B"替换。」(確認按鈕用 md_popup_btn)
    'map_title': (0.02, 0.11, 0.22, 0.18),         # 樓層地圖左上「正在探索第1层」
    # 鏡像迷宮商店
    'shop_title': (0.15, 0.14, 0.26, 0.21),        # 左上「商店」
    'shop_leave': (0.82, 0.86, 0.96, 0.94),        # 右下「离开」
    'shop_money': (0.43, 0.16, 0.50, 0.22),        # 目前經費 (中間偏左的 656)
    'shop_refresh_cost': (0.73, 0.20, 0.83, 0.24), # 「刷新」下面的花費
    'shop_items': (0.42, 0.42, 0.92, 0.72),        # 8 格饰品的價格和名稱
    'shop_buy_title': (0.33, 0.21, 0.56, 0.27),    # 「购买E.G.O饰品」
    'shop_buy_btn': (0.51, 0.63, 0.66, 0.71),      # 「购买」
    'shop_sub_title': (0.38, 0.10, 0.62, 0.19),    # 「强化E.G.O饰品」「合成E.G.O饰品」「合成 - 关键词选择」
    'enhance_money': (0.73, 0.10, 0.88, 0.18),     # 強化畫面右上的經費 (501 ▸ 451)
    'enhance_cost': (0.17, 0.68, 0.42, 0.75),      # 「是否消耗50经费进行强化?」
    # 戰鬥後的獎勵
    'reward_card_title': (0.28, 0.14, 0.56, 0.24),  # 「选择遭遇战奖励卡」
    'reward_card_count': (0.70, 0.15, 0.82, 0.23),  # 「可选择 0/1」
    'reward_card_text': (0.10, 0.50, 0.92, 0.60),   # 卡片下方的說明
    'gift_reward_marker': (0.15, 0.57, 0.92, 0.62), # 每張卡上的「追加的苦难」
    'gift_reward_level': (0.09, 0.61, 0.91, 0.66),  # 「敌方等级增加 +2」
    'gift_reward_aff': (0.09, 0.66, 0.91, 0.73),    # 苦難名稱和效果
    'gift_reward_btns': (0.66, 0.76, 0.97, 0.85),   # 「拒绝饰品」「选择 0/2」
    # 事件的判定
    'judge_title': (0.64, 0.41, 0.87, 0.48),       # 「选择一位罪人来进行判定:」
    'judge_levels': (0.03, 0.84, 0.69, 0.877),     # 罪人頭上的「极高 / 高 / 普通 / 低 / 极低」
    'gift_tag_row': (0.05, 0.19, 0.95, 0.25),      # 每張饰品卡右上的「获得E.G.O饰品」標籤
    'parallel_title': (0.30, 0.22, 0.70, 0.55),    # 第 5 層打完的「平行叠加模式」
    'finish_title': (0.07, 0.12, 0.31, 0.23),      # 「探索完成」
    'finish_claim': (0.80, 0.78, 0.97, 0.88),      # 「领取奖励」
    'weekly_bonus': (0.30, 0.42, 0.70, 0.54),      # 「要消耗"每周加成"以领取额外奖励吗?」
    'node_enter': (0.80, 0.69, 0.97, 0.82),        # 點節點後右下的「进入」
    'event_skip': (0.80, 0.84, 0.97, 0.95),        # 事件畫面右下「SKIP」
    'event_options_title': (0.52, 0.13, 0.70, 0.23),   # 「选项」
    'event_options': (0.54, 0.22, 0.92, 0.85),     # 選項框 (一個選項 = 大字 + 下面的小字)
    # 戰鬥中右下角的「胜率 / 伤害」按鈕 (行動槽變多時會往右移，範圍抓寬一點)
    'battle_hud': (0.50, 0.70, 0.95, 0.87),        # 「胜率 / 伤害」：上場人數少時在中間偏右，人多時往右移
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


# 主題卡包：卡包卡片中心 x 用名稱位置；選擇 = 從卡片往下拖
PACK_DRAG_FROM_Y = 0.45
PACK_DRAG_TO_Y = 0.92
PACK_OBS_ICON_DX = 0.045         # 觀測後卡包右上角的 ↻ 在名稱中心右邊
PACK_OBS_ICON_Y = 0.305
PACK_MODE_ARROW = (0.666, 0.064) # 難度切換箭頭
PACK_OBSERVE_BTN = (0.163, 0.064)
PACK_REFRESH_BTN = (0.835, 0.064)       # 右上「刷新」按鈕 (OCR 找不到字時用)


# 「连续进行」下拉面板
#   ▲/▼ 開關：用 vision.find_bright_blob 在文字右邊找白色三角形
#   展開後那一列 (1« − [數字] + »10) 先用 OCR 找「《」和「+」，找不到才用下面的位移
#   位移都相對於 ▲/▼ 的中心 (用經驗本卡片量的)
class REPEAT:
    toggle_search_dx = 0.08   # ▲ 在文字右邊多遠以內
    row_dy = 0.044            # 展開那一列在 ▲ 下方多少
    min_dx = -0.152           # 1« 在 ▲ 左邊多少
    plus_dx = -0.018          # 綠色 + 在 ▲ 左邊多少


# 鏡像迷宮樓層地圖
MAP_CENTER = (0.50, 0.50)   # 在這裡滾滾輪縮小地圖
MAP_ZOOM_SCROLLS = 3        # 縮小時滾幾輪 (每輪 -10 格，縮到最小為止)
# 節點類型：設定裡的名稱 -> assets/lc 裡的模板檔名 (map_xxx.png，存的是節點中間的圖示)
NODE_TYPES = {
    '事件': 'map_event',
    '戰鬥': 'map_battle',
    '異想體': 'map_abno',
    '精英戰鬥': 'map_elite',
    '商店': 'map_shop',
    '休息': 'map_rest',
    '頭目': 'map_boss',
}
NODE_UNKNOWN = '未知'
NODE_ENTER_BTN = (0.885, 0.754)     # 「进入」(OCR 找不到時點這裡)
EVENT_SKIP_BTN = (0.885, 0.898)     # 「SKIP」(沒亮也照點，點到出現選項)
JUDGE_SINNER_X0, JUDGE_SINNER_DX = 0.061, 0.054   # 12 個罪人頭像中心 x
JUDGE_SINNER_Y = 0.907
EVENT_OPTION_GAP = 0.07             # 同一個選項框裡兩行字的最大間距 (畫面高度比例)
NODE_MATCH_THRESHOLD = 0.6


# 鏡像迷宮商店 (相對座標，量自 2560x1440 截圖)
SHOP_ITEM_X = (0.4875, 0.6075, 0.7275, 0.8475)   # 8 格饰品圖示中心，4 欄 x 2 列
SHOP_ITEM_Y = (0.367, 0.58)
SHOP_PRICE_DY = (0.05, 0.097)      # 價格在圖示下方這個範圍
SHOP_REFRESH_BTN = (0.793, 0.169)
SHOP_LEAVE_BTN = (0.885, 0.90)
SHOP_ENHANCE_BTN = (0.125, 0.544)
SHOP_FUSE_BTN = (0.2165, 0.544)
SHOP_BUY_BTN = (0.585, 0.673)
SHOP_CLOSE_BTN = (0.383, 0.813)    # 強化 / 合成畫面「关闭」
# 強化 / 合成畫面右邊「所持饰品」：每列 5 個
ENHANCE_GRID = (0.5325, 0.0718, 0.356, 0.13)   # 第一個 x, 間距 x, 第一列 y, 列距
FUSE_GRID = (0.53, 0.0745, 0.407, 0.13)
OWNED_COLS, OWNED_ROWS = 5, 3
ENHANCE_BTN = (0.615, 0.813)
ENHANCE_PLUS = (0.7085, 0.709)
ENHANCE_PLUSPLUS = (0.805, 0.709)
ENHANCE_CONFIRM = (0.615, 0.809)
FUSE_CENTER = (0.2875, 0.487)      # 合成畫面中間的格子 (點了選關鍵詞)
FUSE_BTN = (0.615, 0.813)
KW_CELL_X = (0.26, 0.3785, 0.4965, 0.6145, 0.7325)   # 關鍵詞選擇：5 欄 x 2 列，順序同 GIFT_KEYWORDS
KW_CELL_Y = (0.409, 0.609)
KW_CONFIRM = (0.615, 0.787)
KEYWORD_TEMPLATES = dict(zip(GIFT_KEYWORDS, ['kw_burn', 'kw_bleed', 'kw_tremor', 'kw_rupture', 'kw_sinking',
                                              'kw_poise', 'kw_charge', 'kw_slash', 'kw_pierce', 'kw_blunt']))
KEYWORD_MATCH_THRESHOLD = 0.85
GIFT_LIT_VALUE = 40                # 所持饰品亮起 (可強化 / 可當材料) 的平均亮度


# 戰鬥後的獎勵
REWARD_CARD_Y = 0.42               # 獎勵卡片圖示的高度 (點這裡選)
REWARD_CARD_CONFIRM = (0.64, 0.735)
GIFT_REWARD_X = (0.19, 0.395, 0.602, 0.808)   # 選饰品獎勵：4 張卡的中心 x
GIFT_REWARD_CLICK_Y = 0.45
GIFT_TAG_TO_CENTER = -0.048        # 「获得E.G.O饰品」標籤中心 → 卡片中心 x
PARALLEL_CANCEL = (0.42, 0.655)
FINISH_CLAIM_BTN = (0.8975, 0.831)
WEEKLY_CONFIRM, WEEKLY_CANCEL = (0.61, 0.685), (0.415, 0.685)
GIFT_REWARD_SELECT = (0.888, 0.804)
GIFT_REWARD_TIER = (-0.035, 0.27, 0.012, 0.34)       # 等級 (相對卡片中心 x 的 x0, y0, x1, y1)
GIFT_REWARD_KEYWORD = (0.005, 0.33, 0.055, 0.405)  # 關鍵詞圖示


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
    'pack_obs_title': ['观测第', 'Observe'],
    'unavailable': ['无法选择', 'Unavailable'],
    'hard': ['HARD'],
    'refresh': ['刷新', 'Refresh'],
    'enter': ['Enter', '进入'],
    'pack_replace': ['替换', '将被', 'replace'],   # 字太長時「替 / 换」會被拆成兩行
    'shop_title': ['商店', 'Shop'],
    'parallel': ['平行叠加', 'Parallel'],
    'finish': ['探索完成', 'Exploration Complete'],
    'claim_reward': ['领取奖励', 'Claim'],
    'weekly_bonus': ['每周加成', 'Weekly'],
    'cancel': ['取消', 'Cancel'],
    'judge_title': ['进行判定', '选择一位罪人'],
    'judge_go': ['进行判定', '判定', '继续', 'Continue'],
    'reward_card_title': ['遭遇战奖励', '选择遭遇战'],
    'gift_reward_marker': ['追加的苦难', '苦难'],
    'leave': ['离开', 'Leave'],
    'buy': ['购买', 'Purchase', 'Buy'],
    'enhance_title': ['强化E', '强化'],
    'enhance_cost': ['消耗', '经费'],
    'fuse_title': ['合成E', '合成E.G.O'],
    'kw_select': ['关键词选择', 'Keyword'],
    'map_title': ['正在探索', 'Exploring'],
    'skip': ['SKIP', 'Skip'],
    'event_options_title': ['选项', 'Choices', 'Options'],
    'victory': ['Victory', '胜利'],
    'defeat': ['Defeat', '失败'],
}

# 可以用「擷取模板」任務自動截的模板：名稱 -> (要截的區域, 說明)
CAPTURABLE_TEMPLATES = {
    'home_window': (ROI['home_window'], '停在主畫面 (下方 Window 按鈕是亮紅色)'),
    'enk_max': (ROI['enk_max'], '打開換體力面板 (看得到 >> 全部換成模組的按鈕)'),
    'team_screen': (ROI['team_screen'], '停在進入關卡後的編隊畫面'),
}
