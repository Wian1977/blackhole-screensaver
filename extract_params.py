# -*- coding: utf-8 -*-
"""从源 HTML 抽取 PARAMS / QUALITY 为 params.py（单一真相源，避免与网页分叉）。
纯标准库；机械解析 JS 对象/数组字面量。"""
import re

SRC = '/home/u/ops/blackhole/黑洞模拟_湍流增强.html'
OUT = '/home/u/ops/blackhole/screensaver_native/params.py'


def strip_comments(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'//[^\n]*', '', s)
    return s


def js_to_py(objtext):
    t = strip_comments(objtext)
    t = re.sub(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", r"'\1':", t)
    t = re.sub(r'\btrue\b', 'True', t)
    t = re.sub(r'\bfalse\b', 'False', t)
    t = re.sub(r'\bnull\b', 'None', t)
    t = re.sub(r',(\s*[}\]])', r'\1', t)
    return t


def main():
    h = open(SRC, encoding='utf-8').read()

    i = h.index('const PARAMS = {')
    j = h.index('};', i)
    PARAMS = eval(js_to_py(h[i + len('const PARAMS = {'):j]))

    k = h.index('QUALITY = [')
    m = h.index('];', k)
    QUALITY = eval(js_to_py(h[k + len('QUALITY = ['):m]))

    out = '# -*- coding: utf-8 -*-\n'
    out += '# 由 extract_params.py 从网页 HTML 自动抽取，请勿手改；改源 HTML 后重跑本脚本。\n\n'
    out += 'PARAMS = ' + repr(PARAMS) + '\n\n'
    out += 'QUALITY = ' + repr(QUALITY) + '\n\n'
    out += "QUALITY_BY_NAME = {'high': QUALITY[0], 'mid': QUALITY[1], 'low': QUALITY[2]}\n"
    open(OUT, 'w', encoding='utf-8').write(out)
    print('PARAMS keys:', len(PARAMS))
    print('QUALITY entries:', len(QUALITY))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
