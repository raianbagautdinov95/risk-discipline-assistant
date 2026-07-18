# FastAPI Task Manager

A backend REST API for managing users, projects, and tasks.

The project demonstrates Python backend development using FastAPI, PostgreSQL, SQLAlchemy, JWT authentication, Docker, database migrations, and automated tests.

## Features

- User registration
- JWT authentication
- Current user profile
- Project creation and management
- Task creation inside projects
- Task assignment
- Task filtering by status, creator, and assignee
- Basic access control
- PostgreSQL database
- Alembic migrations
- Automated tests

## Tech Stack

- Python 3.11
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0
- Alembic
- Pydantic
- asyncpg
- JWT
- Docker
- Docker Compose
- Pytest
- HTTPX

## Project Structure

```text
fastapi-task-manager/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── projects.py
│   │       └── tasks.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── crud/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── deps.py
│   └── main.py
├── alembic/
├── tests/
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
Running with Docker

Clone the repository:

git clone https://github.com/raianbagautdinov95/fastapi-task-manager.git
cd fastapi-task-manager

Create the environment file:

cp .env.example .env

Start the application:

docker compose up --build
Database Migrations

Run migrations:

docker compose exec api alembic upgrade head

If the service in docker-compose.yml has a different name, replace api with that service name.

API Documentation

After starting the application, open:

http://127.0.0.1:8000/docs

Alternative documentation:

http://127.0.0.1:8000/redoc
Running Tests
pytest

Or inside Docker:

docker compose exec api pytest
Main API Areas
Authentication
Users
Projects
Tasks
Portfolio Purpose

This project demonstrates my ability to build structured FastAPI applications with authentication, relational database models, migrations, Docker configuration, access control, and automated tests.
