#!/usr/bin/env python3
"""
Тестовый скрипт для проверки скорости генерации Ollama.
Делает запрос к API и выводит время выполнения.
"""

import json
import time
import httpx
import os

OLLAMA_HOST = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_URL = f"{OLLAMA_HOST}/api/generate"
MODEL = "qwen2.5:3b"
SCHEMA_FILE = "resume_schema.json"


def load_schema():
    """Загружает JSON-схему резюме из файла."""
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_resume(schema: dict) -> dict:
    """Делает запрос к Ollama для генерации резюме."""
    prompt = """Создай резюме на основе следующих данных:
    
Имя: Иван Петров
Должность: Senior Python Developer
Описание опыта: 5 лет разработки на Python, работал в компаниях Яндекс и Тинькофф. Основные достижения: оптимизировал производительность сервиса на 40%, внедрил микросервисную архитектуру. Навыки: Python, FastAPI, Docker, PostgreSQL, Kafka.
Ожидания: Ищу работу в продуктовой компании с интересными задачами, удаленный формат или офис в Москве.

Сгенерируй структурированное резюме в формате JSON согласно предоставленной схеме."""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "format": schema,
        "stream": False
    }

    print("Sending request to Ollama...")
    start_time = time.time()
    
    response = httpx.post(OLLAMA_URL, json=payload, timeout=120.0)
    response.raise_for_status()
    
    elapsed = time.time() - start_time
    
    result = response.json()
    return result, elapsed


def main():
    """Точка входа."""
    schema = load_schema()
    print(f"Loaded schema: {SCHEMA_FILE}")
    print(f"Model: {MODEL}")
    print()
    
    result, elapsed = generate_resume(schema)
    
    print(f"Generation time: {elapsed:.2f} seconds")
    print()
    print("Generated resume:")
    # Ollama returns JSON string in 'response' field
    resume_data = json.loads(result["response"])
    print(json.dumps(resume_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
