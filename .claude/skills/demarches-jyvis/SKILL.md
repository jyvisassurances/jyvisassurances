---
name: "demarches-jyvis"
description: "Prendre en charge toutes les démarches carte grise et permis de conduire d'un client JyVis Assurances (changement de titulaire, d'adresse, d'état civil, cotitulaire, duplicata, import, succession, cession ; permis perdu, volé, détérioré, renouvellement, échange de permis étranger, après suspension) : lecture des pièces, contrôle du dossier, calcul des frais officiels et devis PDF à la charte JyVis."
---

# Démarches carte grise & permis — JyVis Assurances

JyVis **monte et dépose le dossier** pour le client ; le nouveau titre (carte grise ou permis) est **délivré par l'ANTS**. Ne jamais retoucher, recréer ni imiter une carte grise, un permis ou toute autre pièce officielle : c'est un faux. Si on le demande, refuser et proposer la démarche officielle correspondante.

Le devis suit **la même charte que le skill `devis-jyvis`** (bandeau bleu marine 62 mm, logo hexagonal, bloc PARTENAIRE, cartes de montant, signatures, pied de page). Ne jamais changer couleurs, en-tête ni structure.

## Catalogue (`python3 scripts/devis_demarche.py --liste`)
**Carte grise** — frais : Y.1 = puissance fiscale (P.6) × taux régional (exonéré si électrique, ÷ 2 si > 10 ans) ; Y.4 = 11 € ; Y.5 = 2,76 € ; Y.6 = malus éventuel.

| Code | Démarche | Frais officiels |
|---|---|---|
| `cg_changement_titulaire` | Achat d'occasion (sous 1 mois) | Y.1 + Y.4 + Y.5 (+ Y.6) |
| `cg_changement_adresse` | Déménagement (sous 1 mois) | Gratuit (étiquette) ; Y.5 si nouvelle carte (`"nouvelle_carte": true`) |
| `cg_duplicata` | Perte, vol, détérioration | Y.4 + Y.5 |
| `cg_etat_civil` | Changement de nom, mariage… | Y.4 + Y.5 |
| `cg_cotitulaire` | Ajout / retrait d'un cotitulaire | Y.1 + Y.4 + Y.5 |
| `cg_modification_technique` | Transformation du véhicule | Y.4 + Y.5 |
| `cg_correction_erreur` | Erreur sur la carte grise | Y.5 |
| `cg_import` | Véhicule importé (UE / hors UE) | Y.1 + Y.4 + Y.5 (+ Y.6) |
| `cg_succession` | Véhicule hérité | Y.1 + Y.4 + Y.5 |
| `cg_declaration_cession` | Le client vend son véhicule | Gratuit |

**Permis de conduire** (demande en ligne ANTS, e-photo obligatoire)

| Code | Démarche | Frais officiels |
|---|---|---|
| `pc_perte` | Permis perdu | Timbre fiscal 25 € |
| `pc_vol` | Permis volé | Gratuit |
| `pc_deterioration` | Permis abîmé | Gratuit |
| `pc_renouvellement` | Fin de validité du titre | Gratuit |
| `pc_etat_civil` | Changement de nom | Gratuit |
| `pc_medical` | Renouvellement après avis médical (pros C/D, suivi médical) | Gratuit (consultation du médecin agréé à la charge du client) |
| `pc_echange_etranger` | Échange d'un permis étranger | Gratuit |
| `pc_apres_suspension` | Après suspension / annulation | Gratuit (visite médicale et tests éventuels à la charge du client) |

**Toujours revérifier les montants et le taux régional** sur immatriculation.ants.gouv.fr / permisdeconduire.ants.gouv.fr ou service-public.fr avant d'envoyer le devis : ils changent régulièrement.

## Méthode
1. **Lire les pièces** envoyées et extraire les données :
   - carte grise : immatriculation (A), 1re mise en circulation (B), titulaire (C.1), marque (D.1), modèle (D.3), VIN (E), énergie (P.3), puissance fiscale (P.6) ;
   - permis : numéro, catégories, date et autorité de délivrance, date de naissance.
2. **Choisir le code** de démarche dans le catalogue.
3. **Contrôler le dossier** et signaler en 1-2 lignes les points bloquants :
   - cession de plus d'un mois, code de cession absent, nom sur la cession ≠ nouveau titulaire ;
   - contrôle technique de plus de 6 mois pour un véhicule de plus de 4 ans ; gage ou opposition ;
   - véhicule non assuré → proposer un devis auto avec le skill `devis-jyvis` ;
   - permis : pièce d'identité expirée, absence d'e-photo, récépissé de vol manquant, suspension en cours, permis étranger hors délai d'échange ;
   - documents illisibles ou qui semblent modifiés → ne pas déposer, demander les originaux.
4. **Remplir le JSON** sur le modèle de `exemples/carte_grise.json` ou `exemples/permis.json` (numéro `JYV-AAAA-MMJJ-CG-NN` ou `-PC-NN`, frais de service JyVis, partenaire). Une liste `"pieces"` personnalisée remplace celle par défaut.
5. **Générer le PDF** :
   ```bash
   python3 .claude/skills/demarches-jyvis/scripts/devis_demarche.py donnees.json devis.pdf
   ```
6. **Vérifier l'aperçu** : `pdftoppm -png -r 80 devis.pdf apercu`, regarder l'image ; rien ne doit se chevaucher ni dépasser, 1 page.
7. **Après signature et paiement** : faire signer le mandat (cerfa 13757 pour la carte grise), déposer la demande sur le SIV (habilitation professionnelle) ou sur le site ANTS, remettre au client l'accusé d'enregistrement (et le certificat provisoire CPI pour une carte grise) ; le titre définitif arrive par courrier sécurisé.

## Coordonnées agence
Tél 01 48 20 98 27 • contact@jyvis-assurances.com • ORIAS 22 00 65 93 • adresse à confirmer avec Marabou (47 rue Jean Jaurès 93200 Saint-Denis ou 10 rue de la Paix 75002 Paris).
