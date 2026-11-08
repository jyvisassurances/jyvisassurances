# Modifications du site jyvis-assurances.com (à coller dans Emergent)

Le site est construit avec Emergent : son code ne se trouve pas dans ce dépôt. Copiez le texte ci-dessous dans Emergent, après avoir remplacé les éléments entre `<…>`.

- `<AW-XXXXXXXXX>`, `<LIBELLE_DEVIS>`, `<LIBELLE_WHATSAPP>` : identifiants donnés par Google Ads lors de la création des conversions (voir [README.md](README.md), étape 2).
- `<LEADS_CLE>` : la valeur de `LEADS_CLE` du fichier `.env` de n8n.

---

```text
Merci d'apporter les modifications suivantes au site, sans changer le design :

1. Balise Google Ads
   Ajoute la balise Google (gtag.js) avec l'identifiant <AW-XXXXXXXXX> dans le <head> de toutes les pages.
   Ne la charge qu'après acceptation des cookies publicitaires (bandeau de consentement conforme CNIL, avec Google Consent Mode v2 :
   ad_storage, ad_user_data et ad_personalization à "denied" par défaut, "granted" après acceptation).

2. Mémoriser la provenance du visiteur
   À l'arrivée sur n'importe quelle page, si l'URL contient gclid, utm_source, utm_medium ou utm_campaign,
   enregistre ces valeurs dans le localStorage (clé "jyvis_provenance", avec la date) et conserve-les 90 jours.

3. Conversion « demande de devis »
   Quand un formulaire de devis (/devis/rc-decennale, /devis/multirisque-pro, /devis/auto, /devis/moto,
   /devis/habitation, /devis/cybersecurite, /devis/complet…) est envoyé avec succès, déclenche :
   gtag('event', 'conversion', { send_to: '<AW-XXXXXXXXX>/<LIBELLE_DEVIS>' });

4. Conversion « clic WhatsApp »
   Quand on clique sur un bouton ou lien WhatsApp (bouton flottant, barre mobile…), déclenche :
   gtag('event', 'conversion', { send_to: '<AW-XXXXXXXXX>/<LIBELLE_WHATSAPP>' });

5. Boutons WhatsApp vers l'agent IA
   Remplace le lien actuel https://wa.me/message/XE3IM2IGGU5VE1 par
   https://wa.me/33787775907?text=<message encodé>
   où le message est « Bonjour, je souhaite un devis » suivi, si une campagne est mémorisée (point 2),
   de « (réf. » + utm_campaign en majuscules + « ) ». Exemple : « Bonjour, je souhaite un devis (réf. GA-DECENNALE) ».
   Sur une page /devis/<type>, mets plutôt « Bonjour, je souhaite un devis <type> ».

6. Case de consentement WhatsApp dans les formulaires de devis
   Ajoute une case à cocher, non cochée par défaut :
   « J'accepte d'être recontacté(e) par JyVis Assurances sur WhatsApp au sujet de ma demande. Je peux me désinscrire à tout moment en écrivant STOP. »

7. Envoi des demandes de devis vers n8n (côté serveur uniquement)
   Après l'enregistrement habituel d'une demande de devis dans le backend, le backend (jamais le navigateur)
   envoie aussi un POST JSON à https://n8n.jyvis-assurances.com/webhook/jyvis-lead
   avec l'en-tête  x-jyvis-cle: <LEADS_CLE>  (à stocker dans une variable d'environnement du backend, jamais dans le code du front)
   et ce contenu :
   {
     "nom": "...", "telephone": "...", "email": "...",
     "produit": "rc_decennale | multirisque_pro | auto | moto | habitation | cyber | sante | prevoyance | autre",
     "message": "texte libre saisi par le client",
     "details": { toutes les autres réponses du formulaire, sous forme clé: valeur },
     "utm_campaign": "...", "gclid": "...",            (depuis le point 2, si présents)
     "consentement_whatsapp": true | false             (case du point 6)
   }
   Un échec de cet envoi ne doit jamais bloquer le visiteur : journalise l'erreur et continue.

8. Politique de confidentialité
   Ajoute un paragraphe : les demandes de devis et les messages WhatsApp sont traités par JyVis Assurances
   pour répondre à la demande ; un assistant virtuel (Anthropic) aide à répondre sur WhatsApp ;
   la mesure d'audience publicitaire (Google Ads) n'est active qu'avec votre consentement.
```
