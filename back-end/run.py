import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers import routes
from services.api_utils import connect_api

app = FastAPI(title="Mistral OCR API", debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client, name = connect_api()
app.state.DOCUMENT_AI_CLIENT = client
app.state.DOCUMENT_AI_NAME = name

app.include_router(routes.router)

if __name__ == "__main__":
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True,)