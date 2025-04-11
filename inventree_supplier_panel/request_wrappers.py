import requests
import os


# ----------------------------------------------------------------------------
# Wrappers around the requests for better error handling
class Wrappers():

    def post_request(self, post_data, path, headers):
        proxy_con = os.getenv('PROXY_CON')
        proxy_url = os.getenv('PROXY_URL')
        if proxy_con and proxy_url:
            proxies = {proxy_con: proxy_url}
        elif self.get_setting('PROXY_CON') != '' and self.get_setting('PROXY_URL') != '':
            proxies = {self.get_setting('PROXY_CON'): self.get_setting('PROXY_URL')}
        else:
            proxies = {}
        try:
            response = requests.post(path,
                                     proxies=proxies,
                                     data=post_data,
                                     timeout=15,
                                     headers=headers
                                     )
        except Exception as e:
            self.status_code = e.args
            raise ConnectionError
        return (response)

    def get_request(self, path, headers):
        proxy_con = os.getenv('PROXY_CON')
        proxy_url = os.getenv('PROXY_URL')
        if proxy_con and proxy_url:
            proxies = {proxy_con: proxy_url}
        elif self.get_setting('PROXY_CON') != '' and self.get_setting('PROXY_URL') != '':
            proxies = {self.get_setting('PROXY_CON'): self.get_setting('PROXY_URL')}
        else:
            proxies = {}
        try:
            response = requests.get(path,
                                    proxies=proxies,
                                    timeout=15,
                                    headers=headers
                                    )
        except Exception as e:
            self.status_code = e.args
            raise ConnectionError
        return (response)
