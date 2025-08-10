import re

_CODE_PATTERN = re.compile(r'\b(CH|TB|C|SU|KT|SK|FL)\s*[\dA-Z-]+\b', re.IGNORECASE)

def detect(img, page_num):
    import pytesseract
    from PIL import Image
    data = pytesseract.image_to_data(Image.fromarray(img), output_type='dict')
    codes = []
    for i in range(len(data['text'])):
        text = data['text'][i]
        if _CODE_PATTERN.match(text):
            codes.append({
                'page': page_num,
                'text': text,
                'conf': data['conf'][i],
                'left': data['left'][i],
                'top': data['top'][i],
                'width': data['width'][i],
                'height': data['height'][i]
            })
    return codes

def normalise_code(code):
    normalized = code.upper()
    changes = [] if normalized == code else ['uppercased']
    return normalized, changes
