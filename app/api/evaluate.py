import os
import json
import requests
import time
from ..utils.ocrTools import _check_image_file, cv2_to_base64, base64_to_cv2
from ..common.config import cfg
from PySide6.QtCore import QThread, Signal


class EvaluateThread(QThread):
    progressFullUpdated = Signal(int) 
    progressPartUpdated = Signal(int)
    evaluateFullCompleted = Signal(list)
    evaluatePartCompleted = Signal(dict)  


    def __init__(self, upload_files, patched_files, model, is_Patch=False, is_Part=False, base_path=None):
        super().__init__()
        self.upload_files = upload_files
        self.patched_files = patched_files
        self.model = model
        self.is_Patch = is_Patch
        self.is_Part = is_Part
        self.base_path = base_path

    def run(self):
        url = f"http://{cfg.serviceIP.value}:{cfg.servicePort.value}/{self.model}"
        if self.is_Patch:
            evaluated_results = []  

            save_path_for_upload = os.path.join(self.base_path, 'results/evaluated_upload_images')
            save_path_for_patched = os.path.join(self.base_path, 'results/evaluated_patched_images')

            if self.is_Part:
                save_path_for_upload = os.path.join(self.base_path, 'results/evaluated_upload_image_part')
                save_path_for_patched = os.path.join(self.base_path, 'results/evaluated_patched_image_part')


            total_images = len(self.upload_files) if not self.is_Part else 1

            processed_images = 0

            for i in range(total_images):
                if self.is_Part:
                    upload_file = self.upload_files
                else:
                    upload_file = self.upload_files[i]

                patched_file = self.patched_files[i]
                if not _check_image_file(upload_file) or not _check_image_file(patched_file):
                    continue 

                with open(upload_file, 'rb') as file:
                    upload_image_data = file.read()

                image_name = os.path.basename(upload_file)

                upload_image_base64 = cv2_to_base64(upload_image_data)

                with open(patched_file, 'rb') as file:
                    patched_image_data = file.read()
                patched_image_base64 = cv2_to_base64(patched_image_data)
                data = {
                    "upload_image": upload_image_base64,
                    "patched_image": patched_image_base64,
                    "model": self.model,
                    "image_name": time.strftime("%Y%m%d%H%M%S", time.localtime())+"_"+image_name,
                    "is_Patch": "true"
                }
                
                response = requests.post(url=url, data=data)
                if response.status_code == 200:
                    detection = json.loads(response.content)
                    clean_bbox_image = detection["clean_bbox_image"]
                    full_bbox_image = detection["full_bbox_image"]
                    ocr_result_clean = json.loads(detection["ocr_result_clean"])
                    ocr_result_full = json.loads(detection["ocr_result_full"])
                    result_full = detection["result_full"]
                    P = detection["P"]
                    R = detection["R"]
                    F = detection["F"]
                    recognized_character_rate = detection["recognized_character_rate"]
                    attack_success_rate = detection["attack_success_rate"]
                    average_edit_distance = detection["average_edit_distance"]

                    upload_image_path = os.path.join(save_path_for_upload, image_name)
                    image_data = base64_to_cv2(clean_bbox_image)
                    with open(upload_image_path, 'wb') as f:
                        f.write(image_data)

                    patched_image_path = os.path.join(save_path_for_patched, image_name)
                    image_data = base64_to_cv2(full_bbox_image)
                    with open(patched_image_path, 'wb') as f:
                        f.write(image_data)

                    evaluated_result = {
                        "image_name": image_name,
                        "ocr_result_clean": ocr_result_clean,
                        "ocr_result_full": ocr_result_full,
                        "P": P,
                        "R": R,
                        "F": F,
                        "recognized_character_rate": recognized_character_rate,
                        "attack_success_rate": attack_success_rate,
                        "average_edit_distance": average_edit_distance

                    }
                    evaluated_results.append(evaluated_result)
                    
                else:
                    print("Failed to process image '{}'. Status code: {}".format(image_name, response.status_code))

                processed_images += 1
                if self.is_Part:
                    self.progressPartUpdated.emit((processed_images / total_images) * 100)
                else:
                    self.progressFullUpdated.emit((processed_images / total_images) * 100)
            if self.is_Part:
                self.evaluatePartCompleted.emit(evaluated_results)
            else:
                self.evaluateFullCompleted.emit(evaluated_results)
        else:
            processed_images = 0
            save_path_for_upload = os.path.join(self.base_path, 'results/evaluated_upload_image_part')
            with open(self.upload_files, 'rb') as file:
                upload_image_data = file.read()
            upload_image_base64 = cv2_to_base64(upload_image_data)
            image_name = os.path.basename(self.upload_files)

            data = {
                    "upload_image": upload_image_base64,
                    "model": self.model,
                    "image_name": time.strftime("%Y%m%d%H%M%S", time.localtime())+"_"+image_name,
                    "is_Patch": "false"
                }
                
            response = requests.post(url=url, data=data)
            if response.status_code == 200:
                detection = json.loads(response.content)

                clean_bbox_image = detection["clean_bbox_image"]
                ocr_result_clean = json.loads(detection["ocr_result_clean"])

                upload_image_path = os.path.join(save_path_for_upload, image_name)
                image_data = base64_to_cv2(clean_bbox_image)
                with open(upload_image_path, 'wb') as f:
                    f.write(image_data)


                evaluated_result = {
                    "ocr_result_clean": ocr_result_clean
                }
                
            else:
                print("Failed to process image '{}'. Status code: {}".format(image_name, response.status_code))

            processed_images += 1
            self.progressPartUpdated.emit(processed_images * 100)
            self.evaluatePartCompleted.emit(evaluated_result)
        
