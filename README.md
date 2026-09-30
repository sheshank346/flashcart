

\## Key Technical Decision



The core of this project is a single line:



```python

product = get\_object\_or\_404(

&#x20;   Product.objects.select\_for\_update(), id=product\_id

)

```



`select\_for\_update()` locks the product's database row for the duration of the transaction. Without it, two simultaneous requests could both read the same stock value (say, "1 left"), both decrement it, and both succeed — resulting in an oversold item. With it, requests are safely serialized at the database level, so only as many purchases succeed as there is actual stock.



\## API Endpoints



\### `POST /api/buy/<product\_id>/`



Attempts to purchase one unit of the given product.



\*\*Success response (200):\*\*

```json

{

&#x20; "success": true,

&#x20; "message": "Purchase successful",

&#x20; "remaining\_stock": 4

}

```



\*\*Sold out response (400):\*\*

```json

{

&#x20; "success": false,

&#x20; "message": "Sold out"

}

```



\### `WS /ws/stock/<product\_id>/`



WebSocket endpoint. Sends a message to all connected clients whenever stock changes:



```json

{

&#x20; "remaining\_stock": 4

}

```



\## Running Locally



\### Prerequisites



\- Python 3.10+

\- Node.js 18+

\- PostgreSQL



\### Backend



```bash

cd backend

python -m venv venv

venv\\Scripts\\activate          # Windows

pip install -r requirements.txt

```



Create a `.env` file in `backend/` (see `.env.example`) with your PostgreSQL credentials, then:



```bash

python manage.py migrate

python manage.py createsuperuser

python manage.py runserver

```



\### Frontend



```bash

cd frontend

npm install

npm run dev

```



Visit `http://localhost:3000` to view the product page, and `http://127.0.0.1:8000/admin` to manage products via Django admin.



\## Demo



Two browser tabs hitting "Buy Now" on the last unit in stock — only one succeeds, the other is correctly told the item is sold out, with live stock updates reflected instantly on both screens without a refresh.



\## What This Project Demonstrates



\- Handling race conditions correctly at the database level (not just application-level checks, which are insufficient under concurrency)

\- Real-time communication via WebSockets, not polling

\- A production-style backend architecture (ASGI server, proper environment-based configuration, relational data modeling)



\## Future Improvements



\- Move `CHANNEL\_LAYERS` from in-memory to Redis-backed, so live updates work correctly across multiple server instances (needed for real horizontal scaling)

\- Add Nginx as a reverse proxy in front of Gunicorn/Daphne for production deployment

\- Add user authentication so orders are tied to actual accounts, not anonymous requests

\- Add a "reserved for 5 minutes" hold mechanic (like seat booking systems) instead of an immediate all-or-nothing purchase

\- Deploy to a live environment (Render/Railway for backend, Vercel for frontend)

