from robogame.runtime import create_runtime
from robogame.types import ModuleState


def test_strategy_actuator_pipeline_reaches_global_done():
    runtime = create_runtime()

    runtime.strategy.start_task({"collect": {"target_id": 1, "threshold": 5}})
    for _ in range(3):
        runtime.collect.run_once()
    for _ in range(3):
        runtime.place.run_once()
    for _ in range(3):
        runtime.build.run_once()

    result = runtime.datahub.get("strategy:task_result")
    assert result["value"]["code"] == int(ModuleState.DONE)
    assert runtime.strategy.completed is True


def test_vision_data_update_is_readable_through_datahub():
    runtime = create_runtime()

    runtime.vision.update_cube_position({"x": 100, "y": 200, "z": 50})
    value, success = runtime.strategy.read_data("vision:cube_position")

    assert success is True
    assert value == {"x": 100, "y": 200, "z": 50}
