import os
import random
import traceback
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SCRAPED_FILES_DIR = Path("scraped_files")
NUM_RETRIES = 5
KNF_BASE_URL = "https://www.knf.gov.pl"
KNF_RECOMMENDATIONS_URL = (
    f"{KNF_BASE_URL}/dla_rynku/regulacje_i_praktyka/rekomendacje_i"
    + "_wytyczne/rekomendacje_dla_bankow?articleId=8522&p_id=18"
)

# agents to avoid being blocked by the website
USER_AGENT_LIST = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/"
        + "605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
    ),
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        + "(KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
    ),
]


SCRAPED_FILES_DIR.mkdir(parents=True, exist_ok=True)


response = None
for _ in range(NUM_RETRIES):
    try:
        headers = {
            "User-Agent": USER_AGENT_LIST[random.randint(0, len(USER_AGENT_LIST) - 1)]
        }
        response = requests.get(KNF_RECOMMENDATIONS_URL, headers=headers)
        if response.status_code in [200, 404]:
            break  # escape loop if response was successful
    except requests.exceptions.ConnectionError:
        print("Connection failed, retrying...")


if response and response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")

    time_html_tag = soup.time
    datetime_atr = time_html_tag["datetime"]  # type: ignore[index]

    pdf_links = []
    for link in soup.find_all("a", title=lambda x: x and "Rekomendacja" in x):
        try:
            href = link.get("href")
            if href and href.endswith(".pdf"):
                # not all .pdf are listed on knf.gov.pl
                if "https" not in href:
                    full_url = KNF_BASE_URL + href
                    pdf_links.append(full_url)
                else:
                    pdf_links.append(href)
        except Exception as e:
            print(f"Problem with link for {link} \n Error messange: {e}\n")

    for pdf_url in pdf_links:
        try:
            pdf_response = requests.get(pdf_url, headers=headers)
            pdf_name = os.path.basename(pdf_url)
            # adding datetime from KNF site to file name
            pdf_path = os.path.join(SCRAPED_FILES_DIR, f"{datetime_atr}_{pdf_name}")
            with open(pdf_path, "wb") as f:
                f.write(pdf_response.content)
                print(f"Downloaded: {pdf_path}")
        except Exception as e:
            print(f"PDF not downloaded: {pdf_url} \n Error messange: {e}\n")
            traceback.print_exc()
else:
    print("Failed to retrieve the main page content after retries.")
