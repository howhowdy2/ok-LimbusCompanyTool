"""src/lc/vision.py 的單元測試：不需要遊戲、不需要 Windows，直接跑
python -m unittest tests.test_vision
"""
import unittest

import cv2
import numpy as np

from src.lc import vision


def make_icon(size=40):
    """畫一個有明顯形狀的測試圖示。"""
    icon = np.full((size, size, 3), 30, np.uint8)
    cv2.rectangle(icon, (6, 6), (size - 7, size - 7), (220, 200, 160), -1)
    cv2.circle(icon, (size // 2, size // 2), size // 5, (20, 20, 20), -1)
    cv2.line(icon, (8, size - 10), (size - 10, 8), (90, 60, 200), 3)
    return icon


def make_frame(width, height, icons):
    """在雜訊背景上放圖示，icons = [(相對 x, 相對 y)]，圖示大小跟著畫面高度縮放。"""
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 60, (height, width, 3), dtype=np.uint8)
    icon = vision.scale_template(make_icon(), height)
    ih, iw = icon.shape[:2]
    for rx, ry in icons:
        x, y = int(rx * width), int(ry * height)
        frame[y:y + ih, x:x + iw] = icon
    return frame


class FindTemplateTest(unittest.TestCase):
    def test_finds_icon_at_1080p(self):
        frame = make_frame(1920, 1080, [(0.5, 0.5)])
        result = vision.find_template(frame, make_icon())
        self.assertEqual(1, len(result))
        self.assertAlmostEqual(960, result[0].x, delta=2)
        self.assertGreater(result[0].score, 0.95)

    def test_same_template_works_at_1440p_and_720p(self):
        for width, height in [(2560, 1440), (1280, 720)]:
            frame = make_frame(width, height, [(0.3, 0.6)])
            result = vision.find_template(frame, make_icon(), threshold=0.8)
            self.assertEqual(1, len(result), f'{width}x{height}')
            self.assertAlmostEqual(0.3 * width, result[0].x, delta=3)

    def test_roi_limits_search(self):
        frame = make_frame(1920, 1080, [(0.1, 0.1)])
        self.assertEqual([], vision.find_template(frame, make_icon(), roi=(0.5, 0.5, 1, 1)))
        self.assertEqual(1, len(vision.find_template(frame, make_icon(), roi=(0, 0, 0.3, 0.3))))

    def test_multiple_results_are_separate(self):
        frame = make_frame(1920, 1080, [(0.2, 0.5), (0.45, 0.5), (0.7, 0.5)])
        result = vision.find_template(frame, make_icon(), max_results=10)
        xs = sorted(m.x for m in result)
        self.assertEqual(3, len(xs))
        for expected, actual in zip([0.2, 0.45, 0.7], xs):
            self.assertAlmostEqual(expected * 1920, actual, delta=3)

    def test_no_match_on_blank_frame(self):
        frame = np.zeros((1080, 1920, 3), np.uint8)
        self.assertEqual([], vision.find_template(frame, make_icon()))

    def test_capture_then_match_round_trip(self):
        # 在 1440p 擷取模板 (換算成 1080p 基準) 後，在 1080p 畫面還找得到
        big = make_frame(2560, 1440, [(0.4, 0.4)])
        roi = (0.39, 0.39, 0.39 + 60 / 1440 * 9 / 16, 0.39 + 60 / 1440)
        template = vision.to_base_scale(vision.crop_rel(big, roi), 1440)
        small = make_frame(1920, 1080, [(0.4, 0.4)])
        self.assertEqual(1, len(vision.find_template(small, template, threshold=0.7)))


class ParseEnkephalinTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual((8, 156), vision.parse_enkephalin('8/156'))
        self.assertEqual((120, 156), vision.parse_enkephalin('120 / 156'))
        self.assertEqual((10, 156), vision.parse_enkephalin('1O/156'))

    def test_bad_text(self):
        self.assertIsNone(vision.parse_enkephalin(''))
        self.assertIsNone(vision.parse_enkephalin('Luxcavation'))
        self.assertIsNone(vision.parse_enkephalin('9999/12'))


class ParseNumberTest(unittest.TestCase):
    def test_repeat(self):
        self.assertEqual(1, vision.parse_repeat('连续进行×1'))
        self.assertEqual(3, vision.parse_repeat('连续进行x 3'))
        self.assertEqual(1, vision.parse_repeat('连续进行1'))  # × 沒讀到
        self.assertIsNone(vision.parse_repeat('连续进行×'))

    def test_fraction(self):
        self.assertEqual((0, 3), vision.parse_fraction('0/3'))
        self.assertEqual((2, 3), vision.parse_fraction('2 / 3'))
        self.assertIsNone(vision.parse_fraction('每日加成'))

    def test_daily_bonus(self):
        self.assertEqual((0, 3), vision.parse_daily_bonus('每日加成0/3'))
        self.assertEqual((2, 3), vision.parse_daily_bonus('每日加成23'))  # 斜線沒讀到
        self.assertEqual((0, 3), vision.parse_daily_bonus('0月3'))
        self.assertEqual((0, 3), vision.parse_daily_bonus('073'))
        self.assertIsNone(vision.parse_daily_bonus('0/'))
        self.assertIsNone(vision.parse_daily_bonus('每日加成0月'))
        self.assertIsNone(vision.parse_daily_bonus('每日加成'))

    def test_int(self):
        self.assertEqual(285, vision.parse_int('285'))
        self.assertEqual(60, vision.parse_int('6O'))
        self.assertIsNone(vision.parse_int('LUNACY'))

    def test_stylized_int(self):
        self.assertEqual(96, vision.parse_stylized_int('本96'))
        self.assertEqual(96, vision.parse_stylized_int('本9G'))
        self.assertIsNone(vision.parse_stylized_int('本'))


class KeywordsRegexTest(unittest.TestCase):
    def test_contains_and_ignores_case(self):
        pattern = vision.keywords_regex(['To Battle', '出击'])
        self.assertTrue(pattern.search('TO BATTLE!'))
        self.assertTrue(pattern.search('出击'))
        self.assertFalse(pattern.search('Confirm'))

    def test_empty_never_matches(self):
        self.assertFalse(vision.keywords_regex([]).search('anything'))


if __name__ == '__main__':
    unittest.main()
