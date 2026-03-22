# Color Educational Platform - Backend API

This backend uses FastAPI, PostgreSQL, and SQLAlchemy for the login and user storage flow.

## Project Structure

```text
backend/
|-- app.py
|-- requirements.txt
|-- .env.example
|-- README.md
```

## Local Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file from `.env.example`.

3. Set the required environment variables:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname
FRONTEND_URL=http://localhost:5500
PORT=8000
```

4. Run the backend:

```bash
python -m uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

- `GET /health`
- `POST /login`
- `GET /users`
- `GET /users/{user_id}`

## Example Login Request

```json
{
  "name": "John Doe",
  "age": 20,
  "designation": "Student",
  "location": "New York",
  "email": "john@example.com"
}
```

## Render Deployment Notes

- The Render service root directory should be `backend`.
- Set `DATABASE_URL` in the Render dashboard environment variables.
- Set `FRONTEND_URL` to your deployed Netlify domain.
- The app starts with:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

## Notes

- Do not commit real database passwords or secrets to the repository.
- For production, keep `DATABASE_URL` only in your hosting provider's environment settings.
