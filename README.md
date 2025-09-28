# Anki flashcard generator

Simple Python app that utilises Brave Image Search API, Google Translate and Claude API to generate flashcards for Anki import.

It generates a CSV of `input`, `target` and `image_url` based on the `input` text.

Claude is used as a judge to give the user the best image for the text they wish to translate.

The CVS can be uploaded to Anki via Anki's 'File Upload' feature.
