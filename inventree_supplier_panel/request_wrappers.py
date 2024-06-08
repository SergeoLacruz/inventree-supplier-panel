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
                                     verify=False,
                                     proxies=proxies,
                                     data=post_data,
                                     timeout=5,
                                     headers=headers
                                     )
        except Exception as e:
            self.status_code = e.args
            raise ConnectionError
        if response.status_code != 200:
            self.status_code = response.status_code
            self.message = response.content
            return (response)
        self.status_code = response.status_code
        self.message = 'OK'
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
                                    verify=False,
                                    proxies=proxies,
                                    timeout=5,
                                    headers=headers
                                    )
        except Exception as e:
            self.status_code = e.args
            raise ConnectionError
        if response.status_code != 200:
            self.status_code = response.status_code
            self.message = response.content
            return (response)
        self.status_code = response.status_code
        self.message = 'OK'
        return (response)
