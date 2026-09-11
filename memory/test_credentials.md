# Test Credentials

## Auth: Emergent Google Auth (no app-managed passwords)

### Admin account (pre-seeded, role=admin)
- Email: kruthivas@emergent.sh
- Role: admin
- user_id: user_60da7151f020
- How to log in: open /login and "Sign in with Google" using this email.

### Notes for testing agents
- App is served (after platform 307 redirect) on the .internal host.
- REACT_APP_BACKEND_URL is set to https://repo-builder-83.internal.preview.emergentagent.com
  as a TEMPORARY unblock so frontend<->backend calls are same-origin (platform edge
  redirects *.preview -> *.internal for all routes, which broke cross-origin auth).
- COOKIE_DOMAIN=.preview.emergentagent.com (valid across .preview and .internal subdomains).
- For automated testing without real Google OAuth, create a session per /app/auth_testing.md:
  users {user_id, email, name, role:'admin', created_at}
  user_sessions {user_id, session_token, expires_at (+7d), created_at}
  then inject cookie session_token (domain .preview.emergentagent.com) OR use
  Authorization: Bearer <session_token>.
