---
name: "carte-grise-jyvis"
description: "Gérer de A à Z un changement de carte grise (changement de titulaire, d'adresse, duplicata, modification) pour un client JyVis Assurances : lecture des pièces, contrôle du dossier, calcul des taxes ANTS et devis PDF à la charte JyVis."
---

# Changement de carte grise — JyVis Assurances

Le document final suit **la même charte que le skill `devis-jyvis`** (bandeau bleu marine 62 mm, logo hexagonal, bloc PARTENAIRE, cartes de montant, signatures, pied de page). Ne jamais changer couleurs, en-tête ni structure.

## Démarches couvertes
| Code `demarche` | Cas | Taxes |
|---|---|---|
| `changement_titulaire` | Achat d'un véhicule d'occasion (délai légal : 1 mois après la cession) | Y.1 régionale + Y.4 (11 €) + Y.5 (2,76 €) + Y.6 malus éventuel |
| `changement_adresse` | Déménagement (délai : 1 mois) | Gratuit (étiquette) pour les 3 premiers changements ; au 4e, nouvelle carte éditée → Y.5 (`"nouvelle_carte": true`) — à confirmer sur l'ANTS |
| `duplicata` | Perte, vol, détérioration | Y.4 + Y.5 |
| `modification` | Changement de caractéristiques, d'état civil… | Y.4 + Y.5 (+ Y.1 selon le cas) |

Règles Y.1 : puissance fiscale (P.6) × taux du cheval fiscal de la région du titulaire. Exonération pour les véhicules 100 % électriques ; demi-tarif pour les véhicules de plus de 10 ans. **Toujours vérifier le taux en vigueur sur le simulateur officiel ANTS** (immatriculation.ants.gouv.fr) avant d'envoyer le devis : les régions le changent chaque année.

## Méthode
1. **Lire les pièces** envoyées (carte grise barrée, certificat de cession cerfa 15776, CNI, permis, justificatif de domicile, contrôle technique, attestation d'assurance) et extraire : immatriculation (A), date de 1re mise en circulation (B), marque (D.1), modèle (D.3), VIN (E), énergie (P.3), puissance fiscale (P.6), ancien titulaire (C.1).
2. **Contrôler le dossier** et signaler en 1-2 lignes les points bloquants :
   - cession de plus d'un mois ou code de cession absent ;
   - contrôle technique de plus de 6 mois (2 mois si contre-visite) pour un véhicule de plus de 4 ans ;
   - nom sur la cession ≠ nom du nouveau titulaire ; conducteur principal ≠ titulaire ;
   - carte grise non barrée / non signée, gage ou opposition (certificat de situation administrative) ;
   - absence d'assurance du véhicule → proposer un devis auto avec le skill `devis-jyvis`.
3. **Remplir le JSON** sur le modèle de `exemples/exemple.json` (numéro `JYV-AAAA-MMJJ-CG-NN`, taux régional, frais de service JyVis, partenaire).
4. **Générer le PDF** :
   ```bash
   python3 .claude/skills/carte-grise-jyvis/scripts/devis_carte_grise.py donnees.json devis.pdf
   ```
5. **Vérifier l'aperçu** : `pdftoppm -png -r 80 devis.pdf apercu` puis regarder l'image ; aucun texte ne doit se chevaucher, tout doit tenir sur 1 page.
6. **Après signature et paiement** : faire signer le mandat cerfa 13757, déposer la demande sur le SIV (habilitation professionnelle) ou sur immatriculation.ants.gouv.fr, remettre au client le certificat provisoire (CPI, valable 1 mois) et l'accusé d'enregistrement ; la carte grise définitive arrive par courrier sécurisé.

## Coordonnées agence
Tél 01 48 20 98 27 • contact@jyvis-assurances.com • ORIAS 22 00 65 93 • adresse à confirmer avec Marabou (47 rue Jean Jaurès 93200 Saint-Denis ou 10 rue de la Paix 75002 Paris).
