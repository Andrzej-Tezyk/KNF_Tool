import requests
from bs4 import BeautifulSoup
import random
import os

# Step 1: Setup target URL and rotating headers
url = 'https://www.knf.gov.pl/dla_rynku/regulacje_i_praktyka/rekomendacje_i_wytyczne/rekomendacje_dla_bankow?articleId=8522&p_id=18'

# List of user agents to rotate to avoid bot detection
user_agent_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363',
]
headers = {"User-Agent": random.choice(user_agent_list)}

# Step 2: Request the webpage content
response = requests.get(url, headers=headers)
if response.status_code != 200:
    raise Exception("Failed to load page")

# Step 3: Parse HTML content
soup = BeautifulSoup(response.content, 'html.parser')

# Step 4: Find all <a> tags with 'title' containing 'Rekomendacja' (likely to be PDF links)
pdf_links = []
for link in soup.find_all('a', title=lambda x: x and 'Rekomendacja' in x):
    href = link.get('href')
    if href and href.endswith('.pdf'):
        full_url = 'https://www.knf.gov.pl' + href
        pdf_links.append(full_url)

# Step 5: Download each PDF found
for pdf_url in pdf_links:
    pdf_response = requests.get(pdf_url, headers=headers)
    pdf_name = os.path.basename(pdf_url)
    
    # Save the PDF file
    with open(pdf_name, 'wb') as f:
        f.write(pdf_response.content)
    print(f"Downloaded: {pdf_name}")
