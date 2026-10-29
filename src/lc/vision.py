"""純影像處理工具：不碰遊戲、不點擊，可以直接寫單元測試。

模板一律存成「1080p 基準」：在 1440p 截的模板會先縮成 1080p 大小再存，
比對時再依目前畫面高度放大或縮小，所以換解析度不用重截。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

BASE_HEIGHT = 1080


@dataclass(frozen=True)
class Match:
    x: int
    y: int
    width: int
    height: int
    score: float

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def rel_to_px(roi, width: int, height: int, pad: float = 0.0) -> tuple[int, int, int, int]:
    """相對座標區域 -> 像素座標，pad 是往外多抓的比例(容許位置些微偏移)。"""
    x0, y0, x1, y1 = roi
    left = max(0, int(round((x0 - pad) * width)))
    top = max(0, int(round((y0 - pad) * height)))
    right = min(width, int(round((x1 + pad) * width)))
    bottom = min(height, int(round((y1 + pad) * height)))
    return left, top, max(left + 1, right), max(top + 1, bottom)


def to_base_scale(image: np.ndarray, frame_height: int) -> np.ndarray:
    """把在 frame_height 畫面上截到的圖縮放成 1080p 基準。"""
    scale = BASE_HEIGHT / frame_height
    if abs(scale - 1.0) < 0.01:
        return image
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=interpolation)


def scale_template(template: np.ndarray, frame_height: int) -> np.ndarray:
    """把 1080p 基準的模板縮放到目前畫面的大小。"""
    scale = frame_height / BASE_HEIGHT
    if abs(scale - 1.0) < 0.01:
        return template
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(template, None, fx=scale, fy=scale, interpolation=interpolation)


def crop_rel(frame: np.ndarray, roi) -> np.ndarray:
    height, width = frame.shape[:2]
    left, top, right, bottom = rel_to_px(roi, width, height)
    return frame[top:bottom, left:right]


def find_template(
    frame: np.ndarray,
    template: np.ndarray,
    roi=None,
    threshold: float = 0.8,
    max_results: int = 1,
    pad: float = 0.02,
) -> list[Match]:
    """在 frame 裡找模板，回傳分數由高到低的結果 (座標是整張 frame 的像素座標)。

    - template 是 1080p 基準，會自動縮放到 frame 的大小
    - roi 是相對座標區域，只在裡面找 (會再往外多抓 pad)
    - max_results > 1 時可以找到多個不重疊的目標 (例如好幾個關卡入口)
    """
    frame_height, frame_width = frame.shape[:2]
    gray = to_gray(frame)
    tpl = to_gray(scale_template(template, frame_height))
    if roi is None:
        left, top, right, bottom = 0, 0, frame_width, frame_height
    else:
        left, top, right, bottom = rel_to_px(roi, frame_width, frame_height, pad)
    region = gray[top:bottom, left:right]
    th, tw = tpl.shape[:2]
    if th < 4 or tw < 4 or region.shape[0] < th or region.shape[1] < tw:
        return []

    response = cv2.matchTemplate(region, tpl, cv2.TM_CCOEFF_NORMED)
    # 純色區域會算出 NaN/inf，當成不相符
    response = np.nan_to_num(response, nan=-1.0, posinf=-1.0, neginf=-1.0)

    results: list[Match] = []
    while len(results) < max_results:
        _, score, _, (x, y) = cv2.minMaxLoc(response)
        if score < threshold:
            break
        results.append(Match(left + x, top + y, tw, th, float(score)))
        # 把這個位置附近塗掉，下一輪才不會找到同一個目標
        x0, y0 = max(0, x - tw // 2), max(0, y - th // 2)
        response[y0:y + th // 2 + 1, x0:x + tw // 2 + 1] = -1.0
    return results


_ENKEPHALIN = re.compile(r'(\d+)\s*/\s*(\d+)')


def parse_enkephalin(text: str) -> tuple[int, int] | None:
    """從 OCR 文字讀出「目前/上限」，例如 '8/156' -> (8, 156)。"""
    if not text:
        return None
    cleaned = text.replace(' ', '').replace('O', '0').replace('o', '0')
    found = _ENKEPHALIN.search(cleaned)
    if not found:
        return None
    current, maximum = int(found.group(1)), int(found.group(2))
    if maximum <= 0 or current > maximum * 3:  # 數字讀錯時常出現離譜的值
        return None
    return current, maximum


def find_bright_blob(frame: np.ndarray, box_px, min_value: int = 200,
                     min_area: int = 12) -> tuple[int, int] | None:
    """在像素區域 box_px=(left, top, right, bottom) 裡找最大的一塊亮色(白色)圖形，回傳中心點。

    用來找「连续进行」右邊的白色 ▲/▼：卡片寬度不同時，它離文字的距離也不同，
    直接找圖形比固定位移可靠。
    """
    left, top, right, bottom = box_px
    region = to_gray(frame[top:bottom, left:right])
    if region.size == 0:
        return None
    mask = (region >= min_value).astype(np.uint8)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    best = None
    for i in range(1, count):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area and (best is None or area > stats[best, cv2.CC_STAT_AREA]):
            best = i
    if best is None:
        return None
    cx, cy = centroids[best]
    return left + int(cx), top + int(cy)


def find_tier_bands(frame: np.ndarray, x_range=(0.35, 0.45), y_range=(0.30, 0.90),
                    min_height: float = 0.018) -> list[float]:
    """E.G.O饰品观测：找出 III / II / I 那幾條藍色分隔條的中心 y (相對座標，由上到下)。

    分隔條是一整條偏藍的橫帶 (B 明顯大於 R)，在饰品還沒排到的欄位取樣就不會被圖示干擾。
    """
    height, width = frame.shape[:2]
    x0, x1 = int(x_range[0] * width), int(x_range[1] * width)
    y0, y1 = int(y_range[0] * height), int(y_range[1] * height)
    strip = frame[y0:y1, x0:x1, :3].astype(np.int32).mean(axis=1)   # 每一列的平均 BGR
    blue = (strip[:, 0] > 60) & (strip[:, 0] > strip[:, 2] * 2.2) & (strip[:, 0] > strip[:, 1] * 1.6)
    bands, start = [], None
    for i, flag in enumerate(list(blue) + [False]):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if (i - start) / height >= min_height:
                bands.append((y0 + (start + i - 1) / 2) / height)
            start = None
    return bands


def parse_fraction(text: str) -> tuple[int, int] | None:
    """'0/3' -> (0, 3)；讀不到回傳 None。"""
    found = _ENKEPHALIN.search((text or '').replace(' ', ''))
    return (int(found.group(1)), int(found.group(2))) if found else None


def parse_daily_bonus(text: str, total: int = 3) -> tuple[int, int] | None:
    """「每日加成 0/3」：斜線字體很花，常被讀成 '03'、'0月3'、'073'，這些也接受。

    規則：第一個數字是已用次數 (0~total)，最後一個數字要是 total。
    """
    found = parse_fraction(text)
    if found and found[1] == total and 0 <= found[0] <= total:
        return found
    digits = re.sub(r'\D', '', text or '')
    if len(digits) >= 2 and digits[-1] == str(total) and int(digits[0]) <= total:
        return int(digits[0]), total
    return None


_REPEAT = re.compile(r'(?:[x×X\*]|进行|Repeat)\s*(\d+)')


def parse_repeat(text: str) -> int | None:
    """「连续进行×3」-> 3。"""
    found = _REPEAT.search(text or '')
    return int(found.group(1)) if found else None


def parse_int(text: str) -> int | None:
    """從 OCR 文字取出整數，'2,85' 或 '285' -> 285；讀不到回傳 None。"""
    digits = re.sub(r'\D', '', (text or '').replace('O', '0').replace('o', '0'))
    return int(digits) if digits else None


_DIGIT_LOOKALIKE = str.maketrans({'O': '0', 'o': '0', 'G': '6', 'B': '8', 'S': '5', 'l': '1', 'I': '1'})


def parse_stylized_int(text: str) -> int | None:
    """遊戲的花體數字常被讀成字母：'本9G' -> 96 (G 當 6、O 當 0 …)。"""
    return parse_int((text or '').translate(_DIGIT_LOOKALIKE))


try:  # ok-script 已經裝了 opencc，用來把繁體設定轉成簡體再比對
    import opencc as _opencc
    _T2S = _opencc.OpenCC('t2s')
except Exception:  # noqa: BLE001
    _T2S = None


def normalize_name(text: str) -> str:
    """名稱比對用：去掉空白和標點、繁轉簡。"""
    text = re.sub(r'[\s·・\-—_:：,，、。.!！?？]', '', text or '')
    return _T2S.convert(text) if _T2S else text


def parse_pack_rule(line: str):
    """「无法去爱」或「1:无法去爱」-> (樓層或 None, 名稱)。"""
    line = (line or '').strip()
    found = re.match(r'^(\d+)\s*[:：]\s*(.+)$', line)
    if found:
        return int(found.group(1)), normalize_name(found.group(2))
    return None, normalize_name(line)


def names_match(a: str, b: str) -> bool:
    """名稱相同，或 OCR 多/少讀了一個字也算 (但「20区的奇迹」和「20区的奇迹 复刻」不算)。"""
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = sorted((a, b), key=len)
    return len(long) - len(short) <= 1 and short in long


def rule_matches(rules, floor, name) -> int | None:
    """name 符合第幾條規則 (越小越優先)，都不符合回傳 None。"""
    target = normalize_name(name)
    for i, (rule_floor, rule_name) in enumerate(rules):
        if rule_floor is not None and rule_floor != floor:
            continue
        if names_match(rule_name, target):
            return i
    return None


def keywords_regex(keywords) -> re.Pattern:
    """關鍵字清單 -> 不分大小寫、包含即可的 regex，給 ok-script 的 ocr(match=...) 用。"""
    if isinstance(keywords, str):
        keywords = [keywords]
    parts = [re.escape(k.strip()) for k in keywords if k and k.strip()]
    if not parts:
        return re.compile(r'(?!)')  # 永遠不會符合
    return re.compile('|'.join(parts), re.IGNORECASE)


# ---------- 鏡像迷宮樓層地圖 ----------

MAP_AREA = (0.15, 0.12, 0.93, 0.86)   # 扣掉上方關鍵字列、右邊按鈕、下方角色列
NODE_ICON_SIZE = 48                    # 節點圖示正規化後的邊長 (模板也存這個大小)
NODE_ICON_RATIO = 0.45                 # 圖示取節點外框高度的多少 (中間那一塊)
NODE_ICON_DY = -0.10                   # 外框下面有立體的邊，圖示中心比外框中心高一點 (外框高度的比例)


@dataclass(frozen=True)
class MapNode:
    x: int        # 節點中心 (像素)
    y: int
    size: int     # 外框高度 (像素)


def lit_mask(frame: np.ndarray, area=MAP_AREA) -> np.ndarray:
    """地圖上「亮藍色」的部分：目前所在的節點、可以走的路線和可以走的節點。走不到的都是暗的。"""
    image = frame[:, :, :3].astype(np.int16)
    b, g, r = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    mask = ((b > 150) & (g > 120) & (b - r > 90)).astype(np.uint8)
    height, width = mask.shape
    left, top, right, bottom = rel_to_px(area, width, height)
    out = np.zeros_like(mask)
    out[top:bottom, left:right] = mask[top:bottom, left:right]
    return out


def find_reachable_nodes(frame: np.ndarray, area=MAP_AREA, strip: float = 0.02,
                         min_span: float = 0.06, gap: float = 0.03) -> list[MapNode]:
    """找出下一步可以走的節點 (由上到下)。

    亮藍色的東西是「目前節點 → 路線 → 可走的節點」，可走的節點一定在最右邊那一欄：
    取最右邊一條窄帶裡的亮點，依 y 分群，每一群就是一個節點外框的右半邊。
    """
    mask = lit_mask(frame, area)
    height, width = mask.shape
    min_pixels = max(12, int(width * height * 0.00001))
    # 去掉零星的亮點 (背景花紋、特效)，不然最右邊會被它們佔走
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    keep = np.zeros(count, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_pixels
    mask = keep[labels].astype(np.uint8)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0 or (xs.max() - xs.min()) / width < min_span:
        return []   # 只剩目前節點自己亮著 (沒有路可走)
    right = xs.max()
    sel = xs >= right - strip * width
    pts = sorted(zip(ys[sel], xs[sel]))
    nodes, group = [], []

    def flush():
        if len(group) >= min_pixels:
            y0, y1 = group[0][0], group[-1][0]
            size = y1 - y0 + 1
            gx = max(x for _, x in group)
            nodes.append(MapNode(int(gx - size / 2), int((y0 + y1) / 2), int(size)))

    for y, x in pts:
        if group and y - group[-1][0] > gap * height:
            flush()
            group = []
        group.append((y, x))
    flush()
    nodes = [n for n in nodes if n.size >= height * 0.02]
    if not nodes:
        return []
    # 外框常被劍、線擋住一部分，量到的高度會偏小；同一張圖的節點一樣大，用最大的那個
    size = max(n.size for n in nodes)
    return [MapNode(int(n.x + n.size / 2 - size / 2), n.y, size) for n in nodes]


def node_icon(frame: np.ndarray, node: MapNode, ratio: float = NODE_ICON_RATIO,
              size: int = NODE_ICON_SIZE) -> np.ndarray:
    """節點中間的圖示 (? / 劍 / 異想體…)，灰階並縮放成固定大小，跟縮放程度無關。"""
    half = max(4, int(node.size * ratio / 2))
    cx, cy = node.x, int(node.y + node.size * NODE_ICON_DY)
    height, width = frame.shape[:2]
    x0, y0 = max(0, cx - half), max(0, cy - half)
    crop = frame[y0:min(height, cy + half), x0:min(width, cx + half)]
    return cv2.resize(to_gray(crop), (size, size), interpolation=cv2.INTER_AREA)


def classify_node(icon: np.ndarray, templates: dict) -> tuple[str | None, float]:
    """icon 跟每個模板比對 (容許上下左右偏一點)，回傳 (最像的類型, 分數)。"""
    best, best_score = None, -1.0
    margin = max(2, icon.shape[0] // 4)
    padded = cv2.copyMakeBorder(icon, margin, margin, margin, margin, cv2.BORDER_REPLICATE)
    for name, tpl in templates.items():
        tpl = to_gray(tpl)
        if tpl.shape[:2] != icon.shape[:2]:
            tpl = cv2.resize(tpl, icon.shape[::-1], interpolation=cv2.INTER_AREA)
        response = np.nan_to_num(cv2.matchTemplate(padded, tpl, cv2.TM_CCOEFF_NORMED), nan=-1.0)
        score = float(response.max())
        if score > best_score:
            best, best_score = name, score
    return best, best_score


# ---------- 鏡像迷宮事件選項 ----------

EVENT_GIFT, EVENT_CHECK, EVENT_BATTLE, EVENT_OTHER = '獲得飾品', '判定', '戰鬥', '其他'
EVENT_KINDS = (EVENT_GIFT, EVENT_CHECK, EVENT_OTHER, EVENT_BATTLE)


def classify_event_option(text: str) -> str:
    """事件選項看下面那行小字：「选择后，获得1件泛用E.G.O饰品」-> 獲得飾品；有「判定」-> 判定；
    有「战斗」-> 戰鬥；其他 (沒有小字、沒見過的) -> 其他。"""
    text = normalize_name(text)
    if '饰品' in text and ('获得' in text or '获取' in text):
        return EVENT_GIFT
    if '判定' in text:
        return EVENT_CHECK
    if '战斗' in text or '交战' in text:
        return EVENT_BATTLE
    return EVENT_OTHER


def group_by_rows(items, key_y, gap: float):
    """把 OCR 文字依 y 分組 (同一個選項框裡的大字和小字一組)，gap 是像素。"""
    groups = []
    for item in sorted(items, key=key_y):
        if groups and key_y(item) - key_y(groups[-1][-1]) <= gap:
            groups[-1].append(item)
        else:
            groups.append([item])
    return groups
