import os
import random
import traceback
from pathlib import Path
import re

import requests
from bs4 import BeautifulSoup


def windows_safe_filename(filename: str) -> str:
    """Removes invalid characters and limits filename length."""
    filename = filename.replace("\n", " ")
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    return filename


def scrape_knf(num_retries: int, user_agent_list: list) -> None:

    scraped_files_dir = Path("scraped_files")

    knf_base_url = "https://www.knf.gov.pl"
    knf_recommendations_url = (
        f"{knf_base_url}/dla_rynku/regulacje_i_praktyka/rekomendacje_i"
        + "_wytyczne/rekomendacje_dla_bankow?articleId=8522&p_id=18"
    )

    scraped_files_dir.mkdir(parents=True, exist_ok=True)

    response = None
    for _ in range(num_retries):
        try:
            headers = {
                "User-Agent": user_agent_list[
                    random.randint(0, len(user_agent_list) - 1)
                ]
            }
            response = requests.get(knf_recommendations_url, headers=headers)
            if response.status_code in [200, 404]:
                break  # escape loop if response was successful
        except requests.exceptions.ConnectionError:
            print("Connection failed, retrying...")

    if response and response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")

        time_html_tag = soup.time
        datetime_atr = time_html_tag["datetime"]  # type: ignore[index]

        pdf_titles_links = {}
        for link in soup.find_all("a", title=lambda x: x and "Rekomendacja" in x):
            try:
                href = link.get("href")
                title = link.get_text(strip=True)
                if href and href.endswith(".pdf"):
                    # not all .pdf are listed on knf.gov.pl
                    if "https" not in href:
                        full_url = knf_base_url + href
                        pdf_titles_links[title] = full_url
                    else:
                        pdf_titles_links[title] = href
            except Exception as e:
                print(f"Problem with link for {link} \n Error messange: {e}\n")

        for title, url in pdf_titles_links.items():
            if len(title) > 1:  # temporary: scraping needs deeper rework;
                try:
                    pdf_response = requests.get(url, headers=headers)
                    safe_title = windows_safe_filename(title) if title else "unknown"
                    # adding datetime from KNF site to file name
                    pdf_path = os.path.join(
                        scraped_files_dir, f"{datetime_atr}_{safe_title[:-11]}.pdf"
                    )
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_response.content)
                        print(f"Downloaded: {pdf_path}")
                except Exception as e:
                    print(f"PDF not downloaded: {url} \n Error messange: {e}\n")
                    traceback.print_exc()
    else:
        print("Failed to retrieve the main page content after retries.")


# scrape_knf()
