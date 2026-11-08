#!/usr/bin/env bash
# Installe (ou met à jour) l'agent WhatsApp JyVis dans l'instance n8n.
# À lancer depuis le dossier n8n/ :   ./whatsapp/installer.sh
# Sans risque à relancer : la base n'est pas effacée, les workflows sont remplacés.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Fichier .env introuvable : copiez .env.example en .env et remplissez-le."; exit 1; }
set -a; . ./.env; set +a

manque=()
for v in WHATSAPP_PHONE_NUMBER_ID WHATSAPP_ACCESS_TOKEN WHATSAPP_APP_SECRET WHATSAPP_VERIFY_TOKEN ANTHROPIC_API_KEY TABLEAU_MOT_DE_PASSE; do
  [ -n "${!v:-}" ] && [ "${!v}" != "changez-moi" ] || manque+=("$v")
done
if [ ${#manque[@]} -gt 0 ]; then echo "À renseigner dans .env : ${manque[*]}"; exit 1; fi

echo "1/5 Démarrage des services…"
docker compose up -d
for _ in $(seq 1 60); do
  docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 && break; sleep 2
done
attendre_n8n() {
  for _ in $(seq 1 90); do
    docker compose exec -T n8n wget -qO- http://127.0.0.1:5678/healthz >/dev/null 2>&1 && return 0; sleep 2
  done
  echo "n8n ne répond pas : consultez « docker compose logs n8n »."; exit 1
}
attendre_n8n

echo "2/5 Tables des prospects…"
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" < whatsapp/schema.sql

echo "3/5 Identifiants n8n (base de données, e-mail)…"
mkdir -p local-files/.installation
python3 - > local-files/.installation/identifiants.json <<'PY'
import json, os
e = os.environ
print(json.dumps([
  {"id": "jyvisPostgres0001", "name": "JyVis Postgres", "type": "postgres",
   "data": {"host": "postgres", "port": 5432, "database": e["POSTGRES_DB"], "user": e["POSTGRES_USER"],
            "password": e["POSTGRES_PASSWORD"], "ssl": "disable"}},
  {"id": "jyvisSmtp00000001", "name": "JyVis SMTP", "type": "smtp",
   "data": {"host": e.get("SMTP_HOST") or "localhost", "port": int(e.get("SMTP_PORT") or 587),
            "user": e.get("SMTP_USER", ""), "password": e.get("SMTP_PASSWORD", ""),
            "secure": (e.get("SMTP_PORT") or "587") == "465"}},
]))
PY
cp whatsapp/workflows/*.json local-files/.installation/
trap 'rm -rf local-files/.installation' EXIT
docker compose exec -T n8n n8n import:credentials --input=/files/.installation/identifiants.json

echo "4/5 Workflows…"
for f in agent-whatsapp relances-whatsapp tableau-de-bord prospects-site; do
  docker compose exec -T n8n n8n import:workflow --input="/files/.installation/$f.json"
done
for id in jyvisWaAgent00001 jyvisWaRelance001 jyvisWaTableau001 jyvisWaSiteLead01; do
  docker compose exec -T n8n n8n publish:workflow --id="$id"
done

echo "5/5 Redémarrage de n8n…"
docker compose restart n8n
attendre_n8n
# Les webhooks sont actifs quand l'URL de vérification Meta ne renvoie plus 404.
for _ in $(seq 1 60); do
  docker compose exec -T n8n node -e "fetch('http://127.0.0.1:5678/webhook/whatsapp').then(r=>process.exit(r.status===404?1:0)).catch(()=>process.exit(1))" && break; sleep 2
done

cat <<FIN

Installation terminée.
  URL de rappel à saisir dans Meta : https://${N8N_HOST}/webhook/whatsapp
  Jeton de vérification          : la valeur de WHATSAPP_VERIFY_TOKEN
  Tableau de bord                : https://${N8N_HOST}/webhook/jyvis  (identifiant : ${TABLEAU_UTILISATEUR:-jyvis})
  Demandes du site (POST)        : https://${N8N_HOST}/webhook/jyvis-lead  (en-tête x-jyvis-cle = LEADS_CLE)
  Conversions Google Ads (CSV)   : https://${N8N_HOST}/webhook/jyvis-conversions
FIN
