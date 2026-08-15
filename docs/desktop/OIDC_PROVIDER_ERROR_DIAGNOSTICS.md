# Desktop OIDC Provider Error Diagnostics

The Desktop OIDC adapter may surface only a normalized OAuth provider `error` code when token exchange fails (for example `invalid_grant`, `invalid_client`, `unauthorized_client`).

It must not expose or persist authorization codes, PKCE verifiers, access tokens, ID tokens, refresh tokens, client secrets, bearer tokens, raw provider payloads, or provider `error_description` text.

This diagnostic behavior exists only to distinguish the provider failure class while preserving the existing provider-neutral Authorization Code + PKCE architecture and canonical `services.identity` session boundary.
