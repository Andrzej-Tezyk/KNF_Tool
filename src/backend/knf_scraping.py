import random
import traceback
from pathlib import Path
import re
import logging

import requests
from bs4 import BeautifulSoup


log = logging.getLogger("__name__")


def windows_safe_filename(filename: str) -> str:
    """Removes invalid characters from the file name.

    This function removes any invalid character in Windows file name from the filename.
    It also replaces end of line characters "\n" with spaces " ".
    Returns the new file name.

    Examples:
        >>> windows_safe_filename('invalid:filename?.txt')
        'invalidfilename.txt'

    Args:
        filename: A string containing the file name.

    Returns:
        A string containing file name cleansed from any invalid characters.

    Raises:
        None
    """
    filename = filename.replace("\n", " ")
    filename = re.sub(
        r'[<>:"/\\|?*]', "", filename
    )  # <>:"/\|?* are invalid characters in Windows file names
    return filename


def scrape_knf(scraped_dir: Path, num_retries: int, user_agent_list: list) -> None:
    """Scrapes pdf files from KNF url.

    This function scrapes pdf files from a KNF url.
    For a certain number of tries it masks under an agent from given agent list
    and downloads the file into a directory. If an error occurs during scraping,
    it logs the error message.

    Examples:
        >>> scrape_knf(10, ["Mozilla/5.0", "Mozilla/4.0"])
        None

    Args:
        num_retries: An int describing number of retries the program will
        attempt of scraping a file.
        user_agent_list: A list of strings with user agents for masking.

    Returns:
        None

    Raises:
        Exception: If an error occurs during processing, it is logged and returned
        in the response dictionary.
    """

    knf_base_url = "https://www.knf.gov.pl"
    knf_recommendations_url = (
        f"{knf_base_url}/dla_rynku/regulacje_i_praktyka/rekomendacje_i"
        + "_wytyczne/rekomendacje_dla_bankow?articleId=8522&p_id=18"
    )

    scraped_dir.mkdir(parents=True, exist_ok=True)

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
            log.error("Connection failed, retrying...")

    if response and response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")

        time_html_tag = soup.time
        datetime_atr = time_html_tag["datetime"]  # type: ignore[index]

        pdf_titles_links = {}
        for link in soup.find_all("a", title=lambda x: x and "rekomendacja" in x.lower()):
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
                log.error(f"Problem with link for {link} \n Error messange: {e}\n")

        for title, url in pdf_titles_links.items():
            if len(title) > 1:  # temporary: scraping needs deeper rework;
                try:
                    pdf_response = requests.get(url, headers=headers)
                    safe_title = windows_safe_filename(title) if title else "unknown"
                    # adding datetime from KNF site to file name
                    pdf_path = scraped_dir / f"{datetime_atr}_{safe_title[:-11]}.pdf"
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_response.content)
                        log.debug(f"Downloaded: {pdf_path}")
                except Exception as e:
                    log.error(f"PDF not downloaded: {url} \n Error messange: {e}\n")
                    traceback.print_exc()
    else:
        log.error("Failed to retrieve the main page content after retries.")