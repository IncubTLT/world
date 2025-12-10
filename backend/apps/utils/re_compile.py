import re

PUNCTUATION_RE = re.compile(r'[^\w\s]')

# Сопоставление символов с заменами
REPLACEMENTS = {
    # Тире и дефисы
    '—': '-', '–': '-', '−': '-',  # длинные тире и минус
    # Кавычки
    '“': '"', '”': '"',  # двойные кавычки типографские
    '‘': "'", '’': "'",  # одинарные кавычки типографские
    # Многоточие
    '…': '...',          # односимвольное многоточие
    # Спецсимволы брендов
    '©': '', '®': '', '™': '',
    # Стрелки
    '→': '->', '←': '<-', '⇒': '=>', '⇐': '<=',
    '➔': '->', '➡': '->', '⬅': '<-',
    # Спецсимволы дробей и делений
    '⁄': '/', '∕': '/',
    # Крестики, ссылки, обелиски
    '†': '', '‡': '',
    # Другие необычные знаки
    '¤': '',  # знак валюты
    '§': '',  # параграф
    '¶': '',  # абзац
    '※': '',  # астеризм
}

# Регулярки на спецобработку
REPLACE_RE = re.compile('|'.join(map(re.escape, REPLACEMENTS.keys())))
SPECIAL_SPACES_RE = re.compile(r'[\u00A0\u2007\u202F\u2009\u200B\u200C\u200D\u2060\uFEFF\u200A]')
CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
MULTIPLE_SPACES_RE = re.compile(r' {2,}')
MULTIPLE_POINT_RE = re.compile(r'\.{2,}')

STYLE_BLOCK_RE = re.compile(r'style="([^"]+)"', re.IGNORECASE)
COLOR_RE = re.compile(r'color\s*:\s*([^;]+)', re.IGNORECASE)


def remove_blackish_color_styles(text: str) -> str:
    def clean_style(match):
        style_content = match.group(1)

        def replace_color(m):
            color = m.group(1).strip().lower()
            try:
                if color.startswith('#'):
                    hex_val = color.lstrip('#')
                    if len(hex_val) == 3:
                        hex_val = ''.join(c * 2 for c in hex_val)
                    r = int(hex_val[0:2], 16)
                    g = int(hex_val[2:4], 16)
                    b = int(hex_val[4:6], 16)
                elif color.startswith('rgb'):
                    nums = re.findall(r'\d+\.?\d*', color)
                    r, g, b = [float(x) for x in nums[:3]]
                else:
                    return '' if color in ('black',) else m.group(0)

                if max(r, g, b) < 50:
                    return ''
            except Exception:
                pass
            return m.group(0)

        new_style = COLOR_RE.sub(replace_color, style_content)
        new_style = new_style.strip().strip('; ')
        return f'style="{new_style}"' if new_style else ''

    return STYLE_BLOCK_RE.sub(clean_style, text)


def normalize_text(text: str) -> str:
    text = remove_blackish_color_styles(text)
    text = REPLACE_RE.sub(lambda m: REPLACEMENTS[m.group(0)], text)
    text = SPECIAL_SPACES_RE.sub(' ', text)
    text = CONTROL_CHARS_RE.sub('', text)
    text = text.replace('\r', ' ').replace('\t', ' ')
    text = MULTIPLE_POINT_RE.sub(lambda m: m.group(0) if len(m.group(0)) == 3 else '.', text)

    return text
