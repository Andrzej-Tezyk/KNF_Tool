import requests #web scraping
from bs4 import BeautifulSoup

from random import randint
import random #rotate agents
import os


# folder for downloaded pdfs
newpath = 'C:/Users/Andrzej T (Standard)/Desktop/Projects/KNF_Tool/scraped_files'
if not os.path.exists(newpath):
    os.makedirs(newpath)

NUM_RETRIES = 5

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

# poxies -> DOES NOT WORK!!!
proxy_list = [
  'http://Username:Password@85.237.57.198:20000',
  'http://Username:Password@85.237.57.198:21000',
  'http://Username:Password@85.237.57.198:22000',
  'http://Username:Password@85.237.57.198:23000',
              ]

response = None
for _ in range(NUM_RETRIES):
    try:
        headers = {"User-Agent": user_agent_list[random.randint(0, len(user_agent_list) - 1)]}
        #proxy_index = randint(0, len(proxy_list) - 1)
        #proxies = {
        #  "http": proxy_list[proxy_index],
        #  "https": proxy_list[proxy_index],
        #}
        response = requests.get(url, headers=headers)
        if response.status_code in [200, 404]:
            break  # escape loop if response was successful
    except requests.exceptions.ConnectionError:
        print("Connection failed, retrying...")


if response and response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser') #makes html text response a nested datastructure, which can be queried


    pdf_links = []
    for link in soup.find_all('a', title=lambda x: x and 'Rekomendacja' in x):
        try:
            href = link.get('href')
            if href and href.endswith('.pdf'):
                if 'https' not in href:
                    full_url = 'https://www.knf.gov.pl' + href
                    pdf_links.append(full_url)
                else:
                    pdf_links.append(href)
        except:
            print(f'Problem with link for {link}')


    for pdf_url in pdf_links:
        try:
            pdf_response = requests.get(pdf_url, headers=headers)
            pdf_name = os.path.basename(pdf_url)
            pdf_path = os.path.join(newpath, pdf_name)
            with open(pdf_path, 'wb') as f:
                f.write(pdf_response.content)
                print(f'Downloaded: {pdf_path}')
        except:
            print(f'PDF not downloaded: {pdf_url}')
else:
    print("Failed to retrieve the main page content after retries.")