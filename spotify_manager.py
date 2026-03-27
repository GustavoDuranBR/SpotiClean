# spotify_manager.py
from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from api import SpotifyHandler, SpotifyHandlerError
import logging
from config import Config  # Importe o Config
import time
from functools import wraps
import os


# Permite HTTP apenas se estiver rodando localmente (desenvolvimento)
if os.getenv('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configurar o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurando o Flask
app = Flask(__name__)
app.config.from_object(Config)  # Carrega as configurações do Config

# Definir a chave secreta para sessões Flask
app.secret_key = Config.SECRET_KEY

def get_spotify_handler():
    """Função auxiliar para obter o handler do Spotify."""
    token_info = session.get('spotify_token_info')
    if not token_info:
        return None
    sp_handler = SpotifyHandler()
    sp_handler.get_access_token()  # Método usa session internamente
    return sp_handler

def refresh_token_if_needed(sp_handler):
    """Verifica se o token está expirado e renova se necessário."""
    token_info = session.get('spotify_token_info')
    if token_info and sp_handler.sp_oauth.is_token_expired(token_info):
        try:
            token_info = sp_handler.get_access_token()  # Atualiza o token
            session['spotify_token_info'] = token_info
            logger.info("Token renovado com sucesso.")
        except SpotifyHandlerError as e:
            logger.error(f"Erro ao renovar o token: {e}")
            flash('Erro ao renovar o token do Spotify.', 'error')
            return redirect(url_for('login'))
    return token_info

@app.route('/')
def home():
    # Verifica se o usuário já tem uma sessão ativa (está logado)
    if 'spotify_token_info' in session:
        return redirect(url_for('dashboard'))
    
    # Se não estiver logado, mostra a tela de login/boas-vindas
    return render_template('login.html')

@app.route('/login')
def login():
    sp_handler = SpotifyHandler()
    auth_url = sp_handler.get_auth_url()
    return redirect(auth_url)

def is_token_expired(token_info):
    return token_info['expires_at'] < time.time()

@app.route('/callback')
def callback():
    try:
        code = request.args.get('code')
        sp_handler = SpotifyHandler()
        token_info = sp_handler.get_access_token(code=code)
        session['spotify_token_info'] = token_info
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Erro ao obter o token: {e}")
        flash('Erro ao obter o token do Spotify.', 'error')
        return redirect(url_for('home'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_info = session.get('spotify_token_info')
        if not token_info:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    sp_handler = get_spotify_handler()
    if not sp_handler:
        flash("Sessão inválida. Faça login novamente.", 'error')
        return redirect(url_for('login'))

    # Verifica e renova o token se necessário
    refresh_token_if_needed(sp_handler)

    try:
        user = sp_handler.sp.current_user()
        user_name = user.get('display_name', 'Usuário')
        user_image = user['images'][0]['url'] if user.get('images') else 'https://example.com/default-image.png'
        return render_template('dashboard.html', user_name=user_name, user_image=user_image)
    except Exception as e:
        logger.error(f"Erro ao recuperar informações do usuário: {e}")
        flash('Erro ao recuperar informações do usuário.', 'error')
        return redirect(url_for('login'))

@app.route('/voltar')
def voltar():
    return redirect(url_for('dashboard'))

@app.route('/create_playlist', methods=['GET', 'POST'])
def create_playlist():
    if request.method == 'POST':
        playlist_name = request.form.get('playlist_name')
        artist_names = request.form.get('artist_names', '').split(',')

        sp_handler = get_spotify_handler()
        if not sp_handler:
            flash("Você precisa estar logado para criar uma playlist.", 'error')
            return redirect(url_for('login'))

        try:
            sp_handler.create_playlist(playlist_name, artist_names)
            flash(f'Playlist "{playlist_name}" criada com sucesso!', 'success')
            return redirect(url_for('create_playlist'))  # Redireciona para a mesma página
        except SpotifyHandlerError as e:
            flash(str(e), 'error')
            return redirect(url_for('create_playlist'))

    return render_template('create_playlist.html')

@app.route('/view_playlists')
@app.route('/view_playlists/<int:page>')
def view_playlists(page=1):
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    try:
        # Obtendo os parâmetros de ordenação da URL
        sort = request.args.get('sort', 'name_asc')  # Padrão: ordem alfabética crescente
        limit = 10
        offset = (page - 1) * limit

        # Obtém as playlists do usuário
        playlists = sp_handler.sp.current_user_playlists(limit=limit, offset=offset)

        # Ordena as playlists com base na opção selecionada
        if sort == 'name_asc':
            playlists['items'].sort(key=lambda x: x['name'].lower())
        elif sort == 'name_desc':
            playlists['items'].sort(key=lambda x: x['name'].lower(), reverse=True)

        total_playlists = sp_handler.sp.current_user_playlists(limit=1)['total']
        total_pages = (total_playlists // limit) + (total_playlists % limit > 0)

        # Passa o parâmetro `sort` para o template
        return render_template('view_playlists.html', playlists=playlists['items'], page=page, total_pages=total_pages, sort=sort)
    except Exception as e:
        logger.error(f"Erro ao recuperar playlists do usuário: {e}")
        flash('Erro ao recuperar playlists.', 'error')
        return redirect(url_for('view_playlists'))

@app.route('/remove_selected_playlists', methods=['POST'])
def remove_selected_playlists():
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    try:
        # Obtém os IDs das playlists selecionadas
        playlist_ids = request.form.getlist('playlist_ids')

        if not playlist_ids:
            flash('Nenhuma playlist selecionada para remoção.', 'warning')
            return redirect(url_for('view_playlists'))

        # Remover cada playlist selecionada
        for playlist_id in playlist_ids:
            sp_handler.remove_playlist(playlist_id)

        flash(f'{len(playlist_ids)} playlists removidas com sucesso.', 'success')
    except Exception as e:
        app.logger.error(f'Erro ao remover playlists selecionadas: {e}')
        flash('Erro ao tentar remover playlists.', 'danger')

    return redirect(url_for('view_playlists'))

@app.route('/remove_playlist/<playlist_id>', methods=['POST'])
def remove_playlist_route(playlist_id):
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    try:
        sp_handler.remove_playlist(playlist_id)
        flash('Playlist removida com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao remover a playlist: {e}")
        flash('Erro ao remover a playlist.', 'error')

    return redirect(url_for('view_playlists'))

@app.route('/update_tracks')
def update_tracks():
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    try:
        limit = 20
        liked_tracks = sp_handler.sp.current_user_saved_tracks(limit=limit)
        return jsonify({
            'tracks': [
                {
                    'id': track['track']['id'],
                    'name': track['track']['name'],
                    'artist': track['track']['artists'][0]['name']
                }
                for track in liked_tracks['items']
            ]
        })
    except Exception as e:
        logger.error(f"Erro ao recuperar a lista de músicas: {e}")
        return jsonify({'tracks': []}), 500

@app.route('/remove_tracks_by_artist', methods=['POST'])
def remove_tracks_by_artist():
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    artist_name = request.form.get('artist_name')

    try:
        sp_handler.remove_liked_tracks(artist_list=[artist_name])
        flash(f'Músicas do artista "{artist_name}" removidas com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao remover músicas do artista: {e}")
        flash('Erro ao remover músicas do artista.', 'error')

    return redirect(url_for('liked_tracks'))

@app.route('/liked_tracks', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/liked_tracks/<int:page>', methods=['GET', 'POST'])
def liked_tracks(page):
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    limit = 200
    offset = (page - 1) * limit

    try:
        # Lidar com a remoção de músicas se o método for POST
        if request.method == 'POST':
            track_ids = request.form.getlist('track_ids')
            if track_ids:
                sp_handler.remove_liked_tracks(track_ids=track_ids)
                flash('Músicas removidas com sucesso!', 'success')
            else:
                flash('Nenhuma música selecionada para remoção.', 'warning')
            return redirect(url_for('liked_tracks', page=page))

        # Recuperar todas as músicas curtidas
        liked_tracks = sp_handler.sp.current_user_saved_tracks(limit=50)
        tracks = [
            {
                'id': track['track']['id'],
                'name': track['track']['name'],
                'artist': track['track']['artists'][0]['name'],
                'image': track['track']['album']['images'][0]['url'] if track['track']['album']['images'] else 'https://via.placeholder.com/50?text=Sem+Capa'
            } for track in liked_tracks['items']
        ]

        # Obter artista e busca da query string
        artist_query = request.args.get('artist')
        search_query = request.args.get('search')
        sort_query = request.args.get('sort')

        # Filtrar as faixas conforme o nome do artista, se fornecido
        if artist_query:
            tracks = [track for track in tracks if artist_query.lower() in track['artist'].lower()]

        # Filtrar as faixas conforme a consulta de busca, se fornecida
        if search_query:
            tracks = [track for track in tracks if search_query.lower() in track['name'].lower()]

        # Ordenar as faixas conforme a consulta de ordenação
        if sort_query == 'name_asc':
            tracks.sort(key=lambda x: x['name'])
        elif sort_query == 'name_desc':
            tracks.sort(key=lambda x: x['name'], reverse=True)

        # Paginar resultados
        total_tracks = len(tracks)
        total_pages = (total_tracks // limit) + (total_tracks % limit > 0)

        # Retornar a template com as faixas
        return render_template('liked_tracks.html', tracks=tracks[offset:offset + limit], page=page, total_pages=total_pages)
    except Exception as e:
        logger.error(f"Erro ao recuperar faixas curtidas: {e}")
        flash('Erro ao recuperar faixas.', 'error')
        return redirect(url_for('liked_tracks', page=1))

@app.route('/liked_artists', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/liked_artists/<int:page>', methods=['GET', 'POST'])
def liked_artists_view(page):
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    limit = 50  # Número máximo de artistas por página

    try:
        # Lidar com a remoção de artistas se o método for POST
        if request.method == 'POST':
            selected_artist_ids = request.form.getlist('artist_ids')
            if selected_artist_ids:
                try:
                    # Chamada correta para remover artistas
                    sp_handler.unfollow_artists(selected_artist_ids)  # Use o método da classe
                    flash('Artistas removidos com sucesso!', 'success')
                except SpotifyHandlerError as e:
                    logger.error(f"Erro ao remover artistas: {e}")
                    flash('Erro ao remover artistas.', 'error')
            else:
                flash('Nenhum artista selecionado para remoção.', 'warning')
            return redirect(url_for('liked_artists_view', page=page))

        # Obter artistas curtidos da API do Spotify
        liked_artists_data = sp_handler.sp.current_user_followed_artists(limit=limit)
        liked_artists = liked_artists_data['artists']['items']

        # Calcular o total de artistas
        total_artists_count = liked_artists_data['artists']['total']
        total_pages = (total_artists_count // limit) + (total_artists_count % limit > 0)

        # Filtrar artistas com base na busca
        artist_search = request.args.get('artist', '').strip()
        if artist_search:
            liked_artists = [
                artist for artist in liked_artists
                if artist_search.lower() in artist['name'].lower()  # Filtrar pelos nomes dos artistas
            ]

        # Lógica de ordenação
        sort_option = request.args.get('sort')
        if sort_option:
            if sort_option == 'name_asc':
                liked_artists.sort(key=lambda artist: artist['name'])  # Ordenar por nome A-Z
            elif sort_option == 'name_desc':
                liked_artists.sort(key=lambda artist: artist['name'], reverse=True)  # Z-A

        return render_template('liked_artists.html', artists=liked_artists, page=page, total_pages=total_pages)

    except SpotifyHandlerError as e:
        logger.error(f"Erro ao recuperar artistas curtidos: {e}")
        flash('Erro ao recuperar artistas curtidos.', 'error')
        return redirect(url_for('dashboard'))

    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        flash('Erro inesperado ao recuperar artistas curtidos.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/logout', methods=['POST'])
def logout():
    spotify_handler = SpotifyHandler()
    spotify_handler.logout()  # Limpa o arquivo .cache
    
    session.clear()  # Garante que a sessão inteira do Flask seja esvaziada
    
    flash('Você foi desconectado com sucesso!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
