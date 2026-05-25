"""Runtime assembly for the RoboGame framework."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from robogame.communication.bus import EventBus
from robogame.datahub.heartbeat import HeartbeatMonitor
from robogame.datahub.hub import DataHub
from robogame.modules import BuildModule, CollectModule, PlaceModule, StrategyModule, VisionModule


@dataclass
class RoboGameRuntime:
    bus: EventBus
    datahub: DataHub
    heartbeat_monitor: HeartbeatMonitor
    strategy: StrategyModule
    vision: VisionModule
    collect: CollectModule
    place: PlaceModule
    build: BuildModule

    def start(self) -> None:
        self.strategy.start()
        self.vision.start()
        self.collect.start()
        self.place.start()
        self.build.start()

    def stop(self) -> None:
        self.strategy.stop()
        self.vision.stop()
        self.collect.stop()
        self.place.stop()
        self.build.stop()


def create_runtime(persistence_dir: str | Path | None = None) -> RoboGameRuntime:
    bus = EventBus()
    persistent_keys = {
        "strategy:task_param",
        "strategy:collect_param",
        "strategy:place_param",
        "strategy:build_param",
        "collect:status",
        "place:status",
        "build:status",
        "module:error_info",
    }
    datahub = DataHub(bus=bus, persistence_dir=persistence_dir, persistent_keys=persistent_keys)
    return RoboGameRuntime(
        bus=bus,
        datahub=datahub,
        heartbeat_monitor=HeartbeatMonitor(bus=bus),
        strategy=StrategyModule(bus=bus),
        vision=VisionModule(bus=bus),
        collect=CollectModule(bus=bus),
        place=PlaceModule(bus=bus),
        build=BuildModule(bus=bus),
    )
