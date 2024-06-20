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

def getImageInfo(img_path, ocr):
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
    # 找到完全一样的直接返回
    for string_box in string_box_list:
        if str1 == string_box[1][0]:
            return string_box
    # 对于被包含的也直接返回
    for string_box in string_box_list:
        if str1 in string_box[1][0]:
            return string_box
    # 以上两种情况都不包括则返回相似度最高的
    print(str1)
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

# 通过直线得到结果值
# def calculate_res_box(box_list, all_box, box_num, result_x):
#     # print(box_list)
#     #确定直线方程
#     slope, intercept = calculate_slope_and_intercept(box_list)

#     # 遍历所有检测框，计算距离最近的三个检测框
#     points = [calculate_center(box) for box in all_box]
#     distances = []
#     for point in points:
#         distance = distance_to_line(point, slope, intercept)
#         distances.append(distance)
#     # 获取距离最近的三个检测框
#     closest_boxs_indices = np.argsort(distances)[:box_num]
#     closest_boxs = [all_box[i] for i in closest_boxs_indices]
#     sorted_boxs = sorted(closest_boxs, key=lambda x: x[0][0][0])
#     # print(sorted_boxs)

#     # 找出离横坐标离result_x最近的检测框
#     distance = []
#     for box in sorted_boxs:
#         distance.append(abs(calculate_center(box)[0] - result_x))
#     min_distance_index = distance.index(min(distance))
#     return sorted_boxs[min_distance_index]

def calculate_res_box(box_list, all_box, result_x):
    # print(box_list)
    #确定直线方程
    slope, intercept = calculate_slope_and_intercept(box_list)
    intersection_point = [result_x, slope * result_x + intercept]

    # 遍历所有检测框，计算距离交点最近检测框
    points = [calculate_center(box) for box in all_box]
    distances = []
    for point in points:
        distance = distance_to_intersection(point, intersection_point)
        distances.append(distance)
    min_distance_index = distances.index(min(distances))
    if all_box[min_distance_index][1][0] == '结' or all_box[min_distance_index][1][0] == '结果':
        min_distance = min(distances)
        second_min_distance = 1000
        for distance in distances:
            if distance < second_min_distance and distance != min_distance:
                second_min_distance = distance
        second_min_distance_index = distances.index(second_min_distance)
        return all_box[second_min_distance_index]
    else:
        return all_box[min_distance_index]
    # # 获取距离最近的三个检测框
    # closest_boxs_indices = np.argsort(distances)[:box_num]
    # closest_boxs = [all_box[i] for i in closest_boxs_indices]
    # sorted_boxs = sorted(closest_boxs, key=lambda x: x[0][0][0])
    # # print(sorted_boxs)

    # # 找出离横坐标离result_x最近的检测框
    # distance = []
    # for box in sorted_boxs:
    #     distance.append(abs(calculate_center(box)[0] - result_x))
    # min_distance_index = distance.index(min(distance))
    # return sorted_boxs[min_distance_index]

def distance_to_intersection(point, intersection_point):
    return ((point[0] - intersection_point[0]) ** 2 + (point[1] - intersection_point[1]) ** 2) ** 1/2