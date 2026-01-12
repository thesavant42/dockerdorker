import requests
import logging

logging.captureWarnings(True)

proxy_state = "ON"

proxies = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080",
}


class ProxySession:
    """Session wrapper that routes requests through proxy when enabled."""
    
    def __init__(self):
        self._session = requests.Session()
        self.headers = self._session.headers
    
    def _apply_proxy_settings(self, kwargs: dict) -> dict:
        """Apply proxy settings if proxy is ON."""
        if proxy_state == "ON":
            kwargs["proxies"] = proxies
        kwargs["verify"] = False
        return kwargs
    
    def get(self, url, **kwargs):
        kwargs = self._apply_proxy_settings(kwargs)
        return self._session.get(url, **kwargs)
    
    def post(self, url, **kwargs):
        kwargs = self._apply_proxy_settings(kwargs)
        return self._session.post(url, **kwargs)
    
    def request(self, method, url, **kwargs):
        kwargs = self._apply_proxy_settings(kwargs)
        return self._session.request(method, url, **kwargs)


class _ProxyRequestNamespace:
    """Callable namespace that mimics requests module with proxy support.
    
    Usage:
        proxy_request.Session()     -> ProxySession instance
        proxy_request.get(url)      -> one-off GET request
        proxy_request.post(url)     -> one-off POST request
        proxy_request("GET", url)   -> backward compatible function call
    """
    
    @staticmethod
    def Session():
        """Factory method to create a ProxySession."""
        return ProxySession()
    
    @staticmethod
    def get(url, **kwargs):
        """One-off GET request through proxy."""
        if proxy_state == "ON":
            kwargs["proxies"] = proxies
        kwargs["verify"] = False
        return requests.get(url, **kwargs)
    
    @staticmethod
    def post(url, **kwargs):
        """One-off POST request through proxy."""
        if proxy_state == "ON":
            kwargs["proxies"] = proxies
        kwargs["verify"] = False
        return requests.post(url, **kwargs)
    
    def __call__(self, method, url, **kwargs):
        """Allow proxy_request('GET', url) syntax for backward compatibility."""
        if proxy_state == "ON":
            kwargs["proxies"] = proxies
        kwargs["verify"] = False
        return requests.request(method, url, **kwargs)


# Export the namespace object - this is what gets imported
proxy_request = _ProxyRequestNamespace()
