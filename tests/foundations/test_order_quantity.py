from decimal import Decimal

from v5_2.foundations.order_quantity import (
    board,
    floor_quantity,
    minimum_buy,
    valid_buy,
    valid_sell,
)


def test_a_share_board_and_buy_lot_rules():
    assert board("600000") == "MAIN"
    assert board("000001") == "MAIN"
    assert board("300001") == "CHINEXT"
    assert board("688001") == "STAR"
    assert minimum_buy("600000") == 100
    assert minimum_buy("300001") == 100
    assert minimum_buy("688001") == 200
    assert valid_buy("600000", 100)
    assert not valid_buy("600000", 150)
    assert valid_buy("688001", 200)
    assert valid_buy("688001", 201)
    assert not valid_buy("688001", 199)


def test_sell_and_floor_rules_preserve_odd_lot_exit():
    assert valid_sell("600000", 50, 50)
    assert not valid_sell("600000", 50, 100)
    assert floor_quantity("600000", Decimal("287.8")) == 200
    assert floor_quantity("688001", Decimal("287.8")) == 287
