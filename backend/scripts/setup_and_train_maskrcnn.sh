#!/bin/bash
# Mask R-CNN Setup and Training Script
# This will run overnight for demo tomorrow

set -e  # Exit on error

echo "🚀 Starting Mask R-CNN Setup and Training"
echo "=========================================="
echo ""

# Activate virtual environment
source backend/venv/bin/activate

# Step 1: Verify PyTorch is installed
echo "📦 Step 1: Verifying PyTorch installation..."
python -c "import torch; print(f'PyTorch {torch.__version__} found')" || {
    echo "❌ PyTorch not found. Please install PyTorch first."
    exit 1
}
echo "✅ PyTorch verified"
echo ""

# Step 2: Install detectron2 dependencies
echo "📦 Step 2: Installing detectron2 dependencies..."
pip install opencv-python pycocotools
echo "✅ Dependencies installed"
echo ""

# Step 3: Install detectron2
echo "📦 Step 3: Installing detectron2..."
pip install --no-build-isolation 'git+https://github.com/facebookresearch/detectron2.git'
echo "✅ detectron2 installed"
echo ""

# Step 4: Convert YOLO dataset to COCO format for Mask R-CNN
echo "🔄 Step 4: Converting dataset to COCO format..."
python backend/scripts/convert_yolo_to_coco_segmentation.py
echo "✅ Dataset converted"
echo ""

# Step 5: Start Mask R-CNN training
echo "🎯 Step 5: Starting Mask R-CNN training (this will run overnight)..."
echo "Training will save checkpoints every 1000 iterations"
echo "You can monitor progress in: runs/maskrcnn/output/"
echo ""

python backend/scripts/train_maskrcnn_segmentation.py

echo ""
echo "✅ Training complete!"
echo "Best model saved to: backend/models/maskrcnn_damage_segmentation.pth"
