# FlashCart — Concurrency-Safe Flash Sale Checkout

A mini eCommerce system built to solve a real, well-known problem in backend engineering: preventing overselling during high-demand flash sales, when many users try to buy limited stock at the exact same moment.

## Table of Contents

- [The Problem](#the-problem)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Key Technical Decision](#key-technical-decision)
- [API Endpoints](#api-endpoints)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Production-Style Deployment](#production-style-deployment-nginx--gunicorn)
- [What This Project Demonstrates](#what-this-project-demonstrates)
- [Future Improvements](#future-improvements)

## The Problem

During a flash sale, if 50 people try to buy the last unit of a product at the same second, a naive system can let multiple people "successfully" buy the same item. This happens because each request reads the current stock count, sees it's available, and decrements it — all without knowing that another request is doing the exact same thing at the exact same time. This is a classic race condition, and it is a real problem that large-scale eCommerce platforms (including Amazon, Flipkart, and ticket-booking systems) have to solve carefully at scale.

Most beginner eCommerce projects skip this problem entirely by testing purchases one at a time, sequentially. FlashCart specifically targets this gap: it is built and tested under genuine concurrent load, using database-level row locking to guarantee correctness even when many requests arrive simultaneously.

## How It Works

- Django + PostgreSQL — the backend uses select_for_update() inside a database transaction to lock a product's row the moment a purchase request reads it. If two requests arrive at nearly the same instant, the second one must wait until the first transaction completes before it can even read the stock value, which eliminates the race condition entirely at the database level rather than relying on fragile application-level checks.
- Django Channels + WebSockets — every connected client receives live stock updates the instant a purchase happens, without needing to refresh the page or poll the server repeatedly.
- Next.js frontend — a simple, clean product page showing live stock count and a Buy Now button, wired to both the REST API for purchases and the WebSocket connection for live updates.
- Daphne (ASGI server) — serves both regular HTTP requests and WebSocket connections from the same Django app during development.
- Gunicorn + Nginx — for a production-style deployment, Gunicorn runs Django as a proper WSGI process, and Nginx sits in front as a reverse proxy, exactly how a real production system would be structured.

## Architecture

    Browser (Next.js frontend)
            |
            |  HTTP POST /api/buy/1/          WebSocket ws/stock/1/
            v                                          ^
    Nginx (reverse proxy, port 80)                      |
            |                                          |
            v                                          |
    Gunicorn (WSGI, port 8000)  <----------->  Daphne (ASGI, WebSockets)
            |
            v
    Django application layer
            |
            v
    PostgreSQL (row-level locking via select_for_update)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Django |
| Database | PostgreSQL |
| Real-time updates | Django Channels (WebSockets) |
| ASGI server | Daphne |
| Production WSGI server | Gunicorn |
| Reverse proxy | Nginx |
| Frontend | Next.js (React) |
| Styling | Tailwind CSS |
| Testing | Django's built-in test framework |

## Project Structure

    flashcart/
    ├── backend/
    │   ├── core/              Django project settings, ASGI/WSGI config
    │   ├── sales/              Main app
    │   │   ├── models.py       Product, Order models
    │   │   ├── views.py        /buy endpoint with locking logic
    │   │   ├── consumers.py    WebSocket consumer for live stock updates
    │   │   ├── routing.py      WebSocket URL routing
    │   │   └── tests.py        Concurrency and correctness tests
    │   ├── requirements.txt
    │   ├── .env.example
    │   └── manage.py
    ├── frontend/
    │   └── app/
    │       └── page.tsx        Product page: live stock and buy button
    └── README.md

## Key Technical Decision

The core of this project is a single line:

    product = get_object_or_404(
        Product.objects.select_for_update(), id=product_id
    )

select_for_update() locks the product's database row for the duration of the transaction. Without it, two simultaneous requests could both read the same stock value (say, "1 left"), both decrement it, and both succeed — resulting in an oversold item, which is exactly the bug that real flash sale systems must avoid. With it, requests are safely serialized at the database level, so only as many purchases succeed as there is actual stock, no matter how many requests arrive at once.

This was verified directly, not just assumed: automated tests (see Testing section) confirm that with 1 unit of stock and 5 simultaneous purchase attempts, exactly 1 order succeeds and stock never goes negative.

## API Endpoints

### POST /api/buy/<product_id>/

Attempts to purchase one unit of the given product.

Success response (200):

    {
      "success": true,
      "message": "Purchase successful",
      "remaining_stock": 4
    }

Sold out response (400):

    {
      "success": false,
      "message": "Sold out"
    }

### WS /ws/stock/<product_id>/

WebSocket endpoint. Sends a message to all connected clients whenever stock changes:

    {
      "remaining_stock": 4
    }

## Running Locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL

### Backend

    cd backend
    python -m venv venv
    source venv/bin/activate        # Linux/Mac
    venv\Scripts\activate           # Windows
    pip install -r requirements.txt

Create a .env file in backend/ (see .env.example) with your PostgreSQL credentials, then:

    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

### Frontend

    cd frontend
    npm install
    npm run dev

Visit http://localhost:3000 to view the product page, and http://127.0.0.1:8000/admin to manage products via Django admin.

## Testing

Automated tests cover the core correctness guarantees of this project:

    python manage.py test sales

Tests include:

- A successful purchase correctly decrements stock by 1
- A purchase attempt on a sold-out product correctly fails with "Sold out"
- Stock never goes negative even after repeated purchase attempts
- With exactly 1 unit in stock, exactly 1 order succeeds even across multiple concurrent attempts

## Production-Style Deployment (Nginx + Gunicorn)

Beyond local development, this project was also deployed using a genuine production-style stack inside a Linux environment (Ubuntu via WSL), to demonstrate the full architecture end-to-end rather than relying only on Django's development server.

- Gunicorn serves the Django app as a WSGI process
- Nginx sits in front of Gunicorn as a reverse proxy, handling incoming requests on port 80 and forwarding them internally to Gunicorn on port 8000
- PostgreSQL runs natively in the Linux environment
- The /buy endpoint, including the concurrency-safe stock locking, was tested and confirmed working through the full chain: Nginx to Gunicorn to Django to PostgreSQL

Deployment commands:

    sudo apt install nginx
    pip install gunicorn
    gunicorn core.wsgi:application --bind 0.0.0.0:8000

Nginx reverse proxy config (/etc/nginx/sites-available/flashcart):

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

This confirms the project runs correctly behind a real reverse proxy and production WSGI server, exactly how it would be deployed in practice, rather than only working on a development server.

## What This Project Demonstrates

- Handling race conditions correctly at the database level, not just with application-level checks, which are insufficient under real concurrency
- Real-time communication via WebSockets, rather than inefficient polling
- A production-style backend architecture: ASGI and WSGI servers, reverse proxy configuration, and proper environment-based configuration
- Relational data modeling with PostgreSQL
- Automated testing of the core correctness guarantees, not just manual spot-checks
- Full-stack deployment in a real Linux environment, not just a description of how it would theoretically work

## Future Improvements

- Move CHANNEL_LAYERS from in-memory to Redis-backed, so live updates work correctly across multiple server instances for real horizontal scaling
- Add user authentication so orders are tied to actual accounts rather than anonymous requests
- Add a "reserved for 5 minutes" hold mechanic, similar to seat-booking systems, instead of an immediate all-or-nothing purchase
- Deploy to a live public environment with a real domain and HTTPS
- Add rate limiting to prevent abuse of the buy endpoint

## License

This project was built as a learning exercise to demonstrate backend concurrency handling and full-stack deployment practices.

## Live Demo

This project can be exposed publicly on demand using ngrok, tunneling through the full Nginx + Gunicorn + Django + PostgreSQL stack running locally. Since this relies on a local machine staying online, it is demoed live rather than hosted at a permanent URL. Available on request for a live walkthrough.
