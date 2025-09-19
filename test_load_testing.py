"""
Load testing for DiscoveryEngine with mock data sources
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from discovery_engine import DiscoveryEngine, TokenCandidate
from sources.mock_firehose import MockFirehoseSource
from rpc_stub import StubSolanaRPC
from tests.stubs_rpc import StubFastRPC
from metrics import init_metrics, metrics

class TestLoadTesting:
    """Load testing scenarios for DiscoveryEngine"""
    
    @pytest.fixture
    def setup_metrics(self):
        """Setup metrics for testing"""
        actual_port = init_metrics(namespace='load_test', host='127.0.0.1', port=9114, enabled=True)
        return actual_port
        
    @pytest.fixture
    def mock_rpc(self):
        """Create mock RPC with realistic latency"""
        return StubSolanaRPC(
            base_latency_ms=30.0,
            jitter_ms=10.0,
            error_rate=0.005,  # 0.5% error rate
            timeout_sec=3.0
        )
        
    @pytest.fixture
    def fast_rpc(self):
        """Create fast stub RPC for high-throughput testing"""
        return StubFastRPC()
        
    @pytest.fixture
    def discovery_engine(self, mock_rpc):
        """Create DiscoveryEngine with mock RPC"""
        # Mock market sources (empty list for load testing)
        from discovery_engine import MarketSource
        mock_sources = []
        
        engine = DiscoveryEngine(
            rpc_endpoint="http://localhost:8899",  # Mock endpoint
            market_sources=mock_sources,
            min_liq_usd=1000.0,
            rpc_client=mock_rpc
        )
        return engine
        
    @pytest.mark.asyncio
    async def test_queue_stability_under_load(self, setup_metrics, discovery_engine):
        """Test that queue doesn't explode under high load"""
        print("\n🧪 Testing queue stability under load...")
        
        # Create high-rate mock source
        firehose = MockFirehoseSource(rate_per_sec=1000, burst=50, jitter_ms=10)
        
        # Start discovery engine
        await discovery_engine.start()
        
        # Start firehose source
        firehose_task = asyncio.create_task(firehose.run(discovery_engine.candidate_queue))
        
        # Monitor for 30 seconds
        start_time = time.time()
        max_queue_size = 0
        queue_samples = []
        
        while time.time() - start_time < 30:
            current_size = discovery_engine.candidate_queue.qsize()
            max_queue_size = max(max_queue_size, current_size)
            queue_samples.append(current_size)
            
            # Check that queue isn't exploding
            assert current_size < 50000, f"Queue size {current_size} too large!"
            
            await asyncio.sleep(0.1)
            
        # Stop firehose
        firehose.stop()
        firehose_task.cancel()
        
        # Stop discovery engine
        await discovery_engine.stop()
        
        # Analyze results
        avg_queue_size = sum(queue_samples) / len(queue_samples)
        print(f"✅ Max queue size: {max_queue_size}")
        print(f"✅ Average queue size: {avg_queue_size:.1f}")
        print(f"✅ Queue samples: {len(queue_samples)}")
        
        # Assertions
        assert max_queue_size < 10000, f"Queue grew too large: {max_queue_size}"
        assert avg_queue_size < 5000, f"Average queue size too high: {avg_queue_size}"
        
    @pytest.mark.asyncio
    async def test_scoring_throughput(self, setup_metrics, discovery_engine):
        """Test scoring throughput under load"""
        print("\n🧪 Testing scoring throughput...")
        
        # Create moderate-rate mock source
        firehose = MockFirehoseSource(rate_per_sec=500, burst=25, jitter_ms=5)
        
        # Start discovery engine
        await discovery_engine.start()
        
        # Start firehose source
        firehose_task = asyncio.create_task(firehose.run(discovery_engine.candidate_queue))
        
        # Monitor scoring for 20 seconds
        start_time = time.time()
        initial_scored = metrics.candidates_scored._value._value if metrics else 0
        
        while time.time() - start_time < 20:
            await asyncio.sleep(1)
            
        # Stop firehose
        firehose.stop()
        firehose_task.cancel()
        
        # Wait for queue to drain
        while discovery_engine.candidate_queue.qsize() > 0:
            await asyncio.sleep(0.1)
            
        # Stop discovery engine
        await discovery_engine.stop()
        
        # Calculate throughput
        final_scored = metrics.candidates_scored._value._value if metrics else 0
        scored_count = final_scored - initial_scored
        throughput = scored_count / 20.0  # per second
        
        print(f"✅ Candidates scored: {scored_count}")
        print(f"✅ Throughput: {throughput:.1f} candidates/sec")
        
        # Assertions
        assert scored_count > 0, "No candidates were scored"
        assert throughput > 10, f"Throughput too low: {throughput} candidates/sec"
        
    @pytest.mark.asyncio
    async def test_no_background_tasks_leak(self, setup_metrics, discovery_engine):
        """Test that no background tasks leak after shutdown"""
        print("\n🧪 Testing background task cleanup...")
        
        # Count initial tasks
        initial_tasks = len(asyncio.all_tasks())
        print(f"Initial tasks: {initial_tasks}")
        
        # Create and start firehose
        firehose = MockFirehoseSource(rate_per_sec=200, burst=10, jitter_ms=5)
        await discovery_engine.start()
        firehose_task = asyncio.create_task(firehose.run(discovery_engine.candidate_queue))
        
        # Let it run for 10 seconds
        await asyncio.sleep(10)
        
        # Stop everything
        firehose.stop()
        firehose_task.cancel()
        await discovery_engine.stop()
        
        # Wait for cleanup
        await asyncio.sleep(2)
        
        # Count final tasks
        final_tasks = len(asyncio.all_tasks())
        print(f"Final tasks: {final_tasks}")
        
        # Check for task leaks
        task_leak = final_tasks - initial_tasks
        print(f"Task leak: {task_leak}")
        
        # Allow some tolerance for test framework tasks
        assert task_leak <= 2, f"Too many leaked tasks: {task_leak}"
        
    @pytest.mark.asyncio
    async def test_metrics_accuracy_under_load(self, setup_metrics, discovery_engine):
        """Test that metrics remain accurate under load"""
        print("\n🧪 Testing metrics accuracy under load...")
        
        if not metrics:
            pytest.skip("Metrics not enabled")
            
        # Reset metrics
        metrics.candidates_seen._value._value = 0
        metrics.candidates_scored._value._value = 0
        metrics.candidates_filtered._value._value = 0
        
        # Create firehose
        firehose = MockFirehoseSource(rate_per_sec=300, burst=15, jitter_ms=5)
        
        # Start discovery engine
        await discovery_engine.start()
        
        # Start firehose source
        firehose_task = asyncio.create_task(firehose.run(discovery_engine.candidate_queue))
        
        # Let it run for 15 seconds
        await asyncio.sleep(15)
        
        # Stop everything
        firehose.stop()
        firehose_task.cancel()
        
        # Wait for queue to drain
        while discovery_engine.candidate_queue.qsize() > 0:
            await asyncio.sleep(0.1)
            
        await discovery_engine.stop()
        
        # Check metrics
        seen = metrics.candidates_seen._value._value
        scored = metrics.candidates_scored._value._value
        filtered = metrics.candidates_filtered._value._value
        
        print(f"✅ Candidates seen: {seen}")
        print(f"✅ Candidates scored: {scored}")
        print(f"✅ Candidates filtered: {filtered}")
        
        # Basic sanity checks
        assert seen > 0, "No candidates were seen"
        assert scored >= 0, "Negative scored count"
        assert filtered >= 0, "Negative filtered count"
        assert scored + filtered <= seen, "Scored + filtered > seen"
        
        # Check that scoring is happening
        if seen > 100:  # Only check if we have enough data
            scoring_rate = scored / seen
            assert scoring_rate > 0.1, f"Scoring rate too low: {scoring_rate}"
            
    @pytest.mark.asyncio
    async def test_high_throughput_with_fast_rpc(self, setup_metrics, fast_rpc):
        """Test high throughput with fast stub RPC"""
        print("\n🧪 Testing high throughput with fast RPC...")
        
        # Create DiscoveryEngine with fast RPC
        engine = DiscoveryEngine(
            rpc_endpoint="http://localhost:8899",
            market_sources=[],
            min_liq_usd=1000.0,
            rpc_client=fast_rpc
        )
        
        # Create high-rate mock source
        firehose = MockFirehoseSource(rate_per_sec=2000, burst=100, jitter_ms=2)
        
        # Start discovery engine
        await engine.start()
        
        # Start firehose source
        firehose_task = asyncio.create_task(firehose.run(engine.candidate_queue))
        
        # Monitor throughput for 15 seconds
        start_time = time.time()
        initial_scored = metrics.candidates_scored._value._value if metrics else 0
        
        while time.time() - start_time < 15:
            await asyncio.sleep(1)
            
        # Stop firehose
        firehose.stop()
        firehose_task.cancel()
        
        # Wait for queue to drain
        while engine.candidate_queue.qsize() > 0:
            await asyncio.sleep(0.1)
            
        # Stop discovery engine
        await engine.stop()
        
        # Calculate results
        final_scored = metrics.candidates_scored._value._value if metrics else 0
        scored_count = final_scored - initial_scored
        throughput = scored_count / 15.0  # per second
        
        print(f"✅ High throughput test: {scored_count} candidates scored in 15s")
        print(f"✅ Throughput: {throughput:.1f} candidates/sec")
        
        # With fast RPC, we should see much higher throughput
        assert scored_count > 0, "No candidates were scored with fast RPC"
        assert throughput > 50, f"Throughput too low with fast RPC: {throughput} candidates/sec"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
