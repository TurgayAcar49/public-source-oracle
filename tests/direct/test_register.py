"""Registration, access control, and feed lifecycle."""

from tests.direct.conftest import BTC_FEED, FLAG_FEED, STATUS_FEED, register, to_hex


def test_deploy_sets_owner(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    assert contract.get_owner() == to_hex(direct_alice)
    assert contract.get_feed_count() == 0


def test_register_feed_persists_state(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")

    feed_id = register(contract, BTC_FEED)
    assert feed_id == 0
    assert contract.get_feed_count() == 1
    assert contract.has_feed("btc-usd") is True

    feed = contract.get_feed(0)
    assert feed["name"] == "btc-usd"
    assert feed["source_url"] == BTC_FEED["source_url"]
    assert feed["json_path"] == "data.price"
    assert feed["value_kind"] == "number"
    assert feed["tolerance_bps"] == 200
    assert feed["status"] == "active"
    assert feed["creator"] == to_hex(direct_alice)
    assert feed["settlement_count"] == 0
    assert feed["last_http_status"] == 0


def test_register_assigns_monotonic_ids(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    assert register(contract, BTC_FEED) == 0
    assert register(contract, STATUS_FEED) == 1
    assert register(contract, FLAG_FEED) == 2
    assert contract.get_feed_count() == 3
    assert contract.get_feed_id("repo-status") == 1


def test_duplicate_name_reverts(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)
    with direct_vm.expect_revert("name already registered"):
        register(contract, BTC_FEED)


def test_rejects_http_url(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    with direct_vm.expect_revert("source_url must be an https URL"):
        contract.register_feed("bad", "http://example.com/price", "price", "number", 0)


def test_rejects_invalid_kind(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    with direct_vm.expect_revert("value_kind must be number, text, or boolean"):
        contract.register_feed(
            "bad",
            "https://api.example.com/x",
            "value",
            "sentiment",
            0,
        )


def test_rejects_out_of_range_tolerance(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    with direct_vm.expect_revert("tolerance_bps must be 0-10000"):
        contract.register_feed(
            "bad",
            "https://api.example.com/x",
            "price",
            "number",
            10001,
        )


def test_non_number_feed_forces_zero_tolerance(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    contract.register_feed(
        "repo-status",
        STATUS_FEED["source_url"],
        "state",
        "text",
        500,
    )
    assert contract.get_feed(0)["tolerance_bps"] == 0


def test_unknown_feed_reverts(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    with direct_vm.expect_revert("unknown feed"):
        contract.get_feed(9)


def test_pause_and_resume_by_creator(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)

    contract.pause_feed(0)
    assert contract.get_feed(0)["status"] == "paused"
    contract.resume_feed(0)
    assert contract.get_feed(0)["status"] == "active"


def test_stranger_cannot_pause(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")
    register(contract, BTC_FEED)

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("not authorized"):
        contract.pause_feed(0)


def test_owner_can_pause_other_creators_feed(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    direct_vm.sender = direct_alice
    contract = direct_deploy("contracts/public_source_oracle.py")

    direct_vm.sender = direct_bob
    register(contract, BTC_FEED)

    direct_vm.sender = direct_alice
    contract.pause_feed(0)
    assert contract.get_feed(0)["status"] == "paused"
