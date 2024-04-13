import json
import os
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
import numpy as np
import csv
import editdistance

# 初始化文本检测文本识别模型
ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # need to run only once to download and load model into memory

# ---读取处理后的指标键值对---

# 读取 缩写-参考值 文件并解析为字典, 数据格式为{"缩写":"下限~上限"}
with open('info/processed/range.json', 'r', encoding='utf-8') as json_file:
    range_data = json.load(json_file)
# 读取 缩写-全称 文件并解析为字典, 数据格式为{"缩写":"全称"}
with open('info/processed/name.json', 'r', encoding='utf-8') as json_file:
    name_data = json.load(json_file)

# ---获取图片名称---
    
def get_image_files(folder_path):
    image_files = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith(('.png', '.jpg')):
            file_path = os.path.join(folder_path, file_name)
            image_files.append(file_path)
    return image_files

# 指定文件夹路径
folder_path = 'data'

# 获取文件夹中所有的 PNG 或 JPG 图片文件名
image_files = get_image_files(folder_path)
print(image_files)

# ---获取图片坐标函数---

def getImageInfo(img_path):
    result = ocr.ocr(img_path, cls=True)
    # print(img_path, ":", result)
    cordinates = []
    for idx in range(len(result)):
        res = result[idx]
        # print(res)
        for line in res:
            cordinates.append(line)
    return cordinates

# ---计算字符串相似度函数---

def levenshtein_similarity(str1, str2):
    distance = editdistance.eval(str1, str2)
    similarity = 1 - (distance / max(len(str1), len(str2)))
    return similarity
def find_most_similar_string(str1, string_list, abbreviation):
    max_similarity = -1
    most_similar_string = None
    for string in string_list:
        similarity = levenshtein_similarity(str1, string[1][0])
        # if abbreviation == 'LACT':
        #     print(f'{str1} and {string[1][0]}: {similarity}')
        if similarity > max_similarity:
            max_similarity = similarity
            most_similar_string = string
    return most_similar_string

# ---计算直线和最近文本框函数---

# 计算两点之间的斜率和截距
def calculate_slope_and_intercept(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    if x2 - x1 == 0:
        slope = None  # 无穷大斜率
        intercept = x1
    else:
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
    return slope, intercept

# 计算点到直线的距离
def distance_to_line(point, slope, intercept):
    x, y = point
    if slope is None:  # 无穷大斜率
        distance = abs(x - intercept)
    else:
        distance = abs(slope * x - y + intercept) / np.sqrt(slope**2 + 1)
    return distance

# 计算由两个文本框确定的直线，以及离这条直线最近的文本框
def calculate_closet_text_box(abbreviation_box, range_box, box_list, box_num):
    #确定直线方程
    abbreviation_point = [(abbreviation_box[0][0][0] + abbreviation_box[0][2][0]) / 2, (abbreviation_box[0][0][1] + abbreviation_box[0][2][1]) / 2]
    range_point = [(range_box[0][0][0] + range_box[0][2][0]) / 2, (range_box[0][0][1] + range_box[0][2][1]) / 2]
    slope, intercept = calculate_slope_and_intercept(abbreviation_point, range_point)
    points = []
    # 遍历所有检测框，计算距离最近的三个检测框
    for box in box_list:
        x = (box[0][0][0] + box[0][2][0]) / 2
        y = (box[0][0][1] + box[0][2][1]) / 2
        points.append([x, y])
    # 计算距离距离
    distances = []
    for point in points:
        distance = distance_to_line(point, slope, intercept)
        distances.append(distance)
    # 获取距离最近的三个检测框
    closest_boxs_indices = np.argsort(distances)[:box_num]
    closest_boxs = [box_list[i] for i in closest_boxs_indices]
    sorted_boxs = sorted(closest_boxs, key=lambda x: x[0][0][0])
    sorted_texts = [box[1][0] for box in sorted_boxs]
    # 获取需要返回的数据
    abbreviation = abbreviation_box[1][0]
    full_name = name_data[abbreviation]
    result = sorted_texts[3]
    range =  range_box[1][0]
    return [abbreviation, full_name, result, range]

for file_path in image_files:
    # 获取当前图片坐标
    print(f'{file_path}:')
    cordinates = getImageInfo(file_path)
    # print(cordinates)
    #cordinates格式如下:[[[[24.0, 458.0], [156.0, 456.0], [157.0, 483.0], [25.0, 485.0]], ('2015-08-30', 0.997961163520813)]]
    index = 1
    result =  []
    for text_info in cordinates:
        # 该检验项目在处理后的"缩写:参考范围"的字典中
        if text_info[1][0] in range_data:
            abbreviation_box = text_info
            # print(text_info[1][0])
            range_box = find_most_similar_string(range_data[text_info[1][0]], cordinates, text_info[1][0])
            row = calculate_closet_text_box(abbreviation_box, range_box, cordinates, 5)
            row.insert(0, index)
            index += 1
            print(row)
            result.append(row)
    #  写入数据到 CSV 文件
    header = ['序号', '简称', '中文名称', '结果', '参考范围']
    output_csv_file_name = 'result/' + file_path.split("\\")[1].split(".")[0] + '.csv'
    with open(output_csv_file_name, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(header)
        writer.writerows(result)
