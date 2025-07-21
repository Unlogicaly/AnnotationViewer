from pathlib import Path
from DetectionAnnotationViewer import DetectionAnnotationViewer
import logging


if __name__ == "__main__":
    images_path = Path(r"D:\data\detection_optical\db\filtered\misc")
    annotations_path = images_path

    # root = tk.Tk()
    annotation_viewer = DetectionAnnotationViewer(
        images_path,
        annotations_path,
        {
            0: (255, 180, 0),
            1: (255, 0, 0),
            2: (255, 100, 0),
        }
    )

    annotation_viewer.logger.setLevel(logging.INFO)

    annotation_viewer.mainloop()