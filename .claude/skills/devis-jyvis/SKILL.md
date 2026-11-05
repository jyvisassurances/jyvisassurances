---
name: "devis-jyvis"
description: "Produire tout devis JyVis Assurances (auto, moto, RC Pro, décennale…) en PDF avec la charte officielle : bandeau bleu marine, logo hexagonal, bloc partenaire."
---

# Devis JyVis Assurances — charte obligatoire

TOUS les devis JyVis suivent ce modèle, sans exception (demande de Marabou, 31/10/2026). Ne jamais changer couleurs, en-tête ni structure.

## Charte
- Bleu marine principal #141B6B, foncé #0E1452, fond de page #F3F5FA, lignes alternées #E9EDF6, texte secondaire #5A607A, sous-titres clairs #C9CCE8.
- En-tête : bandeau bleu marine plein (62 mm), logo hexagonal blanc à gauche, « JYVIS ASSURANCES » (Helvetica-Bold 22) + slogan en italique « « Assurer son quotidien, c'est assurer son avenir » », adresse / ORIAS / tél / mail dessous. À droite : « COURTIER DES PROFESSIONNELS », type de document (ex. DEVIS AUTO), n° JYV-AAAA-MMJJ-PRODUIT-NN, date et validité.
- Sous le bandeau : titre « Offre … » + sous-titre ; bloc « PARTENAIRE » en haut à droite avec le nom de l'assureur partenaire en texte (L'Olivier Assurance en vert #2E7D32 pour l'auto ; Tetris, etc. selon produit). Ne pas redessiner le logo d'une marque tierce : utiliser le fichier officiel fourni par Marabou ou le nom en texte.
- Sections : barres de titre bleu marine en capitales, tableaux clé/valeur à lignes alternées.
- Cotisation : 3 cartes (COTISATION ANNUELLE pleine bleu marine, FRAIS DE DOSSIER, TOTAL 1re ANNÉE), ligne « Mensualité de base : X € (annuel ÷ 12) ».
- Encadré « 1er paiement à la souscription : X € » avec détail et mention « Le contrat n'est émis qu'après signature du présent devis et réception de ce premier paiement. »
- Pièces à fournir, puis signatures « BON POUR ACCORD » / « JYVIS ASSURANCES × PARTENAIRE — Le conseiller ».
- Pied de page bleu marine : JYVIS ASSURANCES × PARTENAIRE • adresse • ORIAS • tél • mail.
- Coordonnées : tél 01 48 20 98 27, contact@jyvis-assurances.com, ORIAS 22 00 65 93 ; adresse à confirmer avec Marabou (47 rue Jean Jaurès 93200 Saint-Denis ou 10 rue de la Paix 75002 Paris).

## Méthode
1. Lire les pièces envoyées (carte grise, CNI, permis, Kbis…) et extraire les données.
2. Calculer : mensualité = annuel ÷ 12 ; 1er paiement selon la règle donnée (ex. 2 mois + frais) ; reste en prélèvements.
3. Générer le PDF avec ReportLab canvas (A4, 1 page si possible) en reprenant le gabarit ci-dessous, en adaptant seulement les données, le type de document et le partenaire.
4. Rendre un aperçu PNG (pdftoppm) et vérifier qu'aucun texte ne se chevauche avant d'envoyer.
5. Signaler en 1-2 lignes les points bloquants (conducteur ≠ titulaire carte grise, CT expiré, pièces manquantes).

## Gabarit — logo hexagonal (ReportLab)
```python
def logo(x, y, r, col=colors.white):
    c.saveState()
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(r * 0.14)
    p = c.beginPath()
    for i in range(6):
        a = math.radians(90 + 60 * i)
        px, py = x + r * math.cos(a), y + r * math.sin(a)
        p.moveTo(px, py) if i == 0 else p.lineTo(px, py)
    p.close(); c.drawPath(p, stroke=1, fill=0)
    for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        c.circle(x + dx * r * 0.2, y + dy * r * 0.2, r * 0.2, stroke=0, fill=1)
    c.setStrokeColor(NAVY if col == colors.white else colors.white)
    c.setLineWidth(r * 0.09)
    c.line(x - r * 0.42, y - r * 0.42, x + r * 0.42, y + r * 0.42)
    c.line(x - r * 0.42, y + r * 0.42, x + r * 0.42, y - r * 0.42)
    c.restoreState()
```
Référence de mise en page : devis auto AISSAOUI / Clio DK-729-BK du 31/10/2026 (en-tête 62 mm, marges 16 mm, cadre de page 8 mm, barres de section 6 mm, cartes 20 mm de haut).