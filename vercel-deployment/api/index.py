from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime

print("Starting API handler")  # Debug print

# Load dictionary
DICTIONARY_PATH = os.path.join(os.path.dirname(__file__), "dictionary.json")
try:
    with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
        DICTIONARY = json.load(f)
        print(f"Dictionary loaded successfully from {DICTIONARY_PATH}")
except Exception as e:
    print(f"Error loading dictionary from {DICTIONARY_PATH}: {e}")
    DICTIONARY = {}

def perform_translation(text, source_lang, target_lang, options=None):
    if source_lang == target_lang:
        return text
    words = text.lower().split()
    translated_words = []
    for word in words:
        dict_key = f"{source_lang}_to_{target_lang}"
        if word in DICTIONARY.get(dict_key, {}):
            translated_words.append(DICTIONARY[dict_key][word])
        else:
            translated_words.append(word)
    return " ".join(translated_words)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"GET request to {self.path}")  # Debug print
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {
            "status": "success",
            "message": "Dayak Translation API is running"
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        print(f"POST request to {self.path}")  # Debug print
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            print(f"Received body: {body}")  # Debug print
            
            data = json.loads(body)
            payload = data.get('payload', {})
            
            text = payload.get('text', '')
            source_lang = payload.get('sourceLang', '')
            target_lang = payload.get('targetLang', '')
            
            print(f"Processing translation request: {text} from {source_lang} to {target_lang}")  # Debug print
            
            if not text:
                raise ValueError("Text is required")
            if source_lang not in ['id', 'dyk'] or target_lang not in ['id', 'dyk']:
                raise ValueError("Invalid language code. Use 'id' for Indonesian or 'dyk' for Dayak")

            translated = perform_translation(text, source_lang, target_lang)
            
            response = {
                "status": "success",
                "requestId": data.get('requestId', ''),
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "translatedText": translated,
                    "sourceLang": source_lang,
                    "targetLang": target_lang
                }
            }
            
            print(f"Sending response: {response}")  # Debug print
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error processing request: {str(e)}")  # Debug print
            error_response = {
                "status": "error",
                "error": {
                    "message": str(e)
                }
            }
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        print(f"OPTIONS request to {self.path}")  # Debug print
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
