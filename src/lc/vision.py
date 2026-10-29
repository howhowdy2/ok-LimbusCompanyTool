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


def keywords_regex(keywords) -> re.Pattern:
    """關鍵字清單 -> 不分大小寫、包含即可的 regex，給 ok-script 的 ocr(match=...) 用。"""
    if isinstance(keywords, str):
        keywords = [keywords]
    parts = [re.escape(k.strip()) for k in keywords if k and k.strip()]
    if not parts:
        return re.compile(r'(?!)')  # 永遠不會符合
    return re.compile('|'.join(parts), re.IGNORECASE)
