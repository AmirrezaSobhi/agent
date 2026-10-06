# MT5 Capability Inventory — v0.1.3

| Agent command / API | Class | Status | Local side effect |
|---|---|---|---|
| `mt5.get_terminal_version` / `version` | READ | IMPLEMENTED | No |
| `mt5.get_account_information` / `account_info` | READ | IMPLEMENTED | No |
| `mt5.get_symbols_total` / `symbols_total` | READ | IMPLEMENTED | No |
| `mt5.get_terminal_information` | READ / health projection | IMPLEMENTED | No |
| symbol metadata/tick/orders/positions/history reads | READ or TRADE_ANALYSIS as applicable | PLANNED | No assumed side effect |
| `symbol_select` | LOCAL_STATE | EXCLUDED | Yes: selection state |
| `market_book_add` | LOCAL_STATE | EXCLUDED | Yes: subscription |
| `market_book_release` | LOCAL_STATE | EXCLUDED | Yes: subscription release |
| `order_send` | TRADE_EXECUTION | EXCLUDED | Yes: trading |

The three primary safe MT5 reads are implemented end to end through the
production `MT5Port` → `RuntimeWorkerMT5Adapter` → authenticated Worker path.
`mt5.get_terminal_information` is a sanitized view of Worker runtime health,
not an additional arbitrary Worker API operation. Implemented commands accept
an empty request payload and return Agent-owned JSON-safe structures. They are
only reachable through the versioned command registry; there is no remote
function-name dispatch. Account values are operationally sensitive: do not
log, publish, or place them in evidence. MT5 errors use safe operation/error
metadata and do not trigger a trade retry. Other inventory entries are not
advertised as executable capabilities. No trading operation is implemented as
a production capability.
