"""Signal registry.

Every signal the team is actively testing or trading must be listed here.
The backtest engine and the tests read ACTIVE_SIGNALS.

To add a signal: import its module and add one line, for example
    "oil_inventory_surprise": oil_inventory_surprise.compute_signal,
"""

from signals import oil_inventory_surprise

ACTIVE_SIGNALS = {
    "oil_inventory_surprise": oil_inventory_surprise.compute_signal,
}
