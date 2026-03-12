# Training Recovery Guide

## 🔌 What Happens During Power Loss?

### Immediate Impact
- ❌ Current epoch progress is **lost**
- ❌ Training process terminates
- ❌ Unsaved in-memory data is gone

### What's Protected
- ✅ **Last completed epoch** saved as `last.pt`
- ✅ **Best model so far** saved as `best.pt`
- ✅ Training configuration preserved
- ✅ Optimizer state saved
- ✅ Learning rate schedule saved

## 📁 Checkpoint Locations

YOLOv8 automatically saves checkpoints after every epoch:

```
runs/detect/backend/runs/damage_detection/yolov8m_damage_v12/weights/
├── last.pt    # Most recent completed epoch
└── best.pt    # Best validation performance
```

## 🔄 How to Resume Training

### Option 1: Automatic Resume (Recommended)

```bash
# Run the resume script
backend/venv/bin/python backend/scripts/resume_training.py
```

This script will:
1. Find your latest checkpoint automatically
2. Load the model state
3. Resume training from the last completed epoch
4. Continue until completion or early stopping

### Option 2: Manual Resume

```bash
# Activate virtual environment
source backend/venv/bin/activate

# Resume from checkpoint
python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/backend/runs/damage_detection/yolov8m_damage_v12/weights/last.pt')
model.train(resume=True)
"
```

### Option 3: Resume with Modified Settings

If you want to change training parameters (e.g., reduce batch size):

```python
from ultralytics import YOLO

# Load checkpoint
model = YOLO('runs/detect/backend/runs/damage_detection/yolov8m_damage_v12/weights/last.pt')

# Resume with new batch size
model.train(
    resume=True,
    batch=4  # Reduced from 8 if you had memory issues
)
```

## 🛡️ Prevention Strategies

### 1. Use UPS (Uninterruptible Power Supply)
- **Best solution** for power fluctuations
- Gives you time to save and shutdown gracefully
- Recommended for long training runs

### 2. Increase Checkpoint Frequency

Modify training script to save more frequently:

```python
# In train_yolo_damage.py, add:
results = model.train(
    # ... other parameters ...
    save_period=5,  # Save checkpoint every 5 epochs instead of default
)
```

### 3. Use Cloud Training

For critical training runs:
- Google Colab (free GPU, but limited time)
- AWS/GCP/Azure (paid, but reliable)
- Kaggle Notebooks (free GPU)

### 4. Monitor Power Supply

```bash
# Install power monitoring (Linux)
sudo apt-get install acpi

# Check battery/UPS status
acpi -V
```

## 📊 Check Training Progress After Recovery

After resuming, verify your progress:

```bash
# Check which epoch you're resuming from
python -c "
from ultralytics import YOLO
model = YOLO('runs/detect/backend/runs/damage_detection/yolov8m_damage_v12/weights/last.pt')
print(f'Resuming from epoch: {model.ckpt[\"epoch\"]}')
"
```

## 🚨 Worst Case Scenarios

### Scenario 1: Power Loss During First Epoch
**Problem**: No checkpoint saved yet (checkpoints save after epoch completes)

**Solution**: Start training from scratch
```bash
backend/venv/bin/python backend/scripts/train_yolo_damage.py
```

**Time Lost**: ~20-30 minutes (one epoch)

### Scenario 2: Corrupted Checkpoint
**Problem**: Checkpoint file is corrupted due to write interruption

**Solution**: Use the `best.pt` instead of `last.pt`
```python
from ultralytics import YOLO
model = YOLO('runs/detect/.../weights/best.pt')
model.train(resume=True)
```

### Scenario 3: Multiple Interruptions
**Problem**: Training keeps getting interrupted

**Solution**: 
1. Invest in UPS
2. Use cloud training
3. Train in shorter sessions with manual checkpoints

## 💡 Pro Tips

### 1. Backup Checkpoints Regularly
```bash
# Create backup script
cp runs/detect/backend/runs/damage_detection/yolov8m_damage_v12/weights/last.pt \
   backups/checkpoint_epoch_$(date +%Y%m%d_%H%M%S).pt
```

### 2. Monitor Training Remotely
```bash
# Use tmux/screen to keep training running
tmux new -s training
backend/venv/bin/python backend/scripts/train_yolo_damage.py

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t training
```

### 3. Set Up Automatic Resume on Reboot

Create systemd service (Linux):
```bash
# /etc/systemd/system/yolo-training.service
[Unit]
Description=YOLO Training Auto-Resume
After=network.target

[Service]
Type=simple
User=kartikay
WorkingDirectory=/home/kartikay/Desktop/car detection
ExecStart=/home/kartikay/Desktop/car detection/backend/venv/bin/python backend/scripts/resume_training.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 📈 Expected Recovery Time

| Scenario | Time Lost | Recovery Time |
|----------|-----------|---------------|
| Power loss mid-epoch | Current epoch only (~20-30 min) | Immediate |
| Power loss after epoch | None | Immediate |
| Corrupted checkpoint | 1-2 epochs (~40-60 min) | 5 minutes |
| No checkpoint yet | Full training (~6-8 hours) | N/A |

## ✅ Verification After Resume

After resuming training, verify everything is working:

1. **Check epoch number**: Should continue from last checkpoint
2. **Check loss values**: Should be similar to where you left off
3. **Check GPU usage**: Should be ~3.3GB (same as before)
4. **Check ETA**: Should reflect remaining epochs

## 🆘 Need Help?

If you encounter issues:

1. Check the checkpoint exists:
   ```bash
   ls -lh runs/detect/backend/runs/damage_detection/yolov8m_damage_v*/weights/
   ```

2. Verify checkpoint is not corrupted:
   ```python
   from ultralytics import YOLO
   try:
       model = YOLO('path/to/last.pt')
       print("✅ Checkpoint is valid")
   except Exception as e:
       print(f"❌ Checkpoint corrupted: {e}")
   ```

3. Check available disk space:
   ```bash
   df -h
   ```

4. Review training logs:
   ```bash
   tail -100 runs/detect/backend/runs/damage_detection/yolov8m_damage_v*/train.log
   ```

---

**Remember**: YOLOv8's automatic checkpointing means you'll never lose more than one epoch of progress! 🎉
