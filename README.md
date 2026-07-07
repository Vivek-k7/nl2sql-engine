# NL2SQL Ecommerce Analytics Engine

This project is a natural-language-to-SQL analytics app for an ecommerce PostgreSQL database built from the Olist dataset. A user asks a plain-English question, the backend selects the relevant tables, builds schema context, asks an LLM to generate SQL, executes the query safely, and returns both the SQL and result rows to a lightweight browser UI.

## Features

- Natural language analytics over ecommerce order, customer, seller, product, payment, and review data.
- LangGraph workflow for table intent detection, schema retrieval, SQL generation, execution, and retry.
- PostgreSQL schema aware prompting with join relationships, table grain notes, and business rules.
- Read-only SQL execution with single statement validation, automatic result limiting, and statement timeout.
- REST endpoint for one-shot queries and WebSocket endpoint for streamed progress updates.
- Static frontend that shows graph progress, generated SQL, results, and retry count.

## Project Structure

```text
proj/
  backend/
    app/
      api/routes.py        # FastAPI REST and WebSocket routes
      core/graph.py        # LangGraph NL2SQL workflow
      core/intent.py       # LLM table selection and relationship bridging
      core/llm.py          # SQL generation
      core/schema.py       # PostgreSQL schema context builder
      db/connector.py      # SQL cleaning, validation, execution, JSON helpers
      main.py              # FastAPI app entrypoint
    requirements.txt
    evaluation/            # Local-only evaluation assets, not committed
  frontend/
    index.html             # Static browser UI
  dataset/                 # Local Olist CSV data, ignored by git
```

## Requirements

- Python 3.11+
- PostgreSQL
- A PostgreSQL database loaded with the Olist ecommerce tables (see Dataset Setup below)
- Groq API key from [console.groq.com](https://console.groq.com)

The app expects these database tables to exist in the PostgreSQL `public` schema:

- `customers`
- `orders`
- `order_items`
- `order_payments`
- `order_reviews`
- `products`
- `sellers`
- `product_category_name_translation`
- `zip_location`

## Dataset Setup

Download the Olist Brazilian E-Commerce dataset from Kaggle:
[https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data)

Extract the CSV files and load them into a PostgreSQL database named `nl2sql_ecommerce`. The dataset contains 9 CSV files that map directly to the tables listed above.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```powershell
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DB_HOST=localhost
DB_NAME=nl2sql_ecommerce
DB_USER=postgres
DB_PASSWORD=postgres
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Adjust the database values to match your local PostgreSQL setup.

## Running The App

Start the backend from the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Open the frontend:

```text
frontend/index.html
```

The frontend connects to:

```text
ws://localhost:8000/ws/query
```

## API

### POST `/query`

Request:

```json
{
  "question": "How many orders were delivered successfully?"
}
```

Response:

```json
{
  "question": "How many orders were delivered successfully?",
  "success": true,
  "sql": "SELECT COUNT(*) AS delivered_orders FROM orders WHERE order_status = 'delivered'",
  "data": [
    {
      "delivered_orders": 96478
    }
  ],
  "error": null,
  "attempts": 1
}
```

### WebSocket `/ws/query`

Send:

```json
{
  "question": "What is the most sold product category in English by number of order items?"
}
```

The server emits:

- `accepted` when the question is received.
- `progress` after each graph node completes.
- `final` with generated SQL, result data, status, and attempts.
- `error` if validation or execution fails unexpectedly.

## How It Works

1. `intent` chooses the information-bearing tables needed for the question.
2. Relationship bridging adds join tables required to connect the selected tables.
3. `schema` reads PostgreSQL metadata and builds a constrained schema prompt.
4. `sql_gen` asks the LLM for a single PostgreSQL `SELECT` query.
5. `execute` validates and runs the SQL in a read-only transaction.
6. Failed SQL execution is fed back to the LLM for up to 3 total attempts.

## Safety Notes

The SQL executor rejects empty SQL, multiple statements, and non-`SELECT`/`WITH` statements. It also wraps unbounded queries with `LIMIT 100` and applies a 5-second PostgreSQL statement timeout.

The database connection is opened in read only mode during query execution.
