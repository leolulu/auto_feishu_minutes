import srt


def read_srt(srt_file_path: str):
    with open(srt_file_path, 'r', encoding='utf-8') as f:
        data = f.read()
        srt_datas = srt.parse(data)
    srt_datas = list(srt_datas)

    result = []
    for srt_data in srt_datas:
        content = srt_data.content
        start_time = srt.timedelta_to_srt_timestamp(srt_data.start)
        start_time = start_time.replace(",", ".")
        end_time = srt.timedelta_to_srt_timestamp(srt_data.end)
        end_time = end_time.replace(",", ".")
        result.append([start_time, end_time, content])
    return result


if __name__ == '__main__':
    print(read_srt(r"C:\fuck\新建文件夹\自慰初体验（直播） (1).srt"))
