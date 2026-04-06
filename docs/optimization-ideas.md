# Идеи оптимизации генерации резюме

## Дата: 31 марта 2025

---

## Идея 1: Map-Reduce для LLM (параллельная генерация блоков)

### Концепция
Основная идея - решать задачу индуктивно, решая частные подзадачи параллельно и затем собирая частные результаты в единый общий.

### Архитектура
1. **Первая LLM** разбирает входящий текст на семантические блоки и отдает их отдельными генерациями по мере готовности
2. **Бэкенд** передает их второй LLM, которая уже генерирует готовый блок итогового JSON (например объект под ключом `salary`)
3. **Сборка** - эти блоки собираются в единый JSON

### Плюсы
- **Параллелизм** - если несколько GPU/инстансов Ollama, блоки генерируются одновременно
- **Специализация** - разные модели под разные задачи (дешёвая для черновика, дорогая для полировки)
- **Отказоустойчивость** - упал один блок → перегенерировали только его, не всё резюме
- **Модульность** - легче тестировать `salary` отдельно от `experience`

### Минусы
- **Потеря контекста** - блок `salary` не знает о `experience`, может нарушиться логика ("зарплата соответствует опыту")
- **Накладные расходы** - сериализация/десериализация между LLM, round-trip по сети
- **Сложность** - нужен оркестратор, retry-логика, сборка результата
- **Для qwen2.5:3b** - модель маленькая, инференс и так быстрый (~10 сек), разбиение не ускорит

### Когда полезно
- Большие тексты (100+ страниц) - не влезают в контекстное окно
- Независимые секции - генерация 1000 товаров для каталога
- Разные модели - одна для структуры (GPT-4), другая для текста (локальная)

---

## Идея 2: Гибридный подход (NLP + LLM)

### Концепция
Использовать традиционный NLP для формирования семантических кластеров перед генерацией.

### Архитектура
```
Входной текст
    ↓
[SBERT] → векторы предложений
    ↓
Сравнение с центроидами (experience, skills, salary...)
    ↓
Кластеры: {experience: ["5 лет...", "в Яндексе..."], skills: ["Python...", "Docker..."]}
    ↓
Параллельно в LLM (каждый с подсхемой):
  - generate(experience_cluster, experience_schema)
  - generate(skills_cluster, skills_schema)
    ↓
Сборка в единый JSON
```

### Реализация
```python
from sentence_transformers import SentenceTransformer

# 1. Центроиды (взвешенные фразы)
CENTROIDS = {
    "experience": ["работал", "опыт", "компания", "проект", "должность"],
    "skills": ["знаю", "умею", "python", "docker", "стек"],
    "salary": ["зарплата", "оклад", "ожидания", "доход"],
    "expectations": ["ищу", "хочу", "удаленка", "офис", "гибкий"]
}

# 2. Векторизация
model = SentenceTransformer('all-MiniLM-L6-v2')
text_vectors = model.encode(sentences)
centroid_vectors = model.encode([" ".join(words) for words in CENTROIDS.values()])

# 3. Кластеризация по близости
clusters = {}
for sent, vec in zip(sentences, text_vectors):
    similarities = cosine_similarity([vec], centroid_vectors)
    best_cluster = list(CENTROIDS.keys())[argmax(similarities)]
    clusters[best_cluster].append(sent)
```

### Плюсы
- ✅ Точная сегментация (не теряем контекст)
- ✅ Можно использовать очень дешёвую модель для кластеризации (MiniLM)
- ✅ Параллелизм сохраняется
- ✅ Каждый блок получает только релевантный текст (экономия токенов)

### Минусы
- ❌ Зависимость от качества центроидов (ручная работа)
- ❌ Новая зависимость `sentence-transformers` (~400MB модель)
- ❌ Усложнение архитектуры (нужен сервис кластеризации)
- ❌ Граничные случаи: предложение относится к двум кластерам?

---

## Идея 3: Самообучающиеся центроиды (векторная БД + feedback loop)

### Концепция
Сохранять результаты генерации в векторную БД и итеративно улучшать центроиды на основе успешных примеров.

### Выбор векторной БД

| БД | Плюсы | Минусы | Рекомендация |
|---|---|---|---|
| **Chroma** | Простая, локальная, Python-native | Только локально | Для прототипов |
| **pgvector** | Расширение PostgreSQL (уже используем!) | Нужна настройка индексов | ⭐ Для нашего проекта |
| **Qdrant** | Быстрая, хорошая документация | Отдельный сервис | Для highload |
| **Pinecone** | Облачная, managed | Платная | Для production |

**Выбор:** `pgvector` - минимум инфраструктуры, раз у нас уже PostgreSQL.

### Схема данных

```sql
-- Расширение для PostgreSQL
CREATE EXTENSION IF NOT EXISTS vector;

-- Таблица для векторов
CREATE TABLE resume_embeddings (
    id SERIAL PRIMARY KEY,
    input_text TEXT,                    -- исходный текст от пользователя
    input_vector vector(384),           -- SBERT-эмбеддинг входа
    resume_vector vector(384),          -- эмбеддинг сгенерированного резюме
    cluster_label VARCHAR(50),          -- к какому кластеру отнесли
    centroid_similarity FLOAT,          -- косинусная близость к центроиду
    generation_success BOOLEAN,         -- успешно ли сгенерировалось
    user_feedback JSONB,               -- {"rating": 5, "corrections": {...}}
    centroid_version INTEGER,          -- версия набора центроидов
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индекс для быстрого поиска похожих
CREATE INDEX ON resume_embeddings USING ivfflat (input_vector vector_cosine_ops);
```

### Итеративное улучшение центроидов

#### 1. Анализ "провальных" кластеров
```python
# Находим центроиды с низкой успешностью
query = """
SELECT 
    cluster_label,
    AVG(centroid_similarity) as avg_sim,
    COUNT(*) FILTER (WHERE generation_success) * 1.0 / COUNT(*) as success_rate
FROM resume_embeddings
WHERE centroid_version = 1
GROUP BY cluster_label
HAVING success_rate < 0.7;
"""
problematic_clusters = db.execute(query)
```

#### 2. Обогащение центроидов из успешных примеров
```python
# Берём успешные примеры и обновляем центроиды
successful_experience = db.query("""
    SELECT input_text, centroid_similarity 
    FROM resume_embeddings 
    WHERE cluster_label = 'experience' 
      AND generation_success = true
      AND centroid_version = 1
    ORDER BY centroid_similarity DESC
    LIMIT 100
""")

# Обновляем центроид (усреднение векторов с взвешиванием)
vectors = [model.encode(text) for text in successful_experience]
weights = [sim for sim in similarities]
new_centroid = np.average(vectors, axis=0, weights=weights)

# Сохраняем как версию 2
CENTROIDS_V2["experience"] = new_centroid
save_centroid_version(2, CENTROIDS_V2)
```

#### 3. A/B тестирование версий центроидов
```python
import random

# При запросе случайно выбираем версию
version = random.choice([1, 2])  # 50/50
clusters = cluster_with_version(text, version=version)

# Сохраняем с меткой версии
save_to_db(..., centroid_version=version)

# Потом анализируем какая версия лучше
compare_versions(v1_success_rate, v2_success_rate)
```

#### 4. Поиск похожих примеров (RAG-подход)
```python
# При новом запросе ищем похожие успешные примеры
query_vector = model.encode(new_input)

similar_examples = db.query("""
    SELECT input_text, resume_json, user_feedback
    FROM resume_embeddings
    WHERE cluster_label = 'experience'
      AND generation_success = true
    ORDER BY input_vector <-> %s  -- косинусное расстояние
    LIMIT 5;
""", query_vector)

# Добавляем в контекст LLM как few-shot examples
enhanced_prompt = f"""
Вот похожие успешные примеры:
{similar_examples}

Сгенерируй резюме для нового текста:
{new_input}
"""
```

### Плюсы
- ✅ Центроиды улучшаются автоматически на реальных данных
- ✅ Можно делать A/B тесты разных подходов
- ✅ RAG-подход улучшает качество через few-shot learning
- ✅ pgvector не требует новой инфраструктуры

### Минусы
- ❌ Нужно накопить достаточно данных для обучения (холодный старт)
- ❌ Усложняется логика (версионирование, миграции центроидов)
- ❌ Нужен механизм сбора обратной связи от пользователей

---

## Выводы и рекомендации

### Этапы реализации

**MVP (v1)**
- Базовая монолитная версия: текст целиком → LLM
- Простая PostgreSQL без pgvector

**v2 (оптимизация)**
- Гибридный подход с кластеризацией (NLP + LLM)
- Статические центроиды, подобранные вручную

**v3 (самообучение)**
- Добавляем pgvector в PostgreSQL
- Сбор feedback от пользователей
- Автоматическое улучшение центроидов на основе успешных генераций
- A/B тестирование версий

### Архитектурный подход

```
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│   Cluster    │  →   │     LLM      │  →   │   PostgreSQL     │
│   Service    │      │   (Ollama)   │      │  + pgvector      │
│              │      │              │      │                  │
│ - SBERT      │      │ - Генерация  │      │ - Резюме         │
│ - Центроиды  │      │ - Кластеры   │      │ - Векторы        │
│ - Поиск      │      │              │      │ - Feedback       │
│   похожих    │      │              │      │ - Версии         │
└──────────────┘      └──────────────┘      └──────────────────┘
       ↑                                              │
       └────────────── Обновление центроидов ←────────┘
```

Это позволяет:
1. Начать просто (v1)
2. Добавить кластеризацию (v2)
3. Достичь самообучающейся системы (v3)
