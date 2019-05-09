import numpy as np
import cv2

#------------------------------------------------------------------------------

class FaceAligner:
    def __init__(
        self, desiredLeftEye=(0.35, 0.35), desiredFaceWidth=256,
        desiredFaceHeight=None
    ):
        self.desiredLeftEye = desiredLeftEye
        self.desiredFaceWidth = desiredFaceWidth
        self.desiredFaceHeight = desiredFaceHeight
        if self.desiredFaceHeight is None:
            self.desiredFaceHeight = self.desiredFaceWidth

    def align(self, image, landmarks):
        leftEye = (landmarks[1], landmarks[1+5])
        rightEye = (landmarks[0], landmarks[0+5])
        # Compute angle between eyes.
        dY = rightEye[1] - leftEye[1]
        dX = rightEye[0] - leftEye[0]
        angle = np.degrees(np.arctan2(dY, dX)) - 180
        # Compute the desired right eye x-coordinate.
        desiredRightEyeX = 1.0 - self.desiredLeftEye[0]
        # Determine scale of new image.
        dist = np.sqrt(dX**2 + dY**2)
        desiredDist = (desiredRightEyeX - self.desiredLeftEye[0])
        desiredDist *= self.desiredFaceWidth
        scale = desiredDist / dist
        # COmpute center coordinates.
        eyesCenter = (
            (leftEye[0] + rightEye[0]) // 2,
            (leftEye[1] + rightEye[1]) // 2
        )
        # Rotation matrix for rotating and scaling the face.
        M = cv2.getRotationMatrix2D(eyesCenter, angle, scale)
        # Update translation component of matrix.
        tX = self.desiredFaceWidth * 0.5
        tY = self.desiredFaceHeight * self.desiredLeftEye[1]
        M[0, 2] += (tX - eyesCenter[0])
        M[1, 2] += (tY - eyesCenter[1])
        # Apply the affine transformation.
        (w, h) = (self.desiredFaceWidth, self.desiredFaceHeight)
        output = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC)
        return output
