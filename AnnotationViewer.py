from pathlib import Path
import cv2
import logging
import tkinter as tk
from PIL import Image, ImageTk
import time
import threading


logging.basicConfig(level=logging.INFO)

def iterate_files(root_path, extensions=None, recursive=False):

    root_path = Path(root_path)

    if extensions is None:
        if recursive:
            iterator = root_path.rglob('*')
        else:
            iterator = root_path.glob('*')
        for item in iterator:
            if item.is_file() or not recursive:
                yield item
        return

    for extension in extensions:
        if extension[0] == ".":
            extension = extension[1:]

        if recursive:
            iterator = root_path.rglob(f"*.{extension}")
        else:
            iterator = root_path.glob(f"*.{extension}")

        for item in iterator:
            if item.is_file() or not recursive:
                yield item

    return


def iterate_images(root_path, recursive=False):
    extensions = ["jpg", "png", "jpeg", "tiff"]

    return iterate_files(root_path, extensions, recursive)


class AnnotationListWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.geometry("50x900")
        self.annotations_list = tk.Text(self, height=900, width=200, bg="white", fg="black", wrap=tk.WORD)
        self.annotations_list.pack(fill="both", expand=True)

    def update_annotations(self, annotations):
        self.annotations_list.delete(1.0, tk.END)
        self.annotations_list.insert(tk.END, "\n".join(annotations), "annotations")
        self.annotations_list.tag_configure("annotations", font=("verdana", 26, "bold"))


class AnnotationViewer(tk.Tk):
    def __init__(self, root_dir, recycle_path=None, cls2color=None, scroll_speed=0.5):
        super().__init__()

        self.window_width = 1920
        self.window_height = 1080
        self.geometry(f"{self.window_width}x{self.window_height}")

        self.logger = logging.getLogger(__name__)

        self.root_dir = root_dir

        self.images_paths = list(iterate_images(root_dir, recursive=True))
        self.logger.info(f"found {len(self.images_paths)} images in {root_dir}")

        self.current_index = -1
        self.current_image_path = None
        self.current_annotation_path = None
        self.current_image = None

        self.recycle_path = recycle_path
        self.logger.info(f"set recycle_path to {recycle_path}")

        if cls2color is None:
            self.cls2color = dict.fromkeys(range(10000), (0, 0, 0))
        else:
            self.cls2color = cls2color

        self.logger.info(f"set colors per class to {cls2color}")

        self.canvas = tk.Canvas(self, width=self.window_width, height=self.window_height)
        self.canvas.pack(fill="both", expand=True)

        self.scrolling = False
        self.quit = False
        self.scroll_speed = scroll_speed
        self.scroll_thread: threading.Thread = None
        self.scroll()

        self.annotations_list = AnnotationListWindow(self)

        self.tkimage = None

        self.bind("<Left>", lambda _: self._move_iterator(-1))
        self.bind("<Right>", lambda _: self._move_iterator(1))
        self.bind("<Control-Left>", lambda _: self._move_iterator(-10))
        self.bind("<Control-Right>", lambda _: self._move_iterator(10))
        self.bind("<Shift-Left>", lambda _: self._move_iterator(-100))
        self.bind("<Shift-Right>", lambda _: self._move_iterator(100))
        self.bind("<Delete>", lambda _: self.delete_image())
        self.bind("<space>", lambda _: self.switch_scroll())
        self.bind("<x>", lambda _: self.adjust_scroll_speed(-0.1))
        self.bind("<c>", lambda _: self.adjust_scroll_speed(0.1))

        self._move_iterator(1)

        self.logger.info("finished initialization")

        # self.pack()

    def get_image(self):
        self.current_annotation_path = self.current_image_path.parent / (self.current_image_path.stem + ".txt")
        if not self.current_annotation_path.exists():
            return False

        self.current_image = cv2.cvtColor(cv2.imread(self.current_image_path), cv2.COLOR_BGR2RGB)
        with open(self.current_annotation_path, "r") as annotation_file:
            annotations = annotation_file.read().split("\n")

        self.annotations_list.update_annotations(list(map(lambda annotation: annotation.split(" ")[0], annotations)))

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
            cv2.putText(self.current_image, str(cls), (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.cls2color[cls], 2)

        cv2.putText(self.current_image, str(self.current_image_path.relative_to(self.root_dir)), (0, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        return True

    def _scroll(self):
        while not self.quit:
            if not self.scrolling:
                time.sleep(0.5)
                continue
            self._move_iterator(1)
            time.sleep(self.scroll_speed)

    def scroll(self):
        self.scroll_thread = threading.Thread(target=self._scroll)
        self.scroll_thread.start()

    def switch_scroll(self):
        if not self.scroll_thread.is_alive():
            self.scroll()
        self.scrolling = not self.scrolling

    def adjust_scroll_speed(self, adjustment):
        self.scroll_speed = max(0, self.scroll_speed + adjustment)

    def draw_image(self):

        image = Image.fromarray(self.current_image)
        original_width, original_height = image.size
        aspect_ratio = original_width / original_height

        if (original_width > self.window_width) or (original_height > self.window_height):
            if (self.window_width / aspect_ratio) <= self.window_height:
                new_width = self.window_width
                new_height = int(self.window_width / aspect_ratio)
            else:
                new_height = self.window_height
                new_width = int(self.window_height * aspect_ratio)

            image = image.resize((new_width, new_height), Image.LANCZOS)
            self.logger.info(f"Resized image to: {new_width}x{new_height}")

        self.tkimage = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.tkimage, anchor=tk.NW)
        self.canvas.image = self.tkimage
        self.canvas.update()

    def _move_iterator(self, shift):

        while True:
            self.current_index += shift

            if self.current_index < 0:
                self.logger.warning("Reached start of images")
                self.current_index -= shift
                return

            if self.current_index >= len(self.images_paths):
                self.logger.warning("Reached end of images")
                self.current_index -= shift
                return

            self.current_image_path = self.images_paths[self.current_index]

            if not self.get_image():
                self.logger.warning(f"Annotations for image {self.current_image_path} not found")
                shift = 1 if shift > 0 else -1
                continue

            break

        self.draw_image()

    def delete_image(self):

        if self.recycle_path is not None:
            self.logger.info(f"putting image {self.current_image_path} to recycle folder")
            (self.recycle_path/self.current_image_path.relative_to(self.root_dir)).parent.mkdir(parents=True, exist_ok=True)
            self.current_image_path.rename(self.recycle_path/self.current_image_path.relative_to(self.root_dir))
            self.current_annotation_path.rename(self.recycle_path/self.current_annotation_path.relative_to(self.root_dir))
        else:
            self.logger.info(f"deleting image {self.current_image_path}")
            self.current_image_path.unlink()
            self.current_annotation_path.unlink()

        self._move_iterator(1)

    def destroy(self):
        self.quit = True
        super().destroy()


if __name__ == "__main__":
    root_dir = Path(r"D:\data\detection_optical\08_07_2025\recycled\cyclone")
    recycle_path = Path(r"D:\data\detection_optical\08_07_2025\recycled")

    # root = tk.Tk()
    annotation_viewer = AnnotationViewer(
        root_dir, recycle_path, {
            0: (255, 180, 0),
            1: (255, 0, 0),
            2: (255, 100, 0),
        }
    )
    annotation_viewer.logger.setLevel(logging.INFO)

    annotation_viewer.mainloop()

