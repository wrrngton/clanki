import os
import requests
import certifi
from dotenv import load_dotenv
load_dotenv()
print(os.getenv("BRAVE_KEY"))

BRAVE_URL = "https://api.search.brave.com/res/v1/images/search"
BRAVE_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": os.getenv("BRAVE_KEY"),
}

def brave_img_search(phrase: str) -> str:
    try:
        brave_res = requests.get(
            BRAVE_URL,
            verify=certifi.where(),
            headers=BRAVE_HEADERS,
            params={
                "q": phrase,
                "count": 20,
                "search_lang": "en-gb",
                "safesearch": "strict",
            },
        )
        brave_res.raise_for_status()
        return brave_res.json()

    except requests.exceptions.HTTPError as e:
        print("HTTPError", e)

    except Exception as e:
        print("Other error", e)


res = brave_img_search("italy")
print(res)
