import cv2
import numpy as np
import math
import os
import glob
import csv
from matplotlib import pyplot as plt

# --- Helper functions (geometry, filtering) ---

def is_square(approx, area_thresh, ar_thresh=0.4):
    if len(approx) != 4 or not cv2.isContourConvex(approx):
        return False
    area = cv2.contourArea(approx)
    if area < area_thresh:
        return False
    x, y, w, h = cv2.boundingRect(approx)
    ar = w / float(h)
    return abs(ar - 1.0) < ar_thresh

def harmonic_ratio_scan(image, center, size=30, axis='x'):
    x, y = center
    if axis == 'x':
        start = max(x - size // 2, 0)
        end = min(x + size // 2, image.shape[1])
        scan_line = image[y, start:end]
    else:
        start = max(y - size // 2, 0)
        end = min(y + size // 2, image.shape[0])
        scan_line = image[start:end, x]

    scan_line = cv2.GaussianBlur(scan_line, (3, 3), 0)
    if scan_line.ndim == 3 and scan_line.shape[-1] == 3:
        scan_line = cv2.cvtColor(scan_line, cv2.COLOR_BGR2GRAY)
    scan_line = cv2.normalize(scan_line.astype('float32'), None, 0.0, 1.0, cv2.NORM_MINMAX)

    binary = (scan_line < 0.5).astype(int)
    transitions = np.diff(binary)
    count = np.sum(np.abs(transitions))
    return 3 <= count <= 6

# --- QR detection using v2.2 then fallback v2.7 ---

def detect_qr_combined_fullscan(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return None, "❌ Failed to load image"

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    qr_decoder = cv2.QRCodeDetector()
    h, w = enhanced.shape

    # --- Primary scan (v2.2) ---
    patch_size, stride, scale_factor = 200, 50, 2.0
    for y in range(0, h - patch_size + 1, stride):
        for x in range(0, w - patch_size + 1, stride):
            patch = enhanced[y:y + patch_size, x:x + patch_size]
            patch_upscaled = cv2.resize(patch, (0, 0), fx=scale_factor, fy=scale_factor)
            data, points, _ = qr_decoder.detectAndDecode(patch_upscaled)
            if data and points is not None:
                points = points / scale_factor
                points = points.astype(int)
                points += np.array([x, y])
                cv2.polylines(image, [points], True, (0, 255, 0), 2)  # Green for v2.2
                return image, data

    # --- Fallback full-image scan (v2.7) ---
    patch_size, stride, scale_factor = 100, 20, 3.0
    for y in range(0, h - patch_size + 1, stride):
        for x in range(0, w - patch_size + 1, stride):
            patch = enhanced[y:y + patch_size, x:x + patch_size]
            patch_upscaled = cv2.resize(patch, (0, 0), fx=scale_factor, fy=scale_factor)
            data, points, _ = qr_decoder.detectAndDecode(patch_upscaled)
            if data and points is not None:
                points = points / scale_factor
                points = points.astype(int)
                points += np.array([x, y])
                cv2.polylines(image, [points], True, (255, 128, 0), 2)  # Orange for fallback
                return image, data

    return image, None

# --- Folder scan and result logger ---

def detect_qr_combined_in_folder(folder_path, save_csv="qr_results_combined.csv"):
    image_paths = glob.glob(os.path.join(folder_path, "*.jpg")) + \
                  glob.glob(os.path.join(folder_path, "*.jpeg")) + \
                  glob.glob(os.path.join(folder_path, "*.png"))

    results = []
    for image_path in sorted(image_paths):
        result_image, result_data = detect_qr_combined_fullscan(image_path)
        filename = os.path.basename(image_path)
        status = f"✅ {result_data}" if result_data else "❌ QR not found"
        print(f"[{filename}] → {status}")

        results.append([filename, result_data if result_data else "Not Detected"])

        # Show image
        plt.figure(figsize=(10, 8))
        plt.imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
        plt.title(f"{filename}\n{status}")
        plt.axis("off")
        plt.show()

    # Save CSV
    with open(save_csv, "w", newline='', encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Filename", "QR Content"])
        writer.writerows(results)
    print(f"\n📄 Results saved to: {save_csv}")

# --- Example usage ---

if __name__ == "__main__":
    test_folder = "/Users/fadil/Documents/capstone/qr_reader/Dataset/Both_Sym_include/Exclude_Duplicate"
    detect_qr_combined_in_folder(test_folder)
