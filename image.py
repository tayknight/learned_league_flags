import cv2
import gif2numpy
import os
import pprint

from PIL import Image

from collections import Counter
from pathlib import Path
from skimage.color import rgb2lab, deltaE_cie76
from sklearn.cluster import KMeans

import matplotlib.pyplot as plt
import numpy as np

def RGB2HEX(color):
    return "#{:02x}{:02x}{:02x}".format(int(color[0]), int(color[1]), int(color[2]))

def get_image(image_path):
    try:
        evaluate = Image.open(image_path)
        if evaluate.format == 'GIF':
            np_images, extensions, image_specs = gif2numpy.convert(image_path)
            image = np_images[0]
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif evaluate.format == 'JPEG':
            image = cv2.imread(str(image_path))
        return image
    except Exception as e:
        print(e)
        return None

def get_colors(image, number_of_colors):
    try:
        modified_image = cv2.resize(image, (87, 154), interpolation = cv2.INTER_AREA)
        modified_image = modified_image.reshape(modified_image.shape[0]*modified_image.shape[1], 3)
        
        clf = KMeans(n_clusters = number_of_colors)
        labels = clf.fit_predict(modified_image)
        
        counts = Counter(labels)
        
        center_colors = clf.cluster_centers_
        # We get ordered colors by iterating through the keys
        ordered_colors = [center_colors[i] for i in counts.keys()]
        hex_colors = []
        rgb_colors = []
        index = 0
        for i in counts.keys():
            r = RGB2HEX(ordered_colors[index])
            hex_colors.append(r)
            o = ordered_colors[index]
            rgb_colors.append(o)
            index += 1
        # hex_colors = [RGB2HEX(ordered_colors[i]) for i in counts.keys()]
        # rgb_colors = [ordered_colors[i] for i in counts.keys()]

        return rgb_colors
    except SyntaxError:
        print('failed {}.'.format(image))
        return None
    except Exception as e:
        print(e)
        return None

def match_image_by_color(image, color, threshold = 60, number_of_colors = 10): 
    
    image_colors = get_colors(image, number_of_colors)
    if image_colors:
        if len(image_colors) < number_of_colors:
            number_of_colors = len(image_colors)

        selected_color = rgb2lab(np.uint8(np.asarray([[color]])))

        select_image = False
        for i in range(number_of_colors):
            curr_color = rgb2lab(np.uint8(np.asarray([[image_colors[i]]])))
            diff = deltaE_cie76(selected_color, curr_color)
            if (diff < threshold):
                select_image = True
        
        return select_image

def show_selected_images(images, color, threshold, colors_to_match):
    index = 1
    found = []
    for i in range(len(images)):
        selected = match_image_by_color(images[i]['image'],
                                        color,
                                        threshold,
                                        colors_to_match)
        if (selected):
            #plt.subplot(1, 5, index)
            #plt.imshow(images[i])
            #index += 1
            found.append(images[i]['path'])
    return found

COLORS = {
    'GREEN': [0, 128, 0],
    'BLUE': [0, 0, 128],
    'YELLOW': [255, 255, 0]
}

images = []
progress = 0
p = Path('images')

paths = []
for i in p.glob('**/*.gif'):
    paths.append(i)

paths = paths[:1000]

for i in paths:
    images.append({'path': i, 'image': get_image(i)})
    if progress % 1000 == 0:
        print(progress)
    progress += 1

found = show_selected_images(images, COLORS['YELLOW'], 60, 5)
print('{} images match'.format(len(found)))
pp = pprint.PrettyPrinter(indent=2)
pp.pprint(found)