import os
import re
import base64
import Levenshtein
import unicodedata
import json
from mistralai import Mistral
from services.api_utils import get_rows_by_rpps_finess_or_name, validate_date


# --------------------------
# Client Initialization
# --------------------------
API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    raise ValueError("Missing MISTRAL_API_KEY in environment variables")

client = Mistral(api_key=API_KEY)


# --------------------------
# Cleaning utilities
# --------------------------
def clean_full_name(full_name):
    '''
    Cleans and standardizes a full name by:
    - Removing titles such as "Dr", "DR", or "Docteur".
    - Stripping extra spaces and converting the text to lowercase.
    - Removing spaces within the name.
    Args:
        full_name (str): The full name of the individual.
    Returns:
        str: The cleaned name, or None if no name is provided.
    '''
    if full_name:
        cleaned_name = re.sub(r'^(Dr|DR|Docteur)\s+', '', full_name.strip(), flags=re.IGNORECASE).lower()
        cleaned_name = cleaned_name.replace(" ", "")
        return cleaned_name
    return None


def clean_value(value):
    '''
    Removes all spaces and trims a value.
    Args:
        value (str): The value to clean.
    Returns:
        str: The cleaned value, or None if empty.
    '''
    return value.replace(" ", "").strip() if value else None


# --------------------------
# OCR Extraction using Mistral
# --------------------------
def mistral_ocr_extract(image_data: bytes, mime_type: str = "image/jpeg") -> str:
    '''
    Sends an image to the Mistral OCR model and returns the extracted text.
    Args:
        image_data (bytes): The preprocessed image content.
        mime_type (str): MIME type of the image, default is 'image/jpeg'.
    Returns:
        str: The OCR-extracted text content.
    '''
    try:
        upload_resp = client.files.upload(
            file={
                "file_name": "ordonnance_input.jpg",
                "content": image_data,
                "mime_type": mime_type
            },
            purpose="ocr"
        )
        file_id = upload_resp.id

        response = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "file", "file_id": file_id}
        )

        if not response.pages or len(response.pages) == 0:
            raise ValueError("No text detected in OCR response.")

        text_output = "\n".join([page.markdown for page in response.pages])
        return text_output

    except Exception as e:
        raise RuntimeError(f"OCR extraction failed: {e}")


# --------------------------
# LLM Extraction
# --------------------------
def call_mistral_llm(ocr_text):
    '''
    Sends OCR text to the Mistral LLM model for structured information extraction.
    Each field includes both a value and a confidence score.
    Args:
        ocr_text (str): The text extracted by OCR.
    Returns:
        str: JSON-formatted string from the LLM.
    '''
    llm_response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a medical assistant specialized in reading prescriptions. "
                    "Carefully analyze the provided text and return ONLY a strictly valid JSON object, without extra text, "
                    "comments, or ```json``` tags. "
                    "The JSON must contain exactly the following keys: "
                    "normal_treatment, ald_treatment, am_finess_number, prescriber_name, prescription_date, rpps_number. "
                    "Each key must be an object with two sub-keys: "
                    "'value' (string) and 'confidence' (float between 0 and 1). "
                    "Missing values should have an empty string and a confidence of 0.0. "
                    "Example: "
                    "{"
                    "\"normal_treatment\": {\"value\": \"bandage replacement\", \"confidence\": 0.92}, "
                    "\"ald_treatment\": {\"value\": \"\", \"confidence\": 0.0}, "
                    "\"am_finess_number\": {\"value\": \"921235255\", \"confidence\": 0.87}, "
                    "\"prescriber_name\": {\"value\": \"Doctor F. Dupont\", \"confidence\": 0.94}, "
                    "\"prescription_date\": {\"value\": \"04/11/2018\", \"confidence\": 0.97}, "
                    "\"rpps_number\": {\"value\": \"10001649424\", \"confidence\": 0.95}"
                    "}"
                )
            },
            {
                "role": "user",
                "content": f"Here is the extracted OCR text:\n{ocr_text}\n\nReturn the requested JSON."
            },
        ],
    )
    return llm_response.choices[0].message.content


def parse_llm_output(structured_output):
    '''
    Parses the LLM output into a Python dictionary, removing Markdown fences if present.
    Args:
        structured_output (str): Raw text returned by the LLM.
    Returns:
        dict: Parsed JSON content.
    '''
    clean_json = re.sub(r"^```(?:json)?|```$", "", structured_output.strip(), flags=re.MULTILINE).strip()
    return json.loads(clean_json)


# --------------------------
# Query response building
# --------------------------
def build_query_responses(data):
    '''
    Builds a query_responses dictionary from the LLM's structured data.
    Args:
        data (dict): JSON dictionary returned by Mistral LLM.
    Returns:
        dict: Dictionary of entities with value and confidence.
    '''
    query_responses = {}

    def put_entity(name, key):
        field = data.get(key)
        if isinstance(field, dict) and "value" in field:
            query_responses[name] = {
                "value": field.get("value", ""),
                "confidence": field.get("confidence", 0.0)
            }

    put_entity("Texte-soin-sans-ALD", "normal_treatment")
    put_entity("Texte-soin-ALD", "ald_treatment")
    put_entity("Numero-AM-Finess", "am_finess_number")
    put_entity("Nom-du-medecin", "prescriber_name")
    put_entity("Date-de-la-prescription", "prescription_date")
    put_entity("Numero-RPPS", "rpps_number")

    return query_responses


def clean_query_responses(query_responses):
    '''
    Cleans the extracted query responses by:
    - Removing spaces in identifiers.
    - Validating and normalizing dates.
    Args:
        query_responses (dict): Dictionary of extracted fields.
    Returns:
        dict: Cleaned query_responses dictionary.
    '''
    for key in ["Numero-RPPS", "Numero-AM-Finess"]:
        if key in query_responses:
            query_responses[key]["value"] = clean_value(query_responses[key]["value"])
    if "Date-de-la-prescription" in query_responses:
        date_value = query_responses["Date-de-la-prescription"]["value"]
        valid_date = validate_date(date_value)
        query_responses["Date-de-la-prescription"]["value"] = valid_date or ""
    return query_responses


# --------------------------
# Enrichment from Database
# --------------------------
def enrich_with_best_matches(query_responses):
    '''
    Uses RPPS, FINESS, and prescriber name to find the best matches from the Supabase database.
    Adds "best_" fields with extracted or default values.
    Args:
        query_responses (dict): Extracted and cleaned responses.
    Returns:
        dict: Enriched query_responses including best_* matches.
    '''
    rpps_number = query_responses.get("Numero-RPPS", {}).get("value")
    finess_number = query_responses.get("Numero-AM-Finess", {}).get("value")
    name = clean_full_name(query_responses.get("Nom-du-medecin", {}).get("value"))
    best_matches = {}

    if rpps_number or finess_number or name:
        rows = get_rows_by_rpps_finess_or_name(rpps_number, finess_number, name)

        if rows:
            best_match, highest_score = sim(rows, name=name, RPPS=rpps_number, FINESS=finess_number)

            if highest_score > 0.2:
                best_matches.update({
                    "best_rpps_number": {
                        "value": best_match.get("numero_rpps", ""),
                        "confidence": "Extracted from database"
                    },
                    "best_prescriber_name": {
                        "value": f"{best_match.get('prenom', '')} {best_match.get('nom', '')}".strip(),
                        "confidence": "Extracted from database"
                    },
                    "best_finess_number": {
                        "value": best_match.get("numero_finess_etablissement_juridique", ""),
                        "confidence": "Extracted from database"
                    }
                })
            else:
                best_matches.update({
                    "best_rpps_number": {"value": "", "confidence": "Not found"},
                    "best_prescriber_name": {"value": "", "confidence": "Not found"},
                    "best_finess_number": {"value": "", "confidence": "Not found"}
                })
        else:
            best_matches.update({
                "best_rpps_number": {"value": "", "confidence": "Not found"},
                "best_prescriber_name": {"value": "", "confidence": "Not found"},
                "best_finess_number": {"value": "", "confidence": "Not found"}
            })

    query_responses.update(best_matches)
    return query_responses


# --------------------------
# Main Extraction Pipeline
# --------------------------
def extract_query_responses(ocr_text: str):
    '''
    End-to-end extraction pipeline that:
    1. Calls the Mistral LLM for structured extraction.
    2. Parses and builds query_responses.
    3. Cleans and validates fields.
    4. Enriches results with best database matches.
    Args:
        ocr_text (str): OCR text extracted from the prescription.
    Returns:
        dict: Final enriched query_responses dictionary.
    '''
    try:
        structured_output = call_mistral_llm(ocr_text)
        data = parse_llm_output(structured_output)
        query_responses = build_query_responses(data)
        query_responses = clean_query_responses(query_responses)
        query_responses = enrich_with_best_matches(query_responses)
        return query_responses
    except Exception as e:
        raise RuntimeError(f"Error in extract_query_responses: {e}")


# --------------------------
# Formatting for Frontend
# --------------------------
def format_response_to_ordonnance(query_responses):
    '''
    Converts a `query_responses` dictionary into a flattened ordonnance object
    formatted for frontend display, preserving both values and confidences.
    Args:
        query_responses (dict): The enriched query_responses dictionary.
    Returns:
        dict: Flattened ordonnance object.
    '''
    ordonnance = {
        "normal_treatment": {"value": "", "confidence": 0.0},
        "ald_treatment": {"value": "", "confidence": 0.0},
        "am_finess_number": {"value": "", "confidence": 0.0},
        "prescriber_name": {"value": "", "confidence": 0.0},
        "prescription_date": {"value": "", "confidence": 0.0},
        "rpps_number": {"value": "", "confidence": 0.0},
        "best_am_finess_number": {"value": "", "confidence": "Not found"},
        "best_prescriber_name": {"value": "", "confidence": "Not found"},
        "best_rpps_number": {"value": "", "confidence": "Not found"}
    }

    mapping = {
        "Texte-soin-sans-ALD": "normal_treatment",
        "Texte-soin-ALD": "ald_treatment",
        "Numero-AM-Finess": "am_finess_number",
        "Nom-du-medecin": "prescriber_name",
        "Date-de-la-prescription": "prescription_date",
        "Numero-RPPS": "rpps_number",
        "best_finess_number": "best_am_finess_number",
        "best_prescriber_name": "best_prescriber_name",
        "best_rpps_number": "best_rpps_number"
    }

    for key, target_key in mapping.items():
        value_dict = query_responses.get(key)
        if isinstance(value_dict, dict):
            ordonnance[target_key]["value"] = value_dict.get("value") or ""
            ordonnance[target_key]["confidence"] = value_dict.get("confidence", 0.0)
        elif isinstance(value_dict, str):
            ordonnance[target_key]["value"] = value_dict
        else:
            ordonnance[target_key]["value"] = ""

    return ordonnance


# --------------------------
# Similarity Computation
# --------------------------
def normalize_text(text):
    '''
    Normalizes text by converting to lowercase, removing accents, and stripping whitespace.
    Args:
        text (str): Input text.
    Returns:
        str: Normalized text.
    '''
    if text is None:
        return ""
    text = str(text).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))


def calculate_weights(name=None, RPPS=None, FINESS=None):
    '''
    Computes weights for each feature (name, RPPS, FINESS) depending on availability.
    Args:
        name (str): Prescriber name.
        RPPS (str): RPPS number.
        FINESS (str): FINESS number.
    Returns:
        dict: Weights for name, RPPS, and FINESS.
    '''
    if not any([name, RPPS, FINESS]):
        return {'name': 0.0, 'rpps': 0.0, 'finess': 0.0}

    available = {'name': name is not None, 'rpps': RPPS is not None, 'finess': FINESS is not None}
    total_available = sum(available.values())

    if total_available == 1:
        return {key: 1.0 if value else 0.0 for key, value in available.items()}
    elif total_available == 2:
        if not available['name']:
            return {'name': 0.0, 'rpps': 0.5, 'finess': 0.5}
        if not available['rpps']:
            return {'name': 0.25, 'rpps': 0.0, 'finess': 0.75}
        if not available['finess']:
            return {'name': 0.25, 'rpps': 0.75, 'finess': 0.0}
    else:
        return {'name': 0.2, 'rpps': 0.4, 'finess': 0.4}


def calculate_similarity(input_text, target_text):
    '''
    Computes the similarity between two strings using Levenshtein ratio.
    Args:
        input_text (str): First string.
        target_text (str): Second string.
    Returns:
        float: Similarity ratio between 0 and 1.
    '''
    return Levenshtein.ratio(normalize_text(input_text), normalize_text(target_text))


def sim(rows, name=None, RPPS=None, FINESS=None):
    '''
    Finds the best match among database rows based on weighted similarity
    of name, RPPS, and FINESS identifiers.
    Args:
        rows (list): List of database records.
        name (str): Prescriber name.
        RPPS (str): RPPS number.
        FINESS (str): FINESS number.
    Returns:
        tuple: (best_match row, highest similarity score)
    '''
    weights = calculate_weights(name, RPPS, FINESS)
    highest_score = 0
    best_match = None

    for row in rows:
        db_name = f"{row.get('prenom', '')} {row.get('nom', '')}".strip()
        db_rpps = row.get('numero_rpps', '')
        db_finess = row.get('numero_finess_etablissement_juridique', '')

        total_score = 0
        max_score = 0

        if name:
            name_similarity = max(
                calculate_similarity(name, f"{row.get('prenom', '')} {row.get('nom', '')}"),
                calculate_similarity(name, f"{row.get('nom', '')} {row.get('prenom', '')}")
            )
            total_score += weights['name'] * name_similarity
            max_score += weights['name']

        if RPPS:
            rpps_similarity = calculate_similarity(RPPS, db_rpps)
            total_score += weights['rpps'] * rpps_similarity
            max_score += weights['rpps']

        if FINESS:
            finess_similarity = calculate_similarity(FINESS, db_finess)
            total_score += weights['finess'] * finess_similarity
            max_score += weights['finess']

        normalized_score = total_score / max_score if max_score > 0 else 0
        if normalized_score > highest_score:
            highest_score = normalized_score
            best_match = row

    return best_match, highest_score