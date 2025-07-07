import gradio as gr
import cv2
import numpy as np
import torch
import easyocr
from PIL import Image, ImageDraw, ImageFont
import os
import requests
from pythainlp.util import normalize

# --------------------------
# Constants and Configuration
# --------------------------
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf"
FONT_PATH = "THSarabunNew.ttf"
OCR_LANGS = ['th', 'en']
OCR_CONFIDENCE_THRESHOLD = 0.1#0.4

# --------------------------
# Utilities
# --------------------------

def download_font(font_path: str, url: str) -> None:
    if not os.path.exists(font_path):
        print("Downloading Thai font...")
        r = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(r.content)

def load_font(size: int = 32) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size=size)
    except IOError:
        return ImageFont.load_default()

# --------------------------
# Model Initialization
# --------------------------

# Load YOLOv5s
yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)

# EasyOCR Reader
reader = easyocr.Reader(OCR_LANGS, gpu=torch.cuda.is_available())

# Ensure Thai font is available
download_font(FONT_PATH, FONT_URL)

# --------------------------
# Main Detection Function
# --------------------------

def detect_objects_and_text(image: Image.Image) -> Image.Image:
    image_np = np.array(image)

    # YOLO Object Detection
    results = yolo_model(image_np)
    annotated_img = np.squeeze(results.render())  # BGR image with boxes

    # Convert to PIL
    pil_img = Image.fromarray(annotated_img)
    draw = ImageDraw.Draw(pil_img)
    font = load_font()

    # Draw YOLO labels
    for *box, conf, cls in results.xyxy[0].tolist():
        x1, y1, x2, y2 = map(int, box)
        label = yolo_model.names[int(cls)]
        draw.rectangle([x1, y1, x2, y2], outline="blue", width=3)
        draw.text((x1, max(y1 - 30, 0)), label, fill="blue", font=font)

    # EasyOCR text detection
    ocr_results = reader.readtext(image_np)

    for bbox, text, conf in ocr_results:
        if conf < OCR_CONFIDENCE_THRESHOLD:
            continue

        # Clean up Thai text
        clean_text = normalize(text.strip())

        top_left = tuple(map(int, bbox[0]))
        bottom_right = tuple(map(int, bbox[2]))

        draw.rectangle([top_left, bottom_right], outline="green", width=3)
        draw.text(
            (top_left[0], max(top_left[1] - 30, 0)),
            clean_text,
            fill=(255, 0, 0),
            font=font,
            stroke_width=2,
            stroke_fill=(0, 0, 0)
        )

    return pil_img

# --------------------------
# Gradio UI Setup
# --------------------------

interface = gr.Interface(
    fn=detect_objects_and_text,
    inputs=gr.Image(type="pil", label="Upload Image"),
    outputs=gr.Image(type="pil", label="Detected Image"),
    title="📷 Thai + English Text + Object Detector",
    description="YOLOv5 + EasyOCR pipeline: detects objects and Thai/English text with confidence filtering and cleaned output.",
    theme="default",
    allow_flagging="never"
)

interface.launch()
