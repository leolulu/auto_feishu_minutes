import datetime
import re

import srt


def _compute_end_time(start_delta: datetime.timedelta, end_delta: datetime.timedelta, content: str, max_delta_second):
    if (
        isinstance(max_delta_second, int)
        and ((end_delta.seconds-start_delta.seconds) > max_delta_second)
        and re.search(r".*oh|ああ|うん|啊啊.*", content.lower())
    ):
        return srt.timedelta_to_srt_timestamp(
            start_delta + datetime.timedelta(seconds=max_delta_second)
        )
    else:
        return srt.timedelta_to_srt_timestamp(end_delta)


def read_srt(srt_file_path: str, max_delta_second=None):
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        data = f.read()
        srt_datas = srt.parse(data)
    srt_datas = list(srt_datas)

    result = []
    for srt_data in srt_datas:
        content = srt_data.content
        start_time = srt.timedelta_to_srt_timestamp(srt_data.start)
        start_time = start_time.replace(",", ".")
        end_time = _compute_end_time(srt_data.start, srt_data.end, content, max_delta_second)
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
    print(read_srt(r"C:\Users\pro3\Downloads\16356.srt", max_delta_second=3))
