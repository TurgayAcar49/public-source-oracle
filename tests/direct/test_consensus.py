"""Leader/validator equivalence: independent re-fetch, then compare decision fields."""

from tests.direct.conftest import BTC_FEED, FLAG_FEED, STATUS_FEED, mock_json, register


def test_validator_agrees_on_identical_number(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 42.5}})

    contract.settle(0)
    assert direct_vm.run_validator() is True


def test_validator_agrees_within_tolerance(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 100}})
    contract.settle(0)

    # 1% drift, feed tolerance is 2% (200 bps).
    direct_vm.clear_mocks()
    mock_json(direct_vm, "prices/btc", {"data": {"price": 101}})
    assert direct_vm.run_validator() is True


def test_validator_rejects_outside_tolerance(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 100}})
    contract.settle(0)

    direct_vm.clear_mocks()
    mock_json(direct_vm, "prices/btc", {"data": {"price": 105}})
    assert direct_vm.run_validator() is False


def test_zero_tolerance_requires_exact_number(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    contract.register_feed(
        "block-height",
        "https://api.example.com/v1/height",
        "height",
        "number",
        0,
    )
    mock_json(direct_vm, "v1/height", {"height": 1000})
    contract.settle(0)

    direct_vm.clear_mocks()
    mock_json(direct_vm, "v1/height", {"height": 1001})
    assert direct_vm.run_validator() is False


def test_text_validator_requires_normalized_match(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, STATUS_FEED)
    mock_json(direct_vm, "v1/status", {"state": "  open  "})
    contract.settle(0)

    direct_vm.clear_mocks()
    mock_json(direct_vm, "v1/status", {"state": "open"})
    assert direct_vm.run_validator() is True

    direct_vm.clear_mocks()
    mock_json(direct_vm, "v1/status", {"state": "closed"})
    assert direct_vm.run_validator() is False


def test_boolean_validator_rejects_flip(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, FLAG_FEED)
    mock_json(direct_vm, "v1/flags", {"maintenance": False})
    contract.settle(0)

    direct_vm.clear_mocks()
    mock_json(direct_vm, "v1/flags", {"maintenance": True})
    assert direct_vm.run_validator() is False


def test_validator_rejects_when_source_disappears(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 42.5}})
    contract.settle(0)

    direct_vm.clear_mocks()
    mock_json(direct_vm, "prices/btc", {"error": "gone"}, status=404)
    assert direct_vm.run_validator() is False
