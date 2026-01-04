#!/bin/bash

# 1. Iniciar Backend en segundo plano (puerto 8000)
echo "🚀 Iniciando Backend (FastAPI) en puerto 8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# 2. Esperar unos segundos a que el backend arranque
sleep 5

# 3. Iniciar Frontend (Streamlit) en el puerto de Railway ($PORT)
echo "🚀 Iniciando Frontend (Streamlit) en puerto $PORT..."
# Forzamos API_URL local para que Streamlit (server-side) encuentre a FastAPI
export API_URL="http://127.0.0.1:8000"
streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0
