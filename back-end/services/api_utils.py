from dotenv import load_dotenv
from mistralai import Mistral
from PIL import Image
from datetime import datetime
import locale
import io
import os
import base64
import psycopg2
import re

# Load environment variables
load_dotenv()
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')


# ------------------------------------------
# DATE VALIDATION
# ------------------------------------------
def validate_date(date_str):
    '''
    Validates and standardizes a date string by:
    - Checking multiple common French date formats.
    - Rejecting future dates.
    Args:
        date_str (str): The date string to validate.
    Returns:
        str or None: The formatted date as 'dd/mm/YYYY' if valid, otherwise None.
    '''
    possible_formats = ["%d/%m/%Y", "%d %B %Y", "%d %b %Y"]

    for date_format in possible_formats:
        try:
            parsed_date = datetime.strptime(date_str, date_format)
            if parsed_date > datetime.now():
                return None
            return parsed_date.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


# ------------------------------------------
# MISTRAL API CONNECTION
# ------------------------------------------
def connect_api():
    '''
    Initializes a Mistral API client for OCR.
    Reads the API key from the environment variables.
    Returns:
        tuple: (client, model_name)
    Raises:
        RuntimeError: If the API key is missing or connection fails.
    '''
    try:
        mistral_api_key = os.getenv('MISTRAL_API_KEY')
        if not mistral_api_key:
            raise ValueError("Missing MISTRAL_API_KEY in environment variables.")

        client = Mistral(api_key=mistral_api_key)
        name = "Mistral OCR"
        return client, name
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Mistral API: {e}") from e


# ------------------------------------------
# IMAGE PROCESSING
# ------------------------------------------
def process_image(encoded_image):
    '''
    Decodes a Base64-encoded image, converts it to JPEG, and compresses it.
    Args:
        encoded_image (str): Base64-encoded image data.
    Returns:
        bytes: The processed JPEG image in binary form.
    '''
    image_data = base64.b64decode(encoded_image)
    image_data = convert_to_jpeg(image_data)
    image_data = compress_image(image_data)
    return image_data


def compress_image(image_data, max_size=9 * 1024 * 1024, quality=75):
    '''
    Compresses an image if its size exceeds a given threshold.
    Args:
        image_data (bytes): Binary image data.
        max_size (int): Maximum allowed size in bytes (default: 9MB).
        quality (int): JPEG compression quality (default: 75).
    Returns:
        bytes: Compressed image data.
    '''
    if len(image_data) <= max_size:
        return image_data

    image = Image.open(io.BytesIO(image_data))
    compressed_image_io = io.BytesIO()
    image.save(compressed_image_io, format="JPEG", quality=quality)
    compressed_image_data = compressed_image_io.getvalue()

    return compressed_image_data if len(compressed_image_data) < len(image_data) else image_data


def convert_to_jpeg(image_data):
    '''
    Converts an image to JPEG format if necessary.
    Args:
        image_data (bytes): Image data in any format.
    Returns:
        bytes: Image data in JPEG format.
    '''
    image = Image.open(io.BytesIO(image_data))
    if image.format == "JPEG":
        return image_data

    jpeg_image_io = io.BytesIO()
    image = image.convert("RGB")
    image.save(jpeg_image_io, format="JPEG", quality=95)
    return jpeg_image_io.getvalue()


# ------------------------------------------
# DATABASE CONNECTION AND QUERYING
# ------------------------------------------
def query_database(query, params=None):
    '''
    Executes an SQL query on the Supabase PostgreSQL database
    and returns the result as a list of dictionaries.
    Args:
        query (str): SQL query string.
        params (tuple): Query parameters (optional).
    Returns:
        list[dict]: Query results as a list of dictionaries.
    '''
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME")
        )
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                conn.commit()
                results = []
        conn.close()
        return results

    except Exception as e:
        raise RuntimeError(f"Database query failed: {e}") from e


def get_rows_by_rpps_finess_or_name(rpps_number=None, am_finess_number=None, full_name=None):
    '''
    Retrieves matching rows from the `Personne_activite` table
    based on RPPS number, FINESS number, or full name.
    Args:
        rpps_number (str): The RPPS identifier.
        am_finess_number (str): The FINESS identifier.
        full_name (str): The concatenated name of the prescriber (lowercase, no spaces).
    Returns:
        list[dict]: List of matching database records.
    '''
    if rpps_number:
        rows = query_database(
            "SELECT * FROM Personne_activite WHERE REPLACE(Numero_RPPS, ' ', '') = %s;",
            (rpps_number,)
        )
        if rows:
            return rows

    if am_finess_number:
        rows = query_database(
            """
            SELECT * FROM Personne_activite
            WHERE REPLACE(Numero_FINESS_site, ' ', '') = %s
               OR REPLACE(Numero_FINESS_etablissement_juridique, ' ', '') = %s;
            """,
            (am_finess_number, am_finess_number)
        )
        if rows:
            return rows

    if full_name:
        rows = query_database(
            """
            SELECT * FROM Personne_activite
            WHERE LOWER(REPLACE(CONCAT(prenom, nom), ' ', '')) = %s
               OR LOWER(REPLACE(CONCAT(nom, prenom), ' ', '')) = %s;
            """,
            (full_name, full_name)
        )
        return rows

    return []