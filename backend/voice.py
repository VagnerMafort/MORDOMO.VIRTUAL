"""
Voice Pipeline Module - Local STT (Whisper) + TTS (Piper)
100% offline, no API keys, runs on CPU.
"""
import os
import io
import wave
import tempfile
import logging
import asyncio
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice"])

# Config via env (with sensible defaults)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "int8")
PIPER_VOICE = os.environ.get("PIPER_VOICE", "pt_BR-faber-medium")
MODELS_DIR = Path(os.environ.get("VOICE_MODELS_DIR", "/app/voice_models"))
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Lazy singletons
_whisper_model = None
_piper_voice = None
_whisper_lock = asyncio.Lock()
_piper_lock = asyncio.Lock()


async def get_whisper():
    """Lazy load whisper model (singleton)."""
    global _whisper_model
    if _whisper_model is None:
        async with _whisper_lock:
            if _whisper_model is None:
                logger.info(f"Carregando Whisper {WHISPER_MODEL} ({WHISPER_COMPUTE})...")
                # Imports lazy to avoid startup overhead if voice disabled
                from faster_whisper import WhisperModel
                loop = asyncio.get_event_loop()
                _whisper_model = await loop.run_in_executor(
                    None,
                    lambda: WhisperModel(
                        WHISPER_MODEL,
                        device="cpu",
                        compute_type=WHISPER_COMPUTE,
                        download_root=str(MODELS_DIR / "whisper"),
                    ),
                )
                logger.info("Whisper carregado")
    return _whisper_model


async def get_piper():
    """Lazy load piper voice (singleton)."""
    global _piper_voice
    if _piper_voice is None:
        async with _piper_lock:
            if _piper_voice is None:
                logger.info(f"Carregando Piper {PIPER_VOICE}...")
                piper_dir = MODELS_DIR / "piper"
                piper_dir.mkdir(parents=True, exist_ok=True)
                model_path = piper_dir / f"{PIPER_VOICE}.onnx"
                config_path = piper_dir / f"{PIPER_VOICE}.onnx.json"

                # Download if missing
                if not model_path.exists() or not config_path.exists():
                    logger.info(f"Baixando voz Piper {PIPER_VOICE}...")
                    import urllib.request
                    # Huggingface direct URLs (rhasspy/piper-voices)
                    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR"
                    speaker, quality = PIPER_VOICE.replace("pt_BR-", "").split("-")
                    onnx_url = f"{base_url}/{speaker}/{quality}/{PIPER_VOICE}.onnx"
                    json_url = f"{base_url}/{speaker}/{quality}/{PIPER_VOICE}.onnx.json"
                    try:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, urllib.request.urlretrieve, onnx_url, str(model_path))
                        await loop.run_in_executor(None, urllib.request.urlretrieve, json_url, str(config_path))
                    except Exception as e:
                        logger.error(f"Falha ao baixar Piper: {e}")
                        raise HTTPException(status_code=503, detail=f"Download da voz Piper falhou: {e}")

                from piper.voice import PiperVoice
                loop = asyncio.get_event_loop()
                _piper_voice = await loop.run_in_executor(
                    None,
                    lambda: PiperVoice.load(str(model_path), config_path=str(config_path)),
                )
                logger.info("Piper carregado")
    return _piper_voice


@router.get("/status")
async def voice_status():
    """Status of voice models (loaded/not loaded)."""
    return {
        "whisper_loaded": _whisper_model is not None,
        "piper_loaded": _piper_voice is not None,
        "whisper_model": WHISPER_MODEL,
        "whisper_compute": WHISPER_COMPUTE,
        "piper_voice": PIPER_VOICE,
        "models_dir": str(MODELS_DIR),
    }


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), language: str = Query("pt")):
    """
    Transcribe uploaded audio file to text using Whisper local.
    Supports: WebM, WAV, MP3, M4A, FLAC, OGG
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")

    contents = await file.read()
    if len(contents) < 100:
        raise HTTPException(status_code=400, detail="Audio muito curto ou vazio")
    if len(contents) > 25 * 1024 * 1024:  # 25MB cap
        raise HTTPException(status_code=400, detail="Audio muito grande (>25MB)")

    # Save to temp file (whisper needs file path)
    ext = Path(file.filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        model = await get_whisper()
        loop = asyncio.get_event_loop()

        def run_transcribe():
            segments, info = model.transcribe(
                tmp_path,
                language=language if language != "auto" else None,
                beam_size=1,
                best_of=1,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,
            )
            text_parts = []
            seg_list = []
            for seg in segments:
                text_parts.append(seg.text)
                seg_list.append({"start": seg.start, "end": seg.end, "text": seg.text})
            return "".join(text_parts).strip(), info.language, info.language_probability, seg_list

        text, lang, prob, seg_list = await loop.run_in_executor(None, run_transcribe)
        return {
            "text": text,
            "language": lang,
            "language_probability": prob,
            "segments": seg_list,
        }
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@router.post("/speak")
async def speak_text(text: str = Query(..., max_length=5000)):
    """
    Synthesize text to WAV audio using Piper local.
    Returns audio/wav.
    """
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto vazio")

    voice = await get_piper()
    loop = asyncio.get_event_loop()

    def run_tts():
        buf = io.BytesIO()
        wav = wave.open(buf, "wb")
        try:
            # Piper 1.4+ usa synthesize_wav e configura o wav automaticamente
            voice.synthesize_wav(text, wav)
        finally:
            wav.close()
        buf.seek(0)
        return buf.getvalue()

    try:
        audio_bytes = await loop.run_in_executor(None, run_tts)
    except Exception as e:
        logger.error(f"Piper TTS erro: {e}")
        raise HTTPException(status_code=500, detail=f"TTS falhou: {e}")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=speech.wav"},
    )


@router.post("/warmup")
async def warmup():
    """Pre-load both models (blocks until ready). Call once after deploy."""
    await get_whisper()
    await get_piper()
    return {"status": "warmed", "whisper": True, "piper": True}
