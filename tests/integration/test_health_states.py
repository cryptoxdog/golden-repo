from __future__ import annotations

from pathlib import Path

from chassis.health import ContractsProbe, DatabaseProbe, HealthAggregator


def test_healthy_when_ready_and_probes_pass(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / "packet_envelope_v1.yaml").write_text("contract: {}\n", encoding="utf-8")
    aggregator = HealthAggregator(service_name="svc", version="1.0")
    aggregator.register_probe(DatabaseProbe(str(db_path)))
    aggregator.register_probe(ContractsProbe(str(contracts_dir)))
    aggregator.set_ready()
    result = aggregator.evaluate()
    assert result["status"] == "healthy"


def test_degraded_when_contract_directory_is_empty(tmp_path: Path) -> None:
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    aggregator = HealthAggregator(service_name="svc", version="1.0")
    aggregator.register_probe(ContractsProbe(str(contracts_dir)))
    aggregator.set_ready()
    result = aggregator.evaluate()
    assert result["status"] == "degraded"


def test_unhealthy_when_contract_directory_missing(tmp_path: Path) -> None:
    aggregator = HealthAggregator(service_name="svc", version="1.0")
    aggregator.register_probe(ContractsProbe(str(tmp_path / "missing")))
    aggregator.set_ready()
    result = aggregator.evaluate()
    assert result["status"] == "unhealthy"


def test_not_ready_forces_unhealthy_even_with_good_probe(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    aggregator = HealthAggregator(service_name="svc", version="1.0")
    aggregator.register_probe(DatabaseProbe(str(db_path)))
    result = aggregator.evaluate()
    assert result["status"] == "unhealthy"
    assert result["ready"] is False


def test_uptime_and_identity_are_reported(tmp_path: Path) -> None:
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / "packet_envelope_v1.yaml").write_text("contract: {}\n", encoding="utf-8")
    aggregator = HealthAggregator(service_name="svc", version="2.0")
    aggregator.register_probe(ContractsProbe(str(contracts_dir)))
    aggregator.set_ready()
    result = aggregator.evaluate()
    assert result["service"] == "svc"
    assert result["version"] == "2.0"
    assert result["uptime_seconds"] >= 0
