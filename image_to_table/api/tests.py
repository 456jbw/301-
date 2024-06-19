import json
import os
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
import numpy as np
import csv
import editdistance
import copy
from scipy.optimize import curve_fit

# 指定目标文件夹路径
print()
current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)
folder_path = os.path.join(current_directory,'info')
# 获取文件夹下的所有文件和文件夹名称
files_and_folders = os.listdir(folder_path)
print(files_and_folders)
# 过滤出所有文件的名称
files = [f for f in files_and_folders if os.path.isdir(os.path.join(folder_path, f))]

# 打印所有文件的名称
for file in files:
    print(file)