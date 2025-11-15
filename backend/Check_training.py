from ultralytics import YOLO
import os

# ------------------ CONFIG ------------------
# Path to your trained YOLO model
MODEL_PATH = "runs/detect/train3/weights/best.pt" 

# Folder containing test images
INPUT_FOLDER = "predict3"  
# Folder to save detection results
OUTPUT_FOLDER = "yolo_results"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Confidence thresholds
CONFIDENCE_DEFAULT = 0.5
CONFIDENCE_FALLBACK = 0.3  

# ------------------ LOAD MODEL ------------------
model = YOLO(MODEL_PATH)

# ------------------ DETECTION LOOP ------------------
for img_name in os.listdir(INPUT_FOLDER):
    img_path = os.path.join(INPUT_FOLDER, img_name)
    
    # Skip non-image files
    if not img_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        continue

    print(f"\nProcessing image: {img_name}")
    
    # Run detection with default confidence
    results = model.predict(
        source=img_path,
        conf=CONFIDENCE_DEFAULT,
        show=False,      # set True if you want pop-up display
        save=True,
        project=OUTPUT_FOLDER,
        name="predictions",
        save_conf=True
    )
    
    # Check if any detections
    if len(results[0].boxes) == 0:
        print("No detections at default confidence. Trying lower confidence...")
        results = model.predict(
            source=img_path,
            conf=CONFIDENCE_FALLBACK,
            show=False,
            save=True,
            project=OUTPUT_FOLDER,
            name="predictions",
            save_conf=True
        )

        if len(results[0].boxes) == 0:
            print("Still no detections for this image.")
            continue  # move to next image
    
    # Print detected boxes
    for r in results:
        for i, box in enumerate(r.boxes):
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            print(f"Detection {i+1}: Class={cls}, Confidence={conf:.2f}, BBox={xyxy}")

    # Print saved image path
    for r in results:
        for path in r.files:
            print("Saved result image at:", path)

print("\nAll images processed.")
