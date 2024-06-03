import os
import json
import time
import requests
from ..utils.ocrTools import _check_image_file, cv2_to_base64, base64_to_cv2
from ..common.config import cfg
from PySide6.QtCore import QThread, Signal


class PatchThread(QThread):
    progressFullUpdated = Signal(int)  # 用于更新进度
    patchFullCompleted = Signal(list)  # 用于补丁完成后发送结果
    progressPartUpdated = Signal(int)  # 用于更新部分进度
    patchPartCompleted = Signal(dict)  # 用于部分补丁完成后发送结果


    def __init__(self, file_paths, strength, style, ispart=False, bboxs=None, base_path=None):
        super().__init__()
        self.img_path_list = file_paths
        self.patch_strength = strength
        self.patch_style = style
        self.ispart = ispart
        self.bboxs = bboxs
        self.base_path = base_path

    def run(self):

        url = f"http://{cfg.serviceIP.value}:{cfg.servicePort.value}/patch"
        if self.ispart == False:

            patch_results = []  # List to store results from all images

            save_path = os.path.join(self.base_path, 'results/patched_images')

            total_images = len(self.img_path_list)
            processed_images = 0

            for img_file in self.img_path_list:
                if not _check_image_file(img_file):
                    continue

                with open(img_file, 'rb') as file:
                    image_data = file.read()
                image_name = os.path.basename(img_file)

                image_base64 = cv2_to_base64(image_data)
                data = {
                    "image": image_base64,
                    "strength": self.patch_strength,
                    "style": self.patch_style,
                    "image_name": time.strftime("%Y%m%d%H%M%S", time.localtime())+"_"+image_name,
                    "ispart": "false"
                }
                response = requests.post(url=url, data=data)
                if response.status_code == 200:
                    result = response.json()
                    image_base64 = result[0]["merge_image"]
                    image_data = base64_to_cv2(image_base64)
                    patched_image_path = os.path.join(save_path, image_name)

                    with open(patched_image_path, 'wb') as f:
                        f.write(image_data)

                    patch_results.append(patched_image_path)

                    
                else:
                    print("Failed to process image '{}'. Status code: {}".format(image_name, response.status_code))

                processed_images += 1
                self.progressFullUpdated.emit((processed_images / total_images) * 100)
            self.patchFullCompleted.emit(patch_results)
        else:
            save_path = os.path.join(self.base_path, 'results/patched_image_part')
            processed_images = 0
            total_images = 1
            processed_images = 0
            with open(self.img_path_list, 'rb') as file:
                image_data = file.read()
            image_name = os.path.basename(self.img_path_list)
            image_base64 = cv2_to_base64(image_data)
            self.bboxs = json.dumps(self.bboxs)
            data = {
                "image": image_base64,
                "strength": self.patch_strength,
                "style": self.patch_style,
                "image_name": time.strftime("%Y%m%d%H%M%S", time.localtime())+"_"+image_name,
                "ispart": "true",
                "bboxs": self.bboxs
            }
            response = requests.post(url=url, data=data)
            if response.status_code == 200:
                result = response.json()
                image_base64 = result[0]["merge_image"]
                image_data = base64_to_cv2(image_base64)
                patched_image_path = os.path.join(save_path, image_name)
                with open(patched_image_path, 'wb') as f:
                    f.write(image_data)
                patch_results = patched_image_path
            else:
                print("Failed to process image '{}'. Status code: {}".format(image_name, response.status_code))
            processed_images += 1
            self.progressPartUpdated.emit(processed_images * 100)
            self.patchPartCompleted.emit(patch_results)
