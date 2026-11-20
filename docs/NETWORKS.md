# Supported networks

Updated 25 October 2026. All adapters read mainnet data and never sign transactions.

| Network | Native balances | Automatic history | Review coverage |
| --- | --- | --- | --- |
| Ethereum | ETH | External transactions and ERC-20 transfers, 50 per stream/page | Supported movements can produce suggestions |
| Optimism | ETH | External transactions and ERC-20 transfers, 50 per stream/page | Native ledger alias ETH_OP keeps it separate from Ethereum ETH |
| BNB Chain | BNB | External native transactions with configured Etherscan API access | Native acquisition/disposal review; no token history or decoded swaps |
| Base | ETH | External native history through configured Etherscan API access; paid plan required | Ledger alias ETH_BASE; manual-cost confirmation |
| Arbitrum | ETH | External native history through configured Etherscan API access | Ledger alias ETH_ARB; manual-cost confirmation |
| Polygon | POL | External native history through configured Etherscan API access | Native POL; manual-cost confirmation |
| Avalanche | AVAX | C-Chain external native history via public Routescan, 50/page | Native AVAX; no X/P-Chain support |
| Sonic | S | External native history through configured Etherscan V2 access (chain 146) | Native S review; token history not indexed |
| Gnosis | XDAI | External native xDAI and ERC-20 transfers through public Blockscout | Native xDAI, not staking token GNO |
| Celo | CELO | External native CELO and ERC-20 transfers through public Blockscout | Alternate fee currencies not normalized; enter verified USD fees manually |
| Bitcoin | BTC | Confirmed address transactions, 25/page through mempool.space | Mainnet legacy/SegWit/Taproot checksums; mixed-input transactions excluded from review |
| Stellar | XLM | Horizon payments/create-account, 25/page | Classic G-addresses; issuer-qualified tokens; no muxed M-address support |
| Tron | TRX | Confirmed native TransferContract activity, 20/page | T-address or canonical 41-prefixed hex; no TRC-20 indexing |
| Arc | USDC | External native history with configured Etherscan access | Mainnet 5042; USDC_ARC alias; native18/ERC-20interface6 decimals never mixed |
| Monad | MON | External native history with configured Etherscan access | Mainnet143; no automatic token discovery |
| Robinhood Chain | ETH | External native history with configured Etherscan access | Mainnet4663; ETH_RH alias; not a Robinhood exchange account connection |
| Linea | ETH | External native history with configured Etherscan access | Mainnet59144; ETH_LINEA alias |
| Solana | SOL | Finalized native/SPL owner balance changes, 10 transactions/page | Known-decimal movement patterns can produce suggestions; rent/rewards remain ambiguous |
| Aptos | APT | Signed-account sequence windows, 25/page; recognized APT payloads | Recognized native transfers only; complete incoming and orderless history unavailable |
| Sui | SUI | GraphQL affected-address transactions, 10/page | Known native amounts only; a transaction with unknown token decimals or uncertain gas treatment is excluded from suggestions |

Adding an address triggers balance and history loading. Previously saved wallets receive one history refresh after this adapter upgrade. Transactions shows each wallet's actual coverage, errors and Load older activity when available. Provider failures retain saved history. No on-chain movement is automatically promoted into a purchase or sale.

## BNB explorer configuration

Set the server process environment variable ETHERSCAN_API_KEY to an Etherscan V2 key with BNB Chain history access, then restart `python server.py`. Provider plan restrictions may apply. The key is never returned to the browser or portfolio export. Without it, BNB balance tracking remains available and the UI reports that history setup is required. No BNB credential was supplied, so authenticated live BNB history was not verified; parsing and configuration behavior have offline regression coverage.

BNB pagination freezes the initial upper block and requests successive pages to avoid shifting as newer blocks arrive. Native transaction history excludes token and internal transfers.

## Important limits

Public RPCs and explorers impose rate limits and retention limits. These adapters do not guarantee complete lifetime history. Ethereum/Optimism histories omit internal transfers/NFTs; Aptos account sequence history excludes complete incoming activity; Solana balance changes can include rent/rewards and omit tokens lacking owner metadata; Sui unknown token decimals are shown as raw units rather than fabricated decimal amounts. Suggested swaps are heuristics requiring explicit confirmation, known cost and verified asset identity.

## Provider references

- Blockscout REST and pagination: https://docs.blockscout.com/devs/apis/rest
- Etherscan normal transactions: https://docs.etherscan.io/api-reference/endpoint/txlist
- Solana parsed transactions: https://solana.com/docs/rpc/http/gettransaction
- Solana signature history: https://solana.com/docs/rpc/http/getsignaturesforaddress
- Aptos account sequence history: https://aptos.guide/rest-api/operations/get_account_transactions
- Sui GraphQL queries and retention: https://docs.sui.io/develop/accessing-data/graphql/query-with-graphql

Validation uses temporary account databases, offline provider fixtures, and live public system-address smoke checks. Customer wallets are not used for additional network tests.


## Additional EVM networks

Base, Arbitrum One, Polygon PoS and Avalanche C-Chain support public address validation, native balances, explicit ERC-20 contract inspection, browser-wallet chain selection, market valuations and chain-specific ledger identities. Public RPC chain IDs were verified as 8453, 42161, 137 and 43114 respectively. Polygon uses native POL.

Avalanche external native history uses the public Routescan API; token transfers and internals are not indexed by this adapter. For Base, Arbitrum and Polygon, configure ETHERSCAN_API_KEY with access to the selected chain; Base requires a paid API plan. Current public Blockscout endpoints returned HTTP403 and the canonical service returned HTTP402 without credentials during verification. No supported keyless history fallback was found for those three networks. Balance and ERC-20 inspection remain available without an explorer key.

Optional RPC overrides: BASE_RPC_URL, ARB_RPC_URL, POLYGON_RPC_URL, AVAX_RPC_URL. Defaults are mainnet.base.org, arb1.arbitrum.io/rpc, polygon.publicnode.com and api.avax.network/ext/bc/C/rpc. Mainnet only; bridges, subnets, Polygon zkEVM and Avalanche X/P chains are not implied.

Official references: https://docs.arbitrum.io/chain-info ; https://docs.polygon.technology/pos/reference/rpc-endpoints ; https://build.avax.network/docs/rpcs/c-chain ; https://docs.blockscout.com/base-api .


## Sonic, Gnosis and Celo

Mainnet IDs 146, 100 and 42220 were verified live. Native balances and explicit ERC-20 inspection use read-only RPC endpoints. Native price IDs are sonic-3, xdai and celo; xDAI is fetched as a market quote rather than assumed to equal one USD. Browser wallet chain selection and explorer transaction links are supported. RPC environment overrides: SONIC_RPC_URL, GNOSIS_RPC_URL, CELO_RPC_URL.

Gnosis and Celo public Blockscout history passed live zero-address checks. Sonic uses ETHERSCAN_API_KEY with Sonic chain access and has offline parsing/configuration coverage; authenticated Sonic history was not verified without credentials. Celo supports paying gas in alternative currencies; this adapter leaves its native fee field unavailable instead of mislabelling another token fee as CELO. Original USD fees can be entered during review.

Sources: https://docs.soniclabs.com/sonic/build-on-sonic/getting-started ; https://docs.gnosischain.com/about/networks/mainnet/ ; https://docs.gnosischain.com/about/tokens/xdai . Celo RPC endpoint: https://forno.celo.org (mainnet chain ID verified).


## Bitcoin, Stellar, TRON, Arc, Monad, Robinhood Chain and Linea

Twenty network choices are now available. All new EVM entries use verified mainnet chain IDs (Arc5042, Monad143, Robinhood4663, Linea59144). Arc documentation moved to docs.arc.io and mainnet RPC rpc.mainnet.arc.io. All four EVM balance RPCs passed live read checks; indexed native history uses server ETHERSCAN_API_KEY with the correct chain's plan/access. No key was supplied, so those authenticated history calls were verified with offline fixtures rather than claimed as live imports.

Bitcoin tracks confirmed activity for a single address, not all HD-wallet change addresses. It supports checksummed mainnet legacy, SegWit and Bech32m/Taproot addresses. No seeds/private keys/xpub discovery. Pending transactions do not enter P&L review; mixed-owner inputs require manual review. Public mempool.space API rate limits apply.

Stellar accepts checksummed classic G addresses; muxed M addresses must be replaced by their underlying G address. Unfunded accounts show zero only on a genuine Horizon404. Native XLM balance includes reserves and is not a spendable-balance calculation. Payment history includes issuer-qualified tokens, but excludes full DEX offers/Soroban operations and does not fabricate fees.

TRON accepts checksummed T addresses or canonical41-prefixed account hex. Native TRX units are6decimals. Confirmed simple TransferContract records are recognized; smart contracts/TRC-10/TRC-20 are metadata or outside coverage. Optional TRON_PRO_API_KEY is sent only as a provider header; it is not returned to the UI or included in exports.

Arc uses USDC as native EVM asset with18decimals. Its optional ERC-20 interface at0x3600000000000000000000000000000000000000 exposes the same balance with6decimals. Explicit token inspection omits that interface to prevent duplicate native USDC rows; the app does not add the two balances. Unknown original purchase cost is still not inferred.

Source references: https://docs.arc.io/arc/references/connect-to-arc ; https://docs.arc.io/arc/references/contract-addresses ; https://docs.monad.xyz/developer-essentials/network-information ; https://docs.robinhood.com/chain/connecting/ ; https://docs.linea.build/get-started/build/network-info/ ; https://github.com/Blockstream/esplora/blob/master/API.md ; https://developers.stellar.org/docs/data/apis/horizon ; https://developers.tron.network/reference/get-transaction-info-by-account-address .


## Token inventory

Token snapshots now persist per wallet with full chain/contract identity, exact quantities and safely decoded names/symbols. Automatic EVM discovery requires supported indexing access for wide coverage: a configured Alchemy token API endpoint (per-chain ALCHEMY_*_RPC_URL) or recent Etherscan token-transfer history. These are bounded partial sources, not guaranteed all-time inventories. Robinhood Chain has a limited built-in PONS contract check so that known token is read without an indexer key. Solana continues its existing SPL/Token-2022 discovery. Other native-only adapters do not gain generic token discovery from this change. Explicit watched contracts are retained for future refreshes. Stale results are labelled and tokens without trustworthy pricing remain unvalued in USD.
