from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.glinet_router import update
from custom_components.glinet_router.const import DOMAIN, WAN_INTERFACE_NAMES
from custom_components.glinet_router.entities import (
    binary_sensor,
    button,
    select,
    sensor,
    sensor_descriptions,
    switch,
)

INTEGRATION_DIR = Path(__file__).parent.parent / "custom_components" / "glinet_router"
TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"
LANGUAGES = sorted(path.stem for path in TRANSLATIONS_DIR.glob("*.json"))
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(node: Any, prefix: str) -> dict[str, str]:
    if not isinstance(node, dict):
        return {prefix: node}
    flat: dict[str, str] = {}
    for key, value in node.items():
        flat.update(_flatten(value, f"{prefix}.{key}"))
    return flat


def _translations(language: str) -> dict[str, str]:
    return _flatten(_load(TRANSLATIONS_DIR / f"{language}.json"), f"component.{DOMAIN}")


def _hub() -> MagicMock:
    hub = MagicMock()
    hub.device_mac = "00:11:22:33:44:55"
    hub.device_info = {}
    return hub


def _entities() -> Iterator[tuple[str, Any]]:
    client = SimpleNamespace(mac="aa:bb:cc:dd:ee:ff", name="Phone")
    groups: dict[str, Callable[[], list[Any]]] = {
        "sensor": lambda: [
            *(sensor.SystemStatusSensor(_hub(), d) for d in sensor_descriptions.SYSTEM_SENSORS),
            *(sensor.HubStatusSensor(_hub(), d) for d in sensor_descriptions.HUB_SENSORS),
            *(
                sensor.ClientSensor(_hub(), client, d)
                for d in sensor_descriptions.CLIENT_BANDWIDTH_SENSORS
                + sensor_descriptions.CLIENT_DIAGNOSTIC_SENSORS
            ),
            *(
                sensor.CellularTrafficSensor(_hub(), d)
                for d in sensor_descriptions._build_cellular_traffic_descriptions(1, 0)
            ),
            *(
                sensor.WanStatusSensor(_hub(), name, {"ipv4"})
                for name in [*WAN_INTERFACE_NAMES, "custom_wan"]
            ),
            sensor.RepeaterChannelSensor(_hub()),
        ],
        "binary_sensor": lambda: [
            binary_sensor.RepeaterConnectedBinarySensor(_hub()),
            binary_sensor.RepeaterBareModeBinarySensor(_hub()),
            binary_sensor.FanRunningBinarySensor(_hub()),
            binary_sensor.GLinetBatteryAbnormalBinarySensor(_hub()),
        ],
        "button": lambda: [
            button.RebootButton(_hub()),
            button.DisconnectRepeaterButton(_hub()),
            button.ScanWifiButton(_hub()),
            button.TestFanButton(_hub()),
        ],
        "select": lambda: [
            select.WifiNetworkSelect(_hub()),
            select.RepeaterBandSelect(_hub()),
            select.GLinetClientParentalGroupSelect(_hub(), client),
        ],
        "switch": lambda: [
            switch.TailscaleSwitch(_hub()),
            switch.WireGuardServerSwitch(_hub()),
            switch.OpenVpnServerSwitch(_hub()),
            switch.ZeroTierSwitch(_hub()),
            switch.RepeaterAutoSwitchSwitch(_hub()),
            switch.RepeaterBareModeSwitch(_hub()),
            switch.RepeaterSmartReconnectSwitch(_hub()),
            switch.AdGuardEnabledSwitch(_hub()),
            switch.AdGuardDnsEnabledSwitch(_hub()),
            switch.GLinetDMZSwitch(_hub()),
            switch.GLinetWANAccessSwitch(_hub(), "ping", "mdi:access-point-network"),
            switch.GLinetWANAccessSwitch(_hub(), "https", "mdi:web"),
            switch.GLinetWANAccessSwitch(_hub(), "ssh", "mdi:console-network"),
            switch.GLinetParentalControlGlobalSwitch(_hub()),
            switch.GLinetClientInternetAccessSwitch(_hub(), client),
            switch.LedSwitch(_hub()),
        ],
        "update": lambda: [update.GLinetFirmwareUpdateEntity(_hub())],
    }
    for platform, factory in groups.items():
        for entity in factory():
            yield platform, entity


def _resolved_names(language: str) -> dict[str, str]:
    translations = _translations(language)
    names: dict[str, str] = {}
    for platform, entity in _entities():
        entity.platform_data = SimpleNamespace(
            platform_name=DOMAIN,
            domain=platform,
            platform_translations=translations,
            component_translations={},
        )
        names[entity.unique_id] = entity.name
    return names


def test_strings_json_matches_english_translation() -> None:
    assert _load(INTEGRATION_DIR / "strings.json") == _load(TRANSLATIONS_DIR / "en.json")


@pytest.mark.parametrize("language", [lang for lang in LANGUAGES if lang != "en"])
def test_translation_matches_english_keys_and_placeholders(language: str) -> None:
    english = _translations("en")
    translated = _translations(language)

    assert set(translated) == set(english)
    for key, text in english.items():
        assert set(PLACEHOLDER.findall(translated[key])) == set(PLACEHOLDER.findall(text)), key


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_entity_name_is_translated(language: str) -> None:
    names = _resolved_names(language)

    missing = [uid for uid, name in names.items() if not isinstance(name, str) or not name]
    assert not missing
    unresolved = [name for name in names.values() if PLACEHOLDER.search(name)]
    assert not unresolved


def test_english_entity_names_are_unchanged() -> None:
    names = _resolved_names("en")
    mac = "00:11:22:33:44:55"

    assert names[f"glinet_sensor/{mac}/system_memory_use"] == "Memory usage"
    assert names[f"glinet_sensor/{mac}/battery_charging_status"] == "Battery charging status"
    assert names[f"glinet_sensor/{mac}/wan_status_wan"] == "Ethernet 1 status"
    assert names[f"glinet_sensor/{mac}/wan_status_custom_wan"] == "custom_wan status"
    assert (
        names[f"glinet_sensor/{mac}/cellular_traffic_sim_1_0_traffic_total"]
        == "SIM 1 Traffic total"
    )
    assert names["glinet_client_sensor/aa:bb:cc:dd:ee:ff/total_rx"] == "Total download"
    assert names[f"glinet_binary_sensor/{mac}/fan_running"] == "Fan status"
    assert names[f"glinet_button/{mac}/reboot"] == "Reboot"
    assert names[f"glinet_switch/{mac}/wan_access_ping"] == "WAN Ping"
    assert names[f"glinet_switch/{mac}/led"] == "System LED"
    assert names[f"glinet_update/{mac}/firmware"] == "Firmware"


def test_german_entity_names() -> None:
    names = _resolved_names("de")
    mac = "00:11:22:33:44:55"

    assert names[f"glinet_sensor/{mac}/system_memory_use"] == "RAM-Auslastung"
    assert names[f"glinet_sensor/{mac}/wan_status_wan"] == "Status Ethernet 1"
    assert names[f"glinet_sensor/{mac}/wan_status_custom_wan"] == "Status custom_wan"
    assert (
        names[f"glinet_sensor/{mac}/cellular_traffic_sim_1_0_traffic_total"]
        == "SIM 1 Datenvolumen gesamt"
    )
    assert names[f"glinet_button/{mac}/reboot"] == "Neu starten"
    assert names[f"glinet_switch/{mac}/led"] == "System-LED"
