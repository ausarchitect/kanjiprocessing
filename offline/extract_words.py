import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')


def main():
    input_path = os.path.join(BASE_DIR, 'natural_sentences.json')
    if not os.path.exists(input_path):
        print("natural_sentences.json not found!")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        sentences = json.load(f)

    kanji_map = {}
    katakana_map = {}
    kanji_char_counts = {}

    # Kanji ranges: Extension A, main CJK block, and compatibility ideographs
    kanji_regex = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]')
    katakana_regex = re.compile(r'[\u30A0-\u30FF]')

    for s in sentences:
        japanese = s.get('japanese', '')
        hiragana = s.get('hiragana', '')
        english = s.get('english', '')
        components = s.get('components', [])

        if not isinstance(components, list):
            continue

        for c in components:
            text = c.get('text', '').strip()
            role = c.get('role', '').strip()

            if kanji_regex.search(text):
                for char in kanji_regex.findall(text):
                    kanji_char_counts[char] = kanji_char_counts.get(char, 0) + 1
                if text not in kanji_map:
                    kanji_map[text] = {'meaning': role, 'freq': 0, 'examples': []}
                entry = kanji_map[text]
                entry['freq'] += 1
                if len(entry['examples']) < 3:
                    entry['examples'].append({
                        'japanese': japanese,
                        'hiragana': hiragana,
                        'english': english
                    })

            if katakana_regex.search(text):
                if text not in katakana_map:
                    katakana_map[text] = {'meaning': role, 'freq': 0, 'examples': []}
                entry = katakana_map[text]
                entry['freq'] += 1
                if len(entry['examples']) < 3:
                    entry['examples'].append({
                        'japanese': japanese,
                        'hiragana': hiragana,
                        'english': english
                    })

    existing_kanji = {}
    kanji_words_path = os.path.join(DATA_DIR, 'kanji_words.json')
    if os.path.exists(kanji_words_path):
        try:
            with open(kanji_words_path, 'r', encoding='utf-8') as f:
                for item in json.load(f):
                    existing_kanji[item['word']] = item
        except Exception:
            pass

    kanji_words = sorted(
        [{
            'word': word,
            'reading': existing_kanji.get(word, {}).get('reading', ''),
            'meaning': data['meaning'],
            'english': existing_kanji.get(word, {}).get('english', data['meaning']),
            'frequency': data['freq'],
            'examples': data['examples']
        } for word, data in kanji_map.items()],
        key=lambda x: x['frequency'],
        reverse=True
    )

    katakana_words = sorted(
        [{
            'word': word,
            'reading': word,
            'meaning': data['meaning'],
            'frequency': data['freq'],
            'examples': data['examples']
        } for word, data in katakana_map.items()],
        key=lambda x: x['frequency'],
        reverse=True
    )

    with open(kanji_words_path, 'w', encoding='utf-8') as f:
        json.dump(kanji_words, f, ensure_ascii=False, indent=2)

    with open(os.path.join(DATA_DIR, 'katakana_words.json'), 'w', encoding='utf-8') as f:
        json.dump(katakana_words, f, ensure_ascii=False, indent=2)

    kanji_characters = sorted(kanji_char_counts)
    kanji_characters_data = {
        'count': len(kanji_characters),
        'kanji': kanji_characters,
        'occurrences': {k: kanji_char_counts[k] for k in kanji_characters}
    }
    with open(os.path.join(DATA_DIR, 'kanji_characters.json'), 'w', encoding='utf-8') as f:
        json.dump(kanji_characters_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully extracted {len(kanji_words)} kanji words to kanji_words.json")
    print(f"Successfully extracted {len(katakana_words)} katakana words to katakana_words.json")
    print(f"Successfully extracted {len(kanji_characters)} unique kanji characters to kanji_characters.json")

if __name__ == '__main__':
    main()
