#!/bin/bash
# Script para exportar cookies de Firefox y enviarlas a BeagleBone
# Uso: ./export_cookies.sh [usuario@host] [-v|-vv|-q]
#
# Niveles de debug:
#   -q, --quiet   : Nivel 0 - Solo errores y resultado final
#   (default)     : Nivel 1 - Progreso normal
#   -v, --verbose : Nivel 2 - Debug detallado
#   -vv, --debug  : Nivel 3 - Debug máximo (incluye valores de cookies)

set -e

# === CONFIGURACIÓN ===
BBB_HOST="debian@beaglebone"
BBB_COOKIES_PATH="~/.config/ytplayer/cookies.txt"
DEBUG_LEVEL=1  # 0=quiet, 1=normal, 2=verbose, 3=debug

# === PARSEAR ARGUMENTOS ===
for arg in "$@"; do
    case $arg in
        -q|--quiet)
            DEBUG_LEVEL=0
            ;;
        -v|--verbose)
            DEBUG_LEVEL=2
            ;;
        -vv|--debug)
            DEBUG_LEVEL=3
            ;;
        -*)
            echo "Opción desconocida: $arg"
            echo "Uso: $0 [usuario@host] [-q|-v|-vv]"
            exit 1
            ;;
        *)
            BBB_HOST="$arg"
            ;;
    esac
done

# === FUNCIONES DE LOGGING ===
log_error() {
    echo "ERROR: $*" >&2
}

log_info() {
    # Nivel 1+: Mensajes normales de progreso
    [ "$DEBUG_LEVEL" -ge 1 ] && echo "$*"
}

log_verbose() {
    # Nivel 2+: Información adicional
    [ "$DEBUG_LEVEL" -ge 2 ] && echo "  [DEBUG] $*"
}

log_debug() {
    # Nivel 3: Información muy detallada
    [ "$DEBUG_LEVEL" -ge 3 ] && echo "  [TRACE] $*"
}

# Archivo temporal para las cookies
TEMP_COOKIES="/tmp/youtube_cookies.txt"

log_info "=== Exportador de Cookies de YouTube para BeagleBone ==="
log_verbose "Nivel de debug: $DEBUG_LEVEL"
log_verbose "Host destino: $BBB_HOST"
log_verbose "Ruta destino: $BBB_COOKIES_PATH"
log_info ""

# 1. Cerrar Firefox
log_info "[1/4] Cerrando Firefox..."
log_verbose "Ejecutando: pkill -f firefox"
pkill -f firefox || true
log_verbose "Esperando 2 segundos..."
sleep 2

# 2. Buscar el perfil de Firefox
log_info "[2/4] Buscando perfil de Firefox..."
FIREFOX_DIR="$HOME/.mozilla/firefox"
log_verbose "Directorio de Firefox: $FIREFOX_DIR"

if [ ! -d "$FIREFOX_DIR" ]; then
    log_error "No se encontró el directorio de Firefox: $FIREFOX_DIR"
    exit 1
fi
log_debug "Directorio existe: OK"

# Encontrar el perfil default
log_verbose "Buscando perfiles con patrón *.default*"
PROFILE_DIR=$(find "$FIREFOX_DIR" -maxdepth 1 -type d -name "*.default*" | head -1)

if [ -z "$PROFILE_DIR" ]; then
    log_error "No se encontró un perfil de Firefox"
    log_debug "Perfiles disponibles:"
    [ "$DEBUG_LEVEL" -ge 3 ] && ls -la "$FIREFOX_DIR"
    exit 1
fi
log_info "   Perfil encontrado: $PROFILE_DIR"

COOKIES_DB="$PROFILE_DIR/cookies.sqlite"
log_verbose "Base de datos de cookies: $COOKIES_DB"

if [ ! -f "$COOKIES_DB" ]; then
    log_error "No se encontró la base de datos de cookies: $COOKIES_DB"
    exit 1
fi
log_debug "Tamaño de cookies.sqlite: $(du -h "$COOKIES_DB" | cut -f1)"

# 3. Exportar cookies de YouTube en formato Netscape
log_info "[3/4] Extrayendo cookies de YouTube..."

# Copiar la base de datos (Firefox puede tenerla bloqueada)
log_verbose "Copiando base de datos a /tmp/cookies_copy.sqlite"
cp "$COOKIES_DB" /tmp/cookies_copy.sqlite
log_debug "Copia creada: $(du -h /tmp/cookies_copy.sqlite | cut -f1)"

# Extraer cookies de YouTube en formato Netscape
log_verbose "Ejecutando consulta SQL para youtube.com y google.com"
sqlite3 -separator $'\t' /tmp/cookies_copy.sqlite <<EOF > "$TEMP_COOKIES"
.mode tabs
SELECT
    CASE WHEN host LIKE '.%' THEN host ELSE '.' || host END,
    CASE WHEN host LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
    path,
    CASE WHEN isSecure THEN 'TRUE' ELSE 'FALSE' END,
    expiry,
    name,
    value
FROM moz_cookies
WHERE host LIKE '%youtube.com' OR host LIKE '%google.com';
EOF

log_debug "Cookies extraídas (raw):"
[ "$DEBUG_LEVEL" -ge 3 ] && head -5 "$TEMP_COOKIES"

# Agregar header del formato Netscape
log_verbose "Agregando header Netscape al archivo"
TEMP_COOKIES2="/tmp/youtube_cookies2.txt"
echo "# Netscape HTTP Cookie File" > "$TEMP_COOKIES2"
echo "# Exported from Firefox for ytplayer" >> "$TEMP_COOKIES2"
echo "" >> "$TEMP_COOKIES2"
cat "$TEMP_COOKIES" >> "$TEMP_COOKIES2"
mv "$TEMP_COOKIES2" "$TEMP_COOKIES"

# Limpiar copia temporal
log_verbose "Limpiando copia temporal de la base de datos"
rm -f /tmp/cookies_copy.sqlite

COOKIE_COUNT=$(wc -l < "$TEMP_COOKIES")
ACTUAL_COOKIES=$((COOKIE_COUNT - 3))
log_info "   Cookies exportadas: $ACTUAL_COOKIES"

if [ "$ACTUAL_COOKIES" -eq 0 ]; then
    log_error "No se encontraron cookies de YouTube/Google. ¿Estás logueado?"
    exit 1
fi

log_debug "Nombres de cookies encontradas:"
[ "$DEBUG_LEVEL" -ge 3 ] && awk -F'\t' 'NR>3 {print "    - " $6}' "$TEMP_COOKIES"

# 4. Enviar a BeagleBone
log_info "[4/4] Enviando cookies a $BBB_HOST..."
log_verbose "Destino: $BBB_COOKIES_PATH"

# Crear directorio en BBB si no existe
log_verbose "Creando directorio remoto si no existe"
log_debug "Ejecutando: ssh $BBB_HOST mkdir -p ~/.config/ytplayer"
ssh "$BBB_HOST" "mkdir -p ~/.config/ytplayer"

# Enviar archivo
log_verbose "Enviando archivo via SCP"
log_debug "Ejecutando: scp $TEMP_COOKIES $BBB_HOST:$BBB_COOKIES_PATH"
scp "$TEMP_COOKIES" "$BBB_HOST:$BBB_COOKIES_PATH"

# 5. Verificar
log_verbose "Verificando archivo en destino"
REMOTE_SIZE=$(ssh "$BBB_HOST" "ls -la $BBB_COOKIES_PATH" 2>/dev/null)
log_debug "Archivo remoto: $REMOTE_SIZE"

# Limpiar
log_verbose "Limpiando archivo temporal local"
rm -f "$TEMP_COOKIES"

log_info ""
log_info "=== LISTO ==="
log_info "Las cookies fueron enviadas a $BBB_HOST:$BBB_COOKIES_PATH"
log_info ""
log_verbose "Para probar, ejecuta en la BeagleBone:"
log_verbose "  mpv --no-video --ytdl-raw-options=cookies=$BBB_COOKIES_PATH 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'"

[ "$DEBUG_LEVEL" -ge 1 ] && echo "IMPORTANTE: Asegúrate de estar logueado en YouTube antes de ejecutar este script."
[ "$DEBUG_LEVEL" -ge 1 ] && echo "Las cookies expiran, así que tendrás que ejecutar esto de nuevo si dejan de funcionar."
