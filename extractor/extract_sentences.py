#!/usr/bin/env python3
"""
Тестовый скрипт для разбиения текста на предложения с помощью razdel.
"""

from razdel import sentenize


def extract_sentences(text: str) -> list[str]:
    """Разбивает текст на предложения."""
    return [sent.text for sent in sentenize(text)]


def main():
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
    
    sentences = extract_sentences(sample_text)
    
    print(f"Найдено предложений: {len(sentences)}\n")
    for i, sent in enumerate(sentences, 1):
        print(f"{i}. {sent}")


if __name__ == "__main__":
    main()
