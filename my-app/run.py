"""Arranque local: python run.py  ->  http://localhost:5001"""
from app import app
from config import Config

if __name__ == "__main__":
    # 127.0.0.1: solo accesible desde tu computador. El modo debug solo se activa fuera de produccion.
    app.run(host="127.0.0.1", port=Config.APP_PORT, debug=Config.DEBUG)