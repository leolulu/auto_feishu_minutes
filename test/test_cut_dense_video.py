import os
import shutil
import subprocess

# 导入需要测试的函数
import tempfile
import unittest
from unittest.mock import mock_open, patch

from cut_dense_video import (
    _calculate_speed_by_duration,
    _get_video_duration,
    _natural_sort_key,
    _process_silence_segment,
    _time_str_to_seconds,
    concat_video,
    cut_video,
)


class TestCutDenseVideo(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)
    
    def test_get_video_duration_success(self):
        """测试成功获取视频时长"""
        with patch('subprocess.check_output') as mock_check:
            mock_check.return_value = "120.5\n"
            duration = _get_video_duration("test.mp4")
            self.assertEqual(duration, 120.5)
    
    def test_get_video_duration_file_not_found(self):
        """测试文件不存在时的处理"""
        with patch('subprocess.check_output') as mock_check:
            mock_check.side_effect = FileNotFoundError()
            duration = _get_video_duration("nonexistent.mp4")
            self.assertIsNone(duration)
    
    def test_get_video_duration_subprocess_error(self):
        """测试subprocess调用失败时的处理"""
        with patch('subprocess.check_output') as mock_check:
            mock_check.side_effect = subprocess.CalledProcessError(1, "cmd")
            duration = _get_video_duration("test.mp4")
            self.assertIsNone(duration)
    
    def test_time_str_to_seconds_standard_format(self):
        """测试标准时间格式转换"""
        result = _time_str_to_seconds("01:30:45.500")
        self.assertEqual(result, 5445.5)
    
    def test_time_str_to_seconds_no_milliseconds(self):
        """测试无毫秒的时间格式"""
        result = _time_str_to_seconds("00:05:30")
        self.assertEqual(result, 330.0)
    
    def test_time_str_to_seconds_edge_cases(self):
        """测试边界情况"""
        result = _time_str_to_seconds("00:00:00.001")
        self.assertEqual(result, 0.001)
        
        result = _time_str_to_seconds("10:00:00.000")
        self.assertEqual(result, 36000.0)
        
        result = _time_str_to_seconds("00:00:30.999")
        self.assertEqual(result, 30.999)
    
    def test_natural_sort_key_with_number(self):
        """测试包含数字的文件名排序"""
        result = _natural_sort_key("video_123_test.mp4")
        self.assertEqual(result, 123)
    
    def test_natural_sort_key_no_number(self):
        """测试不包含数字的文件名排序"""
        result = _natural_sort_key("video_test.mp4")
        self.assertEqual(result, -1)
    
    def test_natural_sort_key_multiple_numbers(self):
        """测试包含多个数字的文件名排序"""
        result = _natural_sort_key("video_001_test_002.mp4")
        self.assertEqual(result, 1)
        
        result = _natural_sort_key("001_video_002.mp4")
        self.assertEqual(result, 1)
    
    def test_natural_sort_key_edge_cases(self):
        """测试边界情况"""
        result = _natural_sort_key("")
        self.assertEqual(result, -1)
        
        result = _natural_sort_key("video.mp4")
        self.assertEqual(result, -1)
        
        result = _natural_sort_key("video_abc_test.mp4")
        self.assertEqual(result, -1)
    
    def test_calculate_speed_by_duration_short(self):
        """测试短静音片段的速度计算"""
        self.assertEqual(_calculate_speed_by_duration(1.0), 2)
        self.assertEqual(_calculate_speed_by_duration(2.0), 2)
        self.assertEqual(_calculate_speed_by_duration(3.9), 2)
    
    def test_calculate_speed_by_duration_medium(self):
        """测试中静音片段的速度计算"""
        self.assertEqual(_calculate_speed_by_duration(4.0), 2)
        self.assertEqual(_calculate_speed_by_duration(5.0), 3)
        self.assertEqual(_calculate_speed_by_duration(6.0), 3)
        self.assertEqual(_calculate_speed_by_duration(7.9), 4)
    
    def test_calculate_speed_by_duration_long(self):
        """测试长静音片段的速度计算"""
        self.assertEqual(_calculate_speed_by_duration(14.0), 7)
        self.assertEqual(_calculate_speed_by_duration(15.0), 8)
        self.assertEqual(_calculate_speed_by_duration(20.0), 8)
        self.assertEqual(_calculate_speed_by_duration(100.0), 8)

    @patch('cut_dense_video._time_str_to_seconds', side_effect=[0.0, 5.0])
    @patch('cut_dense_video._calculate_speed_by_duration', return_value=4)
    def test_process_silence_segment(self, mock_speed_calc, mock_time_conv):
        """测试静音片段处理"""
        commands = []
        _process_silence_segment(
            video_path="test.mp4",
            output_dir=self.test_dir,
            video_name="test_video",
            start_time="00:00:00.000",
            end_time="00:00:05.000",
            idx=1,
            parallel=False,
            commands=commands
        )
        self.assertEqual(len(commands), 1)
        self.assertIn("atempo=4", commands[0].command)
        self.assertIn("setpts=0.25*PTS", commands[0].command)

    @patch('os.path.exists', return_value=True)
    @patch('cut_dense_video.read_srt')
    @patch('subprocess.call')
    @patch('builtins.open', new_callable=mock_open)
    def test_cut_video(self, mock_file, mock_sub_call, mock_read_srt, mock_exists):
        """测试视频剪切功能"""
        mock_read_srt.return_value = [
            ("00:00:01.000", "00:00:03.000", "Hello"),
            ("00:00:05.000", "00:00:07.000", "World")
        ]
        video_path = os.path.join(self.test_dir, "test.mp4")
        srt_path = os.path.join(self.test_dir, "test.srt")
        
        output_dir = cut_video(video_path, srt_path, if_print=False)
        
        self.assertEqual(mock_sub_call.call_count, 2)
        self.assertTrue(os.path.exists(output_dir))

    @patch('os.listdir')
    @patch('subprocess.call')
    @patch('builtins.open', new_callable=mock_open)
    def test_concat_video(self, mock_file, mock_sub_call, mock_listdir):
        """测试视频合并功能"""
        mock_listdir.return_value = ["test_0_speech.mp4", "test_1_speech.mp4"]
        
        concat_video(self.test_dir, if_print=False)
        
        mock_file.assert_called_with(os.path.join(self.test_dir, "filelist.txt"), "a", encoding="utf-8")
        handle = mock_file()
        handle.write.assert_any_call(f"file '{os.path.join(self.test_dir, 'test_0_speech.mp4')}'\n")
        handle.write.assert_any_call(f"file '{os.path.join(self.test_dir, 'test_1_speech.mp4')}'\n")
        mock_sub_call.assert_called_once()
        self.assertIn("-c:a aac", mock_sub_call.call_args[0][0])


if __name__ == '__main__':
    unittest.main()