import base64
import csv
import json
import os
import pprint
import sys
import time
import urllib
from binascii import Error as BinasciiError

import anthropic
import certifi
import httpx
import requests
from anthropic import APIConnectionError, APIStatusError, RateLimitError
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

from validate_b64 import is_valid_base64_image

load_dotenv()

claude_client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_KEY"))
use_ai = True

BRAVE_URL = "https://api.search.brave.com/res/v1/images/search"
BRAVE_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": os.getenv("BRAVE_KEY"),
}
MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]

image_prompt = """
You are responsible for taking the images above and scoring from 1-10 how well they match the supplied <text> field.

You must return only an array of integer scores based on how well the supplied image matches the text. Do not include any preamble or conclusions.
{text}

Here are some examples of what to return:
For 4 images:
<example1>
[1, 2, 9, 4]
</example1>

For 3 images:

<example2>
[1, 0, 3]
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


def brave_img_search(phrase: str) -> str:
    try:
        res = requests.get(
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
        res.raise_for_status()
        return res.json()

    except requests.exceptions.HTTPError as e:
        raise

    except Exception as e:
        raise


def search_web_image(phrases: list) -> list:
    sys.stdout.write(f"Generating images...\n")
    image_matches = []

    for phrase in phrases:
        try:
            data = brave_img_search(phrase)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print("hit rate limit, back off")
                time.sleep(1)
                data = brave_img_search(phrase)
            else:
                print(f"HTTPError: {e}")
                return None

        except Exception as e:
            print(f"Another error occurred: {e}")

        # Is user opts out of AI, Claude isn't called and we rely on Brave's confidence score, images immediately returned
        if not use_ai:
            eligible_images = []
            for i in data.get("results"):
                img_dict = {"url": "", "file_type": ""}

                if i.get("confidence") == "high":
                    img_dict["url"] = i.get("properties").get("url")
                    img_dict["file_type"] = (
                        get_image_type(i.get("properties").get("url")),
                    )
                elif i.get("confidence") == "medium":
                    img_dict["url"] = i.get("properties").get("url")
                    img_dict["file_type"] = (
                        get_image_type(i.get("properties").get("url")),
                    )
                else:
                    img_dict["url"] = i.get("properties").get("url")
                    img_dict["file_type"] = (
                        get_image_type(i.get("properties").get("url")),
                    )

                eligible_images.append(img_dict)

            chosen_image = eligible_images[0]
            image_matches.append(chosen_image)
            continue  # break from parent loop

        images = [
            {
                "url": i.get("properties").get("url"),
                "file_type": f"image/{get_image_type(i.get("properties").get("url"))}",
            }
            for i in data.get("results")
        ]

        images_reduced_list = []

        for img in images:
            try:
                req = requests.get(img.get("url"))
                mtype = req.headers.get("Content-Type")
                if mtype not in MIME_TYPES:
                    continue
                images_reduced_list.append(
                    {"url": img.get("url"), "file_type": img.get("file_type")}
                )
            except Exception as e:
                print("Error fetching or encoding image", e)

        images_base64_list = [
            {
                "base_img_data": base64.standard_b64encode(
                    httpx.get(img.get("url")).content
                ).decode("utf-8"),
                "file_type": img.get("file_type"),
            }
            for img in images_reduced_list
        ]

        images_base64_list_reduced = [
            i
            for i in images_base64_list
            if is_valid_base64_image(i.get("base_img_data"), i.get("file_type"))
        ]

        images_prompt_data = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img_data.get("file_type"),
                    "data": img_data.get("base_img_data"),
                },
            }
            for img_data in images_base64_list_reduced
        ]
        updated_image_prompt = image_prompt.replace(
            "{text}", f"<text>{phrase}</text>")

        images_prompt_data.append(
            {"type": "text", "text": updated_image_prompt})

        try:
            message = claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system="You are an image classifier and rater",
                messages=[
                    {"role": "user", "content": images_prompt_data},
                    {"role": "assistant", "content": PREFILL},
                ],
            )
        except anthropic.APIConnectionError as e:
            print("The server could not be reached")
        except anthropic.RateLimitError as e:
            print("A 429 status code was received; we should back off a bit.")
        except anthropic.APIStatusError as e:
            print(e)

        final_completion_str = f"{PREFILL}{message.content[0].text}"
        final_completion_list = json.loads(final_completion_str)
        max_score = max(final_completion_list)
        best_image_index = final_completion_list.index(max_score)
        best_image_url = images[best_image_index]
        image_matches.append(best_image_url)

    return image_matches


def handle_cli() -> str:
    global use_ai
    arguments = sys.argv
    arg_length = len(arguments)

    if arg_length < 2:
        sys.stderr.write("Error: you must provide at least one argument")
        sys.exit(1)

    if arguments[1] != "--file" and arguments[1] != "--F":
        sys.stderr.write("Error: first argument must be --file or -F")
        sys.exit(1)

    if arg_length == 5:
        ai_bool = arguments[4]
        if ai_bool == "false":
            use_ai = False

    file_path = arguments[2]

    if not os.path.exists(file_path):
        sys.stderr.write("Error: your phrases file doesn't exist")
        sys.exit(1)

    return file_path


def read_file(input_file: str) -> list:
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            phrases = [line.strip() for line in f]
            if not phrases:
                sys.stderr.write(
                    "Error: No phrases detected in your phrases file")
                sys.exit(1)
            return phrases

    except FileNotFoundError:
        sys.stderr.write("Error: file not found, check the name and try again")
        sys.exit(1)


def translate_phrases(inputs: list) -> list:
    sys.stdout.write(f"Translating phrases...\n")
    translations = []
    for i in inputs:
        translated_text = GoogleTranslator(
            source="it", target="en").translate(i)
        translations.append(translated_text)

    return translations


def generate_output(
    original_phrases: list, translated_phrases: list, images: list
) -> None:
    sys.stdout.write(f"Generating csv...\n")
    csv_output = []
    phrase_len = len(original_phrases)

    for i in range(0, phrase_len):
        phrase_dict = {
            "front": translated_phrases[i],
            "back": original_phrases[i],
            "image": f"""<img src='{images[i].get("url")}'/>""",
        }

        csv_output.append(phrase_dict)

    df = open("deck.csv", "w+", encoding="utf-8")
    cw = csv.writer(df)
    for row in csv_output:
        cw.writerow(row.values())

    df.close()


def run():
    input_file = handle_cli()
    input_phrases = read_file(input_file)
    translated_phrases = translate_phrases(input_phrases)
    best_image_matches = search_web_image(input_phrases)
    generate_output(input_phrases, translated_phrases, best_image_matches)
    sys.stdout.write(
        f"Congrats! your deck.csv has been successfully created...\n")


if __name__ == "__main__":
    run()
