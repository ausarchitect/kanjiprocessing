import json
import os
import re

def main():
    if not os.path.exists('natural_sentences.json'):
        print("natural_sentences.json not found!")
        return

    with open('natural_sentences.json', 'r', encoding='utf-8') as f:
        sentences = json.load(f)

    kanji_map = {}
    katakana_map = {}

    kanji_regex = re.compile(r'[\u4E00-\u9FAF]')
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
    if os.path.exists('kanji_words.json'):
        try:
            with open('kanji_words.json', 'r', encoding='utf-8') as f:
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

    with open('kanji_words.json', 'w', encoding='utf-8') as f:
        json.dump(kanji_words, f, ensure_ascii=False, indent=2)

    with open('katakana_words.json', 'w', encoding='utf-8') as f:
        json.dump(katakana_words, f, ensure_ascii=False, indent=2)

    print(f"Successfully extracted {len(kanji_words)} kanji words to kanji_words.json")
    print(f"Successfully extracted {len(katakana_words)} katakana words to katakana_words.json")

if __name__ == '__main__':
    main()
