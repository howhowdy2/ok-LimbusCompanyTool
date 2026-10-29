# ok-LimbusCompanyTool

[English](README_en.md) | 中文

用畫面辨識自動跑 **Limbus Company** 日常的工具，基於 [ok-script](https://github.com/ok-oldking/ok-script)。
只看畫面、模擬滑鼠鍵盤，不讀取也不修改遊戲記憶體或遊戲檔案。

> 個人學習用專案。自動化工具可能違反遊戲的服務條款，使用風險自負。

## 功能

| 任務 | 說明 |
|---|---|
| 一鍵日常 | 把體力換成模組 → 打纺锤本 → 打經驗本 → 領通行證獎勵 (次數、是否跳過戰鬥和單獨任務分開設定) |
| 換體力 | 把腦啡肽(體力)全部換成腦啡肽模組，不會用狂氣 |
| 打纺锤本 | 跳過戰鬥打當天開放的纺锤本，預設 3 次，只用剩下的每日加成 (每日加成 N/3 的 N 是剩餘次數) |
| 打經驗本 | 跳過戰鬥 (預設) 或用上次的隊伍打采光經驗本，可設定次數 (1~10) 和關卡 |
| 領通行證獎勵 | 點主畫面的 LIMBUS PASS → 領日常 / 周常任務 → 战斗通行证「全部领取」(可關) |
| 鏡像迷宮 | Drive → 镜像迷宫 → 进入 → 選編隊 (星芒奖励太低就換「镜像迷宫」編隊) → 确认 → 選星之恩惠 (一行一個「編號 等級」，等級 0 / 1 / 2) → 選開局 E.G.O 饰品 → E.G.O饰品观测 (最多 3 格，各選類型、等級、第幾個，或拒絕) → 選主題卡包 (每層從會出現的卡包裡勾選想要的、避開清單、刷新、卡包觀測、難度切換；資料在 assets/lc/mirror_packs.csv；卡包觀測的「…将被…替换」會按确认) → 樓層地圖：滾輪縮小，用火車模板找目前位置，看哪幾條路中間有亮的箭頭 (藍色、紅色主題都可以)，再看下一步連到哪些節點，依「Node Priority」(事件 / 戰鬥 / 異想體…) 選一個 → 进入。事件會一直點 SKIP 到出現選項，依「Event Option Priority」(選擇後獲得 > 根據後續獲得 > 判定 > 其他 > 戰鬥，同級選饰品多的) 選，判定時選頭上機率最高的罪人；沒見過的選項記在 screenshots/event_options/options.txt；戰鬥節點跟經驗本一樣按开始战斗、P + Enter。每個節點結束都回地圖重新縮小、重新選路，下一層會再選卡包。商店：依關鍵詞 / 等級買饰品 (低於最低保留經費就不買)、刷新、強化 (+ / ++)、合成 (選關鍵詞和目標等級，預設關閉)。戰後獎勵：遭遇戰獎勵卡依「星芒 > 經費 > 飾品 > 機率飾品 > 其他」選；選饰品 (附帶苦難) 可以苦難或饰品為準。判定畫面和戰後獎勵尚未完成 |
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

鏡像迷宮地圖的節點類型用 `assets/lc/map_*.png` 辨識 (已附 `map_event` 事件、`map_battle` 戰鬥、`map_abno` 異想體、`map_elite` 精英戰鬥、`map_boss` 頭目)。
遇到不認得的節點，會把圖示存到 `screenshots/map_nodes/unknown_*.png`，
把它改名放進 `assets/lc/`：`map_abno.png` 異想體、`map_elite.png` 精英戰鬥、`map_shop.png` 商店、
`map_rest.png` 休息、`map_boss.png` 頭目，下次就認得了。

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
