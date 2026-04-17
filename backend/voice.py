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

# Lazy singletons — cache multi-voice
_whisper_model = None
_piper_voices = {}  # voice_name -> PiperVoice
_whisper_lock = asyncio.Lock()
_piper_lock = asyncio.Lock()

# Catálogo de vozes PT-BR disponíveis (baixadas sob demanda do HuggingFace rhasspy/piper-voices)
AVAILABLE_VOICES = [
    {"id": "pt_BR-faber-medium", "name": "Faber (masc.)", "gender": "M", "quality": "medium", "default": True},
    {"id": "pt_BR-edresson-low", "name": "Edresson (masc.)", "gender": "M", "quality": "low"},
    {"id": "pt_BR-cadu-medium", "name": "Cadu (masc.)", "gender": "M", "quality": "medium"},
    {"id": "pt_BR-jeff-medium", "name": "Jeff (masc.)", "gender": "M", "quality": "medium"},
]


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


async def get_piper(voice_name: str = None):
    """Lazy load piper voice (por nome). Retorna PiperVoice singleton cacheado."""
    vname = voice_name or PIPER_VOICE
    if vname in _piper_voices:
        return _piper_voices[vname]
    async with _piper_lock:
        if vname in _piper_voices:
            return _piper_voices[vname]
        logger.info(f"Carregando Piper {vname}...")
        piper_dir = MODELS_DIR / "piper"
        piper_dir.mkdir(parents=True, exist_ok=True)
        model_path = piper_dir / f"{vname}.onnx"
        config_path = piper_dir / f"{vname}.onnx.json"
        if not model_path.exists() or not config_path.exists():
            logger.info(f"Baixando voz Piper {vname}...")
            import urllib.request
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR"
            try:
                speaker, quality = vname.replace("pt_BR-", "").split("-")
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Voz '{vname}' não reconhecida")
            onnx_url = f"{base_url}/{speaker}/{quality}/{vname}.onnx"
            json_url = f"{base_url}/{speaker}/{quality}/{vname}.onnx.json"
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, urllib.request.urlretrieve, onnx_url, str(model_path))
                await loop.run_in_executor(None, urllib.request.urlretrieve, json_url, str(config_path))
            except Exception as e:
                logger.error(f"Falha ao baixar Piper {vname}: {e}")
                raise HTTPException(status_code=503, detail=f"Download falhou: {e}")
        from piper.voice import PiperVoice
        loop = asyncio.get_event_loop()
        v = await loop.run_in_executor(None, lambda: PiperVoice.load(str(model_path), config_path=str(config_path)))
        _piper_voices[vname] = v
        logger.info(f"Piper {vname} carregado")
        return v


@router.get("/status")
async def voice_status():
    """Status of voice models (loaded/not loaded)."""
    return {
        "whisper_loaded": _whisper_model is not None,
        "piper_loaded": len(_piper_voices) > 0,
        "piper_loaded_voices": list(_piper_voices.keys()),
        "whisper_model": WHISPER_MODEL,
        "whisper_compute": WHISPER_COMPUTE,
        "piper_voice_default": PIPER_VOICE,
        "models_dir": str(MODELS_DIR),
    }


@router.get("/voices")
async def list_voices():
    """Lista vozes Piper disponíveis para seleção."""
    return {"voices": AVAILABLE_VOICES, "default": PIPER_VOICE}


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
async def speak_text(text: str = Query(..., max_length=5000), voice: str = Query(None), speed: float = Query(1.0, ge=0.5, le=2.0)):
    """
    Synthesize text to WAV audio using Piper local.
    - voice: id da voz (opcional, default do env)
    - speed: 0.5 (lenta) a 2.0 (rápida), default 1.0
    """
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto vazio")

    piper_voice = await get_piper(voice)
    loop = asyncio.get_event_loop()

    def run_tts():
        buf = io.BytesIO()
        wav = wave.open(buf, "wb")
        try:
            from piper.config import SynthesisConfig
            # length_scale inverso à velocidade: speed=2 → length_scale=0.5
            length_scale = max(0.5, min(2.0, 1.0 / speed))
            cfg = SynthesisConfig(length_scale=length_scale, noise_scale=0.667, noise_w_scale=0.8)
            piper_voice.synthesize_wav(text, wav, syn_config=cfg)
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
