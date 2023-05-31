import re


def if_eng_only_sentence(content) -> bool:
    if re.match(r"^[a-zA-Z,'， \.?？]+$", content):
        return True
    else:
        return False


def eng_only_sentence_len(content) -> int:
    return len(re.findall(r"[a-zA-Z]", content))
