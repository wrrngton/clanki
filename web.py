import base64
import csv
import io
import json
import os
import pathlib
import sys
import time
import urllib
from binascii import Error as BinasciiError

import anthropic
import certifi
import requests
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from flask import Flask, make_response, render_template, request, send_file

from cli import cli_handle_error
from llm import LLMClient
from prompts import image_prompt, phrase_prompt
from validate_b64 import is_valid_base64_image

load_dotenv()

use_ai = True

app = Flask(__name__)


BRAVE_URL = "https://api.search.brave.com/res/v1/images/search"
BRAVE_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": os.getenv("BRAVE_KEY"),
}
MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]

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

    except requests.exceptions.HTTPError:
        raise

    except Exception:
        raise


def classify_phrase(phrases: list) -> str:
    phrase_prompt_data = phrase_prompt.replace("{text}", str(phrases))
    phrase_prompt_data = phrase_prompt_data.replace("{source_language}", "italian")
    llm_api = LLMClient()
    messages = [{"role": "user", "content": phrase_prompt_data}]

    try:
        message = llm_api.fetch(
            "claude-sonnet-4-20250514", 1000, "you are a phrase classifier", messages
        )
        final_completion_str = message.content[0].text
        final_completion_list = json.loads(final_completion_str)
        return final_completion_list

    except anthropic.APIConnectionError as e:
        print("The server could not be reached", e)
    except anthropic.RateLimitError:
        print("A 429 status code was received; we should back off a bit.")
    except anthropic.APIStatusError as e:
        print("Another issues occurred: ", e)


def search_web_image(phrases: list) -> list:
    sys.stdout.write(f"Generating images...\n")
    image_matches = []

    for phrase in phrases:
        try:
            data = brave_img_search(phrase)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print("hit rate limit, back off", e)
                time.sleep(1)
                data = brave_img_search(phrase)
            else:
                print(f"HTTPError: {e}")
                return None

        except Exception as e:
            print(f"Another error occurred: {e}")

        # If user opts out of AI, Claude isn't called and we rely on Brave's confidence score, images immediately returned
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
                    requests.get(img.get("url")).content
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
        updated_image_prompt = image_prompt.replace("{text}", f"<text>{phrase}</text>")

        images_prompt_data.append({"type": "text", "text": updated_image_prompt})
        messages = [
            {"role": "user", "content": images_prompt_data},
            {"role": "assistant", "content": PREFILL},
        ]

        try:
            llm_client = LLMClient()
            message = llm_client.fetch(
                "claude-sonnet-4-20250514",
                1024,
                "You are an image classifier and rater",
                messages,
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


def read_file(input_file: str) -> list:
    path = pathlib.Path(input_file)
    extension = path.suffix

    if extension != ".txt" and extension != ".csv":
        cli_handle_error("File type must of be '.txt' or '.csv'", 1)

    if extension == ".txt":
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                phrases = [line.strip() for line in f]
                if not phrases:
                    cli_handle_error(
                        "Error: no phrases detected in your phrases file", 1
                    )
                return phrases

        except FileNotFoundError:
            cli_handle_error("Error: file not found, check name and try again", 1)

    if extension == ".csv":
        try:
            with open(input_file, "r", newline="", encoding="utf-8") as c:
                phrases = []
                phrasereader = csv.reader(c, delimiter=",")
                for row in phrasereader:
                    if len(row) > 1:
                        cli_handle_error(
                            "CSV files should only have one column containing phrases, delete any additional columns",
                            1,
                        )
                    else:
                        phrases.append(row[0])

                return phrases

        except FileNotFoundError:
            sys.stderr.write("Error: file not found, check the name and try again")
            sys.exit(1)


def translate_phrases(inputs: list) -> list:
    sys.stdout.write(f"Translating phrases...\n")
    translations = []
    for i in inputs:
        translated_text = GoogleTranslator(source="it", target="en").translate(i)
        translations.append(translated_text)

    return translations


def generate_output(
    original_phrases: list,
    translated_phrases: list,
    images: list,
    input_file: str = "phrases",
) -> str:
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

    output = io.StringIO()
    cw = csv.writer(output)

    for row in csv_output:
        cw.writerow([row["front"], row["back"], row["image"]])

    csv_content = output.getvalue()
    output.close()

    sys.stdout.write(f"CSV generated successfully!\n")
    return csv_content


def parse_uploaded_file(file) -> list:
    filename = file.filename
    file_extension = pathlib.Path(filename).suffix.lower()

    if file_extension not in [".txt", ".csv"]:
        raise ValueError("File type must be '.txt' or '.csv'")

    file_content = file.read().decode("utf-8")
    file.seek(0)  # Reset file pointer

    if file_extension == ".txt":
        phrases = [line.strip() for line in file_content.split("\n") if line.strip()]
        if not phrases:
            raise ValueError("Error: no phrases detected in your phrases file")
        return phrases

    elif file_extension == ".csv":
        phrases = []
        csv_reader = csv.reader(io.StringIO(file_content))
        for row in csv_reader:
            if len(row) > 1:
                raise ValueError(
                    "CSV files should only have one column containing phrases"
                )
            elif len(row) == 1:
                phrases.append(row[0].strip())
        return phrases


def process_phrases(input_phrases: list, use_ai_setting: bool = True) -> str:
    """Process phrases through the full pipeline and return CSV content"""
    global use_ai
    use_ai = use_ai_setting

    translated_phrases = translate_phrases(input_phrases)

    optimised_search_phrases = classify_phrase(input_phrases)

    best_image_matches = search_web_image(optimised_search_phrases)

    csv_content = generate_output(input_phrases, translated_phrases, best_image_matches)

    return csv_content


@app.route("/create-cards", methods=["POST"])
def create_cards():
    try:
        print("Form data:", dict(request.form))
        print("Files:", list(request.files.keys()))

        use_ai_setting = request.form.get("use_ai") == "on"

        phrases_form_data = request.form.get("phrases")
        print("Phrases from form:", repr(phrases_form_data))

        if phrases_form_data:
            phrases_text = phrases_form_data.strip()
            if phrases_text:
                phrases = [
                    line.strip() for line in phrases_text.split("\n") if line.strip()
                ]
                print("Parsed phrases:", phrases)
            else:
                return "No phrases provided", 400

        elif "file" in request.files and request.files["file"].filename:
            file = request.files["file"]
            phrases = parse_uploaded_file(file)

        else:
            return (
                "No input provided. Please either enter phrases or upload a file.",
                400,
            )

        if not phrases:
            return "No valid phrases found", 400

        csv_content = process_phrases(phrases, use_ai_setting)

        response = make_response(csv_content)
        response.headers["Content-Type"] = "text/csv"
        response.headers["Content-Disposition"] = (
            "attachment; filename=translation_cards.csv"
        )

        return response

    except Exception as e:
        return f"Error processing request: {str(e)}", 500


@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":
    app.run(debug=True)
