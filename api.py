import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import requests
import base64
from dotenv import load_dotenv
import logging

# Configurar logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("spotify_app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class SpotifyHandlerError(Exception):
    """Classe de exceção personalizada para erros do SpotifyHandler."""
    pass

class SpotifyHandler:
    def __init__(self):
        self.client_id = os.getenv('SPOTIPY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('REDIRECT_URI')
        self.scope = "user-library-read user-library-modify playlist-modify-public user-follow-read user-follow-modify"  # Inclua o escopo necessário
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = None

    def get_auth_url(self):
        """Retorna a URL de autorização do Spotify."""
        return self.sp_oauth.get_authorize_url()

    def get_access_token(self, code):
        """Obtém o token de acesso do Spotify usando o código de autenticação."""
        try:
            token_info = self.sp_oauth.get_access_token(code)
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            return token_info
        except Exception as e:
            logger.error(f"Erro ao obter o token de acesso: {e}")
            raise SpotifyHandlerError(f"Erro ao obter o token de acesso: {e}")

    def revoke_token(self, access_token):
        """Revoga o token de acesso do Spotify."""
        try:
            revoke_url = "https://accounts.spotify.com/api/token/revoke"
            headers = {
                "Authorization": f"Basic {self._get_basic_auth()}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {"token": access_token}
            response = requests.post(revoke_url, headers=headers, data=data)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Erro ao revogar o token: {e}")
            raise SpotifyHandlerError(f"Erro ao revogar o token: {e}")

    def _get_basic_auth(self):
        """Codifica as credenciais client_id e client_secret em Base64."""
        return base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

    def create_playlist(self, playlist_name, artist_list):
        """Cria uma playlist no Spotify baseada em uma lista de artistas."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")
        if not playlist_name or not artist_list:
            raise SpotifyHandlerError("Nome da playlist e lista de artistas são obrigatórios")

        track_ids = []
        try:
            user_id = self.sp.me()["id"]

            for artist_name in artist_list:
                artist_name = artist_name.strip()
                
                # Buscar o artista pelo nome
                artist_search = self.sp.search(q=f'artist:"{artist_name}"', type="artist", limit=1)
                if artist_search['artists']['items']:
                    artist_id = artist_search['artists']['items'][0]['id']
                    # Buscar as músicas mais tocadas desse artista
                    results = self.sp.artist_top_tracks(artist_id)
                    track_ids.extend([track["id"] for track in results['tracks'] if track["id"]])
                else:
                    logger.warning(f"Artista '{artist_name}' não encontrado.")

            track_ids = list(set(track_ids))  # Remove duplicatas
            if track_ids:
                # Criar a playlist e adicionar as músicas
                playlist = self.sp.user_playlist_create(user_id, playlist_name)
                self.sp.user_playlist_add_tracks(user_id, playlist["id"], track_ids)
                logger.info(f'Playlist "{playlist_name}" criada com {len(track_ids)} músicas.')
            else:
                raise SpotifyHandlerError("Nenhuma música encontrada para adicionar à playlist.")

        except Exception as e:
            logger.error(f"Erro ao criar a playlist: {e}")
            raise SpotifyHandlerError(f"Erro ao criar a playlist: {e}")

    def remove_playlist(self, playlist_id):
        """Remove uma playlist do usuário."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")
        try:
            user_id = self.sp.me()["id"]
            self.sp.user_playlist_unfollow(user_id, playlist_id)
            logger.info(f'Playlist com ID {playlist_id} removida com sucesso.')
        except Exception as e:
            logger.error(f"Erro ao remover a playlist: {e}")
            raise SpotifyHandlerError(f"Erro ao remover a playlist: {e}")

    def remove_liked_tracks(self, track_ids=None, artist_list=None):
        """Remove músicas curtidas do usuário, com base em IDs de faixas ou artistas."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")

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
        except Exception as e:
            logger.error(f"Erro ao remover músicas curtidas: {e}")
            raise SpotifyHandlerError(f"Erro ao remover músicas curtidas: {e}")

    def get_liked_tracks(self, limit=50, offset=0):
        """Obtém as músicas curtidas pelo usuário."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")

        try:
            liked_tracks = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            
            if not liked_tracks['items']:
                raise SpotifyHandlerError("Nenhuma música curtida encontrada.")
            
            # Formatar o retorno
            tracks = []
            for item in liked_tracks['items']:
                track_info = item['track']
                tracks.append({
                    'title': track_info['name'],  # Nome da música
                    'artist': ', '.join(artist['name'] for artist in track_info['artists'])  # Nome(s) do(s) artista(s)
                })
            
            return tracks  # Retorna a lista de músicas formatada
        except Exception as e:
            logger.error(f"Erro ao obter músicas curtidas: {e}")
            raise SpotifyHandlerError(f"Erro ao obter músicas curtidas: {e}")

    def get_user_info(self):
        """Retorna informações do usuário logado.""" 
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")
        return self.sp.me()

    def get_recommended_tracks(self, limit=5):
        """Obtém músicas recomendadas com base nas músicas curtidas pelo usuário.""" 
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")
        recommendations = self.sp.recommendations(seed_genres=['pop'], limit=limit)
        return recommendations['tracks']

    def get_liked_artists(self, limit=50, offset=0):
        """Retorna uma lista de artistas cujas músicas estão entre as faixas curtidas pelo usuário.""" 
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")

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
            logger.error(f"Erro específico do Spotify: {e}")
            raise SpotifyHandlerError(f"Erro ao obter artistas curtidos: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise SpotifyHandlerError(f"Erro ao obter artistas curtidos: {e}")

    def get_user_playlists(self, limit=50, offset=0):
        """Retorna as playlists do usuário.""" 
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")
        try:
            playlists = self.sp.current_user_playlists(limit=limit, offset=offset)
            return playlists['items']
        except Exception as e:
            logger.error(f"Erro ao obter playlists: {e}")
            raise SpotifyHandlerError(f"Erro ao obter playlists: {e}")

    def unfollow_artists(self, artist_ids):
        """Desfazer o follow em uma lista de artistas."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client não está autenticado")
        if not artist_ids:
            raise SpotifyHandlerError("Nenhum ID de artista fornecido")

        try:
            # Use o método correto para desfazer o follow
            self.sp.user_unfollow_artists(artist_ids)  
            logger.info(f'Artistas com IDs {artist_ids} foram desfavoritados com sucesso.')
        except Exception as e:
            logger.error(f"Erro ao desfazer o follow nos artistas: {e}")
            raise SpotifyHandlerError(f"Erro ao desfazer o follow nos artistas: {e}")


