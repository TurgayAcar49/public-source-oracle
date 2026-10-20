"""Settlement writes attested values after the leader extraction."""

from tests.direct.conftest import BTC_FEED, FLAG_FEED, STATUS_FEED, mock_json, register


MICRO = 1_000_000


def test_settle_number_feed(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 42.5}})

    contract.settle(0)

    feed = contract.get_feed(0)
    assert feed["last_number"] == int(42.5 * MICRO)
    assert feed["last_http_status"] == 200
    assert feed["settlement_count"] == 1
    assert feed["last_error"] == ""

    value = contract.get_last_value(0)
    assert value["kind"] == "number"
    assert value["value"] == int(42.5 * MICRO)
    assert value["settlement_count"] == 1


def test_settle_nested_array_path(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    contract.register_feed(
        "first-rate",
        "https://api.example.com/v1/rates",
        "rates.0.usd",
        "number",
        0,
    )
    mock_json(direct_vm, "v1/rates", {"rates": [{"usd": 1}, {"usd": 2}]})

    contract.settle(0)
    assert contract.get_last_value(0)["value"] == 1 * MICRO


def test_settle_text_feed(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, STATUS_FEED)
    mock_json(direct_vm, "v1/status", {"state": "open"})

    contract.settle(0)
    assert contract.get_last_value(0)["value"] == "open"


def test_settle_boolean_feed_from_string(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, FLAG_FEED)
    mock_json(direct_vm, "v1/flags", {"maintenance": "true"})

    contract.settle(0)
    assert contract.get_last_value(0)["value"] is True


def test_settle_paused_feed_reverts(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    contract.pause_feed(0)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 42.5}})

    with direct_vm.expect_revert("feed is paused"):
        contract.settle(0)


def test_anyone_can_settle(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 10}})

    direct_vm.sender = direct_bob
    contract.settle(0)
    assert contract.get_feed(0)["settlement_count"] == 1


def test_missing_json_field_reverts(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"volume": 1}})

    with direct_vm.expect_revert("path field 'price' was not found"):
        contract.settle(0)


def test_client_error_reverts_external(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"error": "gone"}, status=404)

    with direct_vm.expect_revert("[EXTERNAL] source returned 404"):
        contract.settle(0)
    assert contract.get_feed(0)["settlement_count"] == 0


def test_invalid_json_reverts_parse(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", "not-json")

    with direct_vm.expect_revert("[PARSE] source body is not valid JSON"):
        contract.settle(0)


def test_resettle_overwrites_previous_value(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    mock_json(direct_vm, "prices/btc", {"data": {"price": 10}})
    contract.settle(0)

    direct_vm.clear_mocks()
    mock_json(direct_vm, "prices/btc", {"data": {"price": 11}})
    contract.settle(0)

    assert contract.get_last_value(0)["value"] == 11 * MICRO
    assert contract.get_feed(0)["settlement_count"] == 2
