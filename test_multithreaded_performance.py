#!/usr/bin/env python3
"""
Test script to compare performance between single-threaded and multithreaded processing.
"""

import time
import subprocess
import sys
from pathlib import Path


def run_processor(script_name: str, workers: int = None) -> tuple[float, str]:
    """Run a processor script and return execution time and output."""
    cmd = [sys.executable, script_name]
    
    if workers:
        cmd.extend(['--workers', str(workers)])
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        end_time = time.time()
        
        if result.returncode == 0:
            return end_time - start_time, result.stdout
        else:
            return -1, f"Error: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return -1, "Timeout after 5 minutes"
    except Exception as e:
        return -1, f"Exception: {e}"


def main():
    """Main function to test performance."""
    print("🚀 ND Court Rules - Performance Comparison Test")
    print("=" * 60)
    
    # Check if raw files exist
    raw_dir = Path('data/raw')
    if not raw_dir.exists():
        print("❌ Raw directory not found. Please run the scraper first to generate raw files.")
        return 1
    
    category_files = list(raw_dir.glob("category_*.html"))
    if not category_files:
        print("❌ No category files found. Please run the scraper first.")
        return 1
    
    print(f"📁 Found {len(category_files)} category files to process")
    print()
    
    # Test single-threaded version
    print("🔄 Testing single-threaded processor...")
    single_time, single_output = run_processor('process_raw_files.py')
    
    if single_time > 0:
        print(f"✅ Single-threaded completed in {single_time:.2f} seconds")
    else:
        print(f"❌ Single-threaded failed: {single_output}")
        return 1
    
    print()
    
    # Test multithreaded versions with different worker counts
    worker_counts = [2, 4, 8]
    results = {}
    
    for workers in worker_counts:
        print(f"🔄 Testing multithreaded processor with {workers} workers...")
        multi_time, multi_output = run_processor('process_raw_files_multithreaded.py', workers)
        
        if multi_time > 0:
            results[workers] = multi_time
            speedup = single_time / multi_time
            print(f"✅ {workers} workers completed in {multi_time:.2f} seconds (speedup: {speedup:.2f}x)")
        else:
            print(f"❌ {workers} workers failed: {multi_output}")
    
    print()
    print("📊 Performance Summary:")
    print("=" * 40)
    print(f"Single-threaded: {single_time:.2f} seconds (baseline)")
    
    for workers, time_taken in results.items():
        speedup = single_time / time_taken
        efficiency = (speedup / workers) * 100
        print(f"{workers} workers: {time_taken:.2f} seconds (speedup: {speedup:.2f}x, efficiency: {efficiency:.1f}%)")
    
    # Find best configuration
    if results:
        best_workers = min(results.keys(), key=lambda w: results[w])
        best_time = results[best_workers]
        best_speedup = single_time / best_time
        print(f"\n🏆 Best configuration: {best_workers} workers")
        print(f"   Time: {best_time:.2f} seconds")
        print(f"   Speedup: {best_speedup:.2f}x")
    
    return 0


if __name__ == "__main__":
    exit(main()) 