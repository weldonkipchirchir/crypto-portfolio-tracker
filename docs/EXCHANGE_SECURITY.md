# Exchange credentials and operating limits

Orbit supports Binance HMAC API keys for read-only Spot balance snapshots. It verifies the permission endpoint before reading balances, including on every manual sync. Trading, withdrawal and transfer permissions are rejected; missing permission flags are not accepted as proof of safety. Matched Simple Earn Flexible balances are queried read-only when LD positions are returned. Futures, margin, other Earn products and historical purchase costs are not imported. Holdings appear separately on Overview to prevent double counting wallet and ledger balances.

## Credential storage

- AES-256-GCM authenticated encryption using the maintained Python cryptography library.
- Fresh cryptographically random 96-bit nonce for every encryption. Nonce and authentication tag are stored with ciphertext; the master key is not stored in the portfolio database.
- Associated data binds records to Binance, the owning user, connection ID, envelope version and key ID. Cross-account copying and ciphertext/header tampering fail authentication.
- Versioned envelope: `v1:<key-id>:<nonce-and-ciphertext-base64>`. The key ID is public metadata, not key material.
- Production master key is a random 32-byte value stored as a Vercel Secret. Never place it in source control, client bundles, browser storage, screenshots or logs. Production and test environments use independent keys.
- Secrets are submitted only to same-origin authenticated endpoints and Binance HTTPS endpoints. Binance URLs are fixed and redirects are rejected. Returned account state never contains credentials; provider failures are replaced with safe messages. Password fields are cleared before connection verification, including failed attempts.
- This is encryption at rest, not a promise that keys cannot be stolen. Application/process compromise can expose credentials while the application decrypts them. A dedicated KMS and audited runtime access would further improve key custody; this deployment currently uses Vercel Secret storage, not KMS envelope encryption.

## Key rotation

Keep `ORBIT_EXCHANGE_KEY` as the current base64-encoded 32-byte key. `ORBIT_EXCHANGE_KEY_ID` defaults to `primary`. For rotation, choose a new unique ID and place required former keys in the secret `ORBIT_EXCHANGE_PREVIOUS_KEYS`, a JSON object mapping IDs to base64 keys (maximum eight). Previous keys decrypt only; new writes always use the active key. Restrict access to all these values.

Deploy with both keys available, rewrap each owner's records through `exchange_connections.rewrap_credentials(c, uid)` inside a database transaction, verify all records use the active ID, and only then retire old keys according to backup retention and recovery requirements. Rewrapping authenticates/decrypts all that owner's records before issuing updates. Never print plaintext keys or decrypted records during migration.

Legacy unversioned records remain readable with the original active key. Rewrap legacy records to versioned envelopes **before** changing that active key. Never overwrite an encryption key without a migration/recovery plan; lost keys make saved credentials unreadable. A compromised key also requires revoking/reissuing exchange API credentials, not merely re-encrypting them.

## Connecting Binance

In Connections, enter a dedicated Binance API key and secret. Enable reading only; disable all trading, withdrawal, transfer, margin, futures and options permissions. Apply exchange-side IP restrictions when supported by a stable outbound IP. Vercel deployments do not inherently guarantee a fixed egress IP; configure a supported static egress solution before relying on IP allowlisting. Do not enable dangerous permissions just to bypass a verification failure. Revoke the key in Binance when it is no longer used.

Do not paste credentials into chat. Real credential verification depends on Binance permissions, region availability, restrictions and the server clock. Automated tests use mocked Binance responses, not a user's live keys.

## Research

- [OWASP Cryptographic Storage](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html): authenticated AES encryption, secure random generation and key separation.
- [OWASP Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html): restricted custody, lifecycle and rotation.
- [Binance API key permissions](https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account): verified read-only flags.
- [Vercel Secret variables](https://vercel.com/changelog/environment-variables-now-use-config-and-secret-types): production configuration custody.


LD display and valuation: supported LD identifiers display as their underlying symbol with an Earn label, while raw identifiers and quantities remain preserved. Valuation uses matched Flexible Earn `totalAmount` from the fully paginated read-only `/sapi/v1/simple-earn/flexible/position` response, never a presumed 1:1 LD conversion. Only existing LD rows are valued; the same Earn position is not appended again. Spot rows remain separate. Pagination is bounded to 300 positions and unverified/missing responses leave Earn values unpriced. Pricing still depends on curated CoinGecko identities and available quotes. Unknown or ambiguous assets remain unpriced. Existing saved connections get display names on read; Sync balances fetches Earn quantities and new values.

References: [Binance Flexible positions](https://developers.binance.com/en/docs/catalog/investment-and-services-simple-earn/api/rest-api/flexible-locked#get-flexible-product-position-user_data), [Binance LDUSDT conversion explanation](https://www.binance.com/en-IN/support/faq/detail/a3e0a836380f4ef08ea46f9e2e67b4fd).

Automatic portfolio price checks use stored Spot/Earn quantities and public cached quotes. They never decrypt exchange credentials or call signed Binance endpoints. Balance/Earn quantity verification remains a separate Sync balances action. The original balance timestamp is preserved during repricing; missing quotes are marked stale.
