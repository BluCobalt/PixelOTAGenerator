import requests
from bs4 import BeautifulSoup

def __fetch_ota_page() -> str:
    url: str = "https://developers.google.com/android/ota"
    cookie: dict = {"devsite_wall_acks": "nexus-ota-tos"}
    response = requests.get(url, cookies=cookie)
    response.raise_for_status()
    return response.text

def get_all_otas(device: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(__fetch_ota_page(), "html.parser")
    ret = []
    for tr in soup.find_all("tr"):
        if tr.get("id").__contains__(device):
            data = tr.find_all("td")
            ret.append((data[0].text, data[1].find_all("a")[0].get("href")))

    return ret