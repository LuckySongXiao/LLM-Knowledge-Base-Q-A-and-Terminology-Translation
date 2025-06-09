import torch
import torch.nn as nn
import time
import os
import gc

def test_cuda_full():
    print("=" * 70)
    print("Comprehensive CUDA Performance Test")
    print("=" * 70)
    
    # Check CUDA availability
    if not torch.cuda.is_available():
        print("CUDA is not available. Please check your installation.")
        return
    
    # Display CUDA information
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"CUDA version: {torch.version.cuda}")
    print(f"CUDA device count: {torch.cuda.device_count()}")
    print(f"Current CUDA device: {torch.cuda.current_device()}")
    print(f"CUDA device name: {torch.cuda.get_device_name(0)}")
    print(f"CUDA device capability: {torch.cuda.get_device_capability(0)}")
    
    # Warm up GPU
    print("\nWarming up GPU...")
    warmup_tensor = torch.randn(1000, 1000, device='cuda')
    warmup_result = torch.matmul(warmup_tensor, warmup_tensor)
    torch.cuda.synchronize()
    del warmup_tensor, warmup_result
    gc.collect()
    torch.cuda.empty_cache()
    
    # Test 1: Large matrix multiplication
    print("\nTest 1: Large Matrix Multiplication (5000x5000)")
    
    # CPU test
    print("Running on CPU...")
    size = 5000
    cpu_a = torch.randn(size, size)
    cpu_b = torch.randn(size, size)
    
    torch.cuda.synchronize()  # Ensure no GPU operations are pending
    start_time = time.time()
    cpu_result = torch.matmul(cpu_a, cpu_b)
    cpu_time = time.time() - start_time
    print(f"CPU time: {cpu_time:.4f} seconds")
    
    # GPU test
    print("Running on GPU...")
    gpu_a = cpu_a.cuda()
    gpu_b = cpu_b.cuda()
    
    # Clear memory
    del cpu_a, cpu_b
    gc.collect()
    
    torch.cuda.synchronize()
    start_time = time.time()
    gpu_result = torch.matmul(gpu_a, gpu_b)
    torch.cuda.synchronize()
    gpu_time = time.time() - start_time
    print(f"GPU time: {gpu_time:.4f} seconds")
    
    # Results
    speedup = cpu_time / gpu_time
    print(f"GPU speedup: {speedup:.2f}x")
    
    # Clear memory
    del gpu_a, gpu_b, gpu_result
    gc.collect()
    torch.cuda.empty_cache()
    
    # Test 2: ResNet-like CNN model
    print("\nTest 2: ResNet-like CNN model")
    
    class ResidualBlock(nn.Module):
        def __init__(self, in_channels, out_channels, stride=1):
            super(ResidualBlock, self).__init__()
            self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
            self.bn1 = nn.BatchNorm2d(out_channels)
            self.relu = nn.ReLU(inplace=True)
            self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
            self.bn2 = nn.BatchNorm2d(out_channels)
            
            self.shortcut = nn.Sequential()
            if stride != 1 or in_channels != out_channels:
                self.shortcut = nn.Sequential(
                    nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                    nn.BatchNorm2d(out_channels)
                )
                
        def forward(self, x):
            out = self.relu(self.bn1(self.conv1(x)))
            out = self.bn2(self.conv2(out))
            out += self.shortcut(x)
            out = self.relu(out)
            return out
            
    class SimpleCNN(nn.Module):
        def __init__(self):
            super(SimpleCNN, self).__init__()
            self.in_channels = 64
            
            self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
            self.bn1 = nn.BatchNorm2d(64)
            self.relu = nn.ReLU(inplace=True)
            
            self.layer1 = self._make_layer(64, 2, stride=1)
            self.layer2 = self._make_layer(128, 2, stride=2)
            self.layer3 = self._make_layer(256, 2, stride=2)
            
            self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
            self.fc = nn.Linear(256, 10)
            
        def _make_layer(self, out_channels, num_blocks, stride):
            layers = []
            layers.append(ResidualBlock(self.in_channels, out_channels, stride))
            self.in_channels = out_channels
            for _ in range(1, num_blocks):
                layers.append(ResidualBlock(out_channels, out_channels))
            return nn.Sequential(*layers)
            
        def forward(self, x):
            out = self.relu(self.bn1(self.conv1(x)))
            out = self.layer1(out)
            out = self.layer2(out)
            out = self.layer3(out)
            out = self.avgpool(out)
            out = out.view(out.size(0), -1)
            out = self.fc(out)
            return out
    
    # Create model
    model = SimpleCNN()
    
    # Create input (batch_size, channels, height, width)
    batch_size = 64
    input_tensor = torch.randn(batch_size, 3, 224, 224)
    
    # CPU test
    print("Running on CPU...")
    model.eval()  # Set to evaluation mode
    start_time = time.time()
    with torch.no_grad():
        cpu_output = model(input_tensor)
    cpu_time = time.time() - start_time
    print(f"CPU forward pass time: {cpu_time:.4f} seconds")
    
    # GPU test
    print("Running on GPU...")
    model = model.cuda()
    input_tensor = input_tensor.cuda()
    
    torch.cuda.synchronize()
    start_time = time.time()
    with torch.no_grad():
        gpu_output = model(input_tensor)
    torch.cuda.synchronize()
    gpu_time = time.time() - start_time
    print(f"GPU forward pass time: {gpu_time:.4f} seconds")
    
    # Results
    speedup = cpu_time / gpu_time
    print(f"GPU speedup: {speedup:.2f}x")
    
    # Clear memory
    del model, input_tensor
    gc.collect()
    torch.cuda.empty_cache()
    
    # Test 3: Large tensor operations
    print("\nTest 3: Large Tensor Operations")
    print("Creating large tensors (10000x10000)...")
    
    try:
        # CPU test
        print("Running on CPU...")
        size = 10000
        cpu_tensor = torch.randn(size, size)
        
        start_time = time.time()
        cpu_result = torch.relu(cpu_tensor).pow(2).sum(dim=1)
        cpu_time = time.time() - start_time
        print(f"CPU time: {cpu_time:.4f} seconds")
        
        # GPU test
        print("Running on GPU...")
        gpu_tensor = cpu_tensor.cuda()
        
        # Clear memory
        del cpu_tensor
        gc.collect()
        
        torch.cuda.synchronize()
        start_time = time.time()
        gpu_result = torch.relu(gpu_tensor).pow(2).sum(dim=1)
        torch.cuda.synchronize()
        gpu_time = time.time() - start_time
        print(f"GPU time: {gpu_time:.4f} seconds")
        
        # Results
        speedup = cpu_time / gpu_time
        print(f"GPU speedup: {speedup:.2f}x")
        
        # Clear memory
        del gpu_tensor, gpu_result
        gc.collect()
        torch.cuda.empty_cache()
    except RuntimeError as e:
        print(f"Error in Test 3 (possibly out of memory): {e}")
        # Clear memory
        gc.collect()
        torch.cuda.empty_cache()
    
    print("\nCUDA Performance Test Completed!")

if __name__ == "__main__":
    test_cuda_full() 