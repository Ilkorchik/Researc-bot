# Water Research Agent — бот для поиска научных статей

Учебный проект для задания №2:

> Поиск и сбор работ о влиянии диссоциации/рекомбинации молекул воды на процессы переноса в ЭМС; нужны теоретические и экспериментальные работы, их анализ, перевод, саммари, DOI и ссылки.

## Что умеет бот

- принимает научный запрос в Telegram;
- ищет публикации в:
  - **arXiv** — через публичный API;
  - **Scopus** — через Elsevier Scopus Search API, если задан `SCOPUS_API_KEY`;
  - **Web of Science** — через Clarivate Web of Science API, если задан `WOS_API_KEY`;
  - **eLIBRARY** — формирует ссылку на поиск;
- объединяет результаты и удаляет простые дубликаты по DOI/заголовку;
- показывает DOI, авторов, год, источник и ссылки;
- по `/analyze <номер>` делает саммари, научный разбор и перевод;
- по `/export` сохраняет результаты в CSV.

## Ограничения

Нельзя гарантировать «все статьи»: базы данных имеют разные индексы, лимиты, подписки и правила доступа. Scopus и Web of Science требуют соответствующих API-доступов. Полные тексты автоматически не скачиваются из закрытых источников.

## Установка

Нужен Python 3.11+.

```bash
git clone https://github.com/Ilkorchik/Researc-bot.git
cd Researc-bot

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Настройка

Скопируйте `.env.example` в `.env` и заполните доступные ключи:

```env
TELEGRAM_BOT_TOKEN=...

OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5

SCOPUS_API_KEY=...
WOS_API_KEY=...

MAX_RESULTS_PER_SOURCE=10
REQUEST_TIMEOUT=30
```

**Не публикуйте `.env` и API-ключи на GitHub.**

## Запуск

```bash
python app.py
```

## Команды

- `/start` — инструкция;
- `/search <запрос>` — поиск;
- `/results` — последние результаты;
- `/analyze <номер>` — саммари, анализ и перевод;
- `/export` — CSV последнего поиска;
- `/help` — справка.

Можно просто отправить боту текстовый запрос, например:

```text
влияние диссоциации и рекомбинации молекул воды на процессы переноса в ЭМС
```

## Архитектура

```text
Telegram
   |
   v
app.py
   |
   v
Search Service
   |-------- arXiv API
   |-------- Scopus API
   |-------- Web of Science API
   `-------- eLIBRARY search
   |
   v
Deduplication
   |
   +---- results / CSV
   |
   `---- OpenAI
          |-- summary
          |-- scientific analysis
          `-- Russian translation
```

## Структура

```text
.
├── app.py
├── config.py
├── models.py
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── dbs/
│   ├── arxiv.py
│   ├── scopus.py
│   ├── wos.py
│   └── elibrary.py
├── services/
│   ├── search.py
│   ├── llm.py
│   └── export.py
└── tests/
    └── test_models.py
```
