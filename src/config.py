import os

version = "dev"
# 不需要修改 version，GitHub Action 打包時會自動改成 tag 名稱

app_profile = os.environ.get("PYAPPIFY_APP_PROFILE", "")
gui_config = {
    'type': 'web' if app_profile.casefold() == 'web' else 'qt',
    'window_size': {
        'width': 1200,
        'height': 800,
        'min_width': 600,
        'min_height': 450,
    },
}
if gui_config['type'] == 'web':
    gui_config['launch_mode'] = 'pywebview'

REPO_URL = 'https://github.com/howhowdy2/ok-LimbusCompanyTool'

config = {
    'custom_tasks': True,  # 允許在 GUI 裡新增自訂任務
    'debug': False,
    'gui': gui_config,
    'config_folder': 'configs',  # 最好不要修改
    'gui_icon': 'icons/icon.png',
    'wait_until_before_delay': 0,
    'wait_until_check_delay': 0,
    'wait_until_settle_time': 0,
    'ocr': {
        'lib': 'onnxocr',
        'auto_simplify': True,  # 繁體自動轉簡體，關鍵字只要寫英文和簡體
        'params': {
            'use_openvino': True,
        }
    },
    'windows': {
        'exe': ['LimbusCompany.exe'],
        'hwnd_class': 'UnityWndClass',  # Limbus Company 是 Unity 遊戲
        # Limbus Company 在背景收不到點擊，實際上會用 Pynput（前景滑鼠鍵盤）
        'interaction': ['Pynput', 'PostMessage', 'PyDirect', 'ForegroundPostMessage'],
        'capture_method': ['WGC', 'BitBlt_RenderFull', 'BitBlt'],
        'check_hdr': True,  # 開了 AutoHDR 會提醒，顏色偏掉會影響模板比對
        'force_no_hdr': False,
        'require_bg': True,
    },
    'start_timeout': 120,
    'supported_resolution': {
        'ratio': '16:9',
        'min_size': (1280, 720),
        'resize_to': [(2560, 1440), (1920, 1080), (1600, 900), (1280, 720)],
    },
    'links': {
        'default': {
            'github': REPO_URL,
            'share': f'Download from {REPO_URL}',
            'faq': REPO_URL,
        }
    },
    'screenshots_folder': "screenshots",  # 每次重新啟動會清空
    'gui_title': 'ok-LimbusCompanyTool',
    'template_matching': {
        'coco_feature_json': os.path.join('assets', 'coco_annotations.json'),
        'default_horizontal_variance': 0.002,
        'default_vertical_variance': 0.002,
        'default_threshold': 0.8,
    },
    'version': version,
    'my_app': ['src.globals', 'Globals'],
    'onetime_tasks': [  # 使用者按下才跑的任務，顯示順序就是這裡的順序
        ["src.tasks.DailyTask", "DailyTask"],
        ["src.tasks.EnkephalinTask", "EnkephalinTask"],
        ["src.tasks.ExpLuxcavationTask", "ExpLuxcavationTask"],
        ["src.tasks.ThreadLuxcavationTask", "ThreadLuxcavationTask"],
        ["src.tasks.PassTask", "PassTask"],
        ["src.tasks.CaptureTemplateTask", "CaptureTemplateTask"],
        ["ok", "DiagnosisTask"],
    ],
}
