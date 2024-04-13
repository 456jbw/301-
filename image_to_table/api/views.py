from django.shortcuts import render
from django.http import JsonResponse
from .utils import *


# Create your views here.
def image_to_table(request):
    # 初始化文本检测文本识别模型
    ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # need to run only once to download and load model into memory

    # ---读取处理后的指标键值对---

    # 读取 全称-参考值 文件并解析为字典, 数据格式为{"全称":"参考值"}
    with open(os.path.join(os.path.dirname(__file__),'info/北医三院/range.json'), 'r', encoding='utf-8') as json_file:
        range_data = json.load(json_file)
    # 读取 全称-缩写 文件并解析为字典, 数据格式为{"缩写":"全称"}
    with open(os.path.join(os.path.dirname(__file__),'info/北医三院/name.json'), 'r', encoding='utf-8') as json_file:
        name_data = json.load(json_file)
    # 读取 全称-单位 文件并解析为字典, 数据格式为{"全称":"单位"}
    with open(os.path.join(os.path.dirname(__file__),'info/北医三院/unit.json'), 'r', encoding='utf-8') as json_file:
        unit_data = json.load(json_file)
    # 读取 错误名称-全称 文件并解析为字典, 数据格式为{"错误名称":"全称"}
    with open(os.path.join(os.path.dirname(__file__),'info/北医三院/error_name.json'), 'r', encoding='utf-8') as json_file:
        error_name_data = json.load(json_file) 
    # # 指定文件夹路径
    # folder_path = 'data/北医三院jpg_test'

    # # 获取文件夹中所有的 PNG 或 JPG 图片文件名
    # image_files = get_image_files(folder_path)
    save_path = ''
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        # 获取上传的图片文件名
        image_filename = image_file.name
        # 构造保存路径，这里假设保存在 MEDIA_ROOT 目录下的 images 文件夹中
        save_path = os.path.join(os.path.dirname(__file__),'data/北医三院backend', image_filename)
        # 保存图片到指定路径
        with open(save_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)
    
    file_path = save_path
    # 获取当前图片坐标
    print(f'{file_path}:')
    cordinates = getImageInfo(file_path, ocr)
    # print(cordinates) 
    original_cordinates = copy.deepcopy(cordinates)
    #cordinates格式如下:[[[[24.0, 458.0], [156.0, 456.0], [157.0, 483.0], [25.0, 485.0]], ('2015-08-30', 0.997961163520813)]]
    index = 1
    result =  []
    result_x = 0
    #  写入数据到 CSV 文件
    header = ['序号', '中文名称', '英文名称', '结果', '状态', '单位', '参考值']
    result.append(header)

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
            res_box = calculate_res_box(row_box_list, original_cordinates, 6, result_x)
            try:
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
            except ValueError:
                state = ''
            row = [index, full_name, name_box[1][0], res_box[1][0], state , "" if unit_box is None else unit_box[1][0], "" if range_box is None else range_box[1][0]]
            index += 1
            print(row)
            result.append(row)
    
    return JsonResponse(result, safe=False)