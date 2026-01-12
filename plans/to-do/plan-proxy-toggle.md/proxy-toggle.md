# HTTP Requests Module

Make a centralized HTTP module to not break the "Dont Repeat Yourself" code rule
Includes HTTP Proxy capabilities for Burp Suite itegration

## Status Phase 1

Phase 1: Complete!

Implement and test an HTTP module, with proxy toggle.

- [x] http/https proxy module implemented at (@/app/core/api/ddork_proxy.py)
    - Tests successful! 
    - tested and validated with this snippet:
    
    ```python
    from app.core.api import ddork_proxy
    
    ddork_proxy.proxy_state = "ON"
    
    # GET Image configuration manifests from docker HUB to verify we can work with JSON
    response = ddork_proxy.proxy_request("GET", "https://hub.docker.com/v2/repositories/v3yy/disney/tags/latest/images")
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response into a Python dictionary/list
        data = response.json()
        print(data[0]) # Need ot unlock this to the full json response
    else:
        print(f"Request failed with status code: {response.status_code}")
    ```

    - Received vslid json response! 
    - Results were proxied through Burp!

## Phase 2: Update dependant pages to use proxy function


### Task: 

- The following pages need to be updated with the new function:
    - [ ] `app\core\api\layerslayer\fetcher.py`, 
    - [ ] `.\app\core\api\dockerhub_fetch.py`
    - [ ] `.\app\core\api\dockerhub_v2_api.py`
    - [ ] `.\app\core\api\layerslayer\fetcher.py`
    - [ ] `.\app\modules\enumerate\list_dockerhub_container_files.py`
- For each page, search for all invocations of `requests` and refactor that function to use the new `/app/core/api/ddork_proxy.py` requests module.

# Acceptance Criteria
Search results should show none of the code in .\app\ make requests without going through the new module. 