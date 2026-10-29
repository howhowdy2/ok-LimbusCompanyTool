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


class TierBandTest(unittest.TestCase):
    def test_finds_blue_bands_top_to_bottom(self):
        frame = np.full((1080, 1920, 3), (20, 22, 26), np.uint8)
        for top in (378, 678, 858):           # 三條藍色分隔條，高 36px
            frame[top:top + 36, :] = (85, 38, 25)
        bands = vision.find_tier_bands(frame)
        self.assertEqual(3, len(bands))
        for expected, actual in zip((396, 696, 876), bands):
            self.assertAlmostEqual(expected / 1080, actual, delta=0.003)

    def test_ignores_thin_lines(self):
        frame = np.full((1080, 1920, 3), (20, 22, 26), np.uint8)
        frame[500:505, :] = (85, 38, 25)
        self.assertEqual([], vision.find_tier_bands(frame))


class PackRuleTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual((None, '无法去爱'), vision.parse_pack_rule('无法去爱'))
        self.assertEqual((2, '自动工厂'), vision.parse_pack_rule('2: 自动工厂'))

    def test_match_priority_and_floor(self):
        rules = [vision.parse_pack_rule(r) for r in ['2:自动工厂', '无法去爱', '当碎之物']]
        self.assertEqual(1, vision.rule_matches(rules, 1, '无法去爱'))
        self.assertIsNone(vision.rule_matches(rules, 1, '自动工厂'))   # 只限第 2 層
        self.assertEqual(0, vision.rule_matches(rules, 2, '自动工厂'))
        self.assertIsNone(vision.rule_matches(rules, 1, '被遗忘者们'))

    def test_reprint_is_a_different_pack(self):
        rules = [vision.parse_pack_rule('20区的奇迹')]
        self.assertIsNone(vision.rule_matches(rules, 4, '20区的奇迹 复刻'))
        self.assertEqual(0, vision.rule_matches(rules, 4, '20区的奇'))   # OCR 少一個字

    def test_punctuation_ignored(self):
        rules = [vision.parse_pack_rule('巢、工坊、技术')]
        self.assertEqual(0, vision.rule_matches(rules, 1, '巢，工坊，技术'))


class PackDataTest(unittest.TestCase):
    def test_floors(self):
        from src.lc import packs
        data = packs.load_packs()
        self.assertEqual({'normal': (1, 2), 'hard': (1,)}, data['巢、工坊、技术'])
        self.assertEqual((), data['心意相悖']['normal'])
        self.assertIn('无法去爱', packs.packs_on_floor(1))
        self.assertNotIn('心意相悖', packs.packs_on_floor(5, hard=False))
        self.assertIn('心意相悖', packs.packs_on_floor(5, hard=True))


class MapNodeTest(unittest.TestCase):
    CYAN = (255, 230, 90)   # BGR

    def hexagon(self, frame, cx, cy, r):
        pts = np.array([(cx + r * np.cos(a), cy + r * np.sin(a))
                        for a in np.linspace(0, 2 * np.pi, 7)[:-1]], np.int32)
        cv2.polylines(frame, [pts], True, self.CYAN, 3)

    def test_reachable_nodes_are_the_rightmost_lit_column(self):
        frame = np.full((1440, 2560, 3), (40, 35, 20), np.uint8)
        start = (900, 620)
        targets = [(1150, 430), (1150, 645), (1150, 860)]
        self.hexagon(frame, *start, 40)
        for x, y in targets:
            cv2.line(frame, start, (x - 40, y), self.CYAN, 6)
            self.hexagon(frame, x, y, 40)
        self.hexagon(frame, 1400, 640, 40)            # 走不到的節點是暗的
        frame[600:680, 1360:1440] //= 3
        nodes = vision.find_reachable_nodes(frame)
        self.assertEqual(3, len(nodes))
        for (x, y), node in zip(targets, nodes):
            self.assertAlmostEqual(x, node.x, delta=8)
            self.assertAlmostEqual(y, node.y, delta=8)

    def test_find_train(self):
        frame = np.full((1440, 2560, 3), (40, 35, 20), np.uint8)
        cv2.rectangle(frame, (870, 580), (920, 650), (20, 20, 170), -1)   # 紅色火車
        cv2.rectangle(frame, (300, 1300), (400, 1400), (20, 20, 170), -1)  # 下方角色列不算
        x, y = vision.find_train(frame)
        self.assertAlmostEqual(895, x, delta=3)
        self.assertAlmostEqual(615, y, delta=3)

    def test_nothing_lit(self):
        frame = np.full((1080, 1920, 3), (40, 35, 20), np.uint8)
        self.assertEqual([], vision.find_reachable_nodes(frame))

    def test_classify_with_shipped_templates(self):
        templates = {name: cv2.imread(f'assets/lc/{name}.png') for name in ('map_event', 'map_battle')}
        for name, tpl in templates.items():
            noisy = cv2.add(vision.to_gray(tpl), 10)
            self.assertEqual(name, vision.classify_node(noisy, templates)[0])


class EventOptionTest(unittest.TestCase):
    def test_classify(self):
        self.assertEqual('獲得飾品', vision.classify_event_option('闭上双眼。 选择后，获得1件泛用E.G.O饰品'))
        self.assertEqual('判定', vision.classify_event_option('伸出手 进行判定'))
        self.assertEqual('戰鬥', vision.classify_event_option('拔刀 进入战斗'))
        self.assertEqual('其他', vision.classify_event_option('还以对视。'))

    def test_group_rows(self):
        ys = [331, 369, 527]   # 第一個選項兩行字，第二個一行
        groups = vision.group_by_rows(ys, lambda y: y, 0.07 * 1125)
        self.assertEqual([[331, 369], [527]], groups)


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
