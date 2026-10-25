# Read-only integration capabilities

`token_integrations.token_balances(chain, address, contracts=None)` returns
`{tokens: [...], errors: [...], coverage: str, updated_at: unix_seconds}`.
EVM tokens contain asset_id, contract, quantity (exact decimal string), decimals,
identity_verified=false. Solana tokens contain asset_id, mint, program, quantity,
decimals, identity_verified=false. Errors preserve successful contracts/programs.

Ethereum, Optimism and BNB use only explicit ERC-20 contract addresses (max 20).
There is no automatic token discovery. Solana enumerates both legacy SPL and
Token-2022 accounts and aggregates by mint; max 1000 accounts per program.
Unsupported Aptos/Sui token discovery is explicitly identified in coverage.
Token balances cannot establish purchase history or P&L. Unknown contracts and
mints must not be priced by symbol or added to manually tracked trade holdings,
which would risk counterfeit-token pricing and double counting.

`recent_activity(chain, address, limit=25, before=None)` currently supports Solana
only; limits 1..100. Returns `{activities, next_cursor, coverage, updated_at}`.
Each activity contains signature, slot, nullable timestamp, failed. These are
finalized signature records, not interpreted buys/sells, and provider retention
can omit older activity. It does not fetch transaction details or infer cost basis.
A full page returns a pagination cursor; the next page may be empty.

## Official specifications consulted

- Ethereum eth_call is read-only and supports ERC-20 balanceOf:
  https://ethereum.org/developers/docs/apis/json-rpc/
- SPL account enumeration with jsonParsed:
  https://solana.com/docs/rpc/http/gettokenaccountsbyowner
- Solana recent signatures and before cursor:
  https://solana.com/docs/rpc/http/getsignaturesforaddress
- Solana Foundation lists the separate legacy and Token-2022 program IDs:
  https://github.com/solana-foundation/solana-dev-skill/blob/main/skills/solana-dev/references/rpc-quick-lookups.md

## Exchange connection requirements

Robinhood is an exchange platform, not a blockchain. The official Crypto Trading
API is available to US customers. Read accounts, holdings and orders can be scoped
when generating credentials in crypto account settings. Requests require
x-api-key, x-signature and x-timestamp; the signature uses an API signing private
key (distinct from any wallet seed). Never request a wallet seed or custody key.
Read-only calls exist in both API versions. A connector must restrict requests to
GET and approved fixed hosts/paths, paginate order executions, retain original
IDs for idempotence, normalize fee currency and timestamps, and reconcile
partial fills. Holdings alone cannot establish historical cost basis.

Sources: https://robinhood.com/us/en/support/articles/crypto-api/
and https://docs.robinhood.com/

Coinbase Advanced Trade offers authenticated fill history. A production connector
needs view-only authorization, cursor pagination, fill deduplication and separate
transfer history. See https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/orders/list-fills

No authenticated exchange connector is implemented. Before enabling one, deploy
TLS and encrypted per-user credential storage with a master key kept outside the
database, ensure secrets never appear in logs/state/exports, support revocation,
and verify provider-granted permissions. Public multi-user integrations may also
require provider app registration/OAuth review. CSV remains the credential-free
fallback. Public wallet queries reveal the queried address to the RPC provider.

## Validation

Run `python -m unittest test_token_integrations -v` (8 offline tests). Tests cover
exact units, read-only RPC methods, malformed responses, per-provider partial
failure, SPL aggregation and owner verification, and bounded activity cursors.
No customer addresses or credentials were used for development validation.

## Automatic Ethereum address history

`history.fetch_history(chain,address,cursors=None)` fetches one Blockscout page
(maximum 50 entries) for each of external transactions and token transfers.
Ethereum only is currently supported. Returns `items`, `cursors`, `coverage`,
`updated_at`. Missing cursor keys start their stream; explicit null means that
stream is exhausted and should be skipped. Persist each stream cursor separately.
Items have event_id, hash, date (nullable for pending), kind, direction, asset,
asset_id, quantity, fee (nullable, ETH units), status, from_address, to_address,
identity_verified. Symbols are untrusted; token identity uses the contract address.
Only confirmed actual fees are returned; pending maximum fee estimates are omitted.

No internal transfers, NFTs, swaps or historical purchase costs are inferred.
Transfers are not buys or sells. Failed and pending records must not alter holdings
or accounting. Native and token records may share transaction hashes but have
separate event IDs; fee belongs only to the external transaction record.

Blockscout official REST pagination specification:
https://docs.blockscout.com/devs/apis/rest

Validation: `python -m unittest test_history -v` (5 tests), plus a public Ethereum
zero-address live smoke test fetched 98 native/token/contract events across two
pages. No customer address was used. Live test caught actual transaction cursor
fee fields and pending null timestamps, both handled explicitly.
