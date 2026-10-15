# Local authentication implementation

The local development app no longer opens directly in demo mode. It now starts
at a real signup/login gate.

## Flows

- Sign up with email, password, and display name
- Login with persisted local account
- Session token stored in browser local storage
- Session verification through `GET /api/auth/me`
- Logout and token invalidation
- Authenticated API request headers

## Local storage

Development accounts are stored in `data/local_auth.sqlite3`, which is ignored
by Git. Passwords are PBKDF2-SHA256 hashed and never stored in plaintext.

## Production

For production, replace the local auth provider with Supabase Auth and configure
server-side JWT verification. Local auth is intended to make the complete local
workflow testable without requiring a Supabase project or credentials.
