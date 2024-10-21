from flask import Flask, render_template, redirect, request, session, url_for, flash, jsonify
from api import SpotifyHandler, SpotifyHandlerError
import os
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # Defina uma chave secreta para a sessão

def get_spotify_handler():
    """Função auxiliar para obter o handler do Spotify."""
    token_info = session.get('token_info')
    if not token_info:
        return None
    sp_handler = SpotifyHandler()
    sp_handler.get_access_token(token_info['access_token'])
    return sp_handler

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login')
def login():
    sp_handler = SpotifyHandler()
    auth_url = sp_handler.get_auth_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    try:
        code = request.args.get('code')
        sp_handler = SpotifyHandler()
        token_info = sp_handler.get_access_token(code)
        session['token_info'] = token_info
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Erro ao obter o token: {e}")
        flash('Erro ao obter o token do Spotify.', 'error')
        return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    try:
        user = sp_handler.sp.current_user()
        user_name = user['display_name']
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
        limit = 10
        offset = (page - 1) * limit
        playlists = sp_handler.sp.current_user_playlists(limit=limit, offset=offset)
        total_playlists = sp_handler.sp.current_user_playlists(limit=1)['total']
        total_pages = (total_playlists // limit) + (total_playlists % limit > 0)

        return render_template('view_playlists.html', playlists=playlists['items'], page=page, total_pages=total_pages)
    except Exception as e:
        logger.error(f"Erro ao recuperar playlists do usuário: {e}")
        flash('Erro ao recuperar playlists.', 'error')
        return redirect(url_for('view_playlists'))

@app.route('/remove_liked_tracks', methods=['GET', 'POST'])
def remove_liked_tracks():
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)

    try:
        limit = 20
        offset = (page - 1) * limit
        liked_tracks = sp_handler.get_liked_tracks(limit=limit, offset=offset)

        total_tracks = sp_handler.sp.current_user_saved_tracks(limit=1)['total']
        total_pages = (total_tracks // limit) + (total_tracks % limit > 0)

        if request.method == 'POST':
            track_ids = request.form.getlist('track_ids')
            if track_ids:
                sp_handler.remove_liked_tracks(track_ids=track_ids)
                flash('Músicas removidas com sucesso!', 'success')
            else:
                flash('Nenhuma música selecionada para remoção.', 'warning')
            return redirect(url_for('remove_liked_tracks', page=page))

        tracks = [
            {
                'id': track['track']['id'],
                'name': track['track']['name'],
                'artist': track['track']['artists'][0]['name']
            } for track in liked_tracks['items']
        ]

        return render_template('remove_liked_tracks.html', tracks=tracks, page=page, total_pages=total_pages)
    except Exception as e:
        logger.error(f"Erro ao recuperar ou remover músicas curtidas: {e}")
        flash('Ocorreu um erro ao processar sua solicitação. Tente novamente mais tarde.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/remove_playlist/<playlist_id>', methods=['POST'])
def remove_playlist(playlist_id):
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

    return redirect(url_for('remove_liked_tracks'))

@app.route('/liked_tracks', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/liked_tracks/<int:page>', methods=['GET', 'POST'])
def liked_tracks(page):
    sp_handler = get_spotify_handler()
    if not sp_handler:
        return redirect(url_for('login'))

    limit = 20
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

        # Recuperar as músicas curtidas
        liked_tracks = sp_handler.sp.current_user_saved_tracks(limit=limit, offset=offset)
        total_tracks = sp_handler.sp.current_user_saved_tracks(limit=1)['total']
        total_pages = (total_tracks // limit) + (total_tracks % limit > 0)

        # Obter a opção de ordenação da query string
        sort_option = request.args.get('sort')

        tracks = [
            {
                'id': track['track']['id'],
                'name': track['track']['name'],
                'artist': track['track']['artists'][0]['name']
            } for track in liked_tracks['items']
        ]

        # Ordenar as faixas conforme a opção selecionada
        if sort_option == 'name_asc':
            tracks.sort(key=lambda x: x['name'].lower())  # A-Z
        elif sort_option == 'name_desc':
            tracks.sort(key=lambda x: x['name'].lower(), reverse=True)  # Z-A
        elif sort_option == 'artist_asc':
            tracks.sort(key=lambda x: x['artist'].lower())  # Artista A-Z
        elif sort_option == 'artist_desc':
            tracks.sort(key=lambda x: x['artist'].lower(), reverse=True)  # Artista Z-A

        return render_template('liked_tracks.html', tracks=tracks, page=page, total_pages=total_pages)
    except Exception as e:
        logger.error(f"Erro ao recuperar músicas curtidas: {e}")
        flash('Erro ao recuperar músicas curtidas.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logger.info("Logout iniciado.")
    session.pop('token_info', None)  # Remover o token do Spotify
    session.pop('user_id', None)  # Remover o ID do usuário, se estiver sendo utilizado
    logger.info("Sessão encerrada.")
    flash("Sessão encerrada com sucesso.", 'success')
    return redirect(url_for('home'))  # Redireciona para a página inicial
    
if __name__ == '__main__':
    app.run(port=8080, debug=True)