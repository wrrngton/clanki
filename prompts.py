phrase_prompt = """
You must take a list of phrases provided in the <text> field and based off each phrase, decide on a search query for an image search engine that would most likely return accurate images for that phrase. Examples phrases and search queries are provided below in <example> tags. Your output must match precisely the output shown in <answer> tags  with no additional formatting.

<text>
    {text}
</text>

<examples>
<example>
    <input>
        ["How are you?", "What's happening", "the apple"]
    </input>
    <answer>
        ["How are you?", "Asking someone a question", "apple"]
    </answer>
<example>
<example>
    <input>
        ["nice to meet you", "where are you from?", "what do you do for work?"]
    </input>
    <answer>
        ["people shaking hands", "map of the world", "people working"]
    </answer>
<example>
</examples>

<rules>
1. Input phrases will be in {source_language}, you must first translate the phrase to English before deciding what could be a good search term for that phrase
2. We want to avoid a scenario where a search might lead to a photo of text. e.g if the input phrase is "come ti chiami" the search term should not include "come ti chiami" as this is likely to lead to 
</rules>
3. You must simply return a new 1 dimensional array with no preamble or additional text. Your output format must be exactly an array with items wrapped in double quotes, for example:
["How are you?", "What's happening", "the apple"]
"""
# phrase_prompt_prefill = "["

image_prompt = """
You are responsible for taking the images above and scoring from 1-10 how well they match the supplied <text> field.

You must return only an array of integer scores based on how well the supplied image matches the text. Do not include any preamble or conclusions.
<text>
{text}
</text>

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
image_listprompt_prefill = "["
