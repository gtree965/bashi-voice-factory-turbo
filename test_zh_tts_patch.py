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


if __name__ == "__main__":
    unittest.main()
