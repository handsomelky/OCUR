import os
import json
import time
import requests
from ..utils.ocrTools import _check_image_file, cv2_to_base64, base64_to_cv2
from ..common.config import cfg
from PySide6.QtCore import QThread, Signal
import socket


class TrainThread(QThread):
    progressTrainUpdated = Signal(int)  # 用于更新进度
    TrainCompleted = Signal(list)  # 用于补丁完成后发送结果


    def __init__(self, train_dataset_dir, size, base_path=None):
        super().__init__()
        self.train_dataset_dir = train_dataset_dir
        self.size = size
        self.base_path = base_path

    def check_network_connection(self, host, port, timeout=5):
        try:
            socket.create_connection((host, port), timeout=timeout)
            return True
        except socket.error as err:
            return False

    def run(self):
        
        # 随机生成一个uuid
        uuid = str(time.time()).replace(".", "")
        host = cfg.serviceIP.value
        port = cfg.servicePort.value
        url = f"http://{host}:{port}/train/{uuid}"

        if not self.check_network_connection(host, port):
            error_message = "无法连接到服务器，请检查网络连接或服务器配置。"
            print(error_message)
            return


        save_path = os.path.join(self.base_path, 'patches')

        # 计算总共有多少张图片
        train_paths = [os.path.join(self.train_dataset_dir, f) for f in os.listdir(self.train_dataset_dir) if os.path.isfile(os.path.join(self.train_dataset_dir, f))]

        total_images = len(train_paths)

        processed_images = 0

        for img_file in train_paths:
            processed_images += 1
            is_last = processed_images == total_images

            if not _check_image_file(img_file):
                continue

            with open(img_file, 'rb') as file:
                image_data = file.read()
            image_name = os.path.basename(img_file)

            image_base64 = cv2_to_base64(image_data)
            data = {
                "image": image_base64,
                "image_name": time.strftime("%Y%m%d%H%M%S", time.localtime())+"_"+image_name,
                "size": self.size,
                "is_last": is_last
            }
            response = requests.post(url=url, data=data)
            if response.status_code != 200:
                print(f"Error sending image {image_name}: {response.text}")
                continue
            
            self.progressTrainUpdated.emit((processed_images / total_images) * 100)
        progeress_url = f"http://{host}:{port}/progress/{uuid}"
        return True
        # while True:
        #     response = requests.get(progeress_url)
        #     if response.status_code == 200:
        #         progress_data = response.json()
        #         if progress_data['status'] == 'completed':
        #             self.trainCompleted.emit(progress_data['results'])
        #             break
        #         self.progressTrainUpdated.emit(progress_data['progress'])
        #     time.sleep(10)  # 每10秒查询一次

    