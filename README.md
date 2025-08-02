
# primetimepix
updated pick em application to include other major sports 


# PrimeTimePix

A multi-sport pick'em app for NFL and NBA — designed for league creation, user picks, standings, and a sleek FanDuel-style UI.

## 🚀 Getting Started

1. **Clone the repo**

```bash
git clone <repo-url>
cd primetimepix
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate
```

3. **Install requirements**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
```

5. **Run migrations and create superuser**

```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Run the server**

```bash
python manage.py runserver
```

---

## 🧱 Project Structure

- `apps/games/` – Game models, fetchers for NFL/NBA
- `apps/picks/` – Picks, scores, leaderboard logic
- `apps/users/` – Custom user model and profile logic
- `apps/leagues/` *(coming soon)* – League creation & invites
- `primetimepix/` – Django project config

---

## 🛠️ Coming Soon

- Docker + Celery support
- Tailwind + HTMX UI
- REST API endpoints for mobile apps
>>>>>>> 9983ce6 (Initial commit)
