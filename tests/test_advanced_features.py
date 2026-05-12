"""高级功能测试 - 订阅推送、ACK重传、心跳、持久化、任务调度"""
import time
import threading
import os
import shutil
from blinker import signal

import sys
sys.path.insert(0, 'src')

from robogame.common.datahub import get_datahub, DataHub
from robogame.common.events import DataHubEvent, ModuleEvent
from robogame.common.scheduler import (
    TaskScheduler, TaskPriority,
    HeartbeatManager, get_task_scheduler, get_heartbeat_manager
)


def test_subscription_push():
    """测试1：订阅推送模式"""
    print("\n=== 测试1: 订阅推送模式 ===")

    # 重置DataHub单例
    DataHub._instance = None

    datahub = get_datahub(persistence_dir='data/test_persistence')
    datahub.clear()
    datahub.start()

    received_values = []

    def on_cube_position_changed(key, value):
        print(f"  [订阅回调] key={key}, value={value}")
        received_values.append(value)

    # 订阅vision:cube_position
    datahub.subscribe('vision:cube_position', on_cube_position_changed)

    # 写入数据，触发推送
    print("  [写入] vision:cube_position = {'x': 100, 'y': 200}")
    datahub.write('vision:cube_position', {'x': 100, 'y': 200})

    time.sleep(0.1)

    # 再写入一次，看是否会再次触发
    print("  [写入] vision:cube_position = {'x': 150, 'y': 250}")
    datahub.write('vision:cube_position', {'x': 150, 'y': 250})

    time.sleep(0.1)

    # 写入不同key，不触发订阅
    print("  [写入] vision:other_data = {'x': 999}")
    datahub.write('vision:other_data', {'x': 999})

    time.sleep(0.1)

    datahub.stop()

    if len(received_values) == 2:
        print(f"  [Pass] 订阅推送测试通过，收到{len(received_values)}次推送")
        return True
    else:
        print(f"  [Fail] 期望2次推送，实际{len(received_values)}次")
        return False


def test_ack_with_retry():
    """测试2：事件ACK + 超时重传"""
    print("\n=== 测试2: 事件ACK + 超时重传 ===")

    # 重置DataHub单例
    DataHub._instance = None

    datahub = get_datahub(persistence_dir='data/test_persistence')
    datahub.clear()
    datahub._ack_timeout = 0.5  # 500ms超时
    datahub._max_retries = 2
    datahub.start()

    ack_received = []

    def on_ack(sender, request_id, key, success):
        print(f"  [ACK] request_id={request_id}, key={key}, success={success}")
        ack_received.append(request_id)

    ack_signal = signal('datahub:ack')
    ack_signal.connect(on_ack)

    comm_exception_received = []

    def on_comm_exception(sender, key, operation):
        print(f"  [通信异常] key={key}, operation={operation}")
        comm_exception_received.append(key)

    comm_signal = signal('datahub:communication_exception')
    comm_signal.connect(on_comm_exception)

    # 测试write_with_ack（同步等待）
    print("  [测试] write_with_ack")
    result = datahub.write_with_ack('test:key1', {'value': 1}, timeout=1.0)
    print(f"  [结果] write_with_ack={result}")

    time.sleep(0.2)

    datahub.stop()

    if result and len(ack_received) > 0:
        print(f"  [Pass] ACK机制正常")
        return True
    else:
        print(f"  [Fail] ACK机制异常")
        return False


def test_heartbeat_monitoring():
    """测试3：心跳保活机制"""
    print("\n=== 测试3: 心跳保活机制 ===")

    # 重置DataHub单例
    DataHub._instance = None

    datahub = get_datahub(persistence_dir='data/test_persistence')
    datahub.clear()
    datahub.HEARTBEAT_TIMEOUT = 2.0  # 2秒超时
    datahub.start()

    safety_shutdown_received = []

    def on_safety_shutdown(sender, module):
        print(f"  [安全停机] module={module}")
        safety_shutdown_received.append(module)

    safety_signal = signal('datahub:safety_shutdown')
    safety_signal.connect(on_safety_shutdown)

    # 创建心跳管理器
    hb_manager = get_heartbeat_manager('test_module')
    hb_manager.start()

    # 发送几次心跳
    for i in range(3):
        hb_manager.send_heartbeat()
        print(f"  [心跳] {i+1}")
        time.sleep(0.5)

    # 检查模块状态
    status = datahub.get_module_status('test_module')
    print(f"  [模块状态] test_module={status}")

    hb_manager.stop()

    # 等待超时
    print("  [等待] 等待心跳超时检测...")
    time.sleep(2.5)

    status_after = datahub.get_module_status('test_module')
    print(f"  [模块状态] after timeout={status_after}")

    datahub.stop()

    if status_after == 'offline' and len(safety_shutdown_received) > 0:
        print(f"  [Pass] 心跳监控测试通过，模块失联后触发安全机制")
        return True
    else:
        print(f"  [Fail] 心跳监控测试失败")
        return False


def test_persistence():
    """测试4：轻量持久化"""
    print("\n=== 测试4: 轻量持久化 ===")

    persistence_dir = 'data/test_persistence'

    # 清理旧数据
    if os.path.exists(persistence_dir):
        shutil.rmtree(persistence_dir)

    # 重置DataHub单例
    DataHub._instance = None

    datahub = get_datahub(persistence_dir=persistence_dir)
    datahub.clear()
    datahub.start()

    # 写入关键数据
    print("  [写入] 关键任务参数")
    datahub.write('strategy:task_param', {'task': 'collect_place_build', 'id': 1})
    datahub.write('collect:status', {'code': 1, 'msg': 'navigating'})
    datahub.write('module:error_info', {'error_code': 0})

    # 触发持久化
    datahub.persist_now()
    time.sleep(0.1)

    datahub.stop()

    # 检查文件是否生成
    state_file = os.path.join(persistence_dir, 'datahub_state.json')
    if os.path.exists(state_file):
        print(f"  [文件] 持久化文件已生成: {state_file}")

        with open(state_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"  [内容] {content}")

        # 重新创建DataHub，加载数据
        DataHub._instance = None
        datahub2 = get_datahub(persistence_dir=persistence_dir)
        datahub2.start()

        task_param = datahub2.get('strategy:task_param')
        collect_status = datahub2.get('collect:status')

        print(f"  [恢复] task_param={task_param}")
        print(f"  [恢复] collect_status={collect_status}")

        datahub2.stop()

        if task_param and collect_status:
            print(f"  [Pass] 持久化测试通过")
            return True
        else:
            print(f"  [Fail] 数据恢复失败")
            return False
    else:
        print(f"  [Fail] 持久化文件未生成")
        return False


def test_task_scheduler():
    """测试5：动态任务调度器"""
    print("\n=== 测试5: 动态任务调度器 ===")

    # 重置DataHub单例
    DataHub._instance = None

    datahub = get_datahub(persistence_dir='data/test_persistence')
    datahub.clear()
    datahub.start()

    scheduler = get_task_scheduler()

    task_events = []

    def on_task_created(sender, task_id, task_type):
        print(f"  [任务创建] task_id={task_id}, type={task_type}")
        task_events.append(('created', task_id, task_type))

    def on_task_started(sender, task_id):
        print(f"  [任务开始] task_id={task_id}")
        task_events.append(('started', task_id))

    signal('scheduler:task_created').connect(on_task_created)
    signal('scheduler:task_started').connect(on_task_started)

    # 创建任务
    print("  [创建] collect任务 (优先级NORMAL)")
    task1_id = scheduler.create_task('collect', {'x': 100, 'y': 200}, TaskPriority.NORMAL, cube_id=1)

    print("  [创建] place任务 (优先级HIGH)")
    task2_id = scheduler.create_task('place', {'x': 50, 'y': 50}, TaskPriority.HIGH)

    time.sleep(0.2)

    # 检查任务状态
    pending = scheduler.get_pending_tasks()
    running = scheduler.get_running_task()
    print(f"  [状态] 待执行任务: {len(pending)}, 运行中: {running is not None}")

    # 测试抢占
    print("  [抢占] 创建CRITICAL优先级的collect任务")
    task3_id = scheduler.create_task('collect', {'x': 300, 'y': 400}, TaskPriority.CRITICAL, cube_id=2)

    time.sleep(0.2)

    # 检查抢占后状态
    running_after_preempt = scheduler.get_running_task()
    print(f"  [抢占后] 运行中任务: {running_after_preempt}")

    # 测试目标切换
    print("  [切换] 切换当前任务目标")
    if running_after_preempt:
        scheduler.switch_target(running_after_preempt['task_id'], {'x': 999, 'y': 999})

    # 模拟任务完成
    if running_after_preempt:
        print(f"  [完成] 模拟任务完成")
        scheduler.on_task_complete(running_after_preempt['task_id'], {'success': True})

    time.sleep(0.2)

    # 测试中断恢复
    print("  [中断] 挂起当前任务")
    scheduler.suspend_current_task('test_suspend')

    print("  [恢复] 恢复被挂起的任务")
    # 获取挂起的任务ID
    pending = scheduler.get_pending_tasks()
    if pending:
        for p in pending:
            if p['state'] == 'suspended':
                scheduler.resume_task(p['task_id'])
                break

    time.sleep(0.2)

    datahub.stop()

    # 检查结果
    has_created = any(e[0] == 'created' for e in task_events)
    has_started = any(e[0] == 'started' for e in task_events)

    if has_created and has_started:
        print(f"  [Pass] 任务调度器测试通过")
        return True
    else:
        print(f"  [Fail] 任务调度器测试失败: {task_events}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("RoboGame 高级功能测试")
    print("=" * 60)

    tests = [
        ("订阅推送模式", test_subscription_push),
        ("ACK+超时重传", test_ack_with_retry),
        ("心跳保活机制", test_heartbeat_monitoring),
        ("轻量持久化", test_persistence),
        ("动态任务调度", test_task_scheduler),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"  [Error] {name} 异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

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
        print("\n所有高级功能测试通过!")
    else:
        print(f"\n有 {failed} 项测试失败，请检查!")

    # 清理测试数据
    if os.path.exists('data/test_persistence'):
        shutil.rmtree('data/test_persistence')


if __name__ == '__main__':
    run_all_tests()