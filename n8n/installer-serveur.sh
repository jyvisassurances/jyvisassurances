#!/usr/bin/env bash
# Installation complète de n8n + agent WhatsApp JyVis sur un serveur Ubuntu neuf.
#
# À lancer en « root » sur le serveur, en une seule commande :
#   curl -fsSL https://raw.githubusercontent.com/jyvisassurances/jyvisassurances/refs/heads/claude/affectionate-albattani-z0m065/n8n/installer-serveur.sh | bash
#
# Sans risque à relancer : les mots de passe déjà créés sont conservés.
set -euo pipefail

DEPOT="https://github.com/jyvisassurances/jyvisassurances.git"
BRANCHE="${BRANCHE:-claude/affectionate-albattani-z0m065}"
DOSSIER="/opt/jyvis"

titre() { printf '\n\033[1;34m== %s ==\033[0m\n' "$1"; }
demander() { # demander "Question" "valeur par défaut" -> réponse
  local rep; read -r -p "$1 ${2:+[$2] }: " rep < /dev/tty || true; echo "${rep:-$2}"
}
regler() { # regler CLE valeur  (dans .env)
  local cle="$1" val="$2"
  if grep -q "^${cle}=" .env; then
    python3 - "$cle" "$val" <<'PY'
import sys, re
cle, val = sys.argv[1], sys.argv[2]
lignes = open(".env", encoding="utf-8").read().splitlines()
lignes = [f"{cle}={val}" if l.startswith(cle + "=") else l for l in lignes]
open(".env", "w", encoding="utf-8").write("\n".join(lignes) + "\n")
PY
  else
    echo "${cle}=${val}" >> .env
  fi
}
valeur() { grep -E "^$1=" .env | head -1 | cut -d= -f2- ; }
vide_ou_defaut() { local v; v="$(valeur "$1")"; [ -z "$v" ] || [ "$v" = "changez-moi" ]; }

[ "$(id -u)" -eq 0 ] || { echo "Lancez ce script en root (commande : sudo -i, puis relancez)."; exit 1; }

titre "1/5 Logiciels nécessaires"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl openssl python3 ca-certificates >/dev/null
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh >/dev/null
fi
systemctl enable --now docker >/dev/null 2>&1 || true
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
fi
echo "OK"

titre "2/5 Fichiers JyVis"
if [ -d "$DOSSIER/.git" ]; then
  git -C "$DOSSIER" fetch -q origin "$BRANCHE" && git -C "$DOSSIER" checkout -q "$BRANCHE" && git -C "$DOSSIER" pull -q --ff-only origin "$BRANCHE"
else
  git clone -q --branch "$BRANCHE" "$DEPOT" "$DOSSIER"
fi
cd "$DOSSIER/n8n"
chmod +x whatsapp/installer.sh
echo "OK ($DOSSIER)"

titre "3/5 Réglages"
[ -f .env ] || cp .env.example .env
chmod 600 .env
vide_ou_defaut POSTGRES_PASSWORD && regler POSTGRES_PASSWORD "$(openssl rand -hex 24)"
vide_ou_defaut N8N_ENCRYPTION_KEY && regler N8N_ENCRYPTION_KEY "$(openssl rand -hex 32)"
vide_ou_defaut TABLEAU_MOT_DE_PASSE && regler TABLEAU_MOT_DE_PASSE "$(openssl rand -base64 12 | tr -d '/+=')"
vide_ou_defaut LEADS_CLE && regler LEADS_CLE "$(openssl rand -hex 24)"

echo "Appuyez sur Entrée pour garder la valeur proposée entre crochets."
echo "Laissez vide ce que vous n'avez pas encore : vous pourrez relancer ce script plus tard."
regler N8N_HOST "$(demander "Adresse de n8n" "$(valeur N8N_HOST | sed 's/^n8n\.jyvis-assurances\.fr$/n8n.jyvis-assurances.com/')")"
regler CONSEILLER_EMAIL "$(demander "E-mail qui reçoit les alertes" "$(valeur CONSEILLER_EMAIL)")"
regler WHATSAPP_VERIFY_TOKEN "$(demander "Jeton de vérification Meta (celui donné par l'assistant)" "$(valeur WHATSAPP_VERIFY_TOKEN)")"
regler WHATSAPP_PHONE_NUMBER_ID "$(demander "Identifiant du numéro de téléphone WhatsApp" "$(valeur WHATSAPP_PHONE_NUMBER_ID)")"
regler WHATSAPP_APP_SECRET "$(demander "Clé secrète de l'application Meta" "$(valeur WHATSAPP_APP_SECRET)")"
regler WHATSAPP_ACCESS_TOKEN "$(demander "Jeton d'accès permanent WhatsApp" "$(valeur WHATSAPP_ACCESS_TOKEN)")"
regler ANTHROPIC_API_KEY "$(demander "Clé API Anthropic" "$(valeur ANTHROPIC_API_KEY)")"
vide_ou_defaut WHATSAPP_VERIFY_TOKEN && regler WHATSAPP_VERIFY_TOKEN "jyvis-$(openssl rand -hex 12)"

titre "4/5 Démarrage de n8n"
IP="$(curl -fsS -4 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
HOTE="$(valeur N8N_HOST)"
if command -v getent >/dev/null && ! getent ahostsv4 "$HOTE" | grep -q "$IP"; then
  echo "⚠  $HOTE ne pointe pas encore vers ce serveur ($IP)."
  echo "   Dans Cloudflare : DNS > Ajouter un enregistrement > Type A, Nom « n8n », IPv4 $IP, proxy DÉSACTIVÉ (nuage gris)."
  echo "   Le certificat HTTPS sera créé automatiquement dès que ce sera fait (quelques minutes)."
fi
docker compose up -d

titre "5/5 Agent WhatsApp"
if vide_ou_defaut WHATSAPP_PHONE_NUMBER_ID || vide_ou_defaut WHATSAPP_ACCESS_TOKEN || vide_ou_defaut WHATSAPP_APP_SECRET || vide_ou_defaut ANTHROPIC_API_KEY; then
  echo "Il manque encore des clés (Meta ou Anthropic) : l'agent sera installé quand vous relancerez ce script avec toutes les valeurs."
else
  ./whatsapp/installer.sh
fi

cat <<FIN

──────────────────────────────────────────────────────────────
 n8n                : https://$HOTE   (créez votre compte au premier accès)
 Webhook Meta       : https://$HOTE/webhook/whatsapp
 Jeton vérification : $(valeur WHATSAPP_VERIFY_TOKEN)
 Tableau de bord    : https://$HOTE/webhook/jyvis
   identifiant      : $(valeur TABLEAU_UTILISATEUR)
   mot de passe     : $(valeur TABLEAU_MOT_DE_PASSE)
 Réglages           : $DOSSIER/n8n/.env   (modifier : nano $DOSSIER/n8n/.env)
──────────────────────────────────────────────────────────────
Notez ces informations dans un endroit sûr.
FIN
