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
LOCAL_COOKIES_PATH="$HOME/.config/ytplayer/cookies.txt"
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
log_info "[1/5] Cerrando Firefox..."
log_verbose "Ejecutando: pkill -f firefox"
pkill -f firefox || true
log_verbose "Esperando 2 segundos..."
sleep 2

# 2. Buscar el perfil de Firefox
log_info "[2/5] Buscando perfil de Firefox..."

# Buscar en orden: Snap primero, luego tradicional
FIREFOX_SNAP_DIR="$HOME/snap/firefox/common/.mozilla/firefox"
FIREFOX_TRADITIONAL_DIR="$HOME/.mozilla/firefox"

if [ -d "$FIREFOX_SNAP_DIR" ]; then
    FIREFOX_DIR="$FIREFOX_SNAP_DIR"
    log_verbose "Firefox Snap detectado"
elif [ -d "$FIREFOX_TRADITIONAL_DIR" ]; then
    FIREFOX_DIR="$FIREFOX_TRADITIONAL_DIR"
    log_verbose "Firefox tradicional detectado"
else
    log_error "No se encontró Firefox (ni Snap ni tradicional)"
    log_error "Buscado en: $FIREFOX_SNAP_DIR"
    log_error "Buscado en: $FIREFOX_TRADITIONAL_DIR"
    exit 1
fi
log_verbose "Directorio de Firefox: $FIREFOX_DIR"
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
log_info "[3/5] Extrayendo cookies de YouTube..."

# Copiar la base de datos (Firefox puede tenerla bloqueada)
log_verbose "Copiando base de datos a /tmp/cookies_copy.sqlite"
cp "$COOKIES_DB" /tmp/cookies_copy.sqlite
log_debug "Copia creada: $(du -h /tmp/cookies_copy.sqlite | cut -f1)"

# Extraer cookies de YouTube en formato Netscape
log_verbose "Ejecutando consulta SQL para youtube.com"

# Crear archivo con header Netscape primero
echo "# Netscape HTTP Cookie File" > "$TEMP_COOKIES"
echo "# https://curl.se/docs/http-cookies.html" >> "$TEMP_COOKIES"
echo "# Exported from Firefox for ytplayer" >> "$TEMP_COOKIES"
echo "" >> "$TEMP_COOKIES"

# Extraer cookies con formato correcto (7 campos separados por TAB)
# Solo youtube.com (no google.com)
sqlite3 -separator '	' /tmp/cookies_copy.sqlite "
SELECT
    CASE WHEN host LIKE '.%' THEN host ELSE '.' || host END,
    CASE WHEN host LIKE '.%' THEN 'TRUE' ELSE 'FALSE' END,
    path,
    CASE WHEN isSecure = 1 THEN 'TRUE' ELSE 'FALSE' END,
    CAST(COALESCE(expiry, 0) AS INTEGER),
    name,
    value
FROM moz_cookies
WHERE host LIKE '%youtube.com'
  AND name IS NOT NULL AND name != ''
  AND value IS NOT NULL AND value != ''
  AND expiry IS NOT NULL;
" >> "$TEMP_COOKIES"

log_debug "Cookies extraídas:"
[ "$DEBUG_LEVEL" -ge 3 ] && head -10 "$TEMP_COOKIES"

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

# 4. Guardar copia local
log_info "[4/5] Guardando copia local..."
mkdir -p "$(dirname "$LOCAL_COOKIES_PATH")"
cp "$TEMP_COOKIES" "$LOCAL_COOKIES_PATH"
log_info "   Guardado en: $LOCAL_COOKIES_PATH"

# 5. Enviar a BeagleBone
log_info "[5/5] Enviando cookies a $BBB_HOST..."
log_verbose "Destino: $BBB_COOKIES_PATH"

# Crear directorio en BBB si no existe
log_verbose "Creando directorio remoto si no existe"
log_debug "Ejecutando: ssh $BBB_HOST mkdir -p ~/.config/ytplayer"
ssh "$BBB_HOST" "mkdir -p ~/.config/ytplayer"

# Enviar archivo
log_verbose "Enviando archivo via SCP"
log_debug "Ejecutando: scp $TEMP_COOKIES $BBB_HOST:$BBB_COOKIES_PATH"
scp "$TEMP_COOKIES" "$BBB_HOST:$BBB_COOKIES_PATH"

# Verificar
log_verbose "Verificando archivo en destino"
REMOTE_SIZE=$(ssh "$BBB_HOST" "ls -la $BBB_COOKIES_PATH" 2>/dev/null)
log_debug "Archivo remoto: $REMOTE_SIZE"

# Limpiar
log_verbose "Limpiando archivo temporal"
rm -f "$TEMP_COOKIES"

log_info ""
log_info "=== LISTO ==="
log_info "Cookies guardadas en:"
log_info "   Local:  $LOCAL_COOKIES_PATH"
log_info "   Remoto: $BBB_HOST:$BBB_COOKIES_PATH"
log_info ""

[ "$DEBUG_LEVEL" -ge 1 ] && echo "IMPORTANTE: Asegúrate de estar logueado en YouTube antes de ejecutar este script."
[ "$DEBUG_LEVEL" -ge 1 ] && echo "Las cookies expiran, así que tendrás que ejecutar esto de nuevo si dejan de funcionar."
