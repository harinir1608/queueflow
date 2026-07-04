# QueueFlow

A real-time, priority-based token queue management system built with Python (Flask + SocketIO) and a responsive HTML/CSS/JS frontend. Built as an internship project demonstrating core Data Structures and Algorithms (min-heap priority queue, hash maps, greedy load balancing) applied to a real-world hospital/bank-style token system.

**Live demo:** https://queueflow-9tgh.onrender.com

*(Free-tier hosting — the first request after inactivity may take 30-50 seconds to wake up.)*

## Features

- **Priority-based token queue** — Emergency > Senior > General, served in strict priority order using a min-heap
- **Real-time updates** — WebSocket (Socket.IO) sync across every open browser/device instantly, no page refresh needed
- **Public Get Token page** — anyone can request a token and pick a category
- **Public Live Queue view** — read-only waiting list + "Now Serving" board, safe to display on a waiting-room screen
- **Staff Dashboard** (password-protected) — serve the next token, mark tokens as served, per-counter view
- **Admin Analytics** (password-protected) — total served, average wait time, category distribution, live queue-length trend, per-counter performance table
- **Role separation** — public users can only request tokens; only authenticated staff can serve/manage the queue

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-SocketIO |
| Real-time transport | WebSocket via gevent-websocket |
| Frontend | HTML5, Tailwind CSS, vanilla JavaScript |
| Core algorithms | Min-heap priority queue (`heapq`), hash maps, greedy least-load counter assignment |
| Deployment | Render (free tier), Gunicorn + gevent worker |

## Project structure

```
queueflow/
├── app.py                 Flask + SocketIO server, routes, socket event handlers
├── smartqueue.py           Core DSA logic: TokenQueue class (heap, hash map, load balancer)
├── requirements.txt
├── Procfile                Gunicorn start command for deployment
└── templates/
    ├── get_token.html        Public token request page
    ├── queue.html             Public live queue display
    ├── staff_login.html       Staff authentication
    ├── staff_dashboard.html   Staff controls (Serve Next, Mark Served)
    └── admin.html             Admin analytics dashboard
```

## Data structures used

| Component | Data structure | Time complexity |
|---|---|---|
| Token scheduling | Min-heap (`heapq`) | O(log n) insert/remove |
| Token status lookup | Hash map (`dict`) | O(1) |
| Counter assignment | Greedy least-load-first | O(k), k = number of counters |

## Running locally

```bash
git clone https://github.com/harinir1608/queueflow.git
cd queueflow
pip install -r requirements.txt
python app.py
```
Visit `http://127.0.0.1:5000`

## Routes

| Route | Access | Purpose |
|---|---|---|
| `/` | Public | Request a token |
| `/queue` | Public | Live queue view (read-only) |
| `/staff` | Password-protected | Login + serve/manage tokens |
| `/admin` | Password-protected | Analytics dashboard |

## Deployment

Deployed on [Render](https://render.com) using:
```
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app --bind 0.0.0.0:$PORT
```

## Author

Harini R — Internship Project, 2026
