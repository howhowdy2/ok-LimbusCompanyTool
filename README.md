# ok-LimbusCompanyTool

[English](README_en.md) | 中文

用畫面辨識自動跑 **Limbus Company** 日常的工具，基於 [ok-script](https://github.com/ok-oldking/ok-script)。
只看畫面、模擬滑鼠鍵盤，不讀取也不修改遊戲記憶體或遊戲檔案。

> 個人學習用專案。自動化工具可能違反遊戲的服務條款，使用風險自負。

## 功能

| 任務 | 說明 |
|---|---|
| 一鍵日常 | 把體力換成模組 → 打經驗本 |
| 換體力 | 把腦啡肽(體力)全部換成腦啡肽模組，不會用狂氣 |
| 打經驗本 | 跳過戰鬥 (預設) 或用上次的隊伍打采光經驗本，可設定次數和關卡 |
| 擷取模板 | 從目前的遊戲畫面截出辨識要用的圖片 |

## 遊戲設定

- PC 版 (Steam)，畫面比例 **16:9**，建議 1920×1080 或 2560×1440
- 語言：英文，或 LLC 簡體中文漢化
- 執行時遊戲要在前景 (Limbus Company 在背景收不到點擊)

## 開發環境

需要 Windows 和 [Python 3.12](https://www.python.org/downloads/release/python-31210/)。

```bat
git clone https://github.com/howhowdy2/ok-LimbusCompanyTool.git
cd ok-LimbusCompanyTool
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --index-url https://pypi.org/simple/ --upgrade pip
python -m pip install --index-url https://pypi.org/simple/ --no-deps --upgrade -r requirements.txt
python main_debug.py
```

## 第一次使用：建立模板

辨識需要幾張遊戲畫面的小圖，存在 `assets/lc/`。開工具後用「擷取模板」任務建立：

1. 遊戲停在**主畫面** → 擷取模板選 `home_window` → 開始
2. 點主畫面的體力圖示打開**換體面板** → 選 `enk_max` → 開始
3. 進任一關卡的**編隊畫面** → 選 `team_screen` → 開始 (只有「進入戰鬥」模式會用到)

經驗本列表的按鈕 (进入、跳过战斗、连续进行) 是用 OCR 讀字找的，不需要模板。

建好後把 `assets/lc/*.png` 一起 commit，打包時就會帶進去。

## 專案結構

```
src/
  config.py                 # 視窗、OCR、任務註冊
  lc/layout.py              # 按鈕位置 (相對座標) 和 OCR 關鍵字，改版跑位就改這裡
  lc/vision.py              # 模板比對、數字解析等純函式 (有單元測試)
  tasks/LimbusBaseTask.py   # 共用：找模板、回主畫面、讀體力
  tasks/*Task.py            # 各個任務
tests/
  test_vision.py            # python -m unittest tests.test_vision
```

## 打包發布

推一個 `v` 開頭的 tag，GitHub Actions 會自動打包成安裝檔並建立 Release：

```bat
git tag v0.1.0
git push origin v0.1.0
```

## 致謝

- [ok-script](https://github.com/ok-oldking/ok-script) / [ok-script-app](https://github.com/ok-oldking/ok-script-app) 模板
- [AhabAssistantLimbusCompany](https://github.com/KIYI671/AhabAssistantLimbusCompany)：參考了畫面流程
