"""
Train Mask R-CNN for damage segmentation
Overnight training for demo tomorrow
"""
import os
import json
from pathlib import Path
import torch
import detectron2
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.data import DatasetCatalog, MetadataCatalog
from detectron2.data.datasets import register_coco_instances
from detectron2.engine import DefaultTrainer
from detectron2.evaluation import COCOEvaluator
from detectron2.utils.logger import setup_logger

setup_logger()

print("🚀 Mask R-CNN Training Script")
print("=" * 60)
print(f"PyTorch version: {torch.__version__}")
print(f"Detectron2 version: {detectron2.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device: {torch.cuda.get_device_name(0)}")
print()

# Paths
DATASET_ROOT = Path("backend/datasets/prepared/damage_segmentation_coco")
TRAIN_JSON = DATASET_ROOT / "train_coco.json"
VAL_JSON = DATASET_ROOT / "val_coco.json"
TRAIN_IMAGES = Path("backend/datasets/prepared/damage_detection/train/images")
VAL_IMAGES = Path("backend/datasets/prepared/damage_detection/val/images")
OUTPUT_DIR = "runs/maskrcnn/output"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Register datasets
print("📊 Registering datasets...")
register_coco_instances("damage_train", {}, str(TRAIN_JSON), str(TRAIN_IMAGES))
register_coco_instances("damage_val", {}, str(VAL_JSON), str(VAL_IMAGES))

# Get metadata
train_metadata = MetadataCatalog.get("damage_train")
val_metadata = MetadataCatalog.get("damage_val")

print(f"✅ Train dataset registered: {len(DatasetCatalog.get('damage_train'))} images")
print(f"✅ Val dataset registered: {len(DatasetCatalog.get('damage_val'))} images")
print(f"   Classes: {train_metadata.thing_classes}")
print()

# Configure Mask R-CNN
print("⚙️  Configuring Mask R-CNN...")
cfg = get_cfg()

# Load pre-trained model config
cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

# Model weights
cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")

# Dataset
cfg.DATASETS.TRAIN = ("damage_train",)
cfg.DATASETS.TEST = ("damage_val",)

# Dataloader
cfg.DATALOADER.NUM_WORKERS = 4

# Solver (training parameters)
cfg.SOLVER.IMS_PER_BATCH = 2  # Batch size (adjust based on GPU memory)
cfg.SOLVER.BASE_LR = 0.00025  # Learning rate
cfg.SOLVER.MAX_ITER = 10000  # Train for 10k iterations (overnight)
cfg.SOLVER.STEPS = (7000, 9000)  # LR decay steps
cfg.SOLVER.GAMMA = 0.1  # LR decay factor
cfg.SOLVER.CHECKPOINT_PERIOD = 1000  # Save checkpoint every 1000 iterations

# Model
cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 128  # RoI batch size
cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(train_metadata.thing_classes)  # Number of damage classes

# Output
cfg.OUTPUT_DIR = OUTPUT_DIR

# Test/Evaluation
cfg.TEST.EVAL_PERIOD = 1000  # Evaluate every 1000 iterations

print(f"✅ Configuration:")
print(f"   Batch size: {cfg.SOLVER.IMS_PER_BATCH}")
print(f"   Learning rate: {cfg.SOLVER.BASE_LR}")
print(f"   Max iterations: {cfg.SOLVER.MAX_ITER}")
print(f"   Num classes: {cfg.MODEL.ROI_HEADS.NUM_CLASSES}")
print(f"   Output dir: {cfg.OUTPUT_DIR}")
print()

# Custom Trainer with evaluation
class MaskRCNNTrainer(DefaultTrainer):
    @classmethod
    def build_evaluator(cls, cfg, dataset_name, output_folder=None):
        if output_folder is None:
            output_folder = os.path.join(cfg.OUTPUT_DIR, "inference")
        return COCOEvaluator(dataset_name, cfg, True, output_folder)

# Train
print("🎯 Starting training...")
print("This will run overnight. You can monitor progress in:")
print(f"   {OUTPUT_DIR}/")
print()
print("Training metrics will be logged to:")
print(f"   {OUTPUT_DIR}/metrics.json")
print()

trainer = MaskRCNNTrainer(cfg)
trainer.resume_or_load(resume=False)
trainer.train()

print()
print("✅ Training complete!")
print()

# Save final model
final_model_path = "backend/models/maskrcnn_damage_segmentation.pth"
os.makedirs("backend/models", exist_ok=True)

# Copy best model
import shutil
best_model = os.path.join(OUTPUT_DIR, "model_final.pth")
if os.path.exists(best_model):
    shutil.copy(best_model, final_model_path)
    print(f"✅ Final model saved to: {final_model_path}")
else:
    print(f"⚠️  Warning: Final model not found at {best_model}")

# Evaluate on validation set
print()
print("📊 Evaluating on validation set...")
from detectron2.evaluation import inference_on_dataset
from detectron2.data import build_detection_test_loader

evaluator = COCOEvaluator("damage_val", cfg, False, output_dir=OUTPUT_DIR)
val_loader = build_detection_test_loader(cfg, "damage_val")
results = inference_on_dataset(trainer.model, val_loader, evaluator)

print()
print("✅ Evaluation results:")
print(json.dumps(results, indent=2))

print()
print("🎉 Mask R-CNN training complete!")
print(f"Model saved to: {final_model_path}")
print()
print("Next steps:")
print("1. Integrate model into pipeline (damage_segmentation.py)")
print("2. Test segmentation on sample images")
print("3. Update frontend to display segmentation masks")
