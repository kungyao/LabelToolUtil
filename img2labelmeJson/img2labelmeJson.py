# 擷取對話框內的connected component，然後產生labelme格式的json檔案

import base64
import io
import os

import cv2
import json
import PIL.Image
from argparse import ArgumentParser

def img_array_to_b64(image, fileName):
    imageData = None
    with io.BytesIO() as f:
        ext = os.path.splitext(fileName)[1].lower()
        
        if ext in [".jpg", ".jpeg"]:
            format = "JPEG"
        else:
            format = "PNG"
        image.save(f, format=format)
        f.seek(0)
        imageData = f.read()
    return base64.b64encode(imageData).decode("utf-8")

# box   : region map {'xmax', 'xmin', 'ymax', 'ymin'}
def bBoxes_to_json_shape(bBoxes):
    shape = []
    for box in bBoxes:
        data = {
            "label": "None",
            "points": [
                [
                    int(box['xmin']),
                    int(box['ymin'])
                ],
                [
                    int(box['xmax']),
                    int(box['ymax'])
                ]
            ],
            "group_id": None,
            "shape_type": "rectangle",
            "flags": {}
        }
        shape.append(data)
    return shape

def ccRegion_to_json_shape(ccRegion, label="a"):
    shape = []
    for cc in ccRegion:
        ccData = {
            "label": str(label),
            "points": [
                [
                    int(cc[0][0]),
                    int(cc[0][1])
                ],
                [
                    int(cc[1][0]),
                    int(cc[1][1])
                ]
            ],
            "group_id": None,
            "shape_type": "rectangle",
            "flags": {}
        }
        shape.append(ccData)
    return shape

def connected_component_by_mask(filePath, labelPath):
    manga = cv2.imread(filePath)
    height, width = manga.shape[:2]

    thresImage =  cv2.cvtColor(manga, cv2.COLOR_BGR2GRAY)
    _, thresImage = cv2.threshold(thresImage, 150, 255, cv2.THRESH_BINARY)

    labelX = cv2.bitwise_not(thresImage)
    
    # 對話框label圖
    tmp_labelX = cv2.imread(labelPath, 0)
    # 二值化 轉為 binary image
    _, tmp_labelX = cv2.threshold(tmp_labelX, 150, 255, cv2.THRESH_BINARY)
    # 黑色的地方為manga bubble，所以反白後找connected component
    tmp_labelX = cv2.bitwise_not(tmp_labelX)
    # 和原圖的反白結果and，得到只有文字的區塊
    labelX = cv2.bitwise_and(labelX, tmp_labelX)

    minRegion = 30 * 30
    ccRegion = []
    # 找白色連通區域 (GLabels, GlabelImage, GStats, Gcentroids)
    GLabels, _, GStats, _ = cv2.connectedComponentsWithStats(labelX)
    for GLabel in range(1, GLabels, 1):
        if GStats[GLabel, cv2.CC_STAT_AREA] < minRegion:
            continue
        # top left
        p1 = [GStats[GLabel, cv2.CC_STAT_LEFT], GStats[GLabel, cv2.CC_STAT_TOP]]
        GObjectW = GStats[GLabel, cv2.CC_STAT_WIDTH]
        GObjectH = GStats[GLabel, cv2.CC_STAT_HEIGHT]
        # right bottom
        p2 = p1.copy()
        p2[0] = p2[0] + GObjectW
        p2[1] = p2[1] + GObjectH
        # container
        ccRegion.append([p1, p2])
    
    return ccRegion

# fileName  : fileName with extension。(manga.jpg)
# filePath  : image file path
# labelPath : bubble mask label
# outRoot   : output root folder, output file will be named with outRoot + fileName(without extension).json
def generateImgLabelJson(filePath, outRoot, ccRegion=None, bBoxes=None):
    if ccRegion == None and bBoxes == None :
        print('ccRegion and bBoxes are both None !')
        return

    if not os.path.exists(outRoot):
        print(f'{outRoot} do not exit, create it')
        os.makedirs(outRoot)

    fileName = os.path.basename(filePath)

    if ccRegion != None:
        shape = ccRegion_to_json_shape(ccRegion)
    elif bBoxes != None:
        shape = bBoxes_to_json_shape(bBoxes)
    
    image_pil = PIL.Image.open(filePath)
    imageData = str(img_array_to_b64(image_pil, fileName))
    
    name = os.path.splitext(fileName)[0] + '.json'
    with open(os.path.join(outRoot, name), 'w') as fp:
        data = {
            'version' : "4.5.5",
            "flags": {},
            "shapes": shape,
            "imagePath": fileName,
            "imageData": imageData,
            "imageHeight": image_pil.size[1],
            "imageWidth": image_pil.size[0]
        } 
        data = json.dumps(data, indent=4, sort_keys=True)
        fp.write(data)
        fp.close()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--MangaFolder', help='manga folder', type=str, default=None)
    parser.add_argument('--LabelFolder', help='bubble label folder', type=str, default=None)
    parser.add_argument('--OutputFolder', help='json output folder', type=str, default='./Output')
    
    if parser['MangaFolder']==None or parser['LabelFolder']==None:
        print('MangaFolder or LabelFolder is none')
    else:
        for fileName in os.listdir(os.path.join('./', parser['MangaFolder'])):
            filePath = os.path.join(parser['MangaFolder'], fileName)
            labelPath = os.path.join(parser['LabelFolder'], fileName)
            if not os.exist(labelPath):
                print(fileName + ' : label do not exist')
                continue
            ccRegion = connected_component_by_mask(filePath, labelPath)
            generateImgLabelJson(filePath, outRoot, ccRegion=ccRegion)
        