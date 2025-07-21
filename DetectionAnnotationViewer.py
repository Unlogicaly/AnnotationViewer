from pathlib import Path
import logging
import tkinter as tk
import cv2
from AnnotationViewer import AnnotationViewer

logging.basicConfig(level=logging.INFO)


class DetectionAnnotationViewer(AnnotationViewer):

    def get_image_with_annotations(self):
        self.current_annotation_path = self.annotations_path / self.current_image_path.relative_to(
            self.images_path).parent / (self.current_image_path.stem + ".txt")
        if not self.current_annotation_path.exists():
            return False

        self.current_image = cv2.cvtColor(cv2.imread(self.current_image_path), cv2.COLOR_BGR2RGB)
        with open(self.current_annotation_path, "r") as annotation_file:
            annotations = annotation_file.read().split("\n")

        self.logger.info(f"found {len(annotations)} annotations for image {self.current_image_path}")

        image_h, image_w, _ = self.current_image.shape

        for annotation in annotations:
            if annotation == "":
                continue
            cls, x, y, w, h = map(float, annotation.split(" "))
            cls = int(cls)
            x1 = int((x - w / 2) * image_w)
            y1 = int((y - h / 2) * image_h)
            x2 = int((x + w / 2) * image_w)
            y2 = int((y + h / 2) * image_h)

            cv2.rectangle(self.current_image, (x1, y1), (x2, y2), self.cls2color[cls], 1)
            cv2.putText(self.current_image, str(cls), (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.cls2color[cls],
                        2)

        cv2.putText(self.current_image, str(self.current_image_path.relative_to(self.images_path)), (0, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        return True

