import json
import os
import tempfile
from pathlib import Path
from typing import Any

from llm_client import call_llm, extract_json_from_response


PROFILE_FIELDS = {
    "kanji",
    "curriculum_data",
    "historical_etymology",
    "writing_mechanics",
    "high_yield_vocabulary",
    "common_pitfalls_for_learners",
    "meaning",
    "hiragana_readings",
    "components_and_radicals",
    "relationships",
    "best_way_to_recognize",
    "best_way_to_remember_pronunciation",
    "best_way_to_learn_it",
    "best_way_to_write_it",
}

JSON_SCHEMA_PROMPT = """You are an expert Japanese kanji linguistics and curriculum assistant.
Return only valid JSON with exactly one kanji profile for the requested character, using this structure:
{
  "kanji_profiles": [
    {
      "kanji": "KANJI_HERE",
      "curriculum_data": {
        "jlpt_level": "N5 to N1, or null if unknown",
        "school_grade": "Grade 1-6, Secondary, or null if unknown",
        "frequency_rank": 0
      },
      "historical_etymology": {
        "kanji_type": "Pictograph, Ideogram, Compound Ideograph, or Semantic-Phonetic",
        "ancient_depiction": "string",
        "evolution_to_modern": "string"
      },
      "writing_mechanics": {
        "stroke_count": 0,
        "stroke_order_tip": "string"
      },
      "high_yield_vocabulary": [
        { "word": "string", "reading": "string", "meaning": "string" }
      ],
      "common_pitfalls_for_learners": ["string"],
      "meaning": ["string"],
      "hiragana_readings": {
        "kunyomi": ["string"],
        "onyomi": ["string"]
      },
      "components_and_radicals": [
        { "character": "string", "type": "string", "meaning": "string", "contribution": "string" }
      ],
      "relationships": {
        "by_meaning": [{ "kanji": "string", "meaning": "string" }],
        "by_visual": [{ "kanji": "string", "meaning": "string" }]
      },
      "best_way_to_recognize": "string",
      "best_way_to_remember_pronunciation": "string",
      "best_way_to_learn_it": "string",
      "best_way_to_write_it": "string"
    }
  ],
  "visual_networks": {
    "phonetic_constellations": [],
    "radical_trees": []
  }
}
Generate all details from your own knowledge of the requested kanji. Do not include profiles for any other characters. Do not make up historical, frequency, or curriculum facts; use null or an empty list when a fact is unknown. Keep each profile focused on the requested kanji.
"""


def load_kanji_input(input_file: Path) -> list[str]:
    with input_file.open("r", encoding="utf-8") as file:
        data: Any = json.load(file)

    if not isinstance(data, dict) or not isinstance(data.get("kanji"), list):
        raise ValueError(f"{input_file} must contain a 'kanji' list.")

    kanji_list = data["kanji"]
    for character in kanji_list:
        if not isinstance(character, str) or len(character) != 1:
            raise ValueError(f"Invalid kanji entry in {input_file}: {character!r}.")
    return kanji_list


def load_output(output_file: Path) -> dict[str, Any]:
    if not output_file.exists():
        return {
            "app_metadata": {
                "schema_version": "2.4",
                "description": "LLM-generated kanji learning dataset.",
            },
            "kanji_profiles": [],
            "visual_networks": {
                "phonetic_constellations": [],
                "radical_trees": [],
            },
        }

    with output_file.open("r", encoding="utf-8") as file:
        data: Any = json.load(file)

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("kanji_profiles"), list)
        or not isinstance(data.get("visual_networks"), dict)
    ):
        raise ValueError(f"{output_file} is not a valid kanji database.")

    networks = data["visual_networks"]
    for key in ("phonetic_constellations", "radical_trees"):
        networks.setdefault(key, [])
        if not isinstance(networks[key], list):
            raise ValueError(f"{output_file} field 'visual_networks.{key}' must be a list.")

    return data


def save_output(output_file: Path, data: dict[str, Any]) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_file.parent,
            prefix=f".{output_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, output_file)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def generate_kanji_profile(
    kanji_character: str,
) -> tuple[dict[str, Any], dict[str, list[Any]]]:
    prompt = (
        f"{JSON_SCHEMA_PROMPT}\n"
        f"Requested kanji: {kanji_character}"
    )

    response = call_llm(prompt)
    result: Any = extract_json_from_response(response)
    if result is None:
        response = call_llm(
            f"{prompt}\n\nYour previous response was not valid JSON. "
            "Regenerate it as one complete JSON object only, without markdown "
            "fences or explanatory text."
        )
        result = extract_json_from_response(response)

    if isinstance(result, list):
        raise RuntimeError(
            f"LLM did not return a kanji profile for {kanji_character!r}. "
            "Check that the configured LM Studio server or Gemini API is available."
        )
    if not isinstance(result, dict):
        response_excerpt = response[:500]
        raise ValueError(
            f"LLM returned invalid JSON for kanji {kanji_character!r} after retry. "
            f"Response excerpt: {response_excerpt!r}"
        )

    profiles = result.get("kanji_profiles")
    if not isinstance(profiles, list):
        raise ValueError(f"LLM response for {kanji_character!r} missing 'kanji_profiles' list.")

    # Filter for profiles that match the requested kanji
    matching_profiles = [p for p in profiles if isinstance(p, dict) and p.get("kanji") == kanji_character]

    if len(matching_profiles) != 1:
        raise ValueError(
            f"LLM response for {kanji_character!r} must contain exactly one matching kanji profile. "
            f"Found {len(matching_profiles)} matches out of {len(profiles)} profiles."
        )

    profile = matching_profiles[0]

    missing_fields = PROFILE_FIELDS - profile.keys()
    if missing_fields:
        raise ValueError(
            f"LLM response for {kanji_character!r} is missing profile fields: "
            f"{sorted(missing_fields)}."
        )

    networks: Any = result.get("visual_networks", {})
    if not isinstance(networks, dict):
        raise ValueError(
            f"LLM response for {kanji_character!r} has invalid visual_networks."
        )

    normalized_networks: dict[str, list[Any]] = {}
    for key in ("phonetic_constellations", "radical_trees"):
        value = networks.get(key, [])
        if not isinstance(value, list):
            raise ValueError(
                f"LLM response for {kanji_character!r} has invalid visual_networks.{key}."
            )
        normalized_networks[key] = value

    return profile, normalized_networks


def process_kanji_list(input_file: Path, output_file: Path) -> None:
    source_kanji = load_kanji_input(input_file)
    database = load_output(output_file)

    existing_profiles = database["kanji_profiles"]
    existing_kanji: set[str] = set()
    for profile in existing_profiles:
        if not isinstance(profile, dict) or not isinstance(profile.get("kanji"), str):
            raise ValueError(f"{output_file} contains an invalid kanji profile.")
        if profile["kanji"] in existing_kanji:
            raise ValueError(
                f"{output_file} contains duplicate profiles for {profile['kanji']!r}."
            )
        existing_kanji.add(profile["kanji"])

    total = len(source_kanji)
    for index, character in enumerate(source_kanji, start=1):
        if character in existing_kanji:
            print(f"[{index}/{total}] Skipping {ascii(character)}: already in {output_file.name}.")
            continue

        print(f"[{index}/{total}] Generating profile for {ascii(character)}...")
        profile, networks = generate_kanji_profile(character)

        existing_profiles.append(profile)
        existing_kanji.add(character)
        for key, values in networks.items():
            database["visual_networks"][key].extend(values)

        save_output(output_file, database)
        print(f"Saved {ascii(character)} to {output_file}.")

    print(f"Finished: {len(existing_profiles)} kanji profiles in {output_file}.")


def main() -> None:
    data_directory = Path(__file__).resolve().parent.parent / "data"
    input_file = data_directory / "kanji_characters.json"
    output_file = data_directory / "kanji.json"
    process_kanji_list(input_file, output_file)


if __name__ == "__main__":
    main()
