def detect(img, page_num):
    import pytesseract
    from PIL import Image
    data = pytesseract.image_to_data(Image.fromarray(img), output_type='dict')
    zones = []
    for i in range(len(data['text'])):
        text = data['text'][i]
        if len(text) > 5:  # Simple heuristic for zones
            zones.append({
                'page': page_num,
                'text': text,
                'conf': data['conf'][i],
                'left': data['left'][i],
                'top': data['top'][i],
                'width': data['width'][i],
                'height': data['height'][i]
            })
    return zones
