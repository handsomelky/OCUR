import json
import os

def save_patch_info(file_path, patch_info):
    # 确保文件所在的目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        json.dump(patch_info, f, indent=4)

def load_patch_info(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# 使用示例
patch_info = {
    "patches": [
        {
            'patch_preview': ':/gallery/images/patches/advpatch1_50.png',
            'patch_name': 'Generic Patch 1',
            'patch_time': '-',
            'patch_strength': '100%',
            'patch_size': '30'
        },
        {
            'patch_preview': ':/gallery/images/patches/advpatch2_50.png',
            'patch_name': 'Generic Patch 2',
            'patch_time': '-',
            'patch_strength': '100%',
            'patch_size': '30'
        },
        {
            'patch_preview': ':/gallery/images/patches/advpatch3_50.png',
            'patch_name': 'Generic Patch 3',
            'patch_time': '-',
            'patch_strength': '100%',
            'patch_size': '30'
        },
    ]
}
