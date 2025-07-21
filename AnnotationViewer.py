import logging
import threading
import time
import tkinter as tk
from abc import ABC, abstractmethod
import cv2
from PIL import Image, ImageTk
from utils import iterate_images


class AnnotationViewer(tk.Tk, ABC):
    def __init__(self, images_path, annotations_path, recycle_path=None, cls2color=None, scroll_speed=0.5):
        super().__init__()

        self.window_width = 1920
        self.window_height = 1080
        self.geometry(f"{self.window_width}x{self.window_height}")

        self.logger = logging.getLogger(__name__)

        self.images_path = images_path

        if annotations_path is None:
            self.annotations_path = self.images_path
        else:
            self.annotations_path = annotations_path

        self.images_paths = list(iterate_images(images_path, recursive=True))
        self.logger.info(f"found {len(self.images_paths)} images in {images_path}")

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

    @abstractmethod
    def get_image_with_annotations(self):
        pass

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

            if not self.get_image_with_annotations():
                self.logger.warning(f"Annotations for image {self.current_image_path} not found")
                shift = 1 if shift > 0 else -1
                continue

            break

        self.draw_image()

    def delete_image(self):

        if self.recycle_path is not None:
            self.logger.info(f"putting image {self.current_image_path} to recycle folder")
            (self.recycle_path / self.current_image_path.relative_to(self.images_path)).parent.mkdir(parents=True, exist_ok=True)
            self.current_image_path.rename(self.recycle_path / self.current_image_path.relative_to(self.images_path))
            self.current_annotation_path.rename(self.recycle_path / self.current_annotation_path.relative_to(self.images_path))
        else:
            self.logger.info(f"deleting image {self.current_image_path}")
            self.current_image_path.unlink()
            self.current_annotation_path.unlink()

        self._move_iterator(1)

    def destroy(self):
        self.quit = True
        super().destroy()
