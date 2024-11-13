import requests #web scraping
import random #rotate agents
from random import randint

# KNF recommendation page (contains .pdf documents to scrape)
url = 'https://www.knf.gov.pl/dla_rynku/regulacje_i_praktyka/rekomendacje_i_wytyczne/rekomendacje_dla_bankow?articleId=8522&p_id=18'


## agents and proxies to avoid being blocked by the website -> can be extended using 3 party services if needed; license???

# fake user agents
user_agent_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363',
]

headers={"User-Agent": user_agent_list[random.randint(0, len(user_agent_list)-1)]} # rotate

# poxies
proxy_list = [
  'http://Username:Password@85.237.57.198:20000',
  'http://Username:Password@85.237.57.198:21000',
  'http://Username:Password@85.237.57.198:22000',
  'http://Username:Password@85.237.57.198:23000',
              ]

proxy_index = randint(0, len(proxy_list) - 1)

proxies = {
  "http://": proxy_list[proxy_index],
  "https://": proxy_list[proxy_index],
}



## retry mechanism

NUM_RETRIES = 5

for _ in range(NUM_RETRIES):
    try:
        response = requests.get(url, headers=headers, proxies=proxies)
        if response.status_code in [200, 404]:
            break #escape loop if resposnse was successfull
    except requests.exceptions.ConnectionError:
        print("connection failed")

if response is not None and response.status_code == 200:
    print("connection succeded")

print(response.content)