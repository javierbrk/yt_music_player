# YouTube Music Player

A simple, UI-based YouTube music player that allows you to search for and play audio from YouTube videos without the clutter of a web browser.

## Features

- Search for YouTube videos
- Play audio from videos
- Queue up songs
- Keyboard shortcuts for easy navigation and control
- No ads
- Uses browser cookies to bypass YouTube bot detection

## Installation

### System Dependencies

**MPV and yt-dlp (for audio playback):**

**On Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install mpv yt-dlp python3-venv python3-pyqt5
```

**On Arch Linux:**
```bash
sudo pacman -S mpv yt-dlp python-pyqt5
```

### Python Dependencies

```bash
git clone https://github.com/your-username/yt_music_player.git
cd yt_music_player
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configurar Cookies (IMPORTANTE)

YouTube bloquea peticiones que parecen de bots. Para evitarlo, necesitas exportar las cookies de tu navegador.

### Opción 1: Script automático (desde PC con Firefox)

1. Inicia sesión en YouTube en Firefox
2. Ejecuta el script:
```bash
./export_cookies.sh debian@beaglebone
```

El script:
- Cierra Firefox
- Extrae las cookies de YouTube
- Las envía por SSH a la BeagleBone

### Opción 2: Manual

1. Instala la extensión "cookies.txt" en Firefox
2. Ve a youtube.com e inicia sesión
3. Exporta las cookies
4. Copia al BeagleBone:
```bash
scp cookies.txt debian@beaglebone:~/.config/ytplayer/cookies.txt
```

### Ubicación de las cookies

Las cookies se guardan en:
```
~/.config/ytplayer/cookies.txt
```

Este archivo NO se sube a GitHub (está en .gitignore).

## Usage

```bash
./launch.sh
```

O manualmente:
```bash
python3 yt_mp_player_qt5.py
```

## Keyboard Shortcuts

| Key(s)              | Action                      |
| ------------------- | --------------------------- |
| `↑`/`↓` or `j`/`k`   | Navigate search results     |
| `g`                 | Go to the top of the list   |
| `G`                 | Go to the bottom of the list|
| `Enter` or `Space`  | Play selected song          |
| `e`                 | Enqueue selected song       |
| `s` or `Esc`        | Stop playback               |
| `n`                 | Play next song in the queue |
| `c`                 | Clear the queue             |
| `x`                 | Remove selected from queue  |
| `/` or `Ctrl+F`     | Focus the search bar        |
| `Tab`               | Switch focus between search and results |
| `Ctrl+Q`            | Quit the application        |

## How It Works

1. **Search**: Uses `youtubesearchpython` to search YouTube
2. **Playback**: Uses `mpv` with `yt-dlp` and browser cookies for authentication
3. **Cookies**: Las cookies permiten que YouTube reconozca la sesión como legítima
