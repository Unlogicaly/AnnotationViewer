import logging
import threading
import time
import tkinter as tk
from abc import ABC, abstractmethod
import cv2
import numpy as np
from PIL import Image, ImageTk
from utils import iterate_images
from loguru import logger


class AnnotationViewer(tk.Tk, ABC):
    def __init__(self, images_path, annotations_path, recycle_path=None, cls2color=None, scroll_speed=0.5):
        super().__init__()

        self.window_width = 1920
        self.window_height = 1080
        self.geometry(f"{self.window_width}x{self.window_height}")

        self.scale_threshold_to_change_boxes_thickness = 1.5

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

        self.canvas = tk.Canvas(self, width=self.window_width, height=self.window_height, bg="black")
        self.canvas.pack(fill="both", expand=True)

        self.scrolling = False
        self.quit = False
        self.scroll_speed = scroll_speed
        self.scroll_thread: threading.Thread = None
        self.scroll()

        self.tkimage = None

        self.scale = 1.0
        self.min_scale = 0.1
        self.max_scale = 10.0
        self.offset_x = 0
        self.offset_y = 0
        self.original_image_size = None
        self.current_image_size = None
        self.current_image_center = None
        self.image_to_draw = None

        # --- Бинды клавиш ---
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

        # Windows/macOS:
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        # Linux:
        self.canvas.bind("<Button-4>", lambda e: self._on_mousewheel_linux(e, +1))
        self.canvas.bind("<Button-5>", lambda e: self._on_mousewheel_linux(e, -1))

        self._move_iterator(1)

        self.support_zoom = True

        self.logger.info("finished initialization")

    @abstractmethod
    def get_image_with_annotations(self):
        pass

    def _scroll(self):

        if not self.scrolling:
            self.after(500, self._scroll)
        else:
            time.sleep(0.01)
            self._move_iterator(1)
            self.after(int(self.scroll_speed * 1000), self._scroll)

    def scroll(self):

        self.scroll_thread = threading.Thread(target=self._scroll, daemon=True)
        self.scroll_thread.start()

    def switch_scroll(self):
        self.scrolling = not self.scrolling

    def adjust_scroll_speed(self, adjustment):
        self.scroll_speed = max(0, self.scroll_speed + adjustment)

    def draw_image(self):

        if self.image_to_draw is None:
            return

        image = Image.fromarray(self.image_to_draw)

        original_width, original_height = image.size
        aspect_ratio = original_width / original_height
        #
        # if (original_width > self.window_width) or (original_height > self.window_height):
        #     if (self.window_width / aspect_ratio) <= self.window_height:
        #         base_width = self.window_width
        #         base_height = int(self.window_width / aspect_ratio)
        #     else:
        #         base_height = self.window_height
        #         base_width = int(self.window_height * aspect_ratio)
        #
        #     self.logger.debug(f"Base fit size: {base_width}x{base_height}")
        # else:
        #     base_width, base_height = original_width, original_height

        if self.original_image_size is None:
            self.original_image_size = np.array([original_width, original_height])
            self.current_image_size = self.original_image_size.copy()
            self.current_image_center = self.current_image_size / 2

        self.canvas.delete("all")
        self.tkimage = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.tkimage, anchor=tk.NW)
        self.canvas.image = self.tkimage
        self.canvas.update()

    def _move_iterator(self, shift):

        self.original_image_size = None
        self.current_image_size = None
        self.current_image_center = None

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

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.image_to_draw = self.current_image.copy()

        self.draw_image()

    def delete_image(self):
        if self.recycle_path is not None:
            self.logger.info(f"putting image {self.current_image_path} to recycle folder")
            (self.recycle_path / self.current_image_path.relative_to(self.images_path)).parent.mkdir(parents=True, exist_ok=True)
            (self.recycle_path / self.current_annotation_path.relative_to(self.annotations_path)).parent.mkdir(parents=True, exist_ok=True)
            self.current_image_path.rename(self.recycle_path / self.current_image_path.relative_to(self.images_path))
            self.current_annotation_path.rename(self.recycle_path / self.current_annotation_path.relative_to(self.annotations_path))
        else:
            self.logger.info(f"deleting image {self.current_image_path}")
            self.current_image_path.unlink()
            self.current_annotation_path.unlink()

        self._move_iterator(1)

    def destroy(self):
        self.quit = True
        super().destroy()

    def _on_mousewheel(self, event: tk.Event):

        if not self.support_zoom:
            return

        if self.current_image is None or self.original_image_size is None:
            return

        steps = event.delta / 120.0
        if steps == 0:
            return

        self._zoom_at_canvas_point(event.x, event.y, steps)

    def _on_mousewheel_linux(self, event: tk.Event, direction: int):

        if self.current_image is None or self.original_image_size is None:
            return

        steps = direction
        self._zoom_at_canvas_point(event.x, event.y, steps)

    def _zoom_at_canvas_point(self, cx: int, cy: int, steps: float):

        logger.info(f"Mouse position: ({cx}, {cy})")

        new_scale = max(self.min_scale, min(self.max_scale, self.scale + 0.2 * steps))

        logger.info(f"New scale: {new_scale}")

        if abs(new_scale - self.scale) < 1e-6:
            return

        change_boxes_thickness = False
        if (new_scale - self.scale_threshold_to_change_boxes_thickness) * (self.scale - self.scale_threshold_to_change_boxes_thickness) <= 0:
            change_boxes_thickness = True

        mouse_position = np.array([cx, cy])

        mouse_position_relative = mouse_position / self.original_image_size
        mouse_position_on_original_image = mouse_position_relative * self.current_image_size + self.current_image_center - self.current_image_size / 2

        # current_image_center = (mouse_position_on_original_image + self.current_image_center) / 2
        alpha = 0.8
        current_image_center = alpha * self.current_image_center + (1.0 - alpha) * mouse_position_on_original_image
        current_image_size = self.original_image_size / new_scale

        logger.info(f"Mouse position on original image: {mouse_position_on_original_image}")
        logger.info(f"current image size: {current_image_size}")
        logger.info(f"current image center: {current_image_center}")

        left_border = int(current_image_center[0] - current_image_size[0] / 2)
        right_border = int(current_image_center[0] + current_image_size[0] / 2)
        top_border = int(current_image_center[1] - current_image_size[1] / 2)
        bottom_border = int(current_image_center[1] + current_image_size[1] / 2)

        logger.info(f"left border: {left_border}")
        logger.info(f"right border: {right_border}")
        logger.info(f"top border: {top_border}")
        logger.info(f"bottom border: {bottom_border}")

        left_pad = 0 if left_border > 0 else -left_border
        right_pad = 0 if right_border <= self.original_image_size[0] else right_border - self.original_image_size[0]
        top_pad = 0 if top_border > 0 else -top_border
        bottom_pad = 0 if bottom_border <= self.original_image_size[1] else bottom_border - self.original_image_size[1]

        new_image = self.current_image[
                    max(0, top_border): min(self.original_image_size[1], bottom_border),
                    max(0, left_border): min(self.original_image_size[0], right_border), ]

        new_image = np.pad(new_image, ((top_pad, bottom_pad), (left_pad, right_pad), (0, 0)), mode='constant',
                           constant_values=[0])

        self.current_image_center = current_image_center
        self.current_image_size = current_image_size

        self.image_to_draw = cv2.resize(new_image, (int(self.original_image_size[0]), int(self.original_image_size[1])))

        self.scale = new_scale

        if change_boxes_thickness:
            self.get_image_with_annotations()

        self.draw_image()
