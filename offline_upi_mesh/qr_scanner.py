#!/usr/bin/env python3
"""
OpenCV-based QR Scanner for Offline UPI Mesh
Uses OpenCV's built-in QRCodeDetector (no zbar needed).
More robust than ZXing in poor conditions.
Usage:
  python qr_scanner.py                    # Scan from webcam
  python qr_scanner.py payment_qr.png     # Scan from image file
"""
import sys
import cv2
import requests
import numpy as np

BACKEND_URL = "http://127.0.0.1:8000/upload"


def decode_and_settle(qr_data):
    """Send the scanned packet string ('UM1:...') to the backend for settlement."""
    try:
        if "UM1:" not in qr_data:
            print("[ERROR] QR does not contain a UPI-Mesh packet")
            return None
        print(f"[OK] QR decoded ({len(qr_data)} chars)")
        print("[...] Sending to backend for settlement...")
        resp = requests.post(BACKEND_URL, json={"packet": qr_data}, timeout=10)
        result = resp.json()
        print(f"[RESULT] {result['status']}: {result.get('message', '')}")
        return result
    except Exception as e:
        print(f"[ERROR] Failed to process QR: {e}")
        return None


def scan_from_image(image_path):
    """Scan QR code from image file using OpenCV."""
    print(f"[SCAN] Reading image: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        print("[ERROR] Could not read image")
        return

    # Try multiple approaches for better detection
    detector = cv2.QRCodeDetector()

    # Approach 1: Direct detection
    data, bbox, _ = detector.detectAndDecode(img)
    if data:
        print(f"[FOUND] QR Code: {data[:80]}...")
        decode_and_settle(data)
        return

    # Approach 2: Try with preprocessing
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    data, bbox, _ = detector.detectAndDecode(enhanced)
    if data:
        print(f"[FOUND] QR Code (enhanced): {data[:80]}...")
        decode_and_settle(data)
        return

    # Approach 3: Try multi-scale detection
    for scale in [0.5, 0.75, 1.0, 1.5, 2.0]:
        h, w = img.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        data, bbox, _ = detector.detectAndDecode(resized)
        if data:
            print(f"[FOUND] QR Code (scale={scale}): {data[:80]}...")
            decode_and_settle(data)
            return

    print("[NOT FOUND] No QR code detected in image")


def scan_from_webcam():
    """Scan QR code from webcam using OpenCV (continuous)."""
    print("[SCAN] Starting webcam scanner (press 'q' to quit)...")

    detector = cv2.QRCodeDetector()
    cap = cv2.VideoCapture(0)

    # Set higher resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    cap.set(cv2.CAP_PROP_FOCUS, 0)  # Continuous autofocus

    if not cap.isOpened():
        print("[ERROR] Could not open webcam")
        return

    last_result = None
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            bbox = None  # Initialize bbox

            # Process every 2nd frame for performance
            if frame_count % 2 == 0:
                # Try detection with preprocessing
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)

                data, bbox, _ = detector.detectAndDecode(enhanced)

                if data and data != last_result:
                    print(f"\n[FOUND] QR Code: {data[:80]}...")
                    decode_and_settle(data)
                    last_result = data
                    # Show success briefly
                    cv2.putText(frame, "QR DETECTED - SETTLING...", (50, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # Also try direct detection on color frame (sometimes works better)
                if not data:
                    data, bbox, _ = detector.detectAndDecode(frame)
                    if data and data != last_result:
                        print(f"\n[FOUND] QR Code (color): {data[:80]}...")
                        decode_and_settle(data)
                        last_result = data

            # Draw detection box if found
            if bbox is not None and len(bbox) > 0:
                bbox = bbox.astype(int)
                cv2.polylines(frame, [bbox], True, (0, 255, 0), 3)

            # Show preview
            cv2.putText(frame, "Align QR in frame | Press 'q' to quit", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow('OpenCV QR Scanner', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n[EXIT] Scanner stopped")


def main():
    if len(sys.argv) > 1:
        # Scan from image file
        scan_from_image(sys.argv[1])
    else:
        # Scan from webcam
        scan_from_webcam()


if __name__ == "__main__":
    main()