import unittest

from zh_tts_patch import (
    TtsPatchOptions,
    cleanup_punctuation,
    convert_filepaths,
    convert_phone_numbers,
    convert_classical_references,
    normalize_chinese_tts_text,
)


class ZhTtsPatchTests(unittest.TestCase):
    def test_classical_ref_basic(self):
        result = normalize_chinese_tts_text("古书 1:1 起初有言。")
        self.assertIn("第一章第一节", result)

    def test_classical_ref_pian_range(self):
        result = normalize_chinese_tts_text("诗23:1-6")
        self.assertEqual(result, "诗第二十三篇第一节至第六节")

    def test_time_is_not_misread_as_classical_ref(self):
        result = normalize_chinese_tts_text("下午3:30开会。")
        self.assertIn("3:30", result)
        self.assertNotIn("章", result)

    def test_common_words_do_not_trigger_time_as_classical_ref(self):
        cases = [
            ("春节假期，2:30开会", "2:30", "第二章第三十节"),
            ("文章篇目写完了，下午3:45开会", "3:45", "第三章第四十五节"),
            ("试卷批完了，4:30休息", "4:30", "第四章第三十节"),
            ("这个章节很难，下午5:15上课", "5:15", "第五章第十五节"),
        ]
        for text, time_token, bad_phrase in cases:
            with self.subTest(text=text):
                result = normalize_chinese_tts_text(text)
                self.assertIn(time_token, result)
                self.assertNotIn(bad_phrase, result)

    def test_bracketed_classical_ref_is_recognized(self):
        result = normalize_chinese_tts_text("古书（1:1）说")
        self.assertEqual(result, "古书（第一章第一节）说")

    def test_phone_mobile(self):
        result = convert_phone_numbers("电话138-1234-5678")
        self.assertEqual(result, "电话一三八 一二三四 五六七八")

    def test_phone_landline_with_parentheses(self):
        result = convert_phone_numbers("办公室电话：(010) 8888-9999")
        self.assertEqual(result, "办公室电话：零一零 八八八八 九九九九")

    def test_filepaths_and_url(self):
        self.assertEqual(convert_filepaths("打开https://www.example.com/docs"), "打开example.com")
        self.assertEqual(
            convert_filepaths(r"文件在C:\Users\Alex\Documents\bible.txt里"),
            "文件在bible.txt里",
        )

    def test_windows_path_does_not_swallow_following_prose(self):
        self.assertEqual(
            convert_filepaths(r"at C:\Users\Alex\Docs is a nice folder"),
            "at Docs is a nice folder",
        )

    def test_unix_path_does_not_swallow_chinese_slash_list(self):
        self.assertEqual(convert_filepaths("他要/爬山/跑步/游泳"), "他要/爬山/跑步/游泳")
        self.assertEqual(convert_filepaths("爱好/运动/阅读/旅行"), "爱好/运动/阅读/旅行")

    def test_cleanup_punctuation(self):
        self.assertEqual(cleanup_punctuation("等一下……马上来——真的。"), "等一下，马上来，真的。")

    def test_options_can_disable_patch(self):
        options = TtsPatchOptions(
            enable_classical_ref=False,
            enable_phone=False,
            enable_filepath=False,
            enable_punctuation_cleanup=False,
        )
        text = "古书 1:1 电话138-1234-5678"
        self.assertEqual(normalize_chinese_tts_text(text, options=options), text)

    def test_classical_ref_context_guard(self):
        result = convert_classical_references("下午2:30开会")
        self.assertEqual(result, "下午2:30开会")

    def test_international_prefix_does_not_touch_non_phone_values(self):
        self.assertEqual(convert_phone_numbers("增长了+86.5%"), "增长了+86.5%")
        self.assertEqual(convert_phone_numbers("结果为+86分"), "结果为+86分")

    def test_short_number_does_not_touch_decimal_or_headcount(self):
        self.assertEqual(convert_phone_numbers("114.5 元"), "114.5 元")
        self.assertEqual(convert_phone_numbers("这是110个人"), "这是110个人")


if __name__ == "__main__":
    unittest.main()
