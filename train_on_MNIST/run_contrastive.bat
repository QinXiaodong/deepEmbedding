@echo off
set maxeps=10
set l_r=0.01
set b_s=128
python train_contrastive.py --epochs %maxeps% --lr %l_r% --batch-size=%b_s% --resume
pause