from pathlib import Path
import logging
import tkinter as tk
import cv2
from AnnotationViewer import AnnotationViewer
import numpy as np

logging.basicConfig(level=logging.INFO)


class SegmentationAnnotationViewer(AnnotationViewer):

    def __init__(self, images_path, annotations_path, recycle_path=None, cls2color=None, scroll_speed=0.5, mode="merge"):
        self.mode = mode
        super().__init__(images_path, annotations_path, recycle_path, cls2color, scroll_speed)
        self.switch_mode_button = tk.Button(self, text="Switch mode", command=self.switch_mode)
        self.switch_mode_button.place(x=self.window_width - 100, y=20)

    def switch_mode(self):
        if self.mode == "merge":
            self.mode = "split"
        else:
            self.mode = "merge"

        self._move_iterator(0)

    def get_image_with_annotations(self):
        self.current_annotation_path = self.annotations_path / self.current_image_path.relative_to(self.images_path).parent / (self.current_image_path.stem + ".txt")

        if not self.current_annotation_path.exists():
            return False

        self.current_image = cv2.cvtColor(cv2.imread(self.current_image_path), cv2.COLOR_BGR2RGB)

        with open(self.current_annotation_path, "r") as annotation_file:
            annotations = annotation_file.read().split("\n")

        self.logger.info(f"found {len(annotations)} annotations for image {self.current_image_path}")

        mask = np.full_like(self.current_image, 255)

        image_h, image_w, _ = self.current_image.shape

        for annotation in annotations:
            if annotation == "":
                continue

            split_annotation = annotation.split(" ")

            cls = int(split_annotation[0])
            points = np.array(list(map(float, split_annotation[1:]))).reshape(-1, 2)

            points[:, 0] *= image_w
            points[:, 1] *= image_h

            points = points.astype(np.int32)

            cv2.fillPoly(mask, [points], self.cls2color[cls])

        if self.mode == "merge":
            self.current_image = cv2.addWeighted(self.current_image, 0.7, mask, 0.3, 0)

        elif self.mode == "split":

            aspect_ratio = self.window_width / self.window_height
            aspect_ratio_with_vertical_merge = image_w / (2 * image_h)
            aspect_ratio_with_horizontal_merge = (2 * image_w) / image_h

            deviation_with_vertical_merge = abs(aspect_ratio_with_vertical_merge - aspect_ratio)
            deviation_with_horizontal_merge = abs(aspect_ratio_with_horizontal_merge - aspect_ratio)

            if deviation_with_vertical_merge < deviation_with_horizontal_merge:
                self.current_image = np.vstack((self.current_image, mask))
                if self.current_image.shape[0] > self.window_height:
                    self.current_image = cv2.resize(self.current_image, (image_w * self.window_height / image_h, self.window_height))
            else:
                self.current_image = np.hstack((self.current_image, mask))
                if self.current_image.shape[1] > self.window_width:
                    self.current_image = cv2.resize(self.current_image, (self.window_width, image_h * self.window_width / image_w))

        cv2.putText(self.current_image, str(self.current_image_path.relative_to(self.images_path)), (0, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        return True
