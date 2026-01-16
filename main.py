from pathlib import Path

import cv2

from DetectionAnnotationViewer import DetectionAnnotationViewer
import logging
from SegmentationAnnotationViewer import SegmentationAnnotationViewer
from Visualizer import draw_bounding_box

if __name__ == "__main__":
    images_path = Path(r"D:\data\detection_optical\db")
    annotations_path = Path(r"D:\data\detection_optical\db")

    annotation_viewer = DetectionAnnotationViewer(
        images_path,
        annotations_path,
        cls2color={
            0: (255, 0, 0),
            1: (255, 0, 0),
            2: (255, 255, 0),
            3: (255, 255, 0),
            4: (0, 255, 0),
            5: (0, 255, 255),
            6: (255, 0, 255),
            7: (255, 0, 255),
            8: (255, 0, 255),
            9: (255, 0, 255),
            10: (255, 0, 255),
            11: (255, 0, 255),
        },
        recycle_path=Path(r"D:\data\detection_optical\validation")
    )

    annotation_viewer.logger.setLevel(logging.INFO)

    annotation_viewer.mainloop()