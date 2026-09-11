# Google-Auth Login Redirect Loop - Comprehensive Diagnosis Report

**Date:** 2026-09-11  
**App:** Trinity_01 (github-clone-tool-6)  
**Issue:** After Google sign-in, app redirects to /login instead of /dashboard

---

## Executive Summary

**ROOT CAUSE IDENTIFIED:** Cross-origin CORS preflight failure due to infrastructure 307-redirect creating origin mismatch between React app and API calls.

**STATUS:** ❌ CRITICAL - Login completely broken  
**PREVIOUS TESTING:** Incomplete - only tested curl, not real browser behavior  
**FIX REQUIRED:** Update REACT_APP_BACKEND_URL and COOKIE_DOMAIN to use .internal subdomain

---

## Infrastructure Context

The Emergent preview infrastructure implements a 307-redirect pattern:
- **External URL:** `https://github-clone-tool-6.preview.emergentagent.com`
- **Internal URL:** `https://github-clone-tool-6.internal.preview.emergentagent.com`
- **Redirect:** All requests to `*.preview.emergentagent.com` are 307-redirected to `*.internal.preview.emergentagent.com`

---

## Test Results

### TEST A: Session-Exchange Call Diagnosis

**Objective:** Reproduce the POST /api/auth/session call exactly as the app does

**Setup:**
- Browser on: `https://github-clone-tool-6.internal.preview.emergentagent.com/login` (after 307 redirect)
- Fetch to: `https://github-clone-tool-6.preview.emergentagent.com/api/auth/session` (REACT_APP_BACKEND_URL)
- Method: POST with `credentials: 'include'`

**Result:** ❌ FETCH REJECTED

```
TypeError: Failed to fetch
```

**Browser Console Error:**
```
Access to fetch at 'https://github-clone-tool-6.preview.emergentagent.com/api/auth/session' 
from origin 'https://github-clone-tool-6.internal.preview.emergentagent.com' 
has been blocked by CORS policy: Response to preflight request doesn't pass access control check: 
The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' 
when the request's credentials mode is 'include'.
```

**Analysis:**
1. Browser is on `.internal` origin (after 307 redirect)
2. Fetch targets `.preview` origin (REACT_APP_BACKEND_URL)
3. This is a **CROSS-ORIGIN** request
4. Browser sends OPTIONS preflight to `.preview` URL
5. Cloudflare/proxy responds with `Access-Control-Allow-Origin: *` (before FastAPI sees it)
6. Browser rejects because `credentials: 'include'` + `*` is not allowed per CORS spec
7. Fetch fails, AuthCallback catches error, redirects to /login

---

### TEST B: Cookie-Injection Auth Check

**Objective:** Test if a valid session cookie works through the 307 redirect

**Setup:**
1. Created test user in MongoDB:
   - user_id: `user_fe_admin`
   - email: `fe.admin@example.com`
   - role: `admin`
2. Created test session:
   - session_token: `fe_test_session_123456`
   - expires_at: 7 days from now
3. Injected cookie:
   - domain: `.preview.emergentagent.com`
   - secure: true, httpOnly: false, sameSite: None

**Result:** ❌ REDIRECTED TO /login

**Key Findings:**
- ✅ Cookie was successfully injected and visible in `document.cookie`
- ❌ GET /api/auth/me requests showed **NO COOKIE HEADER SENT**
- ❌ Navigating to /dashboard → redirected to /login
- ✅ BUT /dashboard/kb-editor → STAYED on page (auth succeeded!)

**Analysis:**
The cookie domain mismatch causes inconsistent behavior. The cookie set for `.preview.emergentagent.com` may not be sent correctly when the app is on `.internal.preview.emergentagent.com`.

---

### TEST C: Cookie Storage Across 307 Redirect

**Objective:** Verify if Set-Cookie headers work across the 307 redirect

**Setup:**
- Cleared all cookies
- Fetched /api/health with `credentials: 'include'`
- Checked stored cookies

**Result:**
- No Set-Cookie header received from /api/health
- No cookies stored for session_token
- Only Cloudflare and analytics cookies present

**Analysis:**
The 307 redirect may interfere with Set-Cookie header propagation in cross-origin scenarios.

---

### VERIFICATION TEST: Same-Origin Scenario

**Objective:** Confirm that same-origin requests work correctly

**Setup:**
- Browser on: `https://github-clone-tool-6.internal.preview.emergentagent.com/login`
- Fetch to: `/api/auth/session` (relative URL, same origin)

**Result:** ✅ FETCH RESOLVED

```
Status: 401 Unauthorized
Body: {"detail":"Invalid session_id"}
```

**Key Findings:**
- ✅ NO CORS ERRORS
- ✅ Fetch resolves with HTTP response (401 expected for invalid session_id)
- ✅ Same-origin requests work perfectly

---

## CORS Header Comparison

### OPTIONS to .preview URL (External):
```bash
curl -X OPTIONS "https://github-clone-tool-6.preview.emergentagent.com/api/auth/session" \
  -H "Origin: https://github-clone-tool-6.internal.preview.emergentagent.com"
```

**Response:**
```
access-control-allow-origin: *
access-control-allow-headers: *
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH
```

❌ Returns wildcard `*` (Cloudflare layer, before FastAPI)

---

### OPTIONS to .internal URL (Internal):
```bash
curl -X OPTIONS "https://github-clone-tool-6.internal.preview.emergentagent.com/api/auth/session" \
  -H "Origin: https://github-clone-tool-6.internal.preview.emergentagent.com"
```

**Response:**
```
access-control-allow-credentials: true
access-control-allow-origin: https://github-clone-tool-6.internal.preview.emergentagent.com
access-control-allow-methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
```

✅ Returns reflected origin with credentials (FastAPI)

---

## Root Cause Analysis

### The Problem Chain:

1. **User navigates to:** `https://github-clone-tool-6.preview.emergentagent.com/dashboard`
2. **Infrastructure 307-redirects to:** `https://github-clone-tool-6.internal.preview.emergentagent.com/dashboard`
3. **React app loads from:** `.internal` origin
4. **AuthCallback tries to POST to:** `REACT_APP_BACKEND_URL` = `.preview` origin
5. **This creates:** CROSS-ORIGIN request (`.internal` → `.preview`)
6. **Browser sends:** OPTIONS preflight to `.preview` URL
7. **Cloudflare responds:** `Access-Control-Allow-Origin: *` (before FastAPI)
8. **Browser rejects:** `credentials: 'include'` + `*` not allowed
9. **Fetch fails:** TypeError: Failed to fetch
10. **AuthCallback:** Catches error, redirects to /login
11. **Result:** Login redirect loop

### Why Previous Testing Was Incomplete:

Previous testing used `curl` which:
- Doesn't enforce CORS policies (server-to-server)
- Doesn't follow browser security model
- Can't reproduce the cross-origin preflight failure

Real browser testing with `fetch()` revealed the actual failure point.

---

## The Fix

### Required Changes:

1. **Update frontend/.env:**
   ```bash
   REACT_APP_BACKEND_URL=https://github-clone-tool-6.internal.preview.emergentagent.com
   ```

2. **Update backend/.env:**
   ```bash
   COOKIE_DOMAIN=.internal.preview.emergentagent.com
   ```

3. **Restart services:**
   ```bash
   sudo supervisorctl restart frontend
   sudo supervisorctl restart backend
   ```

### Why This Works:

- React app loads from `.internal` origin
- API calls go to `.internal` origin (same-origin)
- No CORS preflight needed for same-origin requests
- Cookies set for `.internal.preview.emergentagent.com` domain
- Cookies sent correctly on all requests
- No cross-origin issues

---

## Alternative Solutions Considered

### Option 1: Fix Cloudflare CORS Headers
**Status:** Not feasible - infrastructure layer outside our control

### Option 2: Use Proxy in React App
**Status:** Adds complexity, not recommended for production

### Option 3: Change Auth Flow to Use Tokens Instead of Cookies
**Status:** Major refactor, not necessary

### Option 4: Use .internal URLs (RECOMMENDED)
**Status:** Simple, effective, aligns with infrastructure design

---

## Testing Checklist

After implementing the fix, verify:

- [ ] User can sign in with Google
- [ ] After sign-in, user lands on /dashboard (not /login)
- [ ] Session persists across page refreshes
- [ ] Protected routes work correctly
- [ ] Logout works correctly
- [ ] No CORS errors in browser console
- [ ] Cookies are set and sent correctly

---

## Evidence Files

- Browser screenshots: `.screenshots/test_a_1_login_page.png`, `test_b_1_dashboard_with_cookie.png`, `test_b_2_kb_editor_with_cookie.png`
- Console logs: `/root/.emergent/automation_output/*/console_*.log`
- Network logs: Captured in Playwright test output

---

## Conclusion

The login redirect loop is caused by a **cross-origin CORS preflight failure** due to the infrastructure 307-redirect pattern. The fix is to update `REACT_APP_BACKEND_URL` and `COOKIE_DOMAIN` to use the `.internal` subdomain, ensuring same-origin requests and eliminating CORS issues entirely.

**Priority:** CRITICAL  
**Complexity:** LOW (2 env var changes)  
**Risk:** LOW (aligns with infrastructure design)  
**Confidence:** HIGH (verified with comprehensive browser testing)
