'''Train CIFAR10 with PyTorch.'''
from __future__ import print_function

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn

import torchvision_qinxiao
import torchvision.transforms as transforms

import os
import argparse

from models.resnet import ResNet18
from utils_qinxiao import progress_bar

from torchvision_qinxiao import datasets
from utils_qinxiao import KNNEvaluation
from utils_adambielski import *
from losses_bnulihaixia import NCALoss
import numpy as np
import pdb

# Training
def train(epoch):
    print('\nEpoch: %d' % epoch)
    net.train()
    train_loss = 0
    for batch_idx, (inputs, targets) in enumerate(train_loader):
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        _,embeddings = net(inputs)
        loss = criterion(embeddings, targets)
        # print(loss)
        if np.isnan(loss.item()) :
            progress_bar(batch_idx, len(train_loader))
            continue
        loss.backward()
        optimizer.step()

        train_loss += loss.item()

        progress_bar(batch_idx, len(train_loader), 'Loss: %.3f ' % (1.0*train_loss/(batch_idx+1)))

def test(epoch):
    global best_acc,current_best_epoch
    #pdb.set_trace()
    net.eval()
    with torch.no_grad():
        all_embeddings=np.zeros((len(test_loader.dataset),84))
        all_targets=np.zeros(len(test_loader.dataset))
        for batch_idx, (inputs, targets) in enumerate(test_loader):
            inputs, targets = inputs.to(device), targets.to(device)
            _,embeddings = net(inputs)
            all_embeddings[batch_idx*args.batch_size:batch_idx*args.batch_size+embeddings.shape[0],:]=embeddings.cpu().numpy()
            all_targets[batch_idx*args.batch_size:batch_idx*args.batch_size+targets.shape[0]]=targets.cpu().numpy()
            progress_bar(batch_idx, len(test_loader))

    # Save checkpoint.
    acc = KNNEvaluation(all_embeddings,all_targets)
    #pdb.set_trace()
    if acc > best_acc:
        print('Saving..')
        state = {
            'net': net.state_dict(),
            'acc': acc,
            'epoch': epoch,
        }
        if not os.path.isdir('checkpoint'):
            os.mkdir('checkpoint')
        torch.save(state, './checkpoint/NCA_ckpt.t7')
        best_acc = acc
        current_best_epoch=epoch
    print('1NN accuracy on test set:%.3f | current best epoch: %d' % (acc,current_best_epoch))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PyTorch MNIST Training')
    parser.add_argument('--epochs', default=100, type=int, help='epochs')
    parser.add_argument('--lr', default=0.0001, type=float, help='learning rate')
    parser.add_argument('--batch-size', default=128, type=int, help='batch size')
    parser.add_argument('--partition-proportion', default=5, type=int, help='partition proportion')
    parser.add_argument('--resume', '-r', action='store_true', help='resume from checkpoint')

    args = parser.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    best_acc = 0  # best test accuracy
    current_best_epoch=0
    start_epoch = 0  # start from epoch 0 or last checkpoint epoch

    # Data
    print('==> Preparing data..')
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])

    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])

    trainset = torchvision_qinxiao.datasets.CIFAR10(root='../Embedding_data', train=True, download=True, transform=transform_train)
    train_loader = torch.utils.data.DataLoader(trainset, batch_size=args.batch_size, shuffle=True, num_workers=2)

    testset = torchvision_qinxiao.datasets.CIFAR10(root='../Embedding_data', train=False, download=True, transform=transform_test)
    test_loader = torch.utils.data.DataLoader(testset, batch_size=args.batch_size, shuffle=False, num_workers=2)

    classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

    # Model
    print('==> Building model..')

    net = ResNet18()
    net = net.to(device)
    if device == 'cuda':
        net = torch.nn.DataParallel(net)
        cudnn.benchmark = True

    if args.resume:
        # Load checkpoint.
        print('==> Resuming from checkpoint..')
        assert os.path.isdir('checkpoint'), 'Error: no checkpoint directory found!'
        if os.path.isfile('./checkpoint/NCA_ckpt.t7'):
            checkpoint = torch.load('./checkpoint/NCA_ckpt.t7')
            best_acc = checkpoint['acc']
        else:
            checkpoint = torch.load('./checkpoint/classification_ckpt.t7')
            best_acc = 0
        net.load_state_dict(checkpoint['net'])
        
        start_epoch = checkpoint['epoch']
        current_best_epoch=start_epoch
        print('the current best acc is %.3f on epoch %d'%(best_acc,start_epoch))

    criterion = NCALoss()
    optimizer = optim.SGD(net.parameters(), lr=args.lr, momentum=0.9, weight_decay=5e-4)

    for epoch in range(start_epoch, start_epoch+args.epochs):
        train(epoch)
        test(epoch)


