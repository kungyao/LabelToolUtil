import io
import os
import base64
import argparse
import json

import xml.etree.ElementTree as ET

from PIL import Image

def img_to_base64(imgPath : str) -> str:
    image_data = None
    with open(imgPath, 'rb') as f:
        image_data = f.read()
        f.close()
    return str(base64.b64encode(image_data).decode('utf-8'))

def get_args():
    parser = argparse.ArgumentParser(description='Parse Manga109 annotation xml to LabelMe json format',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', type=str, help='Manga109 data folder', dest='rootFolder')
    return parser.parse_args()

def parse(rootFolder : str):
    xml_folder = os.path.join(rootFolder, 'annotations')
    img_folder = os.path.join(rootFolder, 'images')

    for xml in os.listdir(xml_folder):
        xml_path = os.path.join(xml_folder, xml)

        # parse xml
        tree = ET.parse(xml_path)
        root = tree.getroot()

        manga_name = root.attrib['title']
        manga_folder = os.path.join(img_folder, manga_name)
        
        for child in root:
            # parse Manga109 xml 'page' element
            if child.tag == 'pages':
                for page in child:
                    img_name = page.attrib['index'].zfill(3) + '.jpg'
                    img_path = os.path.join(manga_folder, img_name)
                    image = Image.open(img_path)

                    shape = []
                    default_label = 'a'
                    for element in page:
                        if element.tag == 'text':
                            attr = element.attrib
                            if int(attr['xmin']) < int(attr['xmax']) and int(attr['ymin']) < int(attr['ymax']):
                                shape_data = {
                                    'label' : default_label,
                                    'points' : [
                                        [
                                            int(attr['xmin']),
                                            int(attr['ymin'])
                                        ],
                                        [
                                            int(attr['xmax']),
                                            int(attr['ymax'])
                                        ]
                                    ],
                                    'group_id' : None,
                                    'shape_type' : 'rectangle',
                                    'flags' : {}
                                }
                                shape.append(shape_data)

                    # create LabelMe json file
                    json_path = os.path.join(manga_folder, img_name.split('.')[0] + '.json')
                    with open(json_path, 'w') as fp:
                        data = {
                            'version' : '4.5.5',
                            'flags' : {},
                            'shapes' : shape,
                            'imagePath' : img_name,
                            'imageData' : img_to_base64(img_path),
                            'imageHeight': image.size[1],
                            'imageWidth' : image.size[0],
                        }

                        data = json.dumps(data, indent=4, sort_keys=False)
                        fp.write(data)
                        fp.close()
        print(f'Parse {manga_name} End !')
    return


if __name__ == "__main__":
    args = get_args()

    parse(args.rootFolder)