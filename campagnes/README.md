# Campagnes de prospection — JyVis Assurances

Objectif : attirer des prospects avec Google Ads, puis les faire tous arriver dans le même circuit. L'agent IA WhatsApp les accueille, le tableau de bord les suit, et Google Ads apprend quels clics donnent de vrais clients.

```
Recherche Google ──► Annonce JyVis ──► Page devis du site (jyvis-assurances.com)
                                           │
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
          Bouton WhatsApp « (réf. GA-…) »             Formulaire de devis
                     │                                           │ (backend du site → n8n)
                     ▼                                           ▼
             Agent IA WhatsApp ◄──── message de bienvenue (si le prospect a coché la case)
                     │
                     ▼
     Tableau de bord : fiche, provenance, statut ──► CSV des conversions ──► Google Ads
```

| Fichier | Contenu |
|---|---|
| [`google-ads/campagnes-jyvis.csv`](google-ads/campagnes-jyvis.csv) | 3 campagnes, 8 groupes d'annonces, 108 mots clés et annonces, à importer dans Google Ads Editor |
| [`google-ads/mots-cles-negatifs.txt`](google-ads/mots-cles-negatifs.txt) | Recherches à exclure (emploi, formation, espace client…) |
| [`google-ads/generer.py`](google-ads/generer.py) | Source des campagnes : modifiez-la puis `python3 generer.py` |
| [`prompt-emergent.md`](prompt-emergent.md) | Les modifications à demander à Emergent pour le site |

## Les campagnes

Toutes les campagnes sont des campagnes **Réseau de Recherche**, créées **en pause**.

| Campagne | Groupes d'annonces | Page d'arrivée | Code suivi | Budget de départ |
|---|---|---|---|---|
| RC Décennale | Général · Métiers du BTP · Création / auto-entrepreneur | `/devis/rc-decennale` | `GA-DECENNALE` | 20 €/jour |
| Pro | Multirisque professionnelle · RC Pro | `/devis/multirisque-pro` | `GA-PRO` | 10 €/jour |
| Auto & Moto | Malus & résiliés · Auto général · Moto | `/devis/auto`, `/devis/moto` | `GA-AUTO` | 10 €/jour |

Le budget de départ est d'environ 1 200 € par mois au total, à ajuster selon votre budget réel. La décennale est prioritaire : c'est le cœur du site, la demande est forte et une affaire signée rapporte plus.

Chaque mot clé est présent en « expression exacte » et en « mot clé exact ». Chaque groupe a une annonce responsive (jusqu'à 15 titres et 4 descriptions), reprenant les arguments du site : courtier indépendant, devis gratuit en 2 minutes, Île-de-France et Guadeloupe, ORIAS 26005663.

## Mise en route

### 1. Compte Google Ads

1. Créez le compte sur ads.google.com en **mode expert**, sans créer de campagne. Facturation en euros, fuseau horaire Paris.
2. Les annonces d'assurance peuvent nécessiter la **vérification « services financiers »** de Google. Préparez le Kbis et le numéro ORIAS (26005663).

### 2. Suivi des conversions

Dans *Objectifs → Conversions → Nouvelle action de conversion* :

| Action | Type | Rôle |
|---|---|---|
| Demande de devis | Site web (balise) | Formulaire envoyé sur le site |
| Clic WhatsApp | Site web (balise) | Clic sur un bouton WhatsApp du site |
| Prospect qualifié | **Importer → Clics** | Envoyé depuis le tableau de bord (statut qualifié, RDV, devis envoyé ou converti) |
| Client signé | **Importer → Clics** | Envoyé depuis le tableau de bord (statut converti) |

Notez l'identifiant `AW-…` et les libellés des deux premières actions pour Emergent. Les noms des deux dernières doivent correspondre exactement à `GOOGLE_ADS_CONVERSION_QUALIFIE` et `GOOGLE_ADS_CONVERSION_CLIENT` du `.env` de n8n.

Laissez le **marquage automatique** (gclid) activé : *Paramètres du compte → Marquage automatique*.

### 3. Modifier le site

Collez [`prompt-emergent.md`](prompt-emergent.md) dans Emergent, après l'avoir complété. Cela ajoute :
- la balise Google avec un bandeau de consentement ;
- la mémorisation de la campagne et du gclid ;
- les conversions ;
- les boutons WhatsApp reliés à l'agent IA, avec le code de campagne ;
- la case de consentement WhatsApp et l'envoi des demandes de devis à n8n.

Le texte suppose que n8n est installé sur `n8n.jyvis-assurances.com`. Adaptez l'adresse si vous en choisissez une autre.

### 4. Importer les campagnes

1. Installez **Google Ads Editor** (gratuit) et connectez le compte.
2. *Compte → Importer → À partir d'un fichier* → `google-ads/campagnes-jyvis.csv`. Vérifiez l'aperçu, puis *Conserver*.
3. Pour chaque campagne, complétez dans Editor ce que le fichier ne règle pas :
   - **Zones** : Paris (75), Hauts-de-Seine (92), Seine-Saint-Denis (93), Val-de-Marne (94), Val-d'Oise (95), Guadeloupe. Option « Présence : personnes situées dans ces zones ».
   - **Calendrier** : 7 h à 21 h, 7 j/7 (l'agent répond la nuit, mais les clics nocturnes convertissent moins).
   - **Composants** : appel (01 48 20 98 27), liens annexes (Décennale, Multirisque pro, Auto, Espace client), accroches (« Courtier indépendant », « Devis gratuit »).
4. *Bibliothèque partagée → Listes de mots clés à exclure* : créez « JyVis – exclusions » avec `mots-cles-negatifs.txt` et associez-la aux 3 campagnes.
5. *Publier*, puis activez d'abord la campagne Décennale.

### 5. Brancher n8n

Dans le `.env` de n8n, renseignez `LEADS_CLE`, `WHATSAPP_MODELE_BIENVENUE`, `GOOGLE_ADS_CONVERSION_QUALIFIE` et `GOOGLE_ADS_CONVERSION_CLIENT`, puis relancez `./whatsapp/installer.sh`.

**Modèle WhatsApp de bienvenue.** Il doit être approuvé par Meta : *WhatsApp Manager → Modèles de message → Créer*, catégorie *Marketing* ou *Utilitaire*, langue français, avec une seule variable `{{1}}` pour le prénom. Exemple :

> Bonjour {{1}}, merci pour votre demande de devis sur jyvis-assurances.com. Je suis l'assistant de JyVis Assurances : pouvez-vous me confirmer quelques informations pour finaliser votre dossier ? Répondez STOP pour ne plus recevoir de messages.

Il n'est envoyé qu'aux personnes qui ont coché la case de consentement. Quand la personne répond, l'agent IA reprend avec tout ce qu'elle a saisi sur le site.

## Routine

**Chaque semaine (15 minutes) :**
1. Tableau de bord n8n : mettez à jour le statut des prospects (RDV, devis envoyé, converti, perdu).
2. Cliquez sur *télécharger le fichier CSV* (conversions), puis dans Google Ads *Objectifs → Conversions → Importer* ce fichier. Google Ads apprend ainsi quels mots clés amènent des clients, pas seulement des clics.
3. Google Ads → *Mots clés → Termes de recherche* : excluez les recherches hors sujet.

**Chaque mois :**
- Comparez les campagnes dans le tableau de bord (bloc « Campagnes – 30 derniers jours » : prospects, qualifiés, convertis, taux).
- Augmentez le budget des campagnes qui signent, baissez les autres.
- Après une trentaine de conversions par mois, passez la stratégie d'enchères à « Maximiser les conversions » avec un **CPA cible**.

**Indicateurs à surveiller :** coût par demande de devis, taux de qualification (agent et conseiller), coût par client signé.

## Prospection : ce qui est permis

- **Autorisé** :
  - répondre à toute personne qui vous écrit ;
  - relancer dans les 24 h ;
  - envoyer un modèle WhatsApp à une personne qui l'a accepté (case cochée) ;
  - écrire à une ancienne cliente ou un ancien client qui a donné son accord.
- **Interdit** :
  - envoyer des messages WhatsApp à des numéros achetés ou collectés sans consentement (Meta bloque le numéro, et c'est contraire au RGPD) ;
  - démarcher par téléphone sans consentement préalable.

Pour toucher de nouvelles personnes, passez donc par la publicité (Google Ads, et plus tard Meta Ads avec formulaires) et laissez-les venir vers l'agent.
