
    _    ____    ___
   / \  / ___|  / _ \    __   __   ___   _ __
  / _ \ \___ \ | | | |   \ \ / /  / _ \ | '__|
 / ___ \ ___) || |_| |    \ V /  |  __/ | |
/_/   \_\____/  \___/      \_/    \___| |_|


[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)](https://fastapi.tiangolo.com)
[![Whisper](https://img.shields.io/badge/OpenAI-Whisper-412991)](https://github.com/openai/whisper)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Code style](https://img.shields.io/badge/Code%20Style-Black-000000)](https://github.com/psf/black)

Speech-to-text AI backend powered by OpenAI Whisper, FastAPI, and vector search.

**Tags:** `Python` `FastAPI` `Whisper` `STT` `FAISS` `SQLAlchemy` `Pydantic` `REST API` `Vector Search` `Docker`

---

## Overview

Vox is a speech-to-text platform that transcribes audio using OpenAI Whisper, indexes transcripts with FAISS vector search, and serves results via a FastAPI REST API. It supports real-time WebSocket streaming, user authentication, and podcast management.

---

## Features

- Audio transcription via OpenAI Whisper
- Vector similarity search with FAISS + Sentence Transformers
- User authentication (JWT, bcrypt)
- Podcast episode management
- Real-time WebSocket streaming
- Rate limiting with SlowAPI
- PostgreSQL + Redis storage
- Async test suite with pytest

---

## Quick Start

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

---

## Requirements

See [requirements.txt](requirements.txt) for the full dependency list.
