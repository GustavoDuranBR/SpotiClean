# Aplicativo SpotiClean
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

Este aplicativo permite que os usuários acessem suas playlists do Spotify, adicionem ou removam playlists diretamente pelo app, e criem playlists com base em artistas de interesse.

## Funcionalidades

- **Login no Spotify**: 
  - O aplicativo permite que os usuários façam login em suas contas do Spotify para acessar suas playlists e músicas.
  - **Código Relevante**: `callback` para tratar a autenticação e armazenamento do token de acesso.

- **Criar Playlists**: 
  - Os usuários podem criar novas playlists a partir de uma lista de artistas de sua escolha, e o aplicativo seleciona as músicas mais tocadas desses artistas para adicionar à nova playlist.
  - **Código Relevante**: `create_playlist` para gerenciar a criação de novas playlists e o download de músicas.

- **Visualizar Playlists**: 
  - O aplicativo exibe as playlists existentes do usuário, permitindo que ele as visualize e gerencie.
  - **Código Relevante**: `view_playlists` para recuperar e exibir as playlists do usuário.

- **Remover Músicas Curtidas**: 
  - Os usuários podem remover músicas que curtiram, selecionando-as de uma lista.
  - **Código Relevante**: `remove_liked_tracks` para gerenciar a remoção de músicas.

- **Atualizar Músicas Curtidas**: 
  - O aplicativo permite atualizar a lista de músicas que o usuário curtiu.
  - **Código Relevante**: `update_tracks` para recuperar as músicas curtidas e retornar como JSON.

## Estrutura do Projeto

O projeto está organizado da seguinte forma:

```
app_spotify/
│
├── spotify_manager.py         # Arquivo principal com a lógica do aplicativo e rotas
├── api.py                     # Manipulador da API do Spotify e funções relacionadas
├── templates/                 # Pasta contendo os arquivos HTML para renderização
│   ├── dashboard.html         # Página do dashboard do usuário
│   ├── create_playlist.html    # Página para criar novas playlists
│   ├── liked_tracks.html      # Página para visualizar músicas curtidas
│   └── view_playlists.html    # Página para visualizar playlists do usuário
├── static/                    # Pasta para arquivos estáticos (CSS, JS, imagens)
├── README.md                  # Documentação do projeto
└── requirements.txt           # Dependências do projeto
```

## Instruções de Instalação

1. **Clone este repositório**:
   ```bash
   git clone https://github.com/seuusuario/app_spotify.git
   cd app_spotify
   ```

2. **Crie e ative um ambiente virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/MacOS
   venv\Scripts\activate     # Windows
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Execute o programa**:
   ```bash
   python app.py
   ```

## Uso

- **Login**: Ao acessar o aplicativo, clique em 'Login' para se autenticar com sua conta do Spotify.
- **Dashboard**: Após o login, você será redirecionado para o dashboard, onde verá seu nome de usuário e imagem de perfil.
- **Criar Playlist**: Acesse a página de criação de playlists, insira o nome da nova playlist e os artistas de interesse. Clique em 'Criar Playlist' para gerar a playlist.
- **Visualizar Playlists**: Acesse a página de playlists para ver suas playlists existentes.
- **Remover Músicas Curtidas**: Vá para a página de músicas curtidas, selecione as músicas que deseja remover e clique em 'Remover Músicas'.
- **Atualizar Músicas**: Use a funcionalidade de atualização de músicas para visualizar a lista atualizada de músicas curtidas.

## Autor

Desenvolvido por Gustavo Duran.

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## Contato

Para dúvidas ou ajuda, entre em contato por email: gustavoduran22@gmail.com
