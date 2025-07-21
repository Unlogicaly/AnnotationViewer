from pathlib import Path


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
