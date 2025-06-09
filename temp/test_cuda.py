import torch
import time
import os

def test_cuda():
    print("=" * 50)
    print("CUDA Environment Test")
    print("=" * 50)
    
    # Check if CUDA is available
    print(f"CUDA available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("CUDA is not available, please check installation")
        return
    
    # Get CUDA information
    print(f"CUDA device count: {torch.cuda.device_count()}")
    print(f"Current CUDA device: {torch.cuda.current_device()}")
    print(f"CUDA device name: {torch.cuda.get_device_name(0)}")
    
    # Test a simple tensor operation
    print("\nTesting tensor operations:")
    
    # Create random matrices on CPU
    size = 2000
    cpu_a = torch.randn(size, size)
    cpu_b = torch.randn(size, size)
    
    # Measure CPU matrix multiplication time
    start_time = time.time()
    cpu_result = torch.matmul(cpu_a, cpu_b)
    cpu_time = time.time() - start_time
    print(f"CPU matrix multiplication time: {cpu_time:.4f} seconds")
    
    # Transfer to GPU
    gpu_a = cpu_a.cuda()
    gpu_b = cpu_b.cuda()
    
    # Measure GPU matrix multiplication time
    torch.cuda.synchronize()  # Ensure GPU operations are completed
    start_time = time.time()
    gpu_result = torch.matmul(gpu_a, gpu_b)
    torch.cuda.synchronize()  # Ensure GPU operations are completed
    gpu_time = time.time() - start_time
    print(f"GPU matrix multiplication time: {gpu_time:.4f} seconds")
    
    # Compare performance improvement
    speedup = cpu_time / gpu_time
    print(f"GPU speedup: {speedup:.2f}x")
    
    # Verify result consistency
    cpu_result_np = cpu_result.numpy()
    gpu_result_np = gpu_result.cpu().numpy()
    max_diff = abs(cpu_result_np - gpu_result_np).max()
    print(f"Max difference between CPU and GPU results: {max_diff}")
    print(f"Results consistent: {max_diff < 1e-5}")
    
    print("\nTesting PyTorch model:")
    # Create a simple neural network
    model = torch.nn.Sequential(
        torch.nn.Linear(1000, 1000),
        torch.nn.ReLU(),
        torch.nn.Linear(1000, 1000),
        torch.nn.ReLU(),
        torch.nn.Linear(1000, 10)
    )
    
    # CPU test
    input_tensor = torch.randn(32, 1000)
    start_time = time.time()
    output_cpu = model(input_tensor)
    cpu_time = time.time() - start_time
    print(f"CPU model forward pass time: {cpu_time:.4f} seconds")
    
    # GPU test
    model = model.cuda()
    input_tensor = input_tensor.cuda()
    torch.cuda.synchronize()
    start_time = time.time()
    output_gpu = model(input_tensor)
    torch.cuda.synchronize()
    gpu_time = time.time() - start_time
    print(f"GPU model forward pass time: {gpu_time:.4f} seconds")
    
    # Compare performance improvement
    speedup = cpu_time / gpu_time
    print(f"GPU speedup: {speedup:.2f}x")
    
    print("\nEnvironment variables:")
    print(f"CUDA_HOME: {os.environ.get('CUDA_HOME', 'Not set')}")
    print(f"CUDA_PATH: {os.environ.get('CUDA_PATH', 'Not set')}")
    
    print("\nCUDA test completed!")

if __name__ == "__main__":
    test_cuda() 