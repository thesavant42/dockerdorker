# Bug in authentication when pulling JWTs for docker registry/container layer pulling.

ddork_proxy integration

## Secondary issue (NOT FIXED - unclear root cause)


I Replaced requests in fetcher.py to use ddork_proxy.py instead of directly out to requests. It's mostly working, but the session token is not being sent with the image request.

Making image request with proxy enabled:
- Missing JWT
    - Docker Registry requires a valid JWT, even if it's an anonymous JWT.

```bash
GET /v2/weareenvoy/mcd-photowall-cms/blobs/sha256:df0f8dbb464aa1f07e6669c09b83d739ef3ff05c72ba173628f3dc85bd4c746a HTTP/2
Host: registry-1.docker.io
User-Agent: python-requests/2.32.5
Accept-Encoding: gzip, deflate, br
Accept: application/vnd.docker.distribution.manifest.v2+json
Connection: keep-alive
Range: bytes=0-65535
```

Response to request without JWT:

```bash
HTTP/2 401 Unauthorized
Date: Mon, 12 Jan 2026 07:10:54 GMT
Content-Type: application/json
Content-Length: 171
Docker-Distribution-Api-Version: registry/2.0
Www-Authenticate: Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:weareenvoy/mcd-photowall-cms:pull"
Strict-Transport-Security: max-age=31536000

{"errors":[{"code":"UNAUTHORIZED","message":"authentication required","detail":[{"Type":"repository","Class":"","Name":"weareenvoy/mcd-photowall-cms","Action":"pull"}]}]}
```

- Multiple token requests per image instead of reusing one token

- `_fetch_pull_token()` uses `proxy_request.get()` (one-off request)
- `peek_layer_blob_partial() uses `_session.get()` (ProxySession)
- Token is passed in per-request headers dict, NOT set on session

What I don't understand:

- Why exactly 2 token requests happen (not just the 401 retry at lines 118-122)
- How the OPTIONS preflight fits into the auth flow
    - The exact mechanism the working reference (github.com/thesavant42/layerslayer) code uses to avoid this

Reference code pattern (from layerslayer repo):

```
session.headers["Authorization"] = f"Bearer {token}"  # Set on session, not per-request
save_token(token, filename="token_pull.txt")          # Persist to disk
```

I am not confident I understand the full picture to propose a safe fix. 
A docker registry auth library or more direct examination of working traffic may be needed.