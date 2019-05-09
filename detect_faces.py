import numpy as np
import os
import cv2
import sys
import glob
import PIL
import shutil
import pickle

import utils.facealigner
import utils.detector 
import utils.visualization_utils

#------------------------------------------------------------------------------

def detect_in_images(geofence):
    """
    Detect faces in images.
    """
    # Setup result directory.
    result_dir = os.path.join('results', geofence, 'faces')
    if not os.path.isdir(result_dir):
        os.makedirs(result_dir)

    # Setup dataset.
    filenames = sorted(glob.glob(
        os.path.join('results', geofence, 'images', '*.jpg')
        ))[:100]
    dset = [np.asarray(PIL.Image.open(i)) for i in filenames] 

    # Detect faces using MTCNN.
    cur_face = 0
    for x in dset:
        img = PIL.Image.fromarray(x)
        bboxes, landmarks = utils.detector.detect_faces(img)
        img_drawn = utils.visualization_utils.show_bboxes(
            img, bboxes, landmarks
        )
        import matplotlib.pyplot as plt
        plt.imshow(img_drawn)
        plt.show()

        # Align faces.
        image = np.array(img.convert('RGB'))[:, :, ::-1] # CHW => HWC, RGB => BGR
        fa = utils.facealigner.FaceAligner(
            desiredLeftEye=(0.36, 0.5), desiredFaceWidth=178,
            desiredFaceHeight=218
        )
        for i in landmarks:
            faceAligned = fa.align(image, i)
            while True:
                cv2.imwrite(
                        os.path.join(result_dir, '%06d' % cur_face + '.png'),
                        faceAligned
                    )
                cur_face +=1 
                break

#------------------------------------------------------------------------------

if __name__ == '__main__':
    for geofence in ['gf0', 'gf1']:
        detect_in_images(geofence)
