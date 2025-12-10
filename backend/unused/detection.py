import cv2
from ultralytics import YOLO

# Load YOLOv8 model (use yolov8n.pt for speed)
model = YOLO("yolov8n.pt")

# Open webcam (0 = default camera)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLOv8 on the frame
    results = model(frame)

    # Annotate the frame with results
    annotated_frame = results[0].plot()

    # Show the annotated frame
    cv2.imshow("YOLOv8 Realtime Detection", annotated_frame)

    # Break loop with 'q' key
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()

#yolo task=detect mode=predict model=runs/detect/train/weights/best.pt source=OIP.webp
# to live detection yolo task=detect mode=predict model=runs/detect/train/weights/best.pt source=0

