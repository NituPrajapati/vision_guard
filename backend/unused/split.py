# split_dataset.py
import os
import random
import shutil

images_dir = "id_card_images"   # all your images
labels_dir = "labels"   # YOLO txts
output_dir = "dataset"
train_ratio = 0.8

# Create folders
for sub in ["images/train", "images/val", "labels/train", "labels/val"]:
    os.makedirs(os.path.join(output_dir, sub), exist_ok=True)

# Collect all valid image files
extensions = [".jpg", ".jpeg", ".png", ".webp"]
all_images = [f for f in os.listdir(images_dir) if os.path.splitext(f)[1].lower() in extensions]
random.shuffle(all_images)

split_idx = int(len(all_images) * train_ratio)
train_files = all_images[:split_idx]
val_files = all_images[split_idx:]

def copy_files(files, img_dst, lbl_dst):
    for f in files:
        img_src = os.path.join(images_dir, f)
        lbl_src = os.path.join(labels_dir, os.path.splitext(f)[0] + ".txt")

        if not os.path.exists(img_src):
            print(f"Missing image: {img_src}")
            continue
        if not os.path.exists(lbl_src):
            print(f"Missing label: {lbl_src}")
            continue

        shutil.copy(img_src, img_dst)
        shutil.copy(lbl_src, lbl_dst)

copy_files(train_files, os.path.join(output_dir, "images/train"), os.path.join(output_dir, "labels/train"))
copy_files(val_files, os.path.join(output_dir, "images/val"), os.path.join(output_dir, "labels/val"))

print(f"Done! {len(train_files)} train, {len(val_files)} val.")
