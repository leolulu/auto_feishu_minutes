import datetime
import re
from typing import Optional

import srt

from utils.re_util import eng_only_sentence_len, if_eng_only_sentence


CHAR_SPEAK_DURATION_RATIO = 0.08


def gen_custom_srt(word_level_sub_info):
    def int2str(offset):
        second = int(offset / 1000)
        milli_sec = (offset/1000 - second) * 1000
        delta = datetime.timedelta(seconds=second, milliseconds=milli_sec)
        return srt.timedelta_to_srt_timestamp(delta).replace(",", ".")

    srt_text = ""
    for idx, row in enumerate(word_level_sub_info):
        srt_section = ""
        offset_begin, offset_end, text = row
        offset_begin = int2str(offset_begin)
        offset_end = int2str(offset_end)
        srt_section = "\n{}\n{}\n{}\n".format(
            idx+1,
            "{} --> {}".format(offset_begin, offset_end),
            text
        )
        srt_text += srt_section
    return srt_text


def _compute_end_time(start_delta: datetime.timedelta, end_delta: datetime.timedelta, content: str, max_onomatopoeic_second, max_all_second, truncate_long_eng_sentence: Optional[bool]):
    if max_onomatopoeic_second:
        truncate_long_eng_sentence = True

    def get_seconds(end_delta, start_delta):
        delta = end_delta - start_delta
        return delta.seconds + delta.microseconds/1000/1000

    if (
        (isinstance(max_all_second, int) or isinstance(max_all_second, float))
        and (get_seconds(end_delta, start_delta) > max_all_second)
    ):
        return srt.timedelta_to_srt_timestamp(
            start_delta + datetime.timedelta(seconds=max_all_second)
        )
    elif (
        (isinstance(max_onomatopoeic_second, int) or isinstance(max_onomatopoeic_second, float))
        and (get_seconds(end_delta, start_delta) > max_onomatopoeic_second)
        and re.search(r".*oh|ah|ha|hmm|uh|mm|nps|ああ|あー|あっ|うん|呜呜|哈哈|啊啊|哼哼.*", content.lower())
    ):
        return srt.timedelta_to_srt_timestamp(
            start_delta + datetime.timedelta(seconds=max_onomatopoeic_second)
        )
    elif truncate_long_eng_sentence and if_eng_only_sentence(content):
        char_len = eng_only_sentence_len(content)
        expected_max_seconds = CHAR_SPEAK_DURATION_RATIO * char_len
        return srt.timedelta_to_srt_timestamp(
            start_delta + datetime.timedelta(seconds=min(expected_max_seconds, get_seconds(end_delta, start_delta)))
        )
    else:
        return srt.timedelta_to_srt_timestamp(end_delta)


def read_srt(srt_file_path: str, max_onomatopoeic_second=None, max_all_second=None, truncate_long_eng_sentence=None):
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        data = f.read()
        srt_datas = srt.parse(data)
    srt_datas = list(srt_datas)

    result = []
    for srt_data in srt_datas:
        content = srt_data.content
        start_time = srt.timedelta_to_srt_timestamp(srt_data.start)
        start_time = start_time.replace(",", ".")
        end_time = _compute_end_time(srt_data.start, srt_data.end, content, max_onomatopoeic_second, max_all_second, truncate_long_eng_sentence)
        end_time = end_time.replace(",", ".")
        result.append([start_time, end_time, content])
    return result


def if_srt_empty(srt_file_path: str):
    result = read_srt(srt_file_path)
    if len(result) > 0:
        return False
    else:
        return True


if __name__ == '__main__':
    print(read_srt(r"C:\Users\pro3\Downloads\16356.srt", max_onomatopoeic_second=3))
