import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import requests
import base64
from dotenv import load_dotenv

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
        self.scope = "user-library-read user-library-modify playlist-modify-public"
        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = None

    def get_auth_url(self):
        return self.sp_oauth.get_authorize_url()

    def get_access_token(self, code):
        try:
            token_info = self.sp_oauth.get_access_token(code)
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            return token_info
        except Exception as e:
            raise SpotifyHandlerError(f"Erro ao obter o token de acesso: {e}")

    def revoke_token(self, access_token):
        """Revoga o token de acesso do Spotify."""
        try:
            revoke_url = "https://accounts.spotify.com/api/token/revoke"
            headers = {
                "Authorization": f"Basic {self._get_basic_auth()}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "token": access_token
            }
            response = requests.post(revoke_url, headers=headers, data=data)
            response.raise_for_status()
        except requests.RequestException as e:
            raise SpotifyHandlerError(f"Erro ao revogar o token: {e}")

    def _get_basic_auth(self):
        return base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

    def create_playlist(self, playlist_name, artist_list):
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")
        if not playlist_name or not artist_list:
            raise SpotifyHandlerError("Nome da playlist e lista de artistas são obrigatórios")

        track_ids = []
        try:
            user_id = self.sp.me()["id"]

            for artist_name in artist_list:
                artist_name = artist_name.strip()  # Remove espaços em branco
                
                # Buscar o artista pelo nome
                artist_search = self.sp.search(q=f'artist:"{artist_name}"', type="artist", limit=1)
                print(f"Busca para artista '{artist_name}': {artist_search}")

                if artist_search['artists']['items']:
                    artist_id = artist_search['artists']['items'][0]['id']
                    # Buscar as músicas mais tocadas desse artista
                    results = self.sp.artist_top_tracks(artist_id)

                    print(f"Músicas encontradas para '{artist_name}': {[track['name'] for track in results['tracks']]}")

                    # Adiciona os IDs das músicas mais tocadas
                    track_ids.extend([track["id"] for track in results['tracks'] if track["id"]])
                else:
                    raise SpotifyHandlerError(f"Artista '{artist_name}' não encontrado.")

            track_ids = list(set(track_ids))  # Remove IDs duplicados

            if track_ids:
                # Criar a playlist e adicionar as músicas
                playlist = self.sp.user_playlist_create(user_id, playlist_name)
                self.sp.user_playlist_add_tracks(user_id, playlist["id"], track_ids)
                print(f'Playlist "{playlist_name}" criada com {len(track_ids)} músicas.')
            else:
                raise SpotifyHandlerError("Nenhuma música encontrada para adicionar à playlist.")

        except Exception as e:
            raise SpotifyHandlerError(f"Erro ao criar a playlist: {e}")

    def remove_playlist(self, playlist_id):
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")

        try:
            user_id = self.sp.me()["id"]
            self.sp.user_playlist_unfollow(user_id, playlist_id)
            print(f'Playlist com ID {playlist_id} removida com sucesso.')
        except Exception as e:
            raise SpotifyHandlerError(f"Erro ao remover a playlist: {e}")

    def remove_liked_tracks(self, track_ids=None, artist_list=None):
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")

        try:
            if track_ids:
                self.sp.current_user_saved_tracks_delete(tracks=track_ids)
            elif artist_list:
                for artist in artist_list:
                    results = self.sp.search(q=f"artist:{artist}", type="track", limit=50)
                    track_ids = [track["id"] for track in results['tracks']['items']]
                    if track_ids:
                        self.sp.current_user_saved_tracks_delete(tracks=track_ids)
            else:
                results = self.sp.current_user_saved_tracks(limit=50)
                track_ids = [item['track']['id'] for item in results['items']]
                if track_ids:
                    self.sp.current_user_saved_tracks_delete(tracks=track_ids)
        except Exception as e:
            raise SpotifyHandlerError(f"Erro ao remover músicas curtidas: {e}")

    def get_liked_tracks(self, limit=50, offset=0):
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")

        try:
            liked_tracks = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            if not liked_tracks['items']:
                raise SpotifyHandlerError("Nenhuma música curtida encontrada.")
            return liked_tracks
        except Exception as e:
            raise SpotifyHandlerError(f"Erro ao obter músicas curtidas: {e}")

    def get_user_info(self):
        """Retorna informações do usuário logado."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")
        return self.sp.me()

    def get_recommended_tracks(self, limit=5):
        """Obtém músicas recomendadas com base nas músicas curtidas do usuário."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")
        recommendations = self.sp.recommendations(seed_genres=['pop'], limit=limit)
        return recommendations['tracks']

    def get_recommended_artists(self, limit=5):
        """Obtém artistas recomendados com base nas músicas curtidas do usuário."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")
        top_artists = self.sp.current_user_top_artists(limit=limit)
        return top_artists['items']

    def get_recent_activity(self, limit=5):
        """Obtém atividade recente do usuário (últimas músicas ouvidas)."""
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")
        recent_tracks = self.sp.current_user_recently_played(limit=limit)
        return recent_tracks['items']

    def buscar_musicas_por_artista(self, artist_name):
            """Busca músicas de um artista pelo nome."""
            if not self.sp:
                raise SpotifyHandlerError("Spotify client is not authenticated")
            
            try:
                results = self.sp.search(q=f'artist:"{artist_name}"', type='track', limit=5)
                tracks = results['tracks']['items']

                if not tracks:
                    return None  # Nenhuma música encontrada
                return tracks
            except Exception as e:
                raise SpotifyHandlerError(f"Erro ao buscar músicas do artista '{artist_name}': {e}")
            
    def get_user_playlists(self, limit=50, offset=0):
        if not self.sp:
            raise SpotifyHandlerError("Spotify client is not authenticated")

        try:
            playlists = self.sp.current_user_playlists(limit=limit, offset=offset)
            return playlists
        except Exception as e:
            raise SpotifyHandlerError(f"Erro ao obter playlists: {e}")

