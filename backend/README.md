# GenericWeb

A full-stack web application with React frontend and Django backend.

## Project Structure

```
GenericWeb/
├── frontend/          # React + TypeScript + Vite frontend
├── backend/           # Django REST API backend
└── README.md          # This file
```

## Setup Instructions

### Prerequisites
- Node.js (v18 or higher)
- Python (v3.8 or higher)
- pip

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The frontend will be available at http://localhost:5173

### Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp  .env
python manage.py migrate

## in another terminal: 
in backend/generic3:
ngrok http 8001

python manage.py runserver 0.0.0.0:8001
```
The backend will be available at http://localhost:8001

### Full Development Setup
You can run both frontend and backend simultaneously:

```bash
# Terminal 1 - Backend
cd backend && python manage.py runserver

# Terminal 2 - Frontend  
cd frontend && npm run dev
```

## Environment Variables

### Frontend (.env in frontend/)
- API endpoints and frontend-specific configuration

### Backend (.env in backend/)
- Django settings, database configuration, secret keys
- Copy from `.env.example` and update values

## Deployment

[Need to add deployment instructions when ready]

## Contributing

[Need to add contributing guidelines when ready]
