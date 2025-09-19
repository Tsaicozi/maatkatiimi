#!/usr/bin/env python3
"""
Load testing script for DiscoveryEngine
Runs comprehensive load tests and generates reports
"""
import asyncio
import time
import argparse
import json
from datetime import datetime
from typing import Dict, Any, List
from discovery_engine import DiscoveryEngine
from sources.mock_firehose import MockFirehoseSource
from rpc_stub import StubSolanaRPC
from tests.stubs_rpc import StubFastRPC
from metrics import init_metrics, metrics
from json_logging import setup_json_logging, generate_run_id

class LoadTestRunner:
    """Comprehensive load testing for DiscoveryEngine"""
    
    def __init__(self, test_duration_sec: int = 60, rate_per_sec: int = 500):
        self.test_duration_sec = test_duration_sec
        self.rate_per_sec = rate_per_sec
        self.results: Dict[str, Any] = {}
        self.json_logger = setup_json_logging()
        self.run_id = generate_run_id()
        self.json_logger.set_run_id(self.run_id)
        
    async def run_queue_stability_test(self) -> Dict[str, Any]:
        """Test queue stability under high load"""
        print("🧪 Running queue stability test...")
        
        # Setup
        mock_rpc = StubSolanaRPC(base_latency_ms=25.0, jitter_ms=10.0, error_rate=0.01)
        engine = DiscoveryEngine(
            rpc_endpoint="http://localhost:8899",
            market_sources=[],
            min_liq_usd=1000.0,
            rpc_client=mock_rpc
        )
        
        firehose = MockFirehoseSource(
            rate_per_sec=self.rate_per_sec,
            burst=50,
            jitter_ms=10
        )
        
        # Start components
        await engine.start()
        firehose_task = asyncio.create_task(firehose.run(engine.candidate_queue))
        
        # Monitor
        start_time = time.time()
        queue_samples = []
        max_queue_size = 0
        
        while time.time() - start_time < self.test_duration_sec:
            current_size = engine.candidate_queue.qsize()
            max_queue_size = max(max_queue_size, current_size)
            queue_samples.append({
                'timestamp': time.time(),
                'queue_size': current_size
            })
            await asyncio.sleep(0.1)
            
        # Stop components
        firehose.stop()
        firehose_task.cancel()
        await engine.stop()
        
        # Calculate results
        avg_queue_size = sum(s['queue_size'] for s in queue_samples) / len(queue_samples)
        
        result = {
            'test_name': 'queue_stability',
            'duration_sec': self.test_duration_sec,
            'rate_per_sec': self.rate_per_sec,
            'max_queue_size': max_queue_size,
            'avg_queue_size': avg_queue_size,
            'queue_samples': len(queue_samples),
            'success': max_queue_size < 15000 and avg_queue_size < 8000
        }
        
        self.json_logger.info("Queue stability test completed", extra=result)
        return result
        
    async def run_throughput_test(self) -> Dict[str, Any]:
        """Test scoring throughput"""
        print("🧪 Running throughput test...")
        
        # Setup
        mock_rpc = StubSolanaRPC(base_latency_ms=20.0, jitter_ms=5.0, error_rate=0.005)
        engine = DiscoveryEngine(
            rpc_endpoint="http://localhost:8899",
            market_sources=[],
            min_liq_usd=1000.0,
            rpc_client=mock_rpc
        )
        
        firehose = MockFirehoseSource(
            rate_per_sec=self.rate_per_sec,
            burst=25,
            jitter_ms=5
        )
        
        # Start components
        await engine.start()
        firehose_task = asyncio.create_task(firehose.run(engine.candidate_queue))
        
        # Monitor throughput
        start_time = time.time()
        initial_scored = metrics.candidates_scored._value._value if metrics else 0
        
        # Let it run
        await asyncio.sleep(self.test_duration_sec)
        
        # Stop components
        firehose.stop()
        firehose_task.cancel()
        
        # Wait for queue to drain
        while engine.candidate_queue.qsize() > 0:
            await asyncio.sleep(0.1)
            
        await engine.stop()
        
        # Calculate results
        final_scored = metrics.candidates_scored._value._value if metrics else 0
        scored_count = final_scored - initial_scored
        throughput = scored_count / self.test_duration_sec
        
        result = {
            'test_name': 'throughput',
            'duration_sec': self.test_duration_sec,
            'rate_per_sec': self.rate_per_sec,
            'candidates_scored': scored_count,
            'throughput_per_sec': throughput,
            'success': throughput > 20 and scored_count > 0
        }
        
        self.json_logger.info("Throughput test completed", extra=result)
        return result
        
    async def run_memory_test(self) -> Dict[str, Any]:
        """Test memory usage and cleanup"""
        print("🧪 Running memory test...")
        
        import psutil
        import gc
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Setup
        mock_rpc = StubSolanaRPC(base_latency_ms=30.0, jitter_ms=15.0, error_rate=0.02)
        engine = DiscoveryEngine(
            rpc_endpoint="http://localhost:8899",
            market_sources=[],
            min_liq_usd=1000.0,
            rpc_client=mock_rpc
        )
        
        firehose = MockFirehoseSource(
            rate_per_sec=self.rate_per_sec // 2,  # Lower rate for memory test
            burst=10,
            jitter_ms=5
        )
        
        # Start components
        await engine.start()
        firehose_task = asyncio.create_task(firehose.run(engine.candidate_queue))
        
        # Monitor memory during test
        memory_samples = []
        start_time = time.time()
        
        while time.time() - start_time < self.test_duration_sec:
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append({
                'timestamp': time.time(),
                'memory_mb': current_memory
            })
            await asyncio.sleep(1)
            
        # Stop components
        firehose.stop()
        firehose_task.cancel()
        await engine.stop()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(1)
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024
        max_memory = max(s['memory_mb'] for s in memory_samples)
        memory_leak = final_memory - initial_memory
        
        result = {
            'test_name': 'memory',
            'duration_sec': self.test_duration_sec,
            'initial_memory_mb': initial_memory,
            'max_memory_mb': max_memory,
            'final_memory_mb': final_memory,
            'memory_leak_mb': memory_leak,
            'success': memory_leak < 100 and max_memory < initial_memory + 200
        }
        
        self.json_logger.info("Memory test completed", extra=result)
        return result
        
    async def run_fast_rpc_test(self) -> Dict[str, Any]:
        """Test with fast stub RPC for maximum throughput"""
        print("🧪 Running fast RPC throughput test...")
        
        # Setup with fast RPC
        fast_rpc = StubFastRPC()
        engine = DiscoveryEngine(
            rpc_endpoint="http://localhost:8899",
            market_sources=[],
            min_liq_usd=1000.0,
            rpc_client=mock_rpc
        )
        
        firehose = MockFirehoseSource(
            rate_per_sec=self.rate_per_sec * 2,  # Double rate for fast RPC
            burst=50,
            jitter_ms=1
        )
        
        # Start components
        await engine.start()
        firehose_task = asyncio.create_task(firehose.run(engine.candidate_queue))
        
        # Monitor throughput
        start_time = time.time()
        initial_scored = metrics.candidates_scored._value._value if metrics else 0
        
        # Let it run
        await asyncio.sleep(self.test_duration_sec)
        
        # Stop components
        firehose.stop()
        firehose_task.cancel()
        
        # Wait for queue to drain
        while engine.candidate_queue.qsize() > 0:
            await asyncio.sleep(0.1)
            
        await engine.stop()
        
        # Calculate results
        final_scored = metrics.candidates_scored._value._value if metrics else 0
        scored_count = final_scored - initial_scored
        throughput = scored_count / self.test_duration_sec
        
        result = {
            'test_name': 'fast_rpc_throughput',
            'duration_sec': self.test_duration_sec,
            'rate_per_sec': self.rate_per_sec * 2,
            'candidates_scored': scored_count,
            'throughput_per_sec': throughput,
            'success': throughput > 100 and scored_count > 0  # Higher threshold for fast RPC
        }
        
        self.json_logger.info("Fast RPC test completed", extra=result)
        return result
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all load tests"""
        print(f"🚀 Starting load tests (duration: {self.test_duration_sec}s, rate: {self.rate_per_sec}/s)")
        
        # Setup metrics
        actual_port = init_metrics(namespace='load_test', host='127.0.0.1', port=9115, enabled=True)
        if actual_port:
            print(f"📊 Metrics endpoint: http://127.0.0.1:{actual_port}/metrics")
            
        # Run tests
        tests = [
            self.run_queue_stability_test(),
            self.run_throughput_test(),
            self.run_memory_test(),
            self.run_fast_rpc_test()
        ]
        
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        # Compile final report
        report = {
            'run_id': self.run_id,
            'timestamp': datetime.now().isoformat(),
            'test_duration_sec': self.test_duration_sec,
            'rate_per_sec': self.rate_per_sec,
            'tests': [],
            'summary': {
                'total_tests': len(results),
                'passed_tests': 0,
                'failed_tests': 0
            }
        }
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                report['tests'].append({
                    'test_name': f'test_{i}',
                    'error': str(result),
                    'success': False
                })
                report['summary']['failed_tests'] += 1
            else:
                report['tests'].append(result)
                if result.get('success', False):
                    report['summary']['passed_tests'] += 1
                else:
                    report['summary']['failed_tests'] += 1
                    
        # Save report
        report_file = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"📄 Report saved to: {report_file}")
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"   Total tests: {report['summary']['total_tests']}")
        print(f"   Passed: {report['summary']['passed_tests']}")
        print(f"   Failed: {report['summary']['failed_tests']}")
        
        return report

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Load test DiscoveryEngine')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--rate', type=int, default=500, help='Candidates per second')
    parser.add_argument('--output', type=str, help='Output file for results')
    
    args = parser.parse_args()
    
    runner = LoadTestRunner(
        test_duration_sec=args.duration,
        rate_per_sec=args.rate
    )
    
    try:
        report = await runner.run_all_tests()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Results saved to: {args.output}")
            
        # Exit with error code if any tests failed
        if report['summary']['failed_tests'] > 0:
            exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        exit(130)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
