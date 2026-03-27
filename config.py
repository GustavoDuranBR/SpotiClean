import os
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis do .env

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")  # Chave secreta do Flask
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")  # ID do cliente Spotify
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")  # Segredo do cliente Spotify
    REDIRECT_URI = os.getenv("REDIRECT_URI")  # URI de redirecionamento
