import json
import os
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
import numpy as np
import csv
import editdistance
import copy
from scipy.optimize import curve_fit


# ---获取图片名称---
    
def get_image_files(folder_path):
    image_files = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith(('.png', '.jpg')):
            file_path = os.path.join(folder_path, file_name)
            image_files.append(file_path)
    return image_files


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

def find_most_similar_string_box(str1, string_box_list):
    if str1 == "":
        return None
    max_similarity = -1
    most_similar_string_box = None
    for string_box in string_box_list:
        similarity = levenshtein_similarity(str1, string_box[1][0])
        if similarity > max_similarity:
            max_similarity = similarity
            most_similar_string_box = string_box
    return most_similar_string_box

# ---计算直线和最近文本框函数---
def linear_func(x, m, b):
    return m * x + b
# 计算两点之间的斜率和截距
def calculate_slope_and_intercept(box_list):
    # box_list = [calculate_center(box) for box in box_list]
    # coordinates = np.array(box_list)
    # # 提取 x 和 y 值
    # x_data = coordinates[:, 0]
    # y_data = coordinates[:, 1]
    # # 使用最小二乘法拟合直线
    # coefficients = np.polyfit(x_data, y_data, 1)
    # # 提取斜率和截距
    # slope = coefficients[0]
    # intercept = coefficients[1]
    # return slope, intercept
    # print(box_list)
    box_list = [calculate_center(box) for box in box_list]
    x1, y1 = box_list[0]
    x2, y2 = box_list[1]
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
# 计算一个文本框的中心坐标
def calculate_center(box):
    return [(box[0][0][0] + box[0][2][0]) / 2, (box[0][0][1] + box[0][2][1]) / 2]

def calculate_middle(left_point, right_point):
    return [(left_point[0] + right_point[0]) / 2, (left_point[1] + right_point[1]) / 2]

# 计算由box_list中所有文本框确定的一条直线，以及离这条直线最近的文本框中从左到右的第index（从0开始）个文本框
def calculate_res_box(box_list, all_box, box_num):
    # print(box_list)
    #确定直线方程
    slope, intercept = calculate_slope_and_intercept(box_list)

    # 遍历所有检测框，计算距离最近的三个检测框
    points = [calculate_center(box) for box in all_box]
    distances = []
    for point in points:
        distance = distance_to_line(point, slope, intercept)
        distances.append(distance)
    # 获取距离最近的三个检测框
    closest_boxs_indices = np.argsort(distances)[:box_num]
    closest_boxs = [all_box[i] for i in closest_boxs_indices]
    sorted_boxs = sorted(closest_boxs, key=lambda x: x[0][0][0])
    # print(sorted_boxs)

    # 找出离横坐标离result_x最近的检测框
    distance = []
    state_box = None
    for box in sorted_boxs:
        distance.append(abs(calculate_center(box)[0] - result_x))
        if box[1][0] == "↑" or box[1][0] == "↓":
            state_box = box
    min_distance_index = distance.index(min(distance))
    return sorted_boxs[min_distance_index]


# 初始化文本检测文本识别模型
ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # need to run only once to download and load model into memory

# ---读取处理后的指标键值对---

# 读取 全称-参考值 文件并解析为字典, 数据格式为{"全称":"参考值"}
with open('info/北医三院/range.json', 'r', encoding='utf-8') as json_file:
    range_data = json.load(json_file)
# 读取 全称-缩写 文件并解析为字典, 数据格式为{"缩写":"全称"}
with open('info/北医三院/name.json', 'r', encoding='utf-8') as json_file:
    name_data = json.load(json_file)
# 读取 全称-单位 文件并解析为字典, 数据格式为{"全称":"单位"}
with open('info/北医三院/unit.json', 'r', encoding='utf-8') as json_file:
    unit_data = json.load(json_file)
# 读取 错误名称-全称 文件并解析为字典, 数据格式为{"错误名称":"全称"}
with open('info/北医三院/error_name.json', 'r', encoding='utf-8') as json_file:
    error_name_data = json.load(json_file) 
# 指定文件夹路径
folder_path = 'data/北医三院jpg_test'

# 获取文件夹中所有的 PNG 或 JPG 图片文件名
image_files = get_image_files(folder_path)

for file_path in image_files:
    # 获取当前图片坐标
    print(f'{file_path}:')
    cordinates = getImageInfo(file_path)
    # print(cordinates) 
    original_cordinates = copy.deepcopy(cordinates)
    #cordinates格式如下:[[[[24.0, 458.0], [156.0, 456.0], [157.0, 483.0], [25.0, 485.0]], ('2015-08-30', 0.997961163520813)]]
    index = 1
    result =  []
    result_x = 0
    for text_info in cordinates:  
        if text_info[1][0] == "结果":
            result_x = calculate_center(text_info)[0]
            break
    for text_info in cordinates:
        # 该检验项目在处理后的"全称:缩写"的字典中
        full_name = text_info[1][0]
        if full_name in error_name_data:
            full_name = error_name_data[full_name]
        if full_name in name_data:
            row_box_list = []
            full_name_box = text_info
            name_box = find_most_similar_string_box(name_data[full_name], cordinates)
            unit_box = find_most_similar_string_box(unit_data[full_name], cordinates)
            range_box = find_most_similar_string_box(range_data[full_name], cordinates)
            row_box_list.append(full_name_box)
            # row_box_list.append(name_box)
            if name_box[1][0] == name_data[full_name]:
                row_box_list.append(name_box)
            elif range_box is not None:
                row_box_list.append(range_box)
            else:
                row_box_list.append(name_box)
            res_box = calculate_res_box(row_box_list, original_cordinates, 6)
            res_float = float(res_box[1][0])
            range_string = range_box[1][0] if range_box is not None else ''
            state = ''
            if '-' in range_string:
                range_float = range_string.split('-')
                range_float[0] = float(range_float[0])
                range_float[1] = float(range_float[1])
                if res_float < range_float[0]:
                    state = '↓' 
                elif res_float > range_float[1]:
                    state = '↑'
            elif '>' in range_string:
                range_float = float(range_string.split('>')[1])
                if res_float < range_float:
                    state = '↓'
            elif '<' in range_string:
                range_float = float(range_string.split('<')[1])
                if res_float > range_float:
                    state = '↑'
            else:
                state = ''
            row = [index, full_name, name_box[1][0], res_box[1][0], state , "" if unit_box is None else unit_box[1][0], "" if range_box is None else range_box[1][0]]
            index += 1
            print(row)
            result.append(row)
    #  写入数据到 CSV 文件
    header = ['序号', '中文名称', '英文名称', '结果', '状态', '单位', '参考值']
    output_csv_file_name = 'result/' + file_path.split("\\")[1].split(".")[0] + '.csv'
    with open(output_csv_file_name, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(header)
        writer.writerows(result)
    break
