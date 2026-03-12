"""
Train Mask R-CNN on merged damage segmentation dataset (7 classes)
Optimized for faster convergence with clean class taxonomy

POWER LOSS RECOVERY:
- Checkpoints saved every 2000 iterations to runs/maskrcnn/merged_output/
- To resume after power loss: Just run this script again
- It will automatically detect and resume from the latest checkpoint
"""
import os
import torch
from pathlib import Path
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2 import model_zoo
from detectron2.data.datasets import register_coco_instances
from detectron2.evaluation import COCOEvaluator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register datasets
DATASET_ROOT = "datasets/prepared/damage_segmentation_coco_merged"

register_coco_instances(
    "damage_train_merged",
    {},
    f"{DATASET_ROOT}/train_coco.json",
    f"{DATASET_ROOT}/images/train/images"
)

register_coco_instances(
    "damage_val_merged",
    {},
    f"{DATASET_ROOT}/val_coco.json",
    f"{DATASET_ROOT}/images/val/images"
)

class CocoTrainer(DefaultTrainer):
    @classmethod
    def build_evaluator(cls, cfg, dataset_name, output_folder=None):
        if output_folder is None:
            output_folder = os.path.join(cfg.OUTPUT_DIR, "inference")
        return COCOEvaluator(dataset_name, cfg, True, output_folder)

def setup_config():
    """Setup Detectron2 config for merged dataset"""
    cfg = get_cfg()
    
    # Load base config
    cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    
    # Dataset
    cfg.DATASETS.TRAIN = ("damage_train_merged",)
    cfg.DATASETS.TEST = ("damage_val_merged",)
    
    # Model
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 7  # 7 merged classes
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 256  # Increased for better learning
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
    
    # Training
    cfg.SOLVER.IMS_PER_BATCH = 4  # Batch size (adjust based on GPU memory)
    cfg.SOLVER.BASE_LR = 0.001  # Slightly higher LR for faster convergence
    cfg.SOLVER.MAX_ITER = 20000  # 20k iterations (should be enough with 7 classes)
    cfg.SOLVER.STEPS = (12000, 16000)  # LR decay steps
    cfg.SOLVER.GAMMA = 0.1  # LR decay factor
    cfg.SOLVER.WARMUP_ITERS = 500
    cfg.SOLVER.CHECKPOINT_PERIOD = 2000  # Save every 2k iterations
    
    # Evaluation
    cfg.TEST.EVAL_PERIOD = 2000  # Evaluate every 2k iterations
    
    # Data augmentation
    cfg.INPUT.MIN_SIZE_TRAIN = (640, 672, 704, 736, 768, 800)
    cfg.INPUT.MAX_SIZE_TRAIN = 1333
    cfg.INPUT.MIN_SIZE_TEST = 800
    cfg.INPUT.MAX_SIZE_TEST = 1333
    
    # Output
    cfg.OUTPUT_DIR = "runs/maskrcnn/merged_output"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    
    return cfg

def main():
    """Main training function"""
    logger.info("🚀 Starting Mask R-CNN Training (Merged Dataset)")
    logger.info("=" * 80)
    
    # Setup config
    cfg = setup_config()
    
    logger.info(f"📊 Training Configuration:")
    logger.info(f"   Classes: 7 (merged from 42)")
    logger.info(f"   Max iterations: {cfg.SOLVER.MAX_ITER}")
    logger.info(f"   Batch size: {cfg.SOLVER.IMS_PER_BATCH}")
    logger.info(f"   Base LR: {cfg.SOLVER.BASE_LR}")
    logger.info(f"   Output: {cfg.OUTPUT_DIR}")
    logger.info(f"   GPU: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        logger.info(f"   GPU Name: {torch.cuda.get_device_name(0)}")
        logger.info(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    
    # Create trainer
    trainer = CocoTrainer(cfg)
    
    # Check if we should resume from checkpoint
    checkpoints = list(Path(cfg.OUTPUT_DIR).glob("model_*.pth"))
    if checkpoints:
        # Find latest checkpoint
        latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
        logger.info(f"\n🔄 Found existing checkpoint: {latest_checkpoint}")
        logger.info(f"   Resuming training from this checkpoint...")
        trainer.resume_or_load(resume=True)
    else:
        logger.info("\n🆕 No existing checkpoint found. Starting fresh training...")
        trainer.resume_or_load(resume=False)
    
    logger.info("\n🎯 Starting training...")
    logger.info("   Expected time: ~2-3 hours for 20k iterations")
    logger.info("   Target AP50: 35-50%")
    logger.info("   Target AP: 20-30%")
    logger.info("\n" + "=" * 80)
    
    # Train
    trainer.train()
    
    logger.info("\n✅ Training complete!")
    logger.info(f"   Model saved to: {cfg.OUTPUT_DIR}/model_final.pth")

if __name__ == "__main__":
    main()
