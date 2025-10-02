# Anki flashcard generator

Simple Python app that utilises Brave Image Search API, Google Translate and Claude API to generate flashcards for Anki import.

It generates a CSV of `input`, `target` and `image_url` based on the `input` text.

Claude is used as a judge to give the user the best image for the text they wish to translate.

The CSV can be uploaded to Anki via Anki's 'File Upload' feature.

A sample imput is provided in `sample.txt` and an output in `deck.csv`.

It is designed to be run via the command line with one single `file` flag (short: `-F`, long: `--file`). The `file` is an input .txt file of phrases to be translated. 

```console
░ python3 run.py --file sample.txt
```

Claude image judgements can be skipped in favour of the images API's own confidence score, you can use `--ai` flag set to `false`.

```console
░ python3 run.py --file sample.txt --ai false
```

## To do

- [x] Use Claude to decide the right query to pass to Brave
- [ ] CLI flags for language selection
- [ ] CLI flags for output file

