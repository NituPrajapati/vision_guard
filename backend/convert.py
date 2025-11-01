# coco_to_yolo.py
import json
import os

coco_file = "merged_annotations.json"
labels_dir = "labels"
os.makedirs(labels_dir, exist_ok=True)

with open(coco_file, "r") as f:
    coco = json.load(f)

img_id_to_filename = {img["id"]: img["file_name"] for img in coco["images"]}
img_id_to_size = {img["id"]: (img["width"], img["height"]) for img in coco["images"]}

for ann in coco["annotations"]:
    image_id = ann["image_id"]
    file_name = img_id_to_filename[image_id]
    w, h = img_id_to_size[image_id]

    # COCO bbox format: [x_min, y_min, width, height]
    x, y, bw, bh = ann["bbox"]
    x_center = (x + bw / 2) / w
    y_center = (y + bh / 2) / h
    bw /= w
    bh /= h

    category_id = ann["category_id"] - 1  # YOLO expects 0-based class IDs

    # Write to YOLO .txt file
    txt_file = os.path.splitext(file_name)[0] + ".txt"
    label_path = os.path.join(labels_dir, txt_file)
    with open(label_path, "a") as f:
        f.write(f"{category_id} {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n")

print(f" YOLO labels saved in {labels_dir}/")
