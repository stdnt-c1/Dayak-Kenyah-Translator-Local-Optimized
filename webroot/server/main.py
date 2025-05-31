from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from pathlib import Path
from pydantic import BaseModel, Field, root_validator, validator
import json
import time
from datetime import datetime
import os
import logging
import re
import asyncio
import torch
import numpy as np
from typing import Optional, Dict, List, Any, Union, Tuple
import uvicorn
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI with metadata
app = FastAPI(
    title="Dayak Kenyah Translator API",
    description="Professional translation service for Indonesian and Dayak Kenyah languages",
    version="1.0.0"
)

# Define base directory and GPU settings
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DYNAMIC_DIR = BASE_DIR / "dynamic"

# Initialize CUDA if available
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if torch.cuda.is_available():
    logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
else:
    logger.warning("CUDA not available, using CPU")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files - mount both static and dynamic directories
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/dynamic", StaticFiles(directory=str(DYNAMIC_DIR)), name="dynamic")

# Thread pool for async processing
thread_pool = ThreadPoolExecutor(max_workers=4)

# Load dictionary with CUDA optimization
try:
    with open(DYNAMIC_DIR / "dictionary.json", "r", encoding="utf-8") as f:
        DICTIONARY = json.load(f)
    if not DICTIONARY:
        raise ValueError("Dictionary is empty")
        
    if torch.cuda.is_available():
        # Convert dictionary to tensors for CUDA acceleration
        VOCAB_INDO = list(DICTIONARY.keys())
        VOCAB_DAYAK = list(DICTIONARY.values())
        
        # Pad sequences to same length for tensor operations
        max_length_indo = max((len(word) for word in VOCAB_INDO), default=0)
        max_length_dayak = max((len(word) for word in VOCAB_DAYAK), default=0)
        max_length = max(max_length_indo, max_length_dayak)
        
        def pad_word(word, max_len):
            return [ord(c) for c in word] + [0] * (max_len - len(word))
            
        VOCAB_INDO_VECTORS = torch.tensor([pad_word(word, max_length) for word in VOCAB_INDO], dtype=torch.long).to(DEVICE)
        VOCAB_DAYAK_VECTORS = torch.tensor([pad_word(word, max_length) for word in VOCAB_DAYAK], dtype=torch.long).to(DEVICE)
        
except Exception as e:
    logger.error(f"Failed to load dictionary: {e}")
    raise RuntimeError(f"Failed to initialize translation service: {str(e)}")

class TranslationOptions(BaseModel):
    preserveFormatting: bool = True
    preservePunctuation: bool = True
    caseSensitive: bool = False
    useGPU: bool = True
    batchSize: int = 64
    
    @validator('batchSize')
    def validate_batch_size(cls, v):
        if v < 1 or v > 512:
            raise ValueError("Batch size must be between 1 and 512")
        return v

class TranslationPayload(BaseModel):
    sourceLang: str
    targetLang: str
    text: str
    options: TranslationOptions = Field(default_factory=TranslationOptions)
    
    @validator('sourceLang', 'targetLang')
    def validate_languages(cls, v):
        if v not in ['id', 'dyk']:
            raise ValueError("Language must be either 'id' or 'dyk'")
        return v
        
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty")
        if len(v) > 10000:  # Limit text length to prevent abuse
            raise ValueError("Text too long. Maximum length is 10000 characters")
        return v

class ClientRequest(BaseModel):
    client: str
    requestId: str
    timestamp: str
    payload: TranslationPayload

class TranslationResult(BaseModel):
    sourceLang: str
    targetLang: str
    sourceText: str
    translatedText: str
    confidence: float

class ServerResponse(BaseModel):
    server: str = "translatorService"
    requestId: str
    timestamp: str
    status: str
    payload: Optional[TranslationResult]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder({
            "server": "translatorService",
            "timestamp": datetime.now().strftime("D:%d-%m-%Y#T:%H:%M:%S"),
            "status": "error",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc)
            }
        })
    )

async def cuda_word_match(word: str, vocab_vectors: torch.Tensor, max_length: int, batch_size: int = 64) -> Optional[int]:
    """CUDA-accelerated word matching using batched processing"""
    if not torch.cuda.is_available():
        return None
    
    # Pad the input word tensor to the same max_length
    def pad_word(word, max_len):
        return [ord(c) for c in word] + [0] * (max_len - len(word))
        
    word_tensor = torch.tensor(pad_word(word, max_length), dtype=torch.long).to(DEVICE)
    
    # Process in batches
    for i in range(0, vocab_vectors.size(0), batch_size):
        batch_tensor = vocab_vectors[i:i + batch_size]
                
        # Compute matches
        matches = (batch_tensor == word_tensor).all(dim=1)
        if matches.any():
            match_idx = matches.nonzero()[0].item()
            return int(i + match_idx)  # Explicitly convert to int
    
    return None

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

def strip_indonesian_suffix(word: str) -> str:
    """Basic suffix stripping for Indonesian words."""
    suffixes = ['ku', 'mu', 'nya', 'kan', 'i']
    word_lower = word.lower()
    for suffix in suffixes:
        if word_lower.endswith(suffix):
            # Check if stripping the suffix leaves a valid word stem (basic check)
            stem = word_lower[:-len(suffix)]
            if len(stem) > 1:
                 return stem
    return word_lower

def find_compound_phrases(text: str) -> List[str]:
    """Identify potential compound phrases in Indonesian text."""
    common_phrases = {
        "selamat pagi": True,
        "selamat siang": True,
        "selamat malam": True,
        "selamat datang": True,
        "terima kasih": True
    }
    
    words = text.lower().split()
    phrases = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            potential_phrase = f"{words[i]} {words[i+1]}"
            if potential_phrase in common_phrases:
                phrases.append((i, 2, potential_phrase))  # (start_index, length, phrase)
                i += 2
                continue
        phrases.append((i, 1, words[i]))  # Single word
        i += 1
    return phrases

def analyze_morphology(word: str) -> List[str]:
    """Analyze Indonesian word morphology and return possible base forms."""
    word = word.lower()
    base_forms = [word]  # Always include original form
    
    # Common Indonesian affixes
    prefixes = ['me', 'ber', 'di', 'ter', 'pe', 'se']
    suffixes = ['kan', 'i', 'an', 'nya', 'ku', 'mu']
    
    # Handle suffixes first (like -ku, -nya, etc)
    for suffix in suffixes:
        if word.endswith(suffix):
            base = word[:-len(suffix)]
            if len(base) > 1:  # Ensure we don't create too short words
                base_forms.append(base)
                
                # Handle double suffix cases (e.g., temanku -> teman)
                for other_suffix in suffixes:
                    if base.endswith(other_suffix):
                        deeper_base = base[:-len(other_suffix)]
                        if len(deeper_base) > 1:
                            base_forms.append(deeper_base)
    
    # Handle prefixes
    for prefix in prefixes:
        if word.startswith(prefix):
            base = word[len(prefix):]
            if len(base) > 1:
                base_forms.append(base)
    
    # Common word variations/synonyms
    synonyms = {
        'kawan': ['teman', 'sahabat'],
        'teman': ['kawan', 'sahabat'],
        'sahabat': ['teman', 'kawan']
    }
    
    # Add synonyms for any base forms we found
    extended_forms = base_forms.copy()
    for form in base_forms:
        if form in synonyms:
            extended_forms.extend(synonyms[form])
    
    return list(set(extended_forms))  # Remove duplicates

async def process_tokens(tokens: List[str], source_lang: str, target_lang: str, options: TranslationOptions) -> List[Tuple[str, str, str]]:
    """Processes a list of tokens (words and non-words) and returns translated tokens, match types, and original tokens."""
    results = []
    i = 0 # Use an index to iterate through tokens

    if source_lang == "id":
        source_vocab = VOCAB_INDO
        target_vocab = VOCAB_DAYAK
        source_vectors = VOCAB_INDO_VECTORS if torch.cuda.is_available() else None
    else:
        source_vocab = VOCAB_DAYAK
        target_vocab = VOCAB_INDO
        source_vectors = VOCAB_DAYAK_VECTORS if torch.cuda.is_available() else None

    while i < len(tokens):
        token = tokens[i]

        # Handle non-word tokens directly
        if not re.fullmatch(r'\w+', token):
            results.append((token, "none", token))
            i += 1
            continue

        # It's a word token, try to translate
        original_word = token
        word_lower = original_word.lower()
        translated_word = original_word # Default to original word
        match_type = "none"

        if source_lang == "id":
            # --- Indonesian to Dayak Kenyah ---
            # 1. Exact Match Lookup (Case-insensitive)
            if word_lower in DICTIONARY:
                translated_word = DICTIONARY[word_lower]
                match_type = "exact"
            else:
                # 2. Morphological Analysis and Dictionary Lookup
                possible_forms = analyze_morphology(original_word)
                for form in possible_forms:
                    if form in DICTIONARY:
                        translated_word = DICTIONARY[form]
                        match_type = "morphological"
                        break # Use the first morphological match found

                # 3. Lightweight Matching Fallback (if enabled and no exact/morphological match)
                if match_type == "none" and options.preserveFormatting: # Using preserveFormatting as a proxy for enabling lightweight matching for now
                     best_match = None
                     best_similarity = 0.0

                     # Search in the source vocabulary for similar words
                     vocab_to_search = source_vocab

                     for vocab_word in vocab_to_search:
                         similarity = ngram_similarity(original_word, vocab_word)
                         if similarity > best_similarity and similarity > 0.7: # Threshold for similarity
                             best_similarity = similarity
                             best_match = vocab_word

                     if best_match:
                         # Look up the translation of the best matching source word
                         translated_word = DICTIONARY.get(best_match.lower(), translated_word) # Fallback to original if not found
                         match_type = "lightweight"

            # Apply case preservation for Indonesian to Dayak Kenyah
            if not options.caseSensitive:
                 if original_word.isupper():
                     translated_word = translated_word.upper()
                 elif original_word.istitle():
                     translated_word = translated_word.capitalize()
                 else:
                     translated_word = translated_word.lower()

            # Append result for this Indonesian word
            results.append((translated_word, match_type, original_word))
            i += 1

        else:
            # --- Dayak Kenyah to Indonesian ---
            # Implement cascading word match
            translated = False
            matched_length = 0

            # Try matching 3 words, then 2 words, then 1 word
            for n in range(3, 0, -1): # Try n-grams from 3 down to 1
                if i + n <= len(tokens):
                    phrase_tokens = tokens[i : i + n]
                    # Check if all tokens in the phrase are words before forming phrase string
                    if all(re.fullmatch(r'\w+', t) for t in phrase_tokens):
                        phrase = " ".join(t.lower() for t in phrase_tokens)

                        # Look for exact match of the phrase in dictionary values (Dayak Kenyah)
                        for indo_word, dayak_word in DICTIONARY.items():
                            if phrase == dayak_word.lower():
                                translated_word = indo_word
                                match_type = f"exact_{n}gram"
                                matched_length = n
                                translated = True
                                break # Found a match, break from dictionary search
                    if translated:
                        break # Found a multi-word match, exit the n-gram loop

            # If a multi-word exact match was found
            if translated:
                 # Append results for all tokens in the matched phrase
                 for k in range(matched_length):
                     # Apply case preservation to the translated word for the first token
                     if k == 0:
                         processed_translated_word = translated_word
                         if not options.caseSensitive:
                              if tokens[i+k].isupper():
                                  processed_translated_word = translated_word.upper()
                              elif tokens[i+k].istitle():
                                   processed_translated_word = translated_word.capitalize()
                              else:
                                   processed_translated_word = translated_word.lower()
                         results.append((processed_translated_word, match_type, tokens[i+k]))
                     else:
                         # Subsequent tokens in a multi-word match get empty string translation
                         results.append(("", match_type, tokens[i+k]))
                 i += matched_length # Advance index by the number of words in the matched phrase

            # If no multi-word exact match found, try single word lightweight match
            if not translated:
                # Process as a single word
                # 1. Exact Match Lookup (Case-insensitive) - already covered by n=1 in cascading, but keeping for clarity/fallback
                single_word_translated = False
                if word_lower in DICTIONARY.values(): # Check if the single word exists as a Dayak Kenyah word
                     for indo_word, dayak_word in DICTIONARY.items():
                         if word_lower == dayak_word.lower():
                             translated_word = indo_word
                             match_type = "exact"
                             single_word_translated = True
                             break

                # 2. Lightweight Matching Fallback (if enabled and no exact match)
                if not single_word_translated and options.preserveFormatting: # Using preserveFormatting as a proxy
                     best_match = None
                     best_similarity = 0.0
                     # Search in the source vocabulary for similar words
                     vocab_to_search = source_vocab

                     for vocab_word in vocab_to_search:
                         similarity = ngram_similarity(original_word, vocab_word)
                         if similarity > best_similarity and similarity > 0.7: # Threshold for similarity
                             best_similarity = similarity
                             best_match = vocab_word

                     if best_match:
                          # Find the Indonesian word corresponding to the best matching Dayak word
                          translated_word = next((k for k, v in DICTIONARY.items() if v.lower() == best_match.lower()), translated_word) # Fallback to original if not found
                          match_type = "lightweight"

                # Apply case preservation for single Dayak Kenyah word
                if not options.caseSensitive:
                     if original_word.isupper():
                         translated_word = translated_word.upper()
                     elif original_word.istitle():
                         translated_word = translated_word.capitalize()
                     else:
                         translated_word = translated_word.lower()

                # Append result for this single Dayak Kenyah word
                results.append((translated_word, match_type, original_word))
                i += 1

    return results

async def translate_text_async(text: str, source_lang: str, target_lang: str, options: TranslationOptions) -> TranslationResult:
    """Asynchronous translation with CUDA acceleration, formatting preservation, and lightweight matching"""
    start_time = time.time()

    # Tokenize using regex to separate words and non-word characters (including spaces and newlines)
    # This regex splits on word boundaries, preserving the delimiters (spaces, punctuation, newlines)
    tokens = re.findall(r'(\w+|\W+)', text)

    # Filter out empty tokens that might result from consecutive non-word characters
    tokens = [token for token in tokens if token]

    # Process tokens using the refactored function
    processed_tokens_info = await process_tokens(tokens, source_lang, target_lang, options)

    # Separate translated words, match types, and original tokens
    translated_tokens = [result[0] for result in processed_tokens_info]
    match_types = [result[1] for result in processed_tokens_info]
    original_tokens_for_reconstruction = [result[2] for result in processed_tokens_info]

    # Reconstruct with preserved formatting and case
    result_text = ""
    for i, original_token in enumerate(original_tokens_for_reconstruction):
        translated_token = translated_tokens[i]
        match_type = match_types[i]

        # If the original token was a word, apply case preservation based on the original token
        if re.fullmatch(r'\w+', original_token):
            if options.caseSensitive:
                 # If caseSensitive is true, the translation should ideally already have the correct case
                 result_text += translated_token
            else:
                 # If caseSensitive is false, try to match the original case of the token
                 if original_token.isupper():
                     result_text += translated_token.upper()
                 elif original_token.istitle():
                     result_text += translated_token.capitalize()
                 else:
                     result_text += translated_token.lower()
        else:
            # If the token is not a word (punctuation, space, newline), append it directly
            result_text += original_token # Use original_token to preserve exact formatting (spaces, newlines, etc.)

    # Calculate confidence based on match types
    total_confidence_score = 0
    translatable_tokens_count = 0

    for match_type in match_types:
        # Only consider tokens that were words for confidence calculation (match_type is not 'none')
        if match_type != "none":
             translatable_tokens_count += 1
             if match_type == "exact":
                 total_confidence_score += 1.0
             elif match_type == "morphological":
                 total_confidence_score += 0.9 # High confidence for morphological matches
             elif match_type == "lightweight":
                 total_confidence_score += 0.7 # Partial credit for lightweight matches

    confidence = total_confidence_score / translatable_tokens_count if translatable_tokens_count else 0.0

    return TranslationResult(
        sourceLang=source_lang,
        targetLang=target_lang,
        sourceText=text,
        translatedText=result_text,
        confidence=confidence
    )
@app.post("/translate", response_model=ServerResponse)
async def translate(request: ClientRequest, background_tasks: BackgroundTasks) -> ServerResponse:
    start_time = time.time()
    try:
        # Validate dictionary is loaded
        if not DICTIONARY:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Translation service is not ready",
                    "details": "Dictionary not loaded"
                }
            )

        # Additional validation
        if request.payload.sourceLang == request.payload.targetLang:
            return ServerResponse(
                requestId=request.requestId,
                timestamp=datetime.now().strftime("D:%d-%m-%Y#T:%H:%M:%S"),
                status="success",
                payload=TranslationResult(
                    sourceLang=request.payload.sourceLang,
                    targetLang=request.payload.targetLang,
                    sourceText=request.payload.text,
                    translatedText=request.payload.text,
                    confidence=1.0
                ),
                metadata={
                    "processingTime": "0ms",
                    "model": "direct-copy",
                    "detectedLanguage": request.payload.sourceLang
                }
            )

        # Process translation asynchronously
        try:
            result = await translate_text_async(
                request.payload.text,
                request.payload.sourceLang,
                request.payload.targetLang,
                request.payload.options
            )
        except Exception as translation_error:
            logger.error(f"Translation processing error: {str(translation_error)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "TRANSLATION_PROCESSING_ERROR",
                    "message": "Failed to process translation",
                    "details": str(translation_error)
                }
            )

        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Build response following plan.md format
        response = ServerResponse(
            requestId=request.requestId,
            timestamp=datetime.now().strftime("D:%d-%m-%Y#T:%H:%M:%S"),
            status="success",
            payload=result,
            metadata={
                "processingTime": f"{processing_time * 1000:.0f}ms",
                "model": "translator-v8-cuda" if torch.cuda.is_available() else "translator-v8-cpu",
                "detectedLanguage": request.payload.sourceLang,
                "gpuUtilization": f"{torch.cuda.memory_allocated() / 1024**2:.2f}MB" if torch.cuda.is_available() else "N/A",
                "dictionarySize": len(DICTIONARY),
                "inputLength": len(request.payload.text),
                "outputLength": len(result.translatedText) if result else 0
            }
        )
        return response

    except HTTPException as http_exc:
        # Re-raise HTTPException to be handled by FastAPI's default handler or our universal handler
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors and return a 500 response
        logger.error(f"Unexpected error in translate endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(e)
            }
        )

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=False
    )
