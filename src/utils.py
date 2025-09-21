import re


def create_html_with_ruby(text: str, font_size: str = "1.4rem", rt_font_size: str = "0.9rem") -> str:
    """
    将带括号的日文文本转换为带有ruby标签的HTML

    参数:
    text (str): 包含日文和括号内注音的文本，如"色褪(いろあ)せた"

    返回:
    str: 生成的HTML内容
    """
    # 正则表达式用于匹配汉字和注音
    pattern = r"([一-龯々]+)\(([ぁ-んァ-ンー]+)\)"

    # 找到上一个匹配结束的位置
    last_end = 0

    # HTML头部
    html_content = f"<span style='font-size: {font_size};'>"

    # 处理文本中的每一个匹配
    for match in re.finditer(pattern, text):
        # 添加匹配前的普通文本
        if match.start() > last_end:
            text_before = text[last_end : match.start()]
            if text_before:
                # 将换行符转换为HTML的<br>标签
                text_before = text_before.replace("\n", "<br>\n")
                html_content += text_before

        # 添加带注音的汉字
        kanji = match.group(1)
        reading = match.group(2)
        html_content += (
            f"<ruby>{kanji}<rt style='font-size: {rt_font_size}; font-weight: normal;'>{reading}</rt></ruby>"
        )

        # 更新上一个匹配结束的位置
        last_end = match.end()

    # 添加最后一个匹配后的普通文本
    if last_end < len(text):
        text_after = text[last_end:]
        if text_after:
            # 将换行符转换为HTML的<br>标签
            text_after = text_after.replace("\n", "<br>\n")
            html_content += text_after

    # HTML尾部
    html_content += "</span>"

    return html_content


if __name__ == "__main__":
    ruby = create_html_with_ruby("一人一人(ひとりひとり)の考え(かんがえ)を大事(だいじ)にしましょう。")
    print(ruby)
