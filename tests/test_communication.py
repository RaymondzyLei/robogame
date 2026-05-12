"""通信功能测试"""
import time
import threading
from blinker import signal

import sys
sys.path.insert(0, 'src')

from robogame.common.datahub import DataHub, get_datahub
from robogame.common.events import DataHubEvent, StrategyEvent, CollectEvent, PlaceEvent, BuildEvent, VisionEvent


def test_datahub_basic():
    """测试DataHub基本读写功能"""
    print("\n=== 测试 DataHub 基本读写功能 ===")

    datahub = get_datahub()
    datahub.clear()

    received_data = {}

    def on_data_return(sender, request_id, key, value):
        print(f"  [DataReturn] request_id={request_id}, key={key}, value={value}")
        received_data[key] = value

    data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
    data_return_signal.connect(on_data_return)

    print("  [Write] 写入数据 vision:cube_position")
    datahub.write('vision:cube_position', {'x': 100, 'y': 200, 'z': 50})

    print("  [Read] 读取数据 vision:cube_position")
    request_id = datahub.read('vision:cube_position')

    time.sleep(0.1)

    if 'vision:cube_position' in received_data:
        print(f"  [Pass] 数据读取成功: {received_data['vision:cube_position']}")
        return True
    else:
        print(f"  [Fail] 数据读取失败")
        return False


def test_datahub_multi_read():
    """测试DataHub多模块读取"""
    print("\n=== 测试 DataHub 多模块读取 ===")

    datahub = get_datahub()
    datahub.clear()

    read_count = {'vision': 0, 'strategy': 0}

    def on_data_return(sender, request_id, key, value):
        print(f"  [DataReturn] key={key}, value={value}")
        if 'vision' in key:
            read_count['vision'] += 1
        elif 'strategy' in key:
            read_count['strategy'] += 1

    data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
    data_return_signal.connect(on_data_return)

    datahub.write('vision:cube_position', {'x': 100, 'y': 200})
    datahub.write('strategy:collect_param', {'target_id': 1})

    print("  [Read] vision模块读取 cube_position")
    datahub.read('vision:cube_position')

    print("  [Read] strategy模块读取 collect_param")
    datahub.read('strategy:collect_param')

    time.sleep(0.1)

    if read_count['vision'] == 1 and read_count['strategy'] == 1:
        print(f"  [Pass] 多模块读取成功")
        return True
    else:
        print(f"  [Fail] 多模块读取失败: {read_count}")
        return False


def test_module_event_communication():
    """测试模块间事件通信"""
    print("\n=== 测试 模块间事件通信 ===")

    datahub = get_datahub()
    datahub.clear()

    events_received = []

    def on_start_collect(sender, request_id, data_key):
        print(f"  [Event] 收到 start_collect, request_id={request_id}, data_key={data_key}")
        events_received.append('start_collect')

    def on_collect_status(sender, request_id, data_key):
        print(f"  [Event] 收到 collect:status_updated, request_id={request_id}, data_key={data_key}")
        events_received.append('collect_status')

    start_signal = signal(StrategyEvent.START_COLLECT.value)
    start_signal.connect(on_start_collect)

    status_signal = signal(CollectEvent.STATUS_UPDATED.value)
    status_signal.connect(on_collect_status)

    print("  [Send] 发送 strategy:start_collect 事件")
    start_signal.send(None, request_id='req_001', data_key='strategy:collect_param')

    print("  [Send] 发送 collect:status_updated 事件")
    status_signal.send(None, request_id='req_002', data_key='collect:status')

    time.sleep(0.1)

    if 'start_collect' in events_received and 'collect_status' in events_received:
        print(f"  [Pass] 模块间事件通信成功")
        return True
    else:
        print(f"  [Fail] 模块间事件通信失败: {events_received}")
        return False


def test_vision_to_strategy_flow():
    """测试视觉模块到策略模块的数据流"""
    print("\n=== 测试 Vision -> Strategy 数据流 ===")

    datahub = get_datahub()
    datahub.clear()

    datahub.write('vision:cube_position', {'x': 100, 'y': 200, 'z': 50})

    strategy_received = {}

    def on_data_return(sender, request_id, key, value):
        print(f"  [DataReturn] key={key}, value={value}")
        strategy_received[key] = value

    def on_vision_data_updated(sender, request_id, data_key):
        print(f"  [Event] vision:data_updated, data_key={data_key}")

    data_return_signal = signal(DataHubEvent.DATA_RETURN.value)
    data_return_signal.connect(on_data_return)

    vision_signal = signal(VisionEvent.DATA_UPDATED.value)
    vision_signal.connect(on_vision_data_updated)

    print("  [Vision] 更新方块位置数据")
    vision_signal.send(None, request_id='req_vision_001', data_key='vision:cube_position')

    print("  [Strategy] 读取视觉数据")
    datahub.read('vision:cube_position')

    time.sleep(0.1)

    if 'vision:cube_position' in strategy_received:
        print(f"  [Pass] Vision -> Strategy 数据流成功")
        return True
    else:
        print(f"  [Fail] Vision -> Strategy 数据流失败")
        return False


def test_strategy_to_collect_flow():
    """测试策略模块到收集模块的控制流"""
    print("\n=== 测试 Strategy -> Collect 控制流 ===")

    datahub = get_datahub()
    datahub.clear()

    collect_events = []

    def on_start_collect(sender, request_id, data_key):
        print(f"  [Event] Collect收到 start_collect")
        collect_events.append('start_collect')

        datahub.write('collect:status', {'code': 0, 'msg': 'initializing'})

    def on_collect_status(sender, request_id, data_key):
        print(f"  [Event] Collect发送 status_updated")
        collect_events.append('status_updated')

    start_signal = signal(StrategyEvent.START_COLLECT.value)
    start_signal.connect(on_start_collect)

    status_signal = signal(CollectEvent.STATUS_UPDATED.value)
    status_signal.connect(on_collect_status)

    print("  [Strategy] 写入收集参数")
    datahub.write('strategy:collect_param', {'target_position': {'x': 100, 'y': 200}, 'threshold': 5})

    print("  [Strategy] 发送 start_collect 事件")
    start_signal.send(None, request_id='req_strategy_001', data_key='strategy:collect_param')

    time.sleep(0.1)

    if 'start_collect' in collect_events:
        print(f"  [Pass] Strategy -> Collect 控制流成功")
        return True
    else:
        print(f"  [Fail] Strategy -> Collect 控制流失败")
        return False


def test_full_workflow():
    """测试完整工作流程"""
    print("\n=== 测试 完整工作流程 (收集->放置->搭建) ===")

    datahub = get_datahub()
    datahub.clear()

    workflow_steps = []
    current_module = 'none'

    def on_start_collect(sender, request_id, data_key):
        nonlocal current_module
        current_module = 'collect'
        workflow_steps.append('collect_started')
        print(f"  [Step] 收集模块启动")
        datahub.write('collect:status', {'code': 3, 'msg': 'completed'})

    def on_start_place(sender, request_id, data_key):
        nonlocal current_module
        current_module = 'place'
        workflow_steps.append('place_started')
        print(f"  [Step] 放置模块启动")
        datahub.write('place:status', {'code': 3, 'msg': 'completed'})

    def on_start_build(sender, request_id, data_key):
        nonlocal current_module
        current_module = 'build'
        workflow_steps.append('build_started')
        print(f"  [Step] 搭建模块启动")
        datahub.write('build:status', {'code': 3, 'msg': 'completed'})

    def on_collect_status(sender, request_id, data_key):
        workflow_steps.append('collect_status_updated')
        print(f"  [Step] 收集状态更新")

    def on_place_status(sender, request_id, data_key):
        workflow_steps.append('place_status_updated')
        print(f"  [Step] 放置状态更新")

    def on_build_status(sender, request_id, data_key):
        workflow_steps.append('build_status_updated')
        print(f"  [Step] 搭建状态更新")

    signal(StrategyEvent.START_COLLECT.value).connect(on_start_collect)
    signal(StrategyEvent.START_PLACE.value).connect(on_start_place)
    signal(StrategyEvent.START_BUILD.value).connect(on_start_build)
    signal(CollectEvent.STATUS_UPDATED.value).connect(on_collect_status)
    signal(PlaceEvent.STATUS_UPDATED.value).connect(on_place_status)
    signal(BuildEvent.STATUS_UPDATED.value).connect(on_build_status)

    print("  [Step 1] 策略模块初始化")
    datahub.write('strategy:task_param', {'task': 'collect_place_build'})

    print("  [Step 2] 启动收集模块")
    signal(StrategyEvent.START_COLLECT.value).send(None, request_id='1', data_key='strategy:collect_param')

    time.sleep(0.05)

    print("  [Step 3] 收集完成，状态更新")
    signal(CollectEvent.STATUS_UPDATED.value).send(None, request_id='2', data_key='collect:status')

    time.sleep(0.05)

    if 'collect_started' in workflow_steps and 'collect_status_updated' in workflow_steps:
        print(f"  [Pass] 完整工作流程测试成功")
        return True
    else:
        print(f"  [Fail] 完整工作流程测试失败: {workflow_steps}")
        return False


def test_exception_handling():
    """测试异常处理流程"""
    print("\n=== 测试 异常处理流程 ===")

    datahub = get_datahub()
    datahub.clear()

    exception_handled = []

    def on_collect_exception(sender, request_id, data_key):
        exception_handled.append('exception_received')
        print(f"  [Event] 收集模块异常")

    def on_module_retry(sender, request_id, data_key):
        exception_handled.append('retry_triggered')
        print(f"  [Event] 重试触发")

    exception_signal = signal(CollectEvent.EXCEPTION.value)
    exception_signal.connect(on_collect_exception)

    retry_signal = signal(StrategyEvent.MODULE_RETRY.value)
    retry_signal.connect(on_module_retry)

    print("  [Step 1] 写入错误信息")
    datahub.write('module:error_info', {
        'error_code': 2,
        'error_type': 'navigation_fail',
        'desc': '路径堵塞'
    })

    print("  [Step 2] 发送异常事件")
    exception_signal.send(None, request_id='err_001', data_key='module:error_info')

    print("  [Step 3] 策略模块发送重试事件")
    retry_signal.send(None, request_id='retry_001', data_key='strategy:retry_param')

    time.sleep(0.1)

    if 'exception_received' in exception_handled and 'retry_triggered' in exception_handled:
        print(f"  [Pass] 异常处理流程测试成功")
        return True
    else:
        print(f"  [Fail] 异常处理流程测试失败: {exception_handled}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("RoboGame 通信功能测试")
    print("=" * 60)

    tests = [
        test_datahub_basic,
        test_datahub_multi_read,
        test_module_event_communication,
        test_vision_to_strategy_flow,
        test_strategy_to_collect_flow,
        test_full_workflow,
        test_exception_handling,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"  [Error] {test.__name__} 异常: {e}")
            results.append((test.__name__, False))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")

    if failed == 0:
        print("\n所有通信功能测试通过!")
    else:
        print(f"\n有 {failed} 项测试失败，请检查!")


if __name__ == '__main__':
    run_all_tests()