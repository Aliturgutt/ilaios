# Desktop OIDC Fix Scope

This change does not alter the canonical identity model, Core, tenant model, authorization policy, provider selection, or deployment state.

It only preserves a safe normalized OAuth provider error code at the Desktop token-exchange boundary so a real provider failure can be diagnosed without exposing provider payloads or credentials.
