import pandas as pd
import json

def extract_range_to_json(file_path):
    # 读取 Excel 文件
    df = pd.read_excel(file_path)
    
    # 提取数据并转换为字典
    result = {}
    for index, row in df.iterrows():
        health_upper = row['健康上限']
        health_lower = row['健康下限']
        abbr = row['缩写']
        
        result[abbr] = f"{health_lower}-{health_upper}"
    
    return result

def extract_name_to_json(file_path):
    # 读取 Excel 文件
    df = pd.read_excel(file_path)
    
    # 提取数据并转换为字典
    result = {}
    for index, row in df.iterrows():
        full_name = row['全称']
        abbr = row['缩写']
        
        result[abbr] = full_name
    
    return result

# Excel 文件路径
excel_file_path = 'info/raw/检验检查-202208.xlsx'
extract_type = 'name'
if extract_type == 'range':
    # 提取为 缩写-参考范围 数据格式
    json_data = extract_range_to_json(excel_file_path)
    output_file_path = 'info/processed/range.json'
else:
    # 提取为 缩写-全称 数据格式
    json_data = extract_name_to_json(excel_file_path)
    output_file_path = 'info/processed/name.json'

with open(output_file_path, 'w', encoding='utf-8') as output_file:
    json.dump(json_data, output_file, ensure_ascii=False)

print(f"JSON 数据已写入到文件 {output_file_path}")
