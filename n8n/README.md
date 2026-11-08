# n8n — JyVis Assurances

Instance n8n auto-hébergée pour automatiser les tâches du cabinet (devis, relances, suivi des prospects…).

Contenu :

| Fichier | Rôle |
|---|---|
| `docker-compose.yml` | n8n + PostgreSQL + Caddy (HTTPS automatique) |
| `Caddyfile` | Reverse proxy vers n8n |
| `.env.example` | Variables à copier dans `.env` |

## Prérequis

- Un serveur Linux (VPS 2 Go de RAM minimum) avec Docker et Docker Compose.
- Un nom de domaine, par ex. `n8n.jyvis-assurances.fr`, avec un enregistrement DNS **A** vers l'IP du serveur.
- Ports 80 et 443 ouverts.

## Installation

```bash
git clone https://github.com/jyvisassurances/jyvisassurances.git
cd jyvisassurances/n8n
cp .env.example .env
# Générer les secrets :
sed -i "s/^N8N_ENCRYPTION_KEY=.*/N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)/" .env
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 24)/" .env
nano .env   # renseigner N8N_HOST
docker compose up -d
```

Ouvrir `https://<N8N_HOST>` et créer le compte propriétaire au premier lancement.

## Test en local (sans domaine)

Mettre `N8N_HOST=localhost` dans `.env`, puis `docker compose up -d` : Caddy sert `https://localhost` avec un certificat local.

## Mise à jour

```bash
docker compose pull && docker compose up -d
```

## Sauvegarde

```bash
docker compose exec -T postgres pg_dump -U n8n n8n > sauvegarde-$(date +%F).sql
```

Conservez aussi la valeur `N8N_ENCRYPTION_KEY` du fichier `.env` : sans elle, les identifiants (Gmail, Google Sheets…) enregistrés dans n8n ne peuvent pas être restaurés.

## Logs

```bash
docker compose logs -f n8n
```
