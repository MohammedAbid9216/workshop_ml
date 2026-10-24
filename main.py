import time
import uuid
import json
from typing import Literal
import os 
import sys 
import uvicorn 
from fastapi import FastAPI, Form, Request 
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from booking.routes import router as booking_router
from sanjeevani.api.auth import router as sanjeevani_auth_router
from sanjeevani.api.appointments import router as sanjeevani_appointments_router
from sanjeevani.routes import router as sanjeevani_page_router

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
from fastapi.staticfiles import StaticFiles 
from fastapi.templating import Jinja2Templates 
from src.exception import CustomException 
from src.logger import get_logger 
logger = get_logger(__name__) 
from src.pipeline.predict_pipeline import CustomData, PredictPipeline

from nlp_pretrained.ner_tagger import(get_pos_tags , extract_entities) 
from nlp_pretrained.embedding import (most_similar_words) 
from nlp_pretrained.sentiment_analyzer import analyze_sentiment 




import os 
import sys 
import uvicorn 
from fastapi import FastAPI, Form, Request 
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles 
from fastapi.templating import Jinja2Templates 
from src.exception import CustomException 
from src.logger import get_logger 
logger = get_logger(__name__) 
from src.pipeline.predict_pipeline import CustomData, PredictPipeline

from nlp_pretrained.ner_tagger import(get_pos_tags , extract_entities) 
from nlp_pretrained.embedding import (most_similar_words) 
from nlp_pretrained.sentiment_analyzer import analyze_sentiment 

from rag.rag_pipeline import RAGPipeline 

app= FastAPI(title="Covid Prediction Clinic")
app.include_router(booking_router)
app.include_router(sanjeevani_page_router)
app.include_router(sanjeevani_auth_router)
app.include_router(sanjeevani_appointments_router)

class PerformanceMetric(BaseModel):
    # Strict allowlist: no patient text or arbitrary log fields.
    stage: Literal[
        "stt_to_final_transcript_ms",
        "api_fetch_ms",
        "tts_start_delay_ms",
        "tts_speech_ms",
        "tts_error_ms",
    ]
    duration_ms: float = Field(ge=0, le=120000)


@app.post("/api/performance", status_code=204)
async def log_performance_metric(payload: PerformanceMetric):
    logger.info(
        "CAREMIND_PERF stage=%s duration_ms=%.2f",
        payload.stage,
        payload.duration_ms,
    )
    return Response(status_code=204) 

##mouting the css file 
app.mount("/static", StaticFiles(directory="static"), name="static") 

##Set the template folder 
templates = Jinja2Templates(directory="templates") 

@app.get("/", response_class=HTMLResponse) 
async def home(request:Request):
    logger.info("Home page accessed...") 
    return templates.TemplateResponse(request, "index.html") 

@app.get("/predict", response_class=HTMLResponse)
async def predict_form(request: Request):
    logger.info("Predict form page accessed.....") 
    return templates.TemplateResponse(request, "predict.html", {"result":None}) 

@app.post("/predict", response_class=HTMLResponse)
async def predict_result(
    request: Request,
    age:int = Form(...),
    gender: str = Form(...),
    fever: float = Form(...),
    cough: str = Form(...),
    city: str = Form(...) 
) :
    try:
        logger.info(f"Prediction request received :: age{age}, gender{gender}, fever{fever}, cough{cough},city{city}")
        custom_data = CustomData(age=age,gender=gender,fever=fever,cough=cough,city=city)
        data_df = custom_data.get_data_as_dataframe() 
        predict_pipeline = PredictPipeline() 
        result , probability = predict_pipeline.predict(data_df) 
        return templates.TemplateResponse(
            request,
            "predict.html",
            {
                "result": result,
                "probability":probability,
                "form_data": {
                    "age":age,
                    "gender":gender,
                    "fever":fever,
                    "cough":cough,
                    "city":city
                }
            }
        )
    except Exception as e:
        raise CustomException(e,sys) 

@app.get("/health")
async def health_check():
    logger.info("Monitering alert....")
    return {"status":"ok"}


### NLP Pretrained 

@app.get("/pretrained-nlp" , response_class=HTMLResponse) 
async def pretrained_nlp_form(request: Request):
    return templates.TemplateResponse(request, 
                                      "pretrained_nlp.html",
                                      {
                                          "result": None,

                                          "form_data": {
                                              "query": ""
                                          },
                                          "error": None 
                                      })

@app.post("/pretrained-nlp" , response_class=HTMLResponse) 
async def pretrained_nlp_analysis(
    request: Request,
    query: str= Form(...)
):
    try:
        ## text clean 
        query = query.strip() 
        if not query:
            return templates.TemplateResponse(
                request,
                "pretrained_nlp.html",
                {
                    "result": None,
                    "form_data": {
                        "query": ""
                    },
                    "error": "Please enter some text..." 
                }
            )

        ## Pos tagging 
        pos_tags = get_pos_tags(query) 

        ## NER 
        entities = extract_entities(query) 

        ## Sentiment Analysis 
        sentiment = analyze_sentiment(query) 

        ## Word Embeddings 
        similar_words = [] 
        words = query.split() 
        first_word = words[0].lower() 
        if words:
            try:
                similar_words = most_similar_words(first_word , topn=5) 
            except Exception as e :
                logger.warning(f"Glove similarity failed for: " , {first_word} ,"and the error is:", {e}) 
                similar_words = [] 
        ## final result 
        result = {
            "query": query,
            "pos_tags": pos_tags,
            "entities": entities,
            "similar_words": similar_words,
            "sentiment": sentiment
        }
        ##render result 
        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": result,
                "form_data": {
                    "query": query
                },
                "error": None
            }
        )



    except Exception as e :
        logger.info("Error occured in pretrained nlp analysis")
        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": None,
                "form_data": {
                    "query": query
                },
                "error": str(e)
            }
        )
     



###RAG Pipeline 
rag_pipeline = RAGPipeline() 

@app.get("/ask", response_class=HTMLResponse)
async def clinic_assistant_form(request:Request):
    logger.info("Clinic assistant(RAG) FORM page accessed...") 
    return templates.TemplateResponse(request, "clinic_assistant.html", {"result":None}) 

@app.post("/ask", response_class=HTMLResponse)
async def clinic_assitant_answer(request:Request, question:str=Form(...)):
    logger.info(f"Clinic assistant questino received: '{question}' ") 
    try:
        result = rag_pipeline.answer(question) 
        return templates.TemplateResponse(
            request,
            "clinic_assistant.html",
            {"result":result, 
             "form_data": {"question":question}, "error":None} 
        )
    except Exception as e:
        raise CustomException(e,sys) 




@app.post("/api/ask")
async def clinic_assistant_api(question: str = Form(...)):
    request_started = time.perf_counter()
    try:
        result = rag_pipeline.answer(question)
        logger.info("PERF stage=api_rag_work_ms duration_ms=%.2f", (time.perf_counter() - request_started) * 1000)
        return JSONResponse(content={
            "answer": str(result.get("answer", "")),
            "sources": result.get("sources", []),
            "retrieved_chunks": result.get("retrieved_chunks", [])
        })
    except Exception:
        logger.exception("RAG API request failed")
        return JSONResponse(
            status_code=500,
            content={"detail": "RAG request failed. Check server logs."}
        )


@app.post("/api/ask/stream")
async def clinic_assistant_api_stream(question: str = Form(...)):
    """Stream token events as NDJSON, followed by source metadata."""
    request_id = uuid.uuid4().hex[:12]
    def emit(event: dict) -> str:
        return json.dumps(event, ensure_ascii=False) + "\n"

    def stream_events():
        request_started = time.perf_counter()
        try:
            clean_question = question.strip()
            if not clean_question:
                yield emit({"type": "token", "text": "Please enter a question.", "request_id": request_id})
                yield emit({"type": "done", "sources": [], "retrieved_chunks": [], "request_id": request_id})
                return

            retrieval_started = time.perf_counter()
            chunks = rag_pipeline.retriever.retrieve(clean_question)
            logger.info("PERF request_id=%s stage=retrieval duration_ms=%.2f",
                        request_id, (time.perf_counter() - retrieval_started) * 1000)
            if not isinstance(chunks, list):
                chunks = []

            for piece in rag_pipeline.generator.generate_stream(
                clean_question, chunks, request_id=request_id
            ):
                if piece:
                    yield emit({"type": "token", "text": piece, "request_id": request_id})

            sources = sorted({chunk["source"] for chunk in chunks
                              if isinstance(chunk, dict) and chunk.get("source")})
            total_ms = (time.perf_counter() - request_started) * 1000
            logger.info("PERF request_id=%s stage=backend_total duration_ms=%.2f status=success",
                        request_id, total_ms)
            yield emit({"type": "done", "sources": sources,
                        "retrieved_chunks": chunks, "request_id": request_id,
                        "backend_total_ms": round(total_ms, 2)})
        except Exception:
            logger.exception("Streaming RAG API request failed request_id=%s", request_id)
            yield emit({"type": "error", "request_id": request_id, "message":
                        "The clinic AI could not complete this request. Please try again."})

    return StreamingResponse(
        stream_events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform",
                 "X-Accel-Buffering": "no", "X-Request-ID": request_id},
    )


class VoiceRequest(BaseModel):
    text: str


@app.post("/api/voice")
async def caremind_voice(payload: VoiceRequest):
    """Convert an existing CareMind answer to MP3 audio."""
    text = payload.text.strip()

    if not text:
        return JSONResponse(status_code=400, content={"detail": "Text is required."})
    if len(text) > 4000:
        return JSONResponse(
            status_code=413,
            content={"detail": "Text is too long for one voice request (maximum 4000 characters)."},
        )

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        return JSONResponse(
            status_code=503,
            content={"detail": "ElevenLabs credentials are not configured on the server."},
        )

    try:
        client = ElevenLabs(api_key=api_key)
        audio_chunks = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_chunks)
        if not audio_bytes:
            raise RuntimeError("ElevenLabs returned empty audio.")
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-store"},
        )
    except Exception:
        logger.exception("CareMind ElevenLabs TTS request failed")
        return JSONResponse(
            status_code=502,
            content={"detail": "Voice generation failed. Check server logs and ElevenLabs configuration."},
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 

