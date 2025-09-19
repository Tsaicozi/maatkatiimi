#!/bin/bash
# Hybrid Bot Deployment Script
# Asentaa ja konfiguroi hybrid trading botin systemd-palveluna

set -euo pipefail

# Värit lokitusta varten
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Konfiguraatio
BOT_USER="bot"
BOT_HOME="/opt/hybrid-bot"
SERVICE_NAME="hybrid-bot"
PYTHON_VERSION="3.11"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Tämä skripti vaatii root-oikeudet. Käytä: sudo $0"
    fi
}

install_dependencies() {
    log "Asennetaan riippuvuudet..."
    
    # Päivitä paketit
    apt-get update
    
    # Python ja pip
    apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-pip python${PYTHON_VERSION}-venv
    
    # Systemd-työkalut
    apt-get install -y systemd curl
    
    # Python-paketit
    apt-get install -y python3-dev build-essential
    
    success "Riippuvuudet asennettu"
}

create_user() {
    log "Luodaan käyttäjä: $BOT_USER"
    
    if ! id "$BOT_USER" &>/dev/null; then
        useradd --system --shell /bin/bash --home-dir "$BOT_HOME" --create-home "$BOT_USER"
        success "Käyttäjä $BOT_USER luotu"
    else
        warning "Käyttäjä $BOT_USER on jo olemassa"
    fi
}

setup_directories() {
    log "Luodaan hakemistot..."
    
    mkdir -p "$BOT_HOME"/{logs,data,config}
    chown -R "$BOT_USER:$BOT_USER" "$BOT_HOME"
    
    # Logs-hakemisto systemd:lle
    mkdir -p /var/log/hybrid-bot
    chown -R "$BOT_USER:$BOT_USER" /var/log/hybrid-bot
    
    success "Hakemistot luotu"
}

install_application() {
    log "Asennetaan sovellus..."
    
    # Kopioi sovellustiedostot
    cp -r . "$BOT_HOME/"
    chown -R "$BOT_USER:$BOT_USER" "$BOT_HOME"
    
    # Python virtual environment
    sudo -u "$BOT_USER" python${PYTHON_VERSION} -m venv "$BOT_HOME/venv"
    sudo -u "$BOT_USER" "$BOT_HOME/venv/bin/pip" install --upgrade pip
    sudo -u "$BOT_USER" "$BOT_HOME/venv/bin/pip" install -r "$BOT_HOME/requirements.txt"
    
    success "Sovellus asennettu"
}

install_systemd_service() {
    log "Asennetaan systemd-palvelu..."
    
    # Kopioi service-tiedosto
    cp hybrid-bot.service /etc/systemd/system/
    
    # Päivitä service-tiedosto käyttämään virtual environmentia
    sed -i "s|/usr/bin/python3|$BOT_HOME/venv/bin/python3|g" /etc/systemd/system/hybrid-bot.service
    
    # Lataa systemd
    systemctl daemon-reload
    
    # Ota palvelu käyttöön
    systemctl enable "$SERVICE_NAME"
    
    success "Systemd-palvelu asennettu ja otettu käyttöön"
}

create_config() {
    log "Luodaan konfiguraatio..."
    
    # Kopioi config.yaml jos ei ole olemassa
    if [[ ! -f "$BOT_HOME/config.yaml" ]]; then
        cp config.yaml "$BOT_HOME/"
        chown "$BOT_USER:$BOT_USER" "$BOT_HOME/config.yaml"
    fi
    
    # Luo .env-tiedosto mallista
    if [[ ! -f "$BOT_HOME/.env" ]]; then
        cat > "$BOT_HOME/.env" << EOF
# Hybrid Bot Environment Variables
# Kopioi tämä tiedosto ja täytä arvot

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# API Keys (optional)
DEXSCREENER_API_KEY=
COINMARKETCAP_API_KEY=
CRYPTOCOMPARE_API_KEY=
PUMPPORTAL_API_KEY=

# Metrics
METRICS_ENABLED=1
METRICS_PORT=9108
METRICS_HOST=0.0.0.0

# Runtime
KILL_SWITCH_PATH=/tmp/hybrid_bot.KILL
EOF
        chown "$BOT_USER:$BOT_USER" "$BOT_HOME/.env"
        chmod 600 "$BOT_HOME/.env"
    fi
    
    success "Konfiguraatio luotu"
}

show_status() {
    log "Tarkistetaan palvelun tila..."
    
    systemctl status "$SERVICE_NAME" --no-pager || true
    
    echo
    log "Hyödyllisiä komentoja:"
    echo "  systemctl start $SERVICE_NAME     # Käynnistä palvelu"
    echo "  systemctl stop $SERVICE_NAME      # Pysäytä palvelu"
    echo "  systemctl restart $SERVICE_NAME   # Käynnistä uudelleen"
    echo "  systemctl status $SERVICE_NAME    # Näytä tila"
    echo "  journalctl -u $SERVICE_NAME -f    # Seuraa lokia"
    echo "  journalctl -u $SERVICE_NAME --since today  # Tämän päivän lokit"
    echo
    echo "  # Kill switch:"
    echo "  touch /tmp/hybrid_bot.KILL        # Pysäytä botti"
    echo "  rm /tmp/hybrid_bot.KILL           # Poista esto"
    echo
    echo "  # Metrics:"
    echo "  curl http://127.0.0.1:9108/metrics"
}

main() {
    log "Aloitetaan Hybrid Bot deployment..."
    
    check_root
    install_dependencies
    create_user
    setup_directories
    install_application
    install_systemd_service
    create_config
    
    success "Deployment valmis!"
    
    warning "Muista:"
    echo "  1. Täytä $BOT_HOME/.env tiedosto API-avaimilla"
    echo "  2. Käynnistä palvelu: systemctl start $SERVICE_NAME"
    echo "  3. Seuraa lokia: journalctl -u $SERVICE_NAME -f"
    
    show_status
}

# Suorita pääfunktio
main "$@"
