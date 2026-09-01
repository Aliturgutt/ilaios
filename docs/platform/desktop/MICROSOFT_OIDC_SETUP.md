# ILAIOS Desktop — Microsoft OIDC App Registration Contract

This document defines only the external Microsoft identity inputs required by the existing Desktop broker. It does not claim that a Microsoft App Registration, Store product, publisher identity, or Store certification already exists.

## Registration intent

ILAIOS Desktop is a native/public Windows client. It uses the system browser with OAuth 2.0 Authorization Code + OpenID Connect + S256 PKCE. It must not have an embedded Microsoft client secret.

For the intended product audience, register the application for:

**Accounts in any organizational directory and personal Microsoft accounts.**

This supports both Microsoft Entra work/school identities and personal Microsoft accounts such as Outlook/Hotmail. If product policy changes, account-type scope must be deliberately re-reviewed; do not silently widen or narrow it in code.

## Entra application settings

Use Microsoft Entra **App registrations** and create one application named `ILAIOS Desktop` (or the approved product-visible name).

Required external values/settings:

- Supported account types: organizational directories + personal Microsoft accounts.
- Platform: **Mobile and desktop applications**.
- System-browser redirect URI: `http://localhost/oauth/callback`.
- Public client: enabled for the native Desktop application.
- Application (client) ID: record the value assigned by Microsoft and supply it to Desktop configuration.
- Client secret: **do not create or supply one for ILAIOS Desktop**.

The packaged Desktop identity server listens on an ephemeral local port. At runtime Microsoft authorization requests use `http://localhost:<ephemeral-port>/oauth/callback`. Microsoft Entra's localhost redirect matching ignores the port for native loopback redirects while preserving the path, so the stable registered URI remains `http://localhost/oauth/callback`.

## Provider configuration

Add the Microsoft provider to `ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON` alongside the already configured providers. Replace only the client-ID placeholder with the real Application (client) ID assigned by Microsoft.

```json
{
  "provider_id": "microsoft",
  "display_name": "Microsoft",
  "issuer": "https://login.microsoftonline.com/{tenantid}/v2.0",
  "authorization_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
  "token_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
  "jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
  "client_id": "<MICROSOFT_APPLICATION_CLIENT_ID>",
  "scopes": ["openid", "profile", "email"]
}
```

The Desktop runtime adds `offline_access` to Microsoft authorization requests so that a refresh token can be issued for protected restart continuity. Refresh material remains adapter-owned and is protected by Windows DPAPI; it is not returned to Flutter or logged.

## Verification model

Because the `common` Microsoft v2 metadata is tenant-independent, token verification is not a simple fixed-string issuer check. The Desktop verifier must:

1. cryptographically verify the ID-token signature against Microsoft's published JWKS;
2. validate audience, token time claims, nonce on the interactive callback, and required subject claims;
3. require the `tid` claim to be a GUID;
4. replace `{tenantid}` in the configured issuer template with the token `tid` and require exact equality with token `iss`;
5. bind the signing key's own `issuer` metadata to the same token tenant/issuer;
6. treat `preferred_username`, `name`, and email-like values as display information only, never as stable authorization identity.

The canonical ILAIOS principal remains derived from the verified issuer + subject boundary, and tenant scope remains server-authoritative.

## Real-Windows acceptance

Code/CI readiness is not evidence of real Microsoft sign-in. Once the actual App Registration exists:

1. supply the real Microsoft Application (client) ID without adding a secret;
2. launch one clean exact-head Desktop build;
3. complete Microsoft sign-in in the system browser;
4. close and reopen Desktop three independent times;
5. require 3/3 restored sessions without another interactive Microsoft prompt;
6. explicitly log out and confirm the protected refresh credential is cleared;
7. rerun Google persistence to prove Microsoft support did not regress the existing provider.

Only after those real-Windows checks pass may Microsoft Desktop sign-in be called verified.

## External boundary

Microsoft Store business verification, Store product reservation, assigned package identity/publisher string, signing credentials, legal/privacy/age-rating/market declarations, restricted-capability approval, final submission, and Store certification are separate external release gates. None are inferred from this App Registration contract.

## Microsoft reference material

- Microsoft identity platform authorization code flow: https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow
- Desktop public-client configuration: https://learn.microsoft.com/en-us/entra/identity-platform/scenario-desktop-app-configuration
- Redirect URI restrictions / localhost behavior: https://learn.microsoft.com/en-us/entra/identity-platform/reply-url
- Multitenant issuer and signing-key validation: https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- App registration account types: https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app
