# Detection Only Test - ทดสอบเฉพาะการ detect TIS และ QR
# ใช้รูปที่มีอยู่แล้วแทนการ scrape

import os
import shutil
import logging
import cv2
import json
import csv
from pathlib import Path
from ultralytics import YOLO
from pyzbar import pyzbar

# ======================== CONFIG ========================
class Config:
    # Detection model paths
    TIS_MODEL_PATH = "/Users/fadil/Downloads/TIS.pt"
    QR_YOLO_MODEL_PATH = "/Users/fadil/Downloads/capstone 2/fadil-qr-detection/yolov5/runs/train/qr_detector3/weights/best.pt"
    
    # Input/Output directories
    INPUT_IMAGE_DIR = "/Users/fadil/Downloads/capstone 2/fadil-qr-detection/dataset/images/test"  # ใส่ path รูปที่คุณรวบรวมไว้
    OUTPUT_DIR = "detection_test_results"
    
    # Detection settings
    TIS_CONFIDENCE = 0.5
    QR_CONFIDENCE = 0.25
    
    # Feature flags
    ENABLE_TIS_DETECTION = True
    ENABLE_QR_DETECTION = True

# ======================== DETECTION MODULES ========================
class TISDetector:
    def __init__(self, model_path, confidence=0.5):
        if os.path.exists(model_path):
            self.model = YOLO(model_path)
            self.confidence = confidence
            logging.info(f"✅ TIS Detection model loaded: {model_path}")
        else:
            logging.error(f"❌ TIS model not found: {model_path}")
            self.model = None
    
    def detect(self, image_path):
        """Detect TIS symbol in image"""
        if not self.model:
            return False, 0
            
        try:
            results = self.model.predict(image_path, conf=self.confidence)
            detections = results[0].boxes.xyxy if len(results[0].boxes) > 0 else []
            
            if len(detections) > 0:
                logging.info(f"🎯 TIS symbol detected in {os.path.basename(image_path)}")
                return True, len(detections)
            else:
                logging.info(f"❌ No TIS symbol detected in {os.path.basename(image_path)}")
                return False, 0
        except Exception as e:
            logging.error(f"❌ TIS detection error for {image_path}: {e}")
            return False, 0

class QRDetector:
    def __init__(self, confidence=0.25):
        self.confidence = confidence
        logging.info("✅ QR Detection initialized")
    
    def detect_with_pyzbar(self, image_path):
        """Detect QR codes using pyzbar"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                logging.warning(f"⚠️  Could not load image: {image_path}")
                return False, 0, []
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect QR codes
            qr_codes = pyzbar.decode(gray)
            
            if qr_codes:
                qr_data = []
                for qr in qr_codes:
                    data = qr.data.decode('utf-8')
                    qr_data.append(data)
                    logging.info(f"📱 QR Code detected in {os.path.basename(image_path)}: {data}")
                
                return True, len(qr_codes), qr_data
            else:
                logging.info(f"❌ No QR code detected in {os.path.basename(image_path)}")
                return False, 0, []
                
        except Exception as e:
            logging.error(f"❌ QR detection error for {image_path}: {e}")
            return False, 0, []
    
    def detect(self, image_path):
        """Main QR detection method"""
        return self.detect_with_pyzbar(image_path)

# ======================== INTEGRATED DETECTOR ========================
class IntegratedDetector:
    def __init__(self):
        self.tis_detector = None
        self.qr_detector = None
        
        # Initialize detectors based on config
        if Config.ENABLE_TIS_DETECTION:
            try:
                self.tis_detector = TISDetector(Config.TIS_MODEL_PATH, Config.TIS_CONFIDENCE)
            except Exception as e:
                logging.error(f"❌ Failed to load TIS detector: {e}")
        
        if Config.ENABLE_QR_DETECTION:
            try:
                self.qr_detector = QRDetector(Config.QR_CONFIDENCE)
            except Exception as e:
                logging.error(f"❌ Failed to load QR detector: {e}")
    
    def analyze_image(self, image_path):
        """Analyze image for both TIS and QR detection"""
        results = {
            'tis_detected': False,
            'tis_count': 0,
            'qr_detected': False,
            'qr_count': 0,
            'qr_data': []
        }
        
        # TIS Detection
        if self.tis_detector and Config.ENABLE_TIS_DETECTION:
            tis_found, tis_count = self.tis_detector.detect(image_path)
            results['tis_detected'] = tis_found
            results['tis_count'] = tis_count
        
        # QR Detection
        if self.qr_detector and Config.ENABLE_QR_DETECTION:
            qr_found, qr_count, qr_data = self.qr_detector.detect(image_path)
            results['qr_detected'] = qr_found
            results['qr_count'] = qr_count
            results['qr_data'] = qr_data
        
        return results

# ======================== DETECTION TESTER ========================
class DetectionTester:
    def __init__(self):
        self.detector = IntegratedDetector()
        self.setup_directories()
        self.setup_logging()
        
        self.stats = {
            'total_images': 0,
            'images_with_tis': 0,
            'images_with_qr': 0,
            'images_with_both': 0,
            'images_no_detection': 0,
            'total_tis_detections': 0,
            'total_qr_detections': 0,
            'failed_images': 0
        }
    
    def setup_directories(self):
        """Create output directories"""
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        os.makedirs(f"{Config.OUTPUT_DIR}/with_tis", exist_ok=True)
        os.makedirs(f"{Config.OUTPUT_DIR}/with_qr", exist_ok=True)
        os.makedirs(f"{Config.OUTPUT_DIR}/with_both", exist_ok=True)
        os.makedirs(f"{Config.OUTPUT_DIR}/no_detection", exist_ok=True)
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(f"{Config.OUTPUT_DIR}/detection_test.log", mode='w', encoding="utf-8"),
                logging.StreamHandler()
            ]
        )
    
    def get_image_files(self, directory):
        """Get all image files from directory"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        image_files = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    image_files.append(os.path.join(root, file))
        
        return image_files
    
    def organize_image(self, image_path, detection_results):
        """Organize image based on detection results"""
        filename = os.path.basename(image_path)
        
        if detection_results['tis_detected'] and detection_results['qr_detected']:
            target_dir = f"{Config.OUTPUT_DIR}/with_both"
            category = "both"
        elif detection_results['tis_detected']:
            target_dir = f"{Config.OUTPUT_DIR}/with_tis"
            category = "tis"
        elif detection_results['qr_detected']:
            target_dir = f"{Config.OUTPUT_DIR}/with_qr"
            category = "qr"
        else:
            target_dir = f"{Config.OUTPUT_DIR}/no_detection"
            category = "none"
        
        target_path = os.path.join(target_dir, filename)
        
        try:
            shutil.copy2(image_path, target_path)
            logging.info(f"📁 Organized {filename} to: {category}")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to organize {filename}: {e}")
            return False
    
    def save_results_csv(self, results_data):
        """Save results to CSV"""
        csv_file = f"{Config.OUTPUT_DIR}/detection_results.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Image Path", "Filename", "TIS Detected", "TIS Count", 
                "QR Detected", "QR Count", "QR Data", "Category"
            ])
            
            for result in results_data:
                writer.writerow([
                    result['image_path'],
                    result['filename'],
                    "Yes" if result['tis_detected'] else "No",
                    result['tis_count'],
                    "Yes" if result['qr_detected'] else "No",
                    result['qr_count'],
                    " | ".join(result['qr_data']) if result['qr_data'] else "None",
                    result['category']
                ])
        
        logging.info(f"📊 Results saved to: {csv_file}")
    
    def save_summary_json(self):
        """Save summary statistics to JSON"""
        json_file = f"{Config.OUTPUT_DIR}/detection_summary.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        logging.info(f"📋 Summary saved to: {json_file}")
    
    def run_detection_test(self):
        """Main detection test function"""
        print("🧪 Detection Only Test")
        print("=" * 50)
        
        # Check input directory
        if not os.path.exists(Config.INPUT_IMAGE_DIR):
            print(f"❌ Input directory not found: {Config.INPUT_IMAGE_DIR}")
            print("💡 Please update Config.INPUT_IMAGE_DIR with your image folder path")
            return
        
        # Get all image files
        image_files = self.get_image_files(Config.INPUT_IMAGE_DIR)
        
        if not image_files:
            print(f"❌ No image files found in: {Config.INPUT_IMAGE_DIR}")
            return
        
        print(f"📸 Found {len(image_files)} images to process")
        print(f"📁 Results will be saved to: {Config.OUTPUT_DIR}")
        
        # Process images
        results_data = []
        
        for i, image_path in enumerate(image_files, 1):
            filename = os.path.basename(image_path)
            print(f"\n🔍 Processing {i}/{len(image_files)}: {filename}")
            
            try:
                # Analyze image
                detection_results = self.detector.analyze_image(image_path)
                
                # Update statistics
                self.stats['total_images'] += 1
                
                if detection_results['tis_detected']:
                    self.stats['images_with_tis'] += 1
                    self.stats['total_tis_detections'] += detection_results['tis_count']
                
                if detection_results['qr_detected']:
                    self.stats['images_with_qr'] += 1
                    self.stats['total_qr_detections'] += detection_results['qr_count']
                
                if detection_results['tis_detected'] and detection_results['qr_detected']:
                    self.stats['images_with_both'] += 1
                    category = "both"
                elif detection_results['tis_detected']:
                    category = "tis"
                elif detection_results['qr_detected']:
                    category = "qr"
                else:
                    self.stats['images_no_detection'] += 1
                    category = "none"
                
                # Organize image
                organized = self.organize_image(image_path, detection_results)
                
                # Save result data
                result_data = {
                    'image_path': image_path,
                    'filename': filename,
                    'tis_detected': detection_results['tis_detected'],
                    'tis_count': detection_results['tis_count'],
                    'qr_detected': detection_results['qr_detected'],
                    'qr_count': detection_results['qr_count'],
                    'qr_data': detection_results['qr_data'],
                    'category': category,
                    'organized': organized
                }
                results_data.append(result_data)
                
                # Show results
                print(f"   🎯 TIS: {'✅' if detection_results['tis_detected'] else '❌'} "
                      f"(Count: {detection_results['tis_count']})")
                print(f"   📱 QR: {'✅' if detection_results['qr_detected'] else '❌'} "
                      f"(Count: {detection_results['qr_count']})")
                if detection_results['qr_data']:
                    print(f"   📄 QR Data: {detection_results['qr_data']}")
                
            except Exception as e:
                logging.error(f"❌ Failed to process {filename}: {e}")
                self.stats['failed_images'] += 1
        
        # Save results
        self.save_results_csv(results_data)
        self.save_summary_json()
        
        # Print final summary
        print("\n" + "=" * 50)
        print("📊 DETECTION TEST SUMMARY")
        print("=" * 50)
        print(f"📸 Total images processed: {self.stats['total_images']}")
        print(f"🎯 Images with TIS: {self.stats['images_with_tis']}")
        print(f"📱 Images with QR: {self.stats['images_with_qr']}")
        print(f"🎯📱 Images with both: {self.stats['images_with_both']}")
        print(f"❌ Images with no detection: {self.stats['images_no_detection']}")
        print(f"💥 Failed images: {self.stats['failed_images']}")
        print(f"🎯 Total TIS detections: {self.stats['total_tis_detections']}")
        print(f"📱 Total QR detections: {self.stats['total_qr_detections']}")
        print(f"📁 Results organized in: {Config.OUTPUT_DIR}")

# ======================== MAIN ========================
def main():
    # อัปเดต path ให้ตรงกับโฟลเดอร์รูปของคุณ
    input_path = input("Enter path to your image folder: ").strip()
    if input_path:
        Config.INPUT_IMAGE_DIR = input_path
    
    # สร้างและรัน tester
    tester = DetectionTester()
    tester.run_detection_test()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")