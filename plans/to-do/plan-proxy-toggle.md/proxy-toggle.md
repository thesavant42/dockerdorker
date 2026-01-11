# HTTP Proxy

- Should accept a value for the http_proxy, which will be the same for requests made to HTTP and/or HTTPS
    - "http://127.0.0.1:8080" # Burp proxy example
    - "http://192.168.1.3128" # syno proxy example
    - must set `verify=False` in requests when using proxies


- Proxy config

    ```json
    proxies = {
        "http": "http://127.0.0.1:8080",
        "https": "http://127.0.0.1:8080",
    }
    ```

For example:

Change requests from: 
    - `requests.get(auth_url)`
 to
    - `requests.get(auth_url, Proxies=proxies, Verify=False)`


## Task: Create Proxy Toggle Function

- Create http_proxy_request() function for any function that uses HTTP requests
- Create a state machine for proxy toggle value
    - should default to off, but persist its state across changes and application quits
- Update all modules that use requests to call using the proxy

#### Toggle Switch Top Panel, left of the tag select widget
- Wire up style for swtich.tcss
    - Need to udpate [placeholder style](app\styles\switch.tcss)

- Update dependant pages sto use proxy function:

- The following pages need to be updated with the new function:

    - `.\app\core\api\carve_service.py`
    - `.\app\core\api\dockerhub_fetch.py`
    - `.\app\core\api\dockerhub_v2_api.py`
    - `.\app\core\api\layerslayer\fetcher.py`

- These pages also use requests and should be updated

    - `.\app\modules\carve\carve-file-from-layer.py`
    - `.\app\modules\enumerate\list_dockerhub_container_files.py`
    - `.\app\modules\enumerate\tag-and-enum.py`
    - `.\app\modules\search\search-docker-hub.py`