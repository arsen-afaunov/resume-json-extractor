#!/usr/bin/env python3
"""
FastAPI сервис для генерации резюме.
"""

from fastapi import FastAPI

app = FastAPI(title="Resume Generator API")


@app.get("/health")
def health_check():
    """Проверка работоспособности."""
    return {"status": "ok"}


@app.post("/generate")
def generate_resume():
    """Генерация резюме (заглушка)."""
    return {"message": "Resume generation endpoint (TODO)"}
