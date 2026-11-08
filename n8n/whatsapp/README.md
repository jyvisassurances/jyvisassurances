# Agent IA WhatsApp Business — JyVis Assurances

Un assistant IA répond 24 h/24 aux prospects qui écrivent au numéro WhatsApp Business de JyVis Assurances. Il qualifie leur besoin, remplit leur fiche, relance, et vous alerte quand un humain doit prendre le relais. Vous suivez et reprenez les conversations depuis un tableau de bord.

```
Prospect ──WhatsApp──► Meta ──► n8n ──► Claude (agent IA) ──► réponse WhatsApp
                                  │
                                  ├─► Base PostgreSQL (fiches + conversations)
                                  ├─► E-mail au conseiller (prospect chaud / demande d'un humain)
                                  └─► Tableau de bord  https://<votre-domaine>/webhook/jyvis
```

## Ce que fait l'agent

- **Accueil immédiat**, en annonçant qu'il est un assistant virtuel (obligation de transparence sur l'IA).
- **Qualification** auto, moto, habitation, RC Pro, décennale, santé, prévoyance : il pose les bonnes questions, une ou deux à la fois.
- **Fiche prospect** remplie automatiquement : produit, informations recueillies, résumé, score (chaud / tiède / froid).
- **Passage à un humain** quand le prospect le demande, se plaint, signale un sinistre, ou quand l'IA rencontre une erreur. L'agent se tait alors pour ce prospect.
- **Alerte e-mail** au conseiller pour chaque prospect chaud ou à reprendre.
- **Relance unique**, 3 h après un message resté sans réponse, entre 9 h et 19 h, toujours dans la fenêtre gratuite de 24 h de WhatsApp.
- **STOP** : le prospect ne reçoit plus rien ; START le réactive.
- Plusieurs messages envoyés d'affilée reçoivent **une seule réponse**.

L'agent ne donne **jamais de prix** et ne fait aucune promesse de garantie : le conseil et le devis restent faits par vous (devoir de conseil). Les règles sont dans [`prompt-agent.md`](prompt-agent.md).

## Tableau de bord

`https://<N8N_HOST>/webhook/jyvis`, protégé par l'identifiant et le mot de passe `TABLEAU_UTILISATEUR` / `TABLEAU_MOT_DE_PASSE`.

- Compteurs : prospects, nouveaux de la semaine, chauds, à reprendre, convertis.
- Liste des prospects, conversation complète, fiche et résumé.
- **Reprendre la main** (l'agent s'arrête) ou **la rendre à l'agent IA**.
- **Répondre** au prospect directement depuis la page, tant que son dernier message date de moins de 24 h.
- Changer le statut : nouveau, en cours, qualifié, RDV, devis envoyé, converti, perdu.
- Provenance de chaque prospect (WhatsApp, site, code de campagne Google Ads) et bilan par campagne sur 30 jours.
- Export des conversions pour Google Ads (`/webhook/jyvis-conversions`). Voir [../../campagnes/README.md](../../campagnes/README.md).

Fonctionne sur téléphone.

## Mise en place

### 1. Prérequis Meta (1 à 3 jours, selon la vérification de Meta)

1. Un **Business Manager Meta** (business.facebook.com) au nom de JyVis Assurances, idéalement vérifié.
2. Un **numéro de téléphone dédié** qui n'est pas déjà utilisé sur l'application WhatsApp (ou supprimez d'abord le compte WhatsApp de ce numéro).
3. Sur **developers.facebook.com** : *Créer une application* → type *Entreprise* → ajouter le produit **WhatsApp** → associer le numéro.
4. Notez :
   - l'**identifiant du numéro de téléphone** (*WhatsApp → Configuration de l'API*) → `WHATSAPP_PHONE_NUMBER_ID`
   - la **clé secrète de l'application** (*Paramètres de l'application → Général*) → `WHATSAPP_APP_SECRET`
5. Créez un **jeton permanent** : *Business Manager → Paramètres → Utilisateurs système* → ajouter un utilisateur système administrateur → lui attribuer l'application et le compte WhatsApp → *Générer un jeton* avec les autorisations `whatsapp_business_messaging` et `whatsapp_business_management` → `WHATSAPP_ACCESS_TOKEN`.
6. Ajoutez un moyen de paiement dans le compte WhatsApp. Les réponses aux clients dans les 24 h sont gratuites. Seuls les messages par modèle (non utilisés ici) sont payants.

### 2. Clé Anthropic

Sur console.anthropic.com : créez une clé API → `ANTHROPIC_API_KEY`, et ajoutez du crédit.

### 3. Installation sur le serveur n8n

Le serveur n8n du dossier parent doit être installé (voir [`../README.md`](../README.md)).

```bash
cd jyvisassurances/n8n
nano .env          # remplir la section « Agent WhatsApp » (voir .env.example)
./whatsapp/installer.sh
```

Le script crée les tables, configure les identifiants n8n, importe et active les trois workflows :

| Workflow | Rôle |
|---|---|
| JyVis – Agent WhatsApp | Reçoit les messages, fait répondre l'agent, met à jour la fiche, alerte |
| JyVis – Relances WhatsApp | Toutes les heures, relance les prospects silencieux (une fois) |
| JyVis – Tableau de bord WhatsApp | La page de suivi et les actions du conseiller |
| JyVis – Prospects du site | Reçoit les demandes de devis du site, les ajoute au tableau de bord, envoie le modèle WhatsApp de bienvenue si le prospect l'a accepté |

### 4. Brancher Meta sur n8n

*developers.facebook.com → votre application → WhatsApp → Configuration → Webhook → Modifier* :

- **URL de rappel** : `https://<N8N_HOST>/webhook/whatsapp`
- **Jeton de vérification** : la valeur de `WHATSAPP_VERIFY_TOKEN`
- Puis **S'abonner** au champ `messages`.

Envoyez « Bonjour » au numéro depuis votre téléphone : l'agent répond en quelques secondes.

## Personnaliser

- **Consignes de l'agent** (ton, produits, questions, règles) : modifiez `prompt-agent.md`, puis lancez `python3 whatsapp/build.py` et `./whatsapp/installer.sh`.
- **Numéro ORIAS et horaires** : variables `CABINET_ORIAS` et `CABINET_HORAIRES` du `.env`, puis `docker compose up -d`.
- **Texte et délai de relance** : `build.py`, section « Relances ».

## Sécurité et conformité

- Chaque message reçu est vérifié avec la signature de Meta (`WHATSAPP_APP_SECRET`). Les requêtes falsifiées sont ignorées.
- Le tableau de bord exige un mot de passe et refuse les actions envoyées depuis un autre site.
- Les données restent sur votre serveur (PostgreSQL). Seuls les messages de la conversation sont transmis à Claude pour générer la réponse.
- **RGPD** : ajoutez à votre politique de confidentialité le traitement des messages WhatsApp et le recours à un sous-traitant IA (Anthropic). Pour supprimer un prospect :
  `docker compose exec postgres psql -U n8n -d n8n -c "DELETE FROM prospects WHERE wa_id='33612345678'"`

## Dépannage

| Problème | Vérification |
|---|---|
| Meta refuse l'URL de rappel | Le domaine répond en HTTPS ? `WHATSAPP_VERIFY_TOKEN` identique des deux côtés ? |
| Aucune réponse au message | n8n → *Executions* du workflow « Agent WhatsApp ». Vérifiez `WHATSAPP_APP_SECRET` et `WHATSAPP_PHONE_NUMBER_ID`. |
| « [NON ENVOYÉ] » dans une conversation | Jeton WhatsApp expiré ou invalide, ou plus de 24 h depuis le dernier message du prospect. |
| Le prospect reçoit le message d'attente et passe « à reprendre » | Erreur de l'API Claude (clé, crédit) : le détail est dans le résumé de la fiche. |
| Pas d'e-mail d'alerte | Paramètres `SMTP_*` et `CONSEILLER_EMAIL` du `.env`, puis relancer l'installation. |
