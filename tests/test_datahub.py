from robogame.communication.bus import EventBus
from robogame.datahub.hub import DataHub
from robogame.modules.base import BaseModule


def test_datahub_write_and_read_round_trip():
    bus = EventBus()
    DataHub(bus=bus)
    module = BaseModule("test", bus=bus)

    assert module.write_data("vision:cube_position", {"x": 1, "y": 2})
    value, success = module.read_data("vision:cube_position")

    assert success is True
    assert value == {"x": 1, "y": 2}
