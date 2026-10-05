import json
import os
import re

def extract_kanji(text):
    # Regular expression for common Kanji ranges:
    # \u4e00-\u9faf: CJK Unified Ideographs
    # \u3400-\u4dbf: CJK Unified Ideographs Extension A
    # \u3000-\u303f: CJK Symbols and Punctuation (not kanji)
    # \u3040-\u309f: Hiragana (not kanji)
    # \u30a0-\u30ff: Katakana (not kanji)
    # We specifically want characters in the Kanji ranges.
    kanji_pattern = re.compile(r'[\u4e00-\u9faf\u3400-\u4dbf]')
    return kanji_pattern.findall(text)

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    kanji_words_path = os.path.join(data_dir, 'kanji_words.json')
    kanjiapi_full_path = os.path.join(data_dir, 'kanjiapi_full.json')
    output_path = os.path.join(data_dir, 'kanjiapi_words.json')

    print(f"Loading {kanji_words_path}...")
    try:
        with open(kanji_words_path, 'r', encoding='utf-8') as f:
            words_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {kanji_words_path} not found.")
        return

    # Map each word to its extracted kanji characters
    word_to_kanji = {}
    all_found_kanji = set()
    for item in words_data:
        word = item.get('word', '')
        kanjis = extract_kanji(word)
        word_to_kanji[word] = kanjis
        all_found_kanji.update(kanjis)

    print(f"Processed {len(word_to_kanji)} words, found {len(all_found_kanji)} unique kanji characters.")

    print(f"Loading {kanjiapi_full_path}...")
    try:
        with open(kanjiapi_full_path, 'r', encoding='utf-8') as f:
            full_api_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {kanjiapi_full_path} not found.")
        return

    # The full API data has a "kanjis" key which is a dictionary of kanji entries
    all_kanjis = full_api_data.get('kanjis', {})

    # Filter entries to only those that appear in our found_kanji set
    matched_kanjis = {k: v for k, v in all_kanjis.items() if k in all_found_kanji}

    print(f"Matched {len(matched_kanjis)} kanji entries from the full API.")

    # Save the results with both the word mapping and the kanji data
    output_data = {
        "word_to_kanji": word_to_kanji,
        "kanjis": matched_kanjis
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully wrote matched kanji and word mappings to {output_path}.")


if __name__ == "__main__":
    main()
