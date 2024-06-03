import base64

def cv2_to_base64(image):
    return base64.b64encode(image).decode()

def base64_to_cv2(base64_str):
    return base64.b64decode(base64_str)


def _check_image_file(path):
    img_end = {'jpg', 'bmp', 'png', 'jpeg', 'rgb', 'tif', 'tiff', 'gif'}
    return any([path.lower().endswith(e) for e in img_end])
