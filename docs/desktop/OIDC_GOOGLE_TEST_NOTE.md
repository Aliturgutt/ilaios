# Google Desktop OIDC Test Target

For local Windows testing, ILAIOS Desktop expects an externally supplied Google native/Desktop OAuth client identifier via `ILAIOS_DESKTOP_OIDC_PROVIDERS_JSON` and uses Authorization Code + S256 PKCE with a loopback callback.

The runtime must not require or accept a Google client secret for this public native-client path. Historical Hermes OAuth registrations are not active runtime identity; the client identifier supplied to the current process determines which Google OAuth registration is used.
