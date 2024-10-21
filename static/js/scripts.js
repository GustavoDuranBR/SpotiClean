document.addEventListener('DOMContentLoaded', function () {
    loadTracks(); // Carregar a lista de todas as músicas ao iniciar
    loadLikedTracks(); // Carregar faixas curtidas quando a página é carregada

    // Função para atualizar a lista de artistas
    function updateArtistNames() {
        const artistItems = document.querySelectorAll('.artist-item');
        const artistNames = Array.from(artistItems).map(item => item.textContent.replace('Excluir', '').trim());
        document.getElementById('artist_names').value = artistNames.join(',');

        // Exibe a lista se houver artistas
        const artistList = document.getElementById('artist-list');
        artistList.classList.toggle('d-none', artistItems.length === 0);
    }

    // Adiciona novo artista
    document.getElementById('add-artist-btn').addEventListener('click', function () {
        const artistInput = document.getElementById('artist_name');
        const artistName = artistInput.value.trim(); // Captura o valor do input de artista

        if (artistName) {
            const artistList = document.getElementById('artist-list');

            const artistItem = document.createElement('div');
            artistItem.classList.add('artist-item', 'mb-2', 'text-white');
            artistItem.textContent = artistName;

            // Botão para remover o artista da lista
            const deleteButton = document.createElement('button');
            deleteButton.textContent = 'Excluir';
            deleteButton.classList.add('btn', 'btn-danger', 'btn-sm', 'ms-2');
            deleteButton.addEventListener('click', function () {
                artistList.removeChild(artistItem); // Remove o artista
                updateArtistNames(); // Atualiza a lista oculta
            });

            artistItem.appendChild(deleteButton);
            artistList.appendChild(artistItem); // Adiciona o artista à lista

            updateArtistNames(); // Atualiza a lista de artistas
            artistInput.value = ''; // Limpa o campo de entrada
        } else {
            alert('Por favor, digite um nome de artista.');
        }
    });

    // Função para carregar a lista de todas as músicas
    function loadTracks() {
        fetch('/update_tracks')
            .then(response => response.json())
            .then(data => {
                const trackList = document.getElementById('track-list'); // Lista de todas as músicas
                trackList.innerHTML = ''; // Limpa a lista antes de adicionar

                data.tracks.forEach(track => {
                    const trackItem = document.createElement('div');
                    trackItem.className = 'form-check';
                    trackItem.innerHTML = `
                        <input type="checkbox" class="form-check-input" id="track-${track.id}" data-track-id="${track.id}">
                        <label class="form-check-label" for="track-${track.id}">${track.name} - ${track.artist}</label>
                    `;
                    trackList.appendChild(trackItem);
                });
            })
            .catch(error => {
                console.error('Erro ao carregar a lista de músicas:', error);
                alert('Erro ao carregar a lista de músicas.');
            });
    }

    // Função para carregar as faixas curtidas
    function loadLikedTracks() {
        fetch('/liked_tracks')
            .then(response => response.json())
            .then(tracks => {
                const likedTrackList = document.getElementById('liked-track-list'); // Lista de faixas curtidas
                likedTrackList.innerHTML = ''; // Limpa a lista antes de adicionar as faixas

                tracks.forEach(track => {
                    const trackItem = document.createElement('div');
                    trackItem.className = 'track-item d-flex justify-content-between align-items-center mb-2';
                    trackItem.innerHTML = `
                        <input type="checkbox" class="track-checkbox" data-track-id="${track.id}">
                        <span>${track.name} - ${track.artist}</span>
                        <button class="btn btn-danger btn-sm" data-track-id="${track.id}">Remover</button>
                    `;
                    likedTrackList.appendChild(trackItem);
                });

                // Adiciona funcionalidade ao botão "Remover"
                const removeButtons = document.querySelectorAll('.btn-danger');
                removeButtons.forEach(button => {
                    button.addEventListener('click', function () {
                        const trackId = this.getAttribute('data-track-id');
                        removeTrack(trackId);
                    });
                });
            })
            .catch(error => {
                console.error('Erro ao carregar as faixas curtidas:', error);
                alert('Erro ao carregar as faixas curtidas.');
            });
    }

    // Desmarca todos os checkboxes
    document.getElementById('deselect-all').addEventListener('click', function () {
        const checkboxes = document.querySelectorAll('#track-list input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false; // Desmarca todos
        });
    });

    // Adiciona funcionalidade ao botão de "Remover"
    document.getElementById('remove-selected-btn').addEventListener('click', function () {
        const checkboxes = document.querySelectorAll('#track-list input[type="checkbox"]:checked');
        const trackIds = Array.from(checkboxes).map(checkbox => checkbox.dataset.trackId);

        if (trackIds.length === 0) {
            alert('Nenhuma música selecionada.');
            return;
        }

        if (confirm(`Tem certeza que deseja remover ${trackIds.length} músicas?`)) {
            fetch('/remove_liked_tracks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    'track_ids': trackIds.join(',')
                })
            })
                .then(response => {
                    if (response.ok) {
                        loadTracks(); // Recarrega a lista de músicas
                    } else {
                        alert('Erro ao remover músicas selecionadas.');
                    }
                })
                .catch(error => {
                    console.error('Erro ao remover músicas selecionadas:', error);
                    alert('Erro ao remover músicas selecionadas.');
                });
        }
    });

    // Cria a playlist
    document.getElementById('create-playlist-btn').addEventListener('click', function () {
        const playlistName = document.getElementById('playlist_name').value.trim();
        const artistNames = document.getElementById('artist_names').value.trim();

        // Verificação de campos obrigatórios
        if (!playlistName) {
            alert('Por favor, insira um nome para a playlist.');
            return;
        }

        if (!artistNames) {
            alert('Por favor, adicione pelo menos um artista à playlist.');
            return;
        }

        // Enviar requisição ao servidor para criar a playlist
        fetch('/create_playlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                'playlist_name': playlistName,
                'artist_names': artistNames
            })
        })
            .then(response => {
                if (response.ok) {
                    alert('Playlist criada com sucesso!');
                    // Limpa o formulário
                    document.getElementById('playlist_name').value = ''; // Limpa o campo de nome
                    document.getElementById('artist_names').value = ''; // Limpa a lista de artistas
                    document.getElementById('artist-list').innerHTML = ''; // Limpa a lista visual
                } else {
                    alert('Erro ao criar a playlist.');
                }
            })
            .catch(error => {
                console.error('Erro ao criar a playlist:', error);
                alert('Erro ao criar a playlist.');
            });
    });

    // Função para remover uma faixa
    function removeTrack(trackId) {
        fetch('/remove_liked_tracks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                'track_ids': trackId // Passa o ID da faixa a ser removida
            })
        }).then(response => {
            if (response.ok) {
                alert('Música removida com sucesso!');
                loadLikedTracks(); // Recarrega a lista de faixas após a remoção
            } else {
                alert('Erro ao remover a música.');
            }
        }).catch(error => {
            console.error('Erro ao remover a música:', error);
            alert('Erro ao remover a música.');
        });
    }
});
