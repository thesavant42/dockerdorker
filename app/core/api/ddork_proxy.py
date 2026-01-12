import requests
import logging

# This helps prevent the log errors from causing exceptions
logging.captureWarnings(True)


proxy_state = "OFF"

proxies = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080",
}


def proxy_request(method, url, **kwargs):
    if proxy_state == "ON":
        kwargs["proxies"] = proxies
    kwargs["verify"] = False
    return requests.request(method, url, **kwargs)