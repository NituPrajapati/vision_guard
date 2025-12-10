# merge_coco.py
import json
import os

# List your annotation files here
coco_files = ["annotations.json", "annotations2.json"]
output_file = "merged_annotations.json"

merged = {"images": [], "annotations": [], "categories": None}
img_id_offset = 0
ann_id_offset = 0

for coco_file in coco_files:
    with open(coco_file, "r") as f:
        coco = json.load(f)

    if merged["categories"] is None:
        merged["categories"] = coco["categories"]

    # Offset IDs to avoid clashes
    for img in coco["images"]:
        img["id"] += img_id_offset
        merged["images"].append(img)

    for ann in coco["annotations"]:
        ann["id"] += ann_id_offset
        ann["image_id"] += img_id_offset
        merged["annotations"].append(ann)

    img_id_offset = max([img["id"] for img in merged["images"]]) + 1
    ann_id_offset = max([ann["id"] for ann in merged["annotations"]]) + 1

with open(output_file, "w") as f:
    json.dump(merged, f, indent=2)

print(f"Merged annotations saved as {output_file}")
