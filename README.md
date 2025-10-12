# 🧠 Prescription Intelligence — AI-Powered Extraction & Validation

This project is a **full-stack system** that reads, extracts, and validates information from medical prescriptions using **Mistral AI** and **a public French healthcare database**.  
It performs **OCR extraction**, **LLM-based field recognition**, and **cross-matching with national RPPS/FINESS registries** to ensure medical data consistency.

---

## 🚀 Features

### 🧩 Back-End (FastAPI + Mistral AI)
- **OCR extraction** of prescription images via `mistral-ocr-latest`.
- **LLM reasoning** (`mistral-small-latest`) to structure data into:
  - Normal treatment (`Texte-soin-sans-ALD`)
  - ALD treatment (`Texte-soin-ALD`)
  - Prescriber name
  - RPPS number
  - FINESS number
  - Prescription date
- **Automatic confidence scoring** for each field (0.0 → 1.0 scale).
- **Smart database cross-matching**:
  - Verifies extracted prescriber data against a **public healthcare database** (derived from the *Annuaire Santé Français*).
  - Returns the best-matching RPPS/FINESS entries.
  - Adds descriptive confidence labels: `"Extracted from database"` or `"Not found"`.
- **Data cleaning & validation**:
  - Automatic date formatting and rejection of future dates.
  - Removal of blank or inconsistent values.

### 💻 Front-End (Angular)
- File upload (image or PDF) interface.
- Live display of:
  - Extracted prescription fields.
  - Confidence scores for each value.
  - Matched database information.
- Editable form for user verification and correction.

---

## 🧱 Project Structure

```
project/
├── back-end/
│   ├── run.py
│   ├── controllers/
│       ├── routes.py  
│   ├── services/
│   │   ├── api_utils.py          # Database connection, OCR utilities
│   │   ├── document_ai.py        # Mistral OCR + LLM extraction logic
│   ├── requirements.txt
│   └── .env                      # Mistral API key and database credentials
│
├── front-end/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Instructions

### 🧠 Back-End Setup

1. Navigate to the back-end directory:
   ```bash
   cd back-end
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file containing your **Mistral AI API key** and **database connection**:

   ```bash
   MISTRAL_API_KEY=your_mistral_api_key_here

   # Public French healthcare database (created from open data provided by the Annuaire Santé Français website)
   DB_HOST=aws-1-eu-west-3.pooler.supabase.com
   DB_PORT=5432
   DB_USER=postgres.ibjapfzjbjdmbdbnxzvf
   DB_PASSWORD=kcOi7GG9c4oPNnOm
   DB_NAME=postgres
   ```

   > ⚠️ **Note:**  
   > The database credentials are intentionally public because the dataset is extracted from the *Annuaire Santé Français*,  
   > which is an open and publicly available source.

4. Run the FastAPI back-end:
   ```bash
   python3 run.py
   ```

---

### 💻 Front-End Setup

1. Navigate to the front-end directory:
   ```bash
   cd front-end
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the front-end application:
   ```bash
   npm start
   ```

4. Access it in your browser:
   ```
   http://localhost:4200
   ```

---

## 🔄 How It Works

1. **Upload a prescription** (JPEG or PDF).  
2. **OCR extraction** using Mistral AI to read text content.  
3. **LLM-based field identification** to structure the text into medical fields.  
4. **Cross-matching** with the public database (RPPS/FINESS).  
5. **Final JSON output** includes extracted and validated data with confidence scores.

Example:
```json
{
  "prescriber_name": { "value": "Docteur Laurence Zenou", "confidence": 0.99 },
  "rpps_number": { "value": "10100721413", "confidence": 0.98 },
  "best_prescriber_name": { "value": "LAURENCE ZENOU", "confidence": "Extracted from database" }
}
```

---

## 🧪 Tech Stack

| Layer | Technology |
|-------|-------------|
| **Front-End** | Angular, TypeScript |
| **Back-End** | FastAPI (Python 3.12) |
| **AI Models** | Mistral API (`mistral-ocr-latest`, `mistral-small-latest`) |
| **Database** | PostgreSQL (Public French Healthcare Registry) |
| **Matching Algorithm** | Levenshtein similarity scoring |
| **Image Processing** | Pillow (JPEG conversion, compression) |

---

## 📋 Requirements

- Python ≥ 3.10  
- Node.js ≥ 18  
- Valid Mistral API key  

---

## 📜 License

This project uses **public open data** from the *Annuaire Santé Français*.  
The source database and its credentials are intentionally public.  
All AI and OCR components are proprietary to Mistral AI.  

© 2025 — Developed for research and educational purposes.
