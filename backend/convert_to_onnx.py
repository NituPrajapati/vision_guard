from ultralytics import YOLO
import os
print("Script started!")

print("=" * 40)
print("   YOLO Model ONNX Converter")
print("=" * 40)

# ── Convert ID Card Model ──
idcard_pt = "runs/detect/train3/weights/best.pt"
idcard_onnx = "runs/detect/train3/weights/best.onnx"

if os.path.exists(idcard_onnx):
    print(f"⚠️  ID card ONNX already exists, skipping...")
else:
    print(f"Converting ID card model...")
    YOLO(idcard_pt).export(format="onnx", imgsz=640, opset=12)
    print(f"✅ ID card model converted!")

# ── Convert COCO Model ──
coco_pt = "yolov8n.pt"
coco_onnx = "yolov8n.onnx"

if os.path.exists(coco_onnx):
    print(f"⚠️  COCO ONNX already exists, skipping...")
else:
    print(f"Converting COCO model...")
    YOLO(coco_pt).export(format="onnx", imgsz=640, opset=12)
    print(f"✅ COCO model converted!")

print("=" * 40)
print("Done! ONNX files created.")
print("Now update config.py paths to .onnx")
print("=" * 40)