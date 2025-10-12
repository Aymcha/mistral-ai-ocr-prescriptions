from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from services import document_ai, api_utils

router = APIRouter(tags=["OCR"])

@router.post("/sendImage")
async def send_image(request: Request):
    try:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")

        content_type = request.headers.get("content-type", "")

        if content_type.startswith("text") or content_type == "application/octet-stream":
            raw_data = body.decode("utf-8")

            if raw_data.startswith("data:image/"):
                header, encoded = raw_data.split(",", 1)
                image_data = api_utils.process_image(encoded)
                ocr_text = document_ai.mistral_ocr_extract(image_data)
                query_responses = document_ai.extract_query_responses(ocr_text)
                ordonnance = document_ai.format_response_to_ordonnance(query_responses)
                return JSONResponse(content=ordonnance, status_code=200)
            else:
                raise HTTPException(status_code=400, detail="Invalid file type. Please upload a valid image.")
        
        else:
            raise HTTPException(status_code=415, detail="Unsupported Content-Type")

    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))