import os
import cv2
from paddleocr import PPStructure,draw_structure_result,save_structure_res
from PIL import Image
import numpy as np


table_engine = PPStructure(show_log=True)
save_folder = './output'
folder_path = "data/北医三院jpg"

def get_image_files(folder_path):
    image_files = []
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        image_files.append(file_path)
    return image_files


def get_table_info(folder_path):
    image_files = get_image_files(folder_path)
    table_info = []
    for img_path in image_files:
        img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), -1)
        result = table_engine(img)
        save_structure_res(result, save_folder,os.path.basename(img_path).split('.')[0])
        for line in result:
            line.pop('img')

        font_path = 'doc/fonts/simfang.ttf' # PaddleOCR下提供字体包
        image = Image.open(img_path).convert('RGB')
        im_show = draw_structure_result(image, result,font_path=font_path)
        im_show = Image.fromarray(im_show)
        im_show.save(f'{os.path.basename(img_path).split(".")[0]}.jpg')
        table_info.append(result)
    return table_info

if __name__ == '__main__':
    table_info = get_table_info(folder_path)







