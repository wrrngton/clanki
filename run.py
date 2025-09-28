import base64
import json
import os
import pprint
import urllib

import httpx
import requests
from anthropic import Anthropic
from anthropic.types import (MessageParam, SearchResultBlockParam,
                             TextBlockParam)
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

placeholder_images = [
    "https://www.shutterstock.com/image-vector/very-good-grunge-office-rubber-260nw-580204963.jpg",
    "https://static.vecteezy.com/system/resources/previews/028/087/830/non_2x/trendy-very-good-vector.jpg",
]

load_dotenv()

claude_client = Anthropic(api_key=os.getenv("CLAUDE_KEY"))

BRAVE_URL = "https://api.search.brave.com/res/v1/images/search"
BRAVE_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": os.getenv("BRAVE_KEY"),
}

web_image_search = {
    "name": "image_search",
    "description": "A tool to search the internet for images",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "the search query",
            }
        },
        "required": ["query"],
    },
}

image_prompt = """
You are responsible for taking the images above and scoring from 1-10 how well they match the supplied <text> field. 

You must return only an array of integer scores based on how well the supplied image matches the text. Do not include any preamble or conclusions.
{text}

Here are some examples of what to return:
<example1>
[1, 2, 9, 4]
</example1>
<example2>
[1, 0, 3, 10]
</example2>
"""
PREFILL = "["


def get_image_type(image_url) -> str:
    parsed_url = urllib.parse.urlsplit(image_url)
    path_split = parsed_url.path.split(".")
    file_type = path_split[len(path_split) - 1]

    if file_type == "jpg":
        return "jpeg"

    return file_type


def search_web_image(query):

    try:
        res = requests.get(
            BRAVE_URL,
            headers=BRAVE_HEADERS,
            params={
                "q": query,
                "count": 10,
                "search_lang": "en-gb",
                "safesearch": "strict",
            },
        )
        res.raise_for_status()

    except requests.exceptions.RequestException as e:
        print(f"Error with image search: {e}")

    data = res.json()
    images = [
        {
            "url": i.get("properties").get("url"),
            "file_type": f"image/{get_image_type(i.get("properties").get("url"))}",
        }
        for i in data.get("results")
    ]

    translated_text = GoogleTranslator(source="it", target="en").translate(query)

    images_base64_list = [
        base64.standard_b64encode(httpx.get(img).content).decode("utf-8")
        for img in images
    ]
    images_prompt_data = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": img_data,
            },
        }
        for img_data in images_base64_list
    ]

    updated_image_prompt = image_prompt.replace(
        "{text}", f"<text>{translated_text}</text>"
    )

    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system="You are an image classifier and rater",
        messages=[
            {
                "role": "user",
                "content": [
                    *images_prompt_data,
                    {"type": "text", "text": updated_image_prompt},
                ],
            },
            {"role": "assistant", "content": PREFILL},
        ],
    )

    final_completion_str = f"{PREFILL}{message.content[0].text}"
    final_completion_list = json.loads(final_completion_str)
    max_score = max(final_completion_list)
    best_image_index = final_completion_list.index(max_score)
    best_image_url = images[best_image_index]
    return best_image_url


def run():
    best_image_match = search_web_image("italy")


if __name__ == "__main__":
    run()
