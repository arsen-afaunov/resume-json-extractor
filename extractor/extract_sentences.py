#!/usr/bin/env python3
"""
Разбиение текста на сырые чанки с помощью RecursiveCharacterTextSplitter.
"""

import asyncio
import re

from fastapi.concurrency import run_in_threadpool
from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=80,
    chunk_overlap=0,
    separators=["\n\n", "\n", r"(?<=[.!?])\s+", ",", " ", ""],
    is_separator_regex=True,
)


def _clean_chunk(chunk: str) -> str | None:
    step1 = chunk.strip()
    step2 = step1.replace("\u00A0", " ")
    step3 = re.sub(r"\s+", " ", step2)
    step4 = re.sub(r"^[-•*→–—]\s+", "", step3)
    if len(step4) >= 2 and any(c.isalnum() for c in step4):
        return step4
    return None


async def extract_raw_chunks(text: str) -> list[str]:
    """Разбивает текст на сырые чанки с пост-очисткой."""
    raw_chunks = await run_in_threadpool(_splitter.split_text, text)
    cleaned = [_clean_chunk(c) for c in raw_chunks]
    return [c for c in cleaned if c is not None]


async def main():
    """Точка входа."""
    sample_text = """
    Меня зовут Иван Петров. Я работаю Python-разработчиком уже 5 лет.
    Сначала работал в Яндексе, потом перешёл в Тинькофф. 
    Мои основные навыки: Python, FastAPI, Docker и PostgreSQL.
    Ищу удалённую работу с зарплатой от 300 тысяч рублей.
    """
    
    print("Исходный текст:")
    print(sample_text)
    print("\n" + "=" * 50 + "\n")
    
    chunks = await extract_raw_chunks(sample_text)
    
    print(f"Найдено чанков: {len(chunks)}\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"{i}. {chunk}")


if __name__ == "__main__":
    asyncio.run(main())
