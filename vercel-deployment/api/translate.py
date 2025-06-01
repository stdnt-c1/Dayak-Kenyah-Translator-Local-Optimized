from http.server import BaseHTTPRequestHandler
import json
import os
import re
from datetime import datetime
from typing import List, Tuple, Dict, Set

# Load dictionary with better error handling
DICTIONARY_PATH = os.path.join(os.path.dirname(__file__), "dictionary.json")
DICTIONARY: Dict[str, str] = {}
DICTIONARY_REVERSE: Dict[str, Set[str]] = {}  # For reverse lookups

try:
    with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
        DICTIONARY = json.load(f)
        
    # Build reverse lookup dictionary
    for indo_word, dayak_word in DICTIONARY.items():
        if dayak_word not in DICTIONARY_REVERSE:
            DICTIONARY_REVERSE[dayak_word] = set()
        DICTIONARY_REVERSE[dayak_word].add(indo_word)
        
    print(f"Dictionary loaded successfully from {DICTIONARY_PATH}")
    print(f"Total entries: {len(DICTIONARY)}")
    print(f"Total reverse mappings: {len(DICTIONARY_REVERSE)}")
        
except FileNotFoundError:
    print(f"Dictionary file not found at {DICTIONARY_PATH}")
    raise
except json.JSONDecodeError as e:
    print(f"Error parsing dictionary file: {e}")
    raise
except Exception as e:
    print(f"Unexpected error loading dictionary: {e}")
    raise

def ngram_similarity(word1: str, word2: str, n: int = 2) -> float:
    """Calculates N-gram similarity between two words."""
    if not word1 or not word2:
        return 0.0
        
    def get_ngrams(word, n):
        return set([word[i:i+n] for i in range(len(word) - n + 1)])
        
    ngrams1 = get_ngrams(word1.lower(), n)
    ngrams2 = get_ngrams(word2.lower(), n)
    
    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))
    
    return intersection / union if union else 0.0

def analyze_morphology(word: str) -> List[Tuple[str, float]]:
    """Analyze Indonesian word morphology and return possible base forms with confidence scores."""
    word = word.lower()
    base_forms = [(word, 1.0)]  # (form, confidence)
    
    # Common Indonesian affixes with confidence scores
    suffixes = [
        ('ku', 0.9),   # Very common possessive
        ('mu', 0.9),   # Very common possessive
        ('nya', 0.9),  # Very common possessive/determiner
        ('kan', 0.8),  # Causative
        ('i', 0.7),    # Locative/repetitive
        ('an', 0.7),   # Nominalizer
    ]
    
    prefixes = [
        ('me', 0.8),
        ('ber', 0.8),
        ('di', 0.8),
        ('ter', 0.7),
        ('pe', 0.7),
        ('se', 0.7),
    ]
    
    # Handle suffixes first - they're more reliable for meaning
    for suffix, confidence in suffixes:
        if word.endswith(suffix):
            base = word[:-len(suffix)]
            if len(base) > 1:
                base_forms.append((base, confidence))
                
                # Handle double suffix cases with reduced confidence
                for other_suffix, other_conf in suffixes:
                    if base.endswith(other_suffix):
                        deeper_base = base[:-len(other_suffix)]
                        if len(deeper_base) > 1:
                            base_forms.append((deeper_base, confidence * other_conf))
    
    # Handle prefixes
    word_forms = base_forms.copy()  # Work with current base forms
    for prefix, confidence in prefixes:
        for base_word, base_conf in word_forms:
            if base_word.startswith(prefix):
                stripped = base_word[len(prefix):]
                if len(stripped) > 1:
                    base_forms.append((stripped, base_conf * confidence))
    
    # Sort by confidence and remove duplicates while preserving best confidence
    seen = {}
    for form, conf in base_forms:
        if form not in seen or conf > seen[form]:
            seen[form] = conf
            
    return [(form, conf) for form, conf in sorted(seen.items(), key=lambda x: x[1], reverse=True)]

def apply_rbmt_rules(word: str, dict_data: Dict[str, str], visited: Set[str] | None = None) -> Tuple[str, str, float]:
    """Apply Rule-Based Machine Translation rules recursively."""
    if visited is None:
        visited = set()
    
    if word in visited:
        return word, "cycle", 0.0
    visited.add(word)
    
    # Direct dictionary match
    if word in dict_data:
        return dict_data[word], "direct", 1.0
        
    # Known synonym mappings with confidences
    synonyms = {
        "kawan": ("teman", 0.95),
        "teman": ("kawan", 0.95),
        "sobat": ("teman", 0.9),
        "sahabat": ("teman", 0.9),
    }
    
    # Try synonym chain translation
    if word in synonyms:
        synonym, confidence = synonyms[word]
        if synonym in dict_data:
            return dict_data[synonym], "synonym_chain", confidence
        # Try one more level of synonyms
        elif synonym in synonyms and synonym not in visited:
            next_syn, next_conf = synonyms[synonym]
            if next_syn in dict_data:
                return dict_data[next_syn], "double_synonym", confidence * next_conf
                
    return word, "none", 0.0

def process_single_word(word: str, source_lang: str, dict_data: Dict[str, str]) -> Tuple[str, str, float]:
    """Process a single word with morphological analysis and RBMT rules."""
    word_lower = word.lower()
    
    # Try direct translation first
    if word_lower in dict_data:
        return dict_data[word_lower], "exact", 1.0
        
    # Try RBMT rules
    translated, rule_type, confidence = apply_rbmt_rules(word_lower, dict_data)
    if rule_type != "none":
        return translated, rule_type, confidence
        
    # Try morphological analysis
    analyzed_forms = analyze_morphology(word_lower)
    for base_form, morph_conf in analyzed_forms:
        # Try direct translation of base form
        if base_form in dict_data:
            return dict_data[base_form], "morphological", morph_conf
            
        # Try RBMT rules on base form
        translated, rule_type, rule_conf = apply_rbmt_rules(base_form, dict_data)
        if rule_type != "none":
            return translated, f"morph_{rule_type}", morph_conf * rule_conf
            
    # If still no match, try lightweight matching
    best_match = None
    best_similarity = 0.0
    best_word = word_lower
    
    for dict_word in dict_data.keys():
        similarity = ngram_similarity(word_lower, dict_word)
        if similarity > best_similarity and similarity > 0.7:
            best_similarity = similarity
            best_match = dict_data[dict_word]
            best_word = dict_word
            
    if best_match:
        return best_match, f"fuzzy_{best_word}", best_similarity
        
    return word, "none", 0.0

# Update process_tokens to use the new functions
def process_tokens(tokens: List[str], source_lang: str, target_lang: str, case_sensitive: bool = False) -> List[Tuple[str, str, str]]:
    """Process tokens and return (translated_word, match_type, original_word)"""
    results = []
    i = 0
    
    while i < len(tokens):
        token = tokens[i]
        
        # Preserve non-word tokens exactly
        if not re.fullmatch(r'\w+', token):
            results.append((token, "preserved", token))
            i += 1
            continue
            
        # Try multi-word sequences first (up to 3 words)
        max_lookahead = min(3, len(tokens) - i)
        translated = False
        
        if source_lang == "id":
            # Try increasingly smaller sequences
            for seq_len in range(max_lookahead, 0, -1):
                phrase_tokens = tokens[i:i + seq_len]
                if all(re.fullmatch(r'\w+', t) for t in phrase_tokens):
                    phrase = " ".join(t.lower() for t in phrase_tokens)
                    
                    # Check if this phrase exists in dictionary
                    if phrase in DICTIONARY:
                        translated_word = DICTIONARY[phrase]
                        match_type = f"exact_{seq_len}gram"
                        translated = True
                        
                        # Handle first token with translation and case preservation
                        orig_token = tokens[i]
                        trans = translated_word
                        if not case_sensitive:
                            if orig_token.isupper():
                                trans = trans.upper()
                            elif orig_token.istitle():
                                trans = trans.capitalize()
                        
                        results.append((trans, match_type, orig_token))
                        
                        # Add empty strings for remaining tokens in phrase
                        for j in range(1, seq_len):
                            results.append(("", f"{match_type}_part", tokens[i+j]))
                            
                        i += seq_len
                        break
                        
            if not translated:
                # Single word processing with new pipeline
                translated_word, match_type, confidence = process_single_word(token, source_lang, DICTIONARY)
                
                # Case preservation
                if not case_sensitive:
                    if token.isupper():
                        translated_word = translated_word.upper()
                    elif token.istitle():
                        translated_word = translated_word.capitalize()
                        
                results.append((translated_word, f"{match_type}_{confidence:.2f}", token))
                i += 1
                
        else:  # target_lang == "id", Dayak to Indonesian
            # Use reverse dictionary for Dayak to Indonesian
            if token.lower() in DICTIONARY_REVERSE:
                candidates = DICTIONARY_REVERSE[token.lower()]
                translated_word = next(iter(candidates))  # Take first candidate
                match_type = "reverse"
            else:
                translated_word = token
                match_type = "none"
                
            # Case preservation
            if not case_sensitive:
                if token.isupper():
                    translated_word = translated_word.upper()
                elif token.istitle():
                    translated_word = translated_word.capitalize()
                    
            results.append((translated_word, match_type, token))
            i += 1
            
    return results

class handler(BaseHTTPRequestHandler):
    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_POST(self):
        start_time = datetime.now()
        request_id = '' # Initialize request_id
        try:
            # Check if dictionary is loaded
            if not DICTIONARY:
                 error_response = {
                     "status": "error",
                     "timestamp": datetime.now().isoformat(),
                     "error": {
                         "code": "DICTIONARY_NOT_LOADED",
                         "message": "Translation dictionary is not loaded."
                     }
                 }
                 self.send_json_response(503, error_response) # Service Unavailable
                 return

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            request_id = data.get('requestId', '')
            payload = data.get('payload', {})
            text = payload.get('text', '')
            source_lang = payload.get('sourceLang', '')
            target_lang = payload.get('targetLang', '')
            options = payload.get('options', {})
            
            # Input validation
            if not text:
                raise ValueError("Text is required")
            if source_lang not in ['id', 'dyk'] or target_lang not in ['id', 'dyk']:
                raise ValueError("Invalid language code. Use 'id' for Indonesian or 'dyk' for Dayak")
            if len(text) > 10000:
                raise ValueError("Text too long. Maximum length is 10000 characters")
                
            # Early return for same language
            if source_lang == target_lang:
                response = {
                    "status": "success",
                    "requestId": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "payload": {
                        "translatedText": text,
                        "sourceLang": source_lang,
                        "targetLang": target_lang,
                        "confidence": 1.0,
                        "sourceText": text
                    },
                    "metadata": {
                        "processingTime": "0ms",
                        "model": "direct-copy",
                        "exactMatches": 0,
                        "morphologicalMatches": 0,
                        "lightweightMatches": 0,
                        "multiWordMatches": 0,
                        "synonymRBMTMatches": 0, # Added synonymRBMTMatches
                        "totalWords": 0
                    }
                }
                self.send_json_response(200, response)
                return
              # Split into lines first to preserve line breaks
            lines = text.splitlines(keepends=True)
            all_tokens = []
            
            for line in lines:
                # Tokenize each line separately
                line_tokens = re.findall(r'(\w+|\s+|[^\w\s]+)', line)
                line_tokens = [token for token in line_tokens if token]
                all_tokens.extend(line_tokens)
            
            tokens = all_tokens
            print(f"[DEBUG] Tokens after tokenization (with newlines): {tokens}") # Added debug print
            
            # Process translation
            processed_tokens = process_tokens(
                tokens,
                source_lang,
                target_lang,
                case_sensitive=options.get('caseSensitive', False)
            )
            
            print(f"[DEBUG] Processed tokens before reconstruction: {processed_tokens}") # Added debug print
            
            # Reconstruct translated text and gather statistics
            translated_text = ''
            word_tokens = []
            exact_matches = 0
            morph_matches = 0
            light_matches = 0
            multi_word_matches = 0
            synonym_rbmt_matches = 0 # Added synonym_rbmt_matches counter
            
            i = 0
            while i < len(processed_tokens):
                token_info = processed_tokens[i]
                trans_word, match_type, orig_word = token_info
                  # Add to translated text, preserving original whitespace and newlines
                if re.fullmatch(r'\w+', orig_word):
                    translated_text += trans_word
                else:
                    # Preserve all types of whitespace exactly
                    translated_text += orig_word
                
                # Count match types
                if re.fullmatch(r'\w+', orig_word):
                    word_tokens.append(token_info)
                    if match_type == "exact":
                        exact_matches += 1
                    elif match_type == "synonym_rbmt": # Count synonym RBMT matches
                        synonym_rbmt_matches += 1
                    elif match_type == "morphological":
                        morph_matches += 1
                    elif match_type == "lightweight":
                        light_matches += 1
                    elif match_type.startswith("exact_") and match_type.endswith("gram"):
                        multi_word_matches += 1
                        # Skip the empty tokens that are part of this multi-word match
                        phrase_len = int(match_type[6:-4])  # extract number from "exact_Xgram"
                        i += phrase_len - 1  # -1 because the loop will increment i
                i += 1
            
            # Calculate confidence
            total_words = len(word_tokens)
            confidence = 0.0
            if total_words > 0:
                # Include synonym RBMT matches in confidence calculation (same as exact)
                confidence = (exact_matches + synonym_rbmt_matches + multi_word_matches + 
                            0.9 * morph_matches + 
                            0.7 * light_matches) / total_words
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000  # in milliseconds
            
            response = {
                "status": "success",
                "requestId": request_id,
                "timestamp": datetime.now().isoformat(),
                "payload": {
                    "translatedText": translated_text,
                    "sourceLang": source_lang,
                    "targetLang": target_lang,
                    "confidence": confidence,
                    "sourceText": text
                },
                "metadata": {
                    "processingTime": f"{processing_time:.0f}ms",
                    "model": "translator-v8-serverless",
                    "exactMatches": exact_matches,
                    "synonymRBMTMatches": synonym_rbmt_matches, # Added synonymRBMTMatches to metadata
                    "morphologicalMatches": morph_matches,
                    "lightweightMatches": light_matches,
                    "multiWordMatches": multi_word_matches,
                    "totalWords": total_words,
                    "dictionarySize": len(DICTIONARY),
                    "reverseDictionarySize": len(DICTIONARY_REVERSE), # Added reverse dictionary size
                    "inputLength": len(text),
                    "outputLength": len(translated_text)
                }
            }
            
            self.send_json_response(200, response)
            
        except json.JSONDecodeError:
            error_response = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "requestId": request_id, # Include request_id in error response
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Invalid JSON in request body"
                }
            }
            self.send_json_response(400, error_response)
        except ValueError as e:
            error_response = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "requestId": request_id, # Include request_id in error response
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": str(e)
                }
            }
            self.send_json_response(400, error_response)
        except Exception as e:
            error_response = {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "requestId": request_id, # Include request_id in error response
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": str(e)
                }
            }
            self.send_json_response(500, error_response)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        response = {
            "status": "success",
            "message": "Dayak Translation API is running",
            "version": "v8-serverless",
            "dictionary_status": "loaded" if DICTIONARY else "not_loaded",
            "dictionary_size": len(DICTIONARY) if DICTIONARY else 0,
            "reverse_dictionary_size": len(DICTIONARY_REVERSE) if DICTIONARY_REVERSE else 0, # Added reverse dictionary size
            "timestamp": datetime.now().isoformat()
        }
        self.send_json_response(200, response)