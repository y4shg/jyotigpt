import json
import os
import re
from deep_translator import GoogleTranslator
from threading import Thread, Lock

INPUT_FILE = "lib/l10n/app_en.arb"
OUTPUT_DIR = "langfiles/"
THREADS = 6  # number of parallel threads

# Detect placeholders like {name}, {count}
placeholder_pattern = re.compile(r"{\w+}")

languages = {
    # 🇮🇳 Indian Languages
    "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "pa": "Punjabi", "ur": "Urdu", "ne": "Nepali", "as": "Assamese",
    "or": "Odia",
    # 🇪🇺 European Languages
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "pl": "Polish",
    "ru": "Russian", "uk": "Ukrainian", "sv": "Swedish", "da": "Danish",
    "no": "Norwegian", "fi": "Finnish", "cs": "Czech", "hu": "Hungarian",
    "ro": "Romanian", "el": "Greek", "sk": "Slovak", "sr": "Serbian",
    "hr": "Croatian", "bg": "Bulgarian",
    # 🌏 Asia-Pacific / Middle East / Africa
    "zh-cn": "zh-CN", "zh-tw": "zh-TW", "ja": "Japanese", "ko": "Korean",
    "id": "Indonesian", "vi": "Vietnamese", "th": "Thai",
    "ar": "Arabic", "fa": "Persian", "he": "Hebrew", "sw": "Swahili",
    # 🌎 Americas
    "es-MX": "es", "pt-BR": "pt"
}

# Load source
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    english_data = json.load(f)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

keys_to_translate = [k for k in english_data if not k.startswith("@") and k != "@@locale"]
lock = Lock()

def translate_language(lang_code):
    translated_data = {"@@locale": lang_code}
    print(f"🌎 Translating to {lang_code}...")

    for key in keys_to_translate:
        value = english_data[key]
        if placeholder_pattern.search(value):
            translated_text = value
        else:
            try:
                translated_text = GoogleTranslator(source='en', target=lang_code).translate(value)
            except Exception as e:
                print(f"⚠️ Error {lang_code} {key}: {e}")
                translated_text = value
        translated_data[key] = translated_text

    # Copy metadata
    for key, value in english_data.items():
        if key.startswith("@"):
            translated_data[key] = value

    output_file = os.path.join(OUTPUT_DIR, f"app_{lang_code}.arb")
    with lock:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(translated_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Created: {output_file}")

threads = []
for lang_code in languages:
    if lang_code == "en":
        continue
    while len([t for t in threads if t.is_alive()]) >= THREADS:
        pass  # wait for a free thread
    t = Thread(target=translate_language, args=(lang_code,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("\n🎉 All translations done! Check your langfiles folder.")
