"""通信延迟测试"""
import time
import statistics
from blinker import signal

import sys
sys.path.insert(0, 'src')

from robogame.common.datahub import get_datahub
from robogame.common.events import DataHubEvent


def test_datahub_write_latency():
    """测试DataHub写入延迟"""
    print("\n=== 测试 DataHub 写入延迟 ===")

    datahub = get_datahub()
    datahub.clear()

    latencies = []
    iterations = 1000

    for i in range(iterations):
        start = time.perf_counter()
        datahub.write('test:data', {'index': i, 'value': i * 2})
        end = time.perf_counter()
        latencies.append((end - start) * 1000)

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)
    p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else max(latencies)

    print(f"  迭代次数: {iterations}")
    print(f"  平均延迟: {avg_latency:.4f} ms")
    print(f"  P50延迟:  {p50_latency:.4f} ms")
    print(f"  P95延迟:  {p95_latency:.4f} ms")
    print(f"  P99延迟:  {p99_latency:.4f} ms")
    print(f"  最大延迟: {max(latencies):.4f} ms")
    print(f"  最小延迟: {min(latencies):.4f} ms")

    return avg_latency


def test_datahub_read_latency():
    """测试DataHub读取延迟（单向，不等待返回）"""
    print("\n=== 测试 DataHub 读取延迟（发送） ===")

    datahub = get_datahub()
    datahub.clear()

    latencies = []
    iterations = 1000

    for i in range(iterations):
        start = time.perf_counter()
        datahub.read('test:data', f'req_{i}')
        end = time.perf_counter()
        latencies.append((end - start) * 1000)

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)

    print(f"  迭代次数: {iterations}")
    print(f"  平均延迟: {avg_latency:.4f} ms")
    print(f"  P50延迟:  {p50_latency:.4f} ms")

    return avg_latency


def test_datahub_write_read_roundtrip():
    """测试DataHub写-读往返延迟"""
    print("\n=== 测试 DataHub 写-读往返延迟 ===")

    datahub = get_datahub()
    datahub.clear()

    received_count = {'count': 0}

    def on_data_return(sender, request_id, key, value):
        received_count['count'] += 1

    data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
    data_return_signal.connect(on_data_return)

    latencies = []
    iterations = 500

    for i in range(iterations):
        request_id = f'req_{i}'

        start = time.perf_counter()
        datahub.write('test:roundtrip', {'index': i})
        datahub.read('test:roundtrip', request_id)
        end = time.perf_counter()

        latencies.append((end - start) * 1000)

    time.sleep(0.1)

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)

    print(f"  迭代次数: {iterations}")
    print(f"  平均延迟: {avg_latency:.4f} ms")
    print(f"  P50延迟:  {p50_latency:.4f} ms")
    print(f"  P95延迟:  {p95_latency:.4f} ms")

    return avg_latency


def test_full_communication_cycle():
    """测试完整通信周期（写->读->返回）"""
    print("\n=== 测试 完整通信周期（写->读->返回） ===")

    datahub = get_datahub()
    datahub.clear()

    received_data = []
    cycle_count = 0

    def on_data_return(sender, request_id, key, value):
        received_data.append({'request_id': request_id, 'key': key, 'value': value, 'time': time.perf_counter()})
        nonlocal cycle_count
        cycle_count += 1

    data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
    data_return_signal.connect(on_data_return)

    iterations = 100
    start_times = []
    end_times = []

    for i in range(iterations):
        request_id = f'cycle_req_{i}'
        start = time.perf_counter()
        start_times.append(start)

        datahub.write('test:cycle_data', {'index': i, 'timestamp': start})
        datahub.read('test:cycle_data', request_id)

        end = time.perf_counter()
        end_times.append(end)

    time.sleep(0.2)

    if received_data:
        latencies = []
        for i, rd in enumerate(received_data[:iterations]):
            if i < len(start_times):
                latencies.append((rd['time'] - start_times[i]) * 1000)

        if latencies:
            avg_latency = statistics.mean(latencies)
            print(f"  完成周期数: {len(received_data)}/{iterations}")
            print(f"  平均延迟: {avg_latency:.4f} ms")
            return avg_latency

    print(f"  完成周期数: {len(received_data)}/{iterations}")
    print(f"  平均延迟: N/A")

    return None


def test_blinker_event_latency():
    """测试Blinker事件发送延迟"""
    print("\n=== 测试 Blinker 事件发送延迟 ===")

    latencies = []
    iterations = 1000

    test_signal = signal('test:latency')

    def handler(sender, **kwargs):
        pass

    test_signal.connect(handler)

    for i in range(iterations):
        start = time.perf_counter()
        test_signal.send(None, index=i)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)

    avg_latency = statistics.mean(latencies)
    p50_latency = statistics.median(latencies)

    print(f"  迭代次数: {iterations}")
    print(f"  平均延迟: {avg_latency:.4f} ms")
    print(f"  P50延迟:  {p50_latency:.4f} ms")

    return avg_latency


def test_multi_module_latency():
    """测试多模块级联延迟"""
    print("\n=== 测试 多模块级联延迟 (Vision->Strategy->Collect) ===")

    datahub = get_datahub()
    datahub.clear()

    from robogame.common.events import VisionEvent, StrategyEvent, CollectEvent

    module_hops = {'vision_to_datahub': [], 'strategy_to_datahub': [], 'collect_to_datahub': []}

    def on_vision_data_updated(sender, request_id, data_key):
        hop_start = time.perf_counter()
        datahub.write('vision:processed', {'processed': True})
        hop_end = time.perf_counter()
        module_hops['vision_to_datahub'].append((hop_end - hop_start) * 1000)

    def on_start_collect(sender, request_id, data_key):
        hop_start = time.perf_counter()
        datahub.read('strategy:collect_param', f'strategy_req_{request_id}')
        hop_end = time.perf_counter()
        module_hops['strategy_to_datahub'].append((hop_end - hop_start) * 1000)

    def on_collect_status(sender, request_id, data_key):
        hop_start = time.perf_counter()
        datahub.write('collect:status', {'code': 1, 'msg': 'navigating'})
        hop_end = time.perf_counter()
        module_hops['collect_to_datahub'].append((hop_end - hop_start) * 1000)

    vision_signal = signal(VisionEvent.DATA_UPDATED.value)
    vision_signal.connect(on_vision_data_updated)

    strategy_signal = signal(StrategyEvent.START_COLLECT.value)
    strategy_signal.connect(on_start_collect)

    collect_signal = signal(CollectEvent.STATUS_UPDATED.value)
    collect_signal.connect(on_collect_status)

    iterations = 100
    total_start = time.perf_counter()

    for i in range(iterations):
        datahub.write('vision:cube_position', {'x': i, 'y': i})
        vision_signal.send(None, request_id=f'vis_{i}', data_key='vision:cube_position')

        datahub.write('strategy:collect_param', {'target_id': i})
        strategy_signal.send(None, request_id=f'str_{i}', data_key='strategy:collect_param')

        datahub.write('collect:status', {'code': 0})
        collect_signal.send(None, request_id=f'col_{i}', data_key='collect:status')

    total_end = time.perf_counter()

    time.sleep(0.1)

    total_avg = ((total_end - total_start) / iterations) * 1000

    print(f"  迭代次数: {iterations}")
    print(f"  每轮平均总耗时: {total_avg:.4f} ms")

    for hop_name, latencies in module_hops.items():
        if latencies:
            print(f"  {hop_name}: {statistics.mean(latencies):.4f} ms (avg)")

    return total_avg


def run_latency_tests():
    """运行所有延迟测试"""
    print("=" * 60)
    print("RoboGame 通信延迟测试")
    print("=" * 60)

    results = {}

    results['datahub_write'] = test_datahub_write_latency()
    results['datahub_read'] = test_datahub_read_latency()
    results['datahub_roundtrip'] = test_datahub_write_read_roundtrip()
    results['full_cycle'] = test_full_communication_cycle()
    results['blinker_event'] = test_blinker_event_latency()
    results['multi_module'] = test_multi_module_latency()

    print("\n" + "=" * 60)
    print("延迟测试结果汇总")
    print("=" * 60)

    for name, latency in results.items():
        if latency is not None:
            print(f"  {name}: {latency:.4f} ms")
        else:
            print(f"  {name}: N/A")

    print("\n结论:")
    print("  - DataHub写入延迟应该在微秒级")
    print("  - Blinker事件发送延迟应该在微秒级")
    print("  - 完整往返延迟取决于事件处理链长度")

    if results.get('datahub_write', float('inf')) < 1.0:
        print("  ✓ DataHub写入延迟 < 1ms (毫秒量级)")
    else:
        print(f"  ✗ DataHub写入延迟 = {results['datahub_write']:.4f}ms (超出预期)")


if __name__ == '__main__':
    run_latency_tests()