from django.shortcuts import render
from django.http import JsonResponse
from .utils import *
import re


# Create your views here.
def image_to_table(request):
    # 初始化文本检测文本识别模型
    ocr = PaddleOCR(use_angle_cls=True, lang="ch")

    # 保存图片
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        # 获取上传的图片文件名
        image_filename = image_file.name
        # 构造保存路径，这里假设保存在 MEDIA_ROOT 目录下的 images 文件夹中
        save_path = os.path.join(os.path.dirname(__file__),'data/photos', image_filename)
        # 保存图片到指定路径
        with open(save_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)
    file_path = save_path

    # ---识别图片来自哪个医院---

    # 获取已有数据的医院
    folder_path = os.path.join(os.path.dirname(__file__),'info')
    files_and_folders = os.listdir(folder_path)
    hospital_names = [f for f in files_and_folders if os.path.isdir(os.path.join(folder_path, f))]

    # 将所有文本进行匹配
    cordinates = getImageInfo(file_path, ocr)
    # print(cordinates)

    hospital_name = ''
    for cordinate in cordinates:
        tag = 0
        for hospital in hospital_names:
            if hospital in cordinate[1][0]:
                hospital_name = hospital
                tag = 1
                break
        if tag == 1:
            break

    # 根据所选医院加载相关信息
    if hospital_name != '':
        # 读取 全称-参考值 文件并解析为字典, 数据格式为{"全称":"参考值"}
        with open(os.path.join(os.path.dirname(__file__), 'info', hospital_name, 'range.json'), 'r', encoding='utf-8') as json_file:
            range_data = json.load(json_file)
        # 读取 全称-单位 文件并解析为字典, 数据格式为{"全称":"单位"}
        with open(os.path.join(os.path.dirname(__file__),'info',hospital_name,'unit.json'), 'r', encoding='utf-8') as json_file:
            unit_data = json.load(json_file)
    else :
         # 读取 全称-参考值 文件并解析为字典, 数据格式为{"全称":"参考值"}
        with open(os.path.join(os.path.dirname(__file__), 'info/其他/range.json'), 'r', encoding='utf-8') as json_file:
            range_data = json.load(json_file)
        # 读取 全称-单位 文件并解析为字典, 数据格式为{"全称":"单位"}
        with open(os.path.join(os.path.dirname(__file__),'info/其他/unit.json'), 'r', encoding='utf-8') as json_file:
            unit_data = json.load(json_file)
    # 获取当前图片坐标
    print(hospital_name)
    print(f'{file_path}:')
    # cordinates = getImageInfo(file_path, ocr)
    # print(cordinates) 
    original_cordinates = copy.deepcopy(cordinates)
    #cordinates格式如下:[[[[24.0, 458.0], [156.0, 456.0], [157.0, 483.0], [25.0, 485.0]], ('2015-08-30', 0.997961163520813)]]
    result =  []
    result_x_list = []
    #  写入数据到 CSV 文件
    header = ['项目', '结果', '状态', '单位', '参考范围']
    result.append(header)

    #确定“结果框”
    for text_info in cordinates:  
        if text_info[1][0] == "结果":
            result_x_list.append(calculate_center(text_info)[0])
        if text_info[1][0] == "结":
            result_x_list.append(calculate_center(text_info)[0])

    for text_info in cordinates:
        # 该检验项目在处理后的"全称:缩写"的字典中
        full_name = text_info[1][0]
        for key in range_data.keys():
            if key in full_name:
                full_name = key
                break
        if full_name in range_data:
            row_box_list = []
            full_name_box = text_info
            # name_box = find_most_similar_string_box(name_data[full_name], cordinates)
            # unit_box = find_most_similar_string_box(unit_data[full_name], cordinates)
            range_box = find_most_similar_string_box(range_data[full_name], cordinates)
            row_box_list.append(full_name_box)
            # row_box_list.append(name_box)
            # if name_box[1][0] == name_data[full_name]:
            #     row_box_list.append(name_box)
            if range_box is not None:
                row_box_list.append(range_box)
            # else:
            #     row_box_list.append(name_box)
            if len(row_box_list) == 2:
                # row_box_list第一个box是全称box，第二个box是参考范围box
                result_x = 0
                for result_x_item in result_x_list:
                    if result_x_item > calculate_center(row_box_list[0])[0] and result_x_item < calculate_center(row_box_list[1])[0]:
                        result_x = result_x_item
                        break
                res_box = calculate_res_box(row_box_list, original_cordinates , result_x)
                try:
                    res_float = float(re.search(r'\d+\.\d+|\d+', res_box[1][0]).group())
                    range_string = range_data[full_name]
                    state = ''
                    if '~' in range_string:
                        range_float = range_string.split('~')
                        range_float[0] = float(range_float[0])
                        range_float[1] = float(range_float[1])
                        if res_float < range_float[0]:
                            state = '↓' 
                        elif res_float > range_float[1]:
                            state = '↑'
                    elif '--' in range_string:
                        range_float = range_string.split('~')
                        range_float[0] = float(range_float[0])
                        range_float[1] = float(range_float[1])
                        if res_float < range_float[0]:
                            state = '↓' 
                        elif res_float > range_float[1]:
                            state = '↑'
                    elif '-' in range_string:
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
                except AttributeError:
                    state = ''
                except ValueError:
                    state = ''
                res_filter = ''

                if re.search(r'\d+\.\d+|\d+', res_box[1][0]) != None:
                    res_filter = re.search(r'\d+\.\d+|\d+', res_box[1][0]).group()
                row = [full_name, res_filter, state , "" if unit_data[full_name] is None else unit_data[full_name], "" if range_data[full_name] is None else range_data[full_name]]
                print(row)
                result.append(row)
    
    return JsonResponse(result, safe=False)