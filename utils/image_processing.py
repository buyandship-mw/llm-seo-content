import hashlib
import os
from io import BytesIO
from typing import Tuple

import requests
from PIL import Image


def download_image(url: str) -> Image.Image:
    """Download an image from a URL and return it as an RGB :class:`Image`."""
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def pad_to_square(img: Image.Image, color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """Pad an image to make it square without cropping."""
    width, height = img.size
    max_side = max(width, height)
    new_img = Image.new("RGB", (max_side, max_side), color)
    paste_x = (max_side - width) // 2
    paste_y = (max_side - height) // 2
    new_img.paste(img, (paste_x, paste_y))
    return new_img


def save_image_from_url(url: str, output_folder: str, color: Tuple[int, int, int] = (255, 255, 255)) -> str:
    """Download ``url`` and save a padded square image to ``output_folder``.

    Returns the path to the saved image.
    """
    if not url:
        raise ValueError("Image URL must not be empty")

    os.makedirs(output_folder, exist_ok=True)
    img = download_image(url)
    square_img = pad_to_square(img, color=color)
    filename = hashlib.sha256(url.encode()).hexdigest()[:16] + ".jpg"
    output_path = os.path.join(output_folder, filename)
    square_img.save(output_path)
    return output_path

if __name__ == "__main__":
    # Example usage
    url = "https://unicorn.lush.com/media/file_upload/9x16%20Wasabi%20Shan%20Kui%20Shampoo%20Cover%20Image%20_%20Lush%20Stories_21eb1c7e.jpg"
    output_folder = "./output_images"
    try:
        local_path = save_image_from_url(url, output_folder)
        print(f"Image saved to: {local_path}")
    except Exception as e:
        print(f"Error saving image: {e}")