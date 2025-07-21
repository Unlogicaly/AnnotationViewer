from pathlib import Path
from DetectionAnnotationViewer import DetectionAnnotationViewer
import logging
from SegmentationAnnotationViewer import SegmentationAnnotationViewer


if __name__ == "__main__":
    images_path = Path(r"D:\data\wires\new\images")
    annotations_path = Path(r"D:\data\wires\new\labels")

    # root = tk.Tk()
    annotation_viewer = SegmentationAnnotationViewer(
        images_path,
        annotations_path,
        cls2color={
            0: (255, 180, 0),
            1: (255, 0, 0),
            2: (255, 0, 160),
            3: (0, 125, 100),
        },
        recycle_path=Path(r"D:\data\wires\recycled"),
        mode="split"
    )

    annotation_viewer.logger.setLevel(logging.INFO)

    annotation_viewer.mainloop()