from app.core.api import ddork_proxy

ddork_proxy.proxy_state = "OFF"

# GET
response = ddork_proxy.proxy_request("GET", "https://hub.docker.com/v2/repositories/v3yy/disney/tags/latest/images")
print(f"GET: {response}")