# api.py
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import base64
import logging
from config import Config  
from flask import session, redirect, url_for
import requests
from spotipy.cache_handler import FlaskSessionCacheHandler

# Configuração do logger
logger = logging.getLogger(__name__)

class SpotifyHandlerError(Exception):
    """Classe de exceção personalizada para erros do SpotifyHandler."""
    pass

class SpotifyHandler:
    def __init__(self):
        self.scope = "user-library-read user-library-modify playlist-modify-public user-follow-read user-follow-modify"
        
        # Cria um gerenciador de cache isolado para cada usuário usando a sessão do Flask
        cache_handler = FlaskSessionCacheHandler(session)

        self.sp_oauth = SpotifyOAuth(
            client_id=Config.SPOTIFY_CLIENT_ID,
            client_secret=Config.SPOTIFY_CLIENT_SECRET,
            redirect_uri=Config.REDIRECT_URI,
            scope=self.scope,
            show_dialog=True,
            cache_handler=cache_handler  # O Spotipy agora respeita a individualidade dos usuários
        )
        self.sp = None

    def get_auth_url(self):
        """Retorna a URL de autorização do Spotify."""
        return self.sp_oauth.get_authorize_url()

    def get_access_token(self, code=None):
        """Obtém e renova o token de acesso usando o código de autenticação ou refresh_token."""
        try:
            if code:
                token_info = self.sp_oauth.get_access_token(code=code)
            else:
                token_info = session.get('spotify_token_info')
                if token_info and self.sp_oauth.is_token_expired(token_info):
                    token_info = self.sp_oauth.refresh_access_token(token_info['refresh_token'])

            # Armazenar o token renovado ou obtido na sessão
            session['spotify_token_info'] = token_info
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            return token_info
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao obter ou renovar o token de acesso: {e}")
            raise SpotifyHandlerError(f"Erro ao obter ou renovar o token de acesso: {e}")

    def is_authenticated(self):
        """Verifica se o usuário está autenticado."""
        return 'spotify_token_info' in session and self.sp is not None

    def logout(self):
        """Remove a instância do cliente Spotify."""
        self.sp = None
        session.clear() # Limpa o cookie do navegador do usuário

    def create_playlist(self, playlist_name, artist_list):
        """Cria uma playlist no Spotify baseada em uma lista de artistas."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")

        if not playlist_name or not artist_list:
            raise SpotifyHandlerError("Nome da playlist e lista de artistas são obrigatórios")

        track_ids = []
        try:
            user_id = self.sp.me()["id"]

            for artist_name in artist_list:
                artist_search = self.sp.search(q=f'artist:"{artist_name.strip()}"', type="artist", limit=1)
                if artist_search['artists']['items']:
                    artist_id = artist_search['artists']['items'][0]['id']
                    results = self.sp.artist_top_tracks(artist_id)
                    track_ids.extend([track["id"] for track in results['tracks']])
                else:
                    logger.warning(f"Artista '{artist_name}' não encontrado.")

            track_ids = list(set(track_ids))
            if track_ids:
                playlist = self.sp.user_playlist_create(user_id, playlist_name)
                self.sp.user_playlist_add_tracks(user_id, playlist["id"], track_ids)
                logger.info(f'Playlist "{playlist_name}" criada com {len(track_ids)} músicas.')
            else:
                raise SpotifyHandlerError("Nenhuma música encontrada para adicionar à playlist.")
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao criar a playlist: {e}")
            raise SpotifyHandlerError(f"Erro ao criar a playlist: {e}")

    def remove_playlist(self, playlist_id):
        """Remove uma playlist do usuário."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")
        try:
            user_id = self.sp.me()["id"]
            self.sp.user_playlist_unfollow(user_id, playlist_id)
            logger.info(f'Playlist com ID {playlist_id} removida com sucesso.')
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao remover a playlist: {e}")
            raise SpotifyHandlerError(f"Erro ao remover a playlist: {e}")

    def remove_liked_tracks(self, track_ids=None, artist_list=None):
        """Remove músicas curtidas do usuário, com base em IDs de faixas ou artistas."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")

        try:
            if track_ids:
                self.sp.current_user_saved_tracks_delete(tracks=track_ids)
            elif artist_list:
                for artist in artist_list:
                    results = self.sp.search(q=f"artist:{artist}", type="track", limit=50)
                    tracks = results['tracks']['items']
                    if tracks:
                        track_ids = [track["id"] for track in tracks]
                        self.sp.current_user_saved_tracks_delete(tracks=track_ids)
                    else:
                        logger.warning(f"Nenhuma música encontrada para o artista: {artist}")
            else:
                results = self.sp.current_user_saved_tracks(limit=50)
                track_ids = [item['track']['id'] for item in results['items']]
                if track_ids:
                    self.sp.current_user_saved_tracks_delete(tracks=track_ids)
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao remover músicas curtidas: {e}")
            raise SpotifyHandlerError(f"Erro ao remover músicas curtidas: {e}")

    def get_liked_tracks(self, limit=50, offset=0):
        """Obtém as músicas curtidas pelo usuário."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")

        try:
            liked_tracks = self.sp.current_user_saved_tracks(limit=limit, offset=offset)

            if not liked_tracks['items']:
                logger.info("Nenhuma música curtida encontrada.")
                return []

            # Formatar o retorno
            tracks = []
            for item in liked_tracks['items']:
                track_info = item['track']
                tracks.append({
                    'title': track_info['name'],
                    'artist': ', '.join(artist['name'] for artist in track_info['artists'])
                })

            return tracks
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao obter músicas curtidas: {e}")
            raise SpotifyHandlerError(f"Erro ao obter músicas curtidas: {e}")

    def get_user_info(self):
        """Retorna informações do usuário logado."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")
        return self.sp.me()

    def get_recommended_tracks(self, limit=5):
        """Obtém músicas recomendadas com base nas músicas curtidas pelo usuário."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")
        try:
            recommendations = self.sp.recommendations(seed_genres=['pop'], limit=limit)
            return recommendations['tracks']
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao obter músicas recomendadas: {e}")
            raise SpotifyHandlerError(f"Erro ao obter músicas recomendadas: {e}")

    def get_liked_artists(self, limit=50, offset=0):
        """Retorna uma lista de artistas cujas músicas estão entre as faixas curtidas pelo usuário."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")

        try:
            liked_tracks = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            artists = set()

            if not liked_tracks['items']:
                logger.info("Nenhuma música curtida encontrada.")
                return []

            for item in liked_tracks['items']:
                track = item.get('track')
                if track:
                    for artist in track.get('artists', []):
                        artists.add(artist['name'])

            if not artists:
                logger.info("Nenhum artista encontrado entre as músicas curtidas.")
                return []

            return list(artists)

        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao obter artistas curtidos: {e}")
            raise SpotifyHandlerError(f"Erro ao obter artistas curtidos: {e}")

    def get_user_playlists(self, limit=50, offset=0):
        """Retorna as playlists do usuário."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")
        try:
            playlists = self.sp.current_user_playlists(limit=limit, offset=offset)
            return playlists['items']
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao obter playlists: {e}")
            raise SpotifyHandlerError(f"Erro ao obter playlists: {e}")

    def unfollow_artists(self, artist_ids):
        """Desfazer o follow em uma lista de artistas."""
        if not self.is_authenticated():
            raise SpotifyHandlerError("Usuário não está autenticado. Faça login para continuar.")
        if not artist_ids:
            raise SpotifyHandlerError("Nenhum ID de artista fornecido")

        try:
            self.sp.user_unfollow_artists(artist_ids)
            logger.info(f'Artistas com IDs {artist_ids} foram desfavoritados com sucesso.')
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro ao desfazer o follow nos artistas: {e}")
            raise SpotifyHandlerError(f"Erro ao desfazer o follow nos artistas: {e}")

    def revoke_token(self):
        """Revoga o token de acesso do usuário no Spotify."""
        token_info = session.get('spotify_token_info')
        if token_info:
            client_id = Config.SPOTIFY_CLIENT_ID
            client_secret = Config.SPOTIFY_CLIENT_SECRET
            token = token_info['access_token']

            # Verificar se client_id e client_secret estão definidos
            if not client_id or not client_secret:
                logger.error("Client ID ou Client Secret não estão definidos.")
                return

            # Montando o cabeçalho de autenticação
            auth_str = f"{client_id}:{client_secret}"
            b64_auth_str = base64.b64encode(auth_str.encode()).decode()
            headers = {
                'Authorization': f'Basic {b64_auth_str}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            data = {'token': token}

            logger.info(f"Revogando o token: {token}")
            logger.info(f"Headers: {headers}")
            logger.info(f"Data: {data}")

            # Fazendo a requisição para revogar o token
            response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)

            logger.info("Response content: %s", response.text)

            if response.status_code == 200:
                logger.info("Token revogado com sucesso.")
                session.clear()  # Limpa a sessão após revogar o token
            else:
                try:
                    error_response = response.json()
                    error_message = error_response.get('error', 'Erro desconhecido')
                except ValueError:
                    error_message = response.text
                logger.error(f"Erro ao revogar token: {response.status_code} - {error_message}")
        else:
            logger.warning("Nenhum token encontrado para revogar.")
