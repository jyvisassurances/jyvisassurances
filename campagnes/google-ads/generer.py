#!/usr/bin/env python3
"""Génère le fichier d'import Google Ads Editor des campagnes JyVis Assurances.

Usage : python3 generer.py   ->   campagnes-jyvis.csv (à importer dans Google Ads Editor)
Les campagnes sont créées EN PAUSE : rien n'est dépensé avant votre relecture.
Vérifie les limites de Google : titres <= 30 caractères, descriptions <= 90, chemins <= 15.
"""
import csv
import pathlib

SITE = "https://jyvis-assurances.com"
ICI = pathlib.Path(__file__).parent

# Éléments communs (tirés du site jyvis-assurances.com)
TITRES_COMMUNS = [
    "Courtier Indépendant",
    "Devis Gratuit en 2 Minutes",
    "Île-de-France & Guadeloupe",
    "Réponse Rapide sur WhatsApp",
    "Courtier ORIAS 26005663",
]
DESCRIPTIONS_COMMUNES = [
    "Courtier indépendant en Île-de-France et en Guadeloupe. Devis gratuit en 2 minutes.",
    "Un conseiller dédié compare pour vous plusieurs assureurs. Réponse rapide sur WhatsApp.",
]

CAMPAGNES = [
    {
        "nom": "JyVis | Recherche | RC Décennale",
        "code": "GA-DECENNALE",
        "budget": 20,
        "groupes": [
            {
                "nom": "Décennale - Général",
                "url": "/devis/rc-decennale",
                "chemins": ("decennale", "devis"),
                "mots_cles": [
                    "assurance décennale", "assurance decennale", "rc décennale", "garantie décennale",
                    "devis assurance décennale", "assurance décennale pas chère", "courtier assurance décennale",
                    "attestation décennale", "assurance décennale artisan", "assurance décennale btp",
                ],
                "titres": [
                    "Assurance Décennale", "Devis RC Décennale", "Attestation Rapide",
                    "Artisans du BTP", "Courtier Spécialiste BTP", "Comparez les Assureurs",
                ],
                "descriptions": [
                    "Assurance décennale pour artisans et entreprises du BTP. Demandez votre devis en ligne.",
                    "Création d'entreprise, résiliation, changement d'assureur : nous trouvons une solution.",
                ],
            },
            {
                "nom": "Décennale - Métiers",
                "url": "/devis/rc-decennale",
                "chemins": ("decennale", "artisan"),
                "mots_cles": [
                    "assurance décennale maçon", "assurance décennale plombier", "assurance décennale électricien",
                    "assurance décennale peintre", "assurance décennale carreleur", "assurance décennale menuisier",
                    "assurance décennale plaquiste", "assurance décennale couvreur", "assurance décennale charpentier",
                    "assurance décennale tous corps d'état",
                ],
                "titres": [
                    "Décennale pour Votre Métier", "Maçon, Plombier, Électricien", "Peintre, Carreleur, Plaquiste",
                    "Devis RC Décennale", "Courtier Spécialiste BTP", "Tous Corps d'État",
                ],
                "descriptions": [
                    "Décennale adaptée à votre activité : maçonnerie, plomberie, électricité, peinture…",
                    "Indiquez votre métier et votre chiffre d'affaires, un conseiller vous répond vite.",
                ],
            },
            {
                "nom": "Décennale - Création & Auto-entrepreneur",
                "url": "/devis/rc-decennale",
                "chemins": ("decennale", "creation"),
                "mots_cles": [
                    "assurance décennale auto entrepreneur", "assurance décennale micro entreprise",
                    "assurance décennale création entreprise", "assurance décennale sans expérience",
                    "assurance décennale jeune entreprise", "décennale auto entrepreneur prix",
                ],
                "titres": [
                    "Décennale Auto-Entrepreneur", "Création d'Entreprise BTP", "Jeune Entreprise Acceptée",
                    "Devis RC Décennale", "Courtier Spécialiste BTP", "Attestation Rapide",
                ],
                "descriptions": [
                    "Vous lancez votre activité dans le bâtiment ? Obtenez votre décennale avec un courtier.",
                    "Micro-entreprise, SASU, EURL : devis décennale gratuit et accompagnement personnalisé.",
                ],
            },
        ],
    },
    {
        "nom": "JyVis | Recherche | Pro (Multirisque & RC Pro)",
        "code": "GA-PRO",
        "budget": 10,
        "groupes": [
            {
                "nom": "Multirisque professionnelle",
                "url": "/devis/multirisque-pro",
                "chemins": ("multirisque", "pro"),
                "mots_cles": [
                    "assurance multirisque professionnelle", "multirisque pro", "assurance local professionnel",
                    "assurance commerce", "assurance restaurant", "assurance boutique", "devis multirisque professionnelle",
                ],
                "titres": [
                    "Multirisque Professionnelle", "Assurez Votre Local Pro", "Commerces et Restaurants",
                    "Devis Multirisque Pro", "Protégez Votre Activité", "Conseiller Dédié",
                ],
                "descriptions": [
                    "Locaux, matériel, stock, perte d'exploitation : une multirisque adaptée à votre activité.",
                    "Commerçants, restaurateurs, artisans : comparez les offres avec un courtier indépendant.",
                ],
            },
            {
                "nom": "RC Pro",
                "url": "/devis/multirisque-pro",
                "chemins": ("rc-pro", "devis"),
                "mots_cles": [
                    "assurance rc pro", "responsabilité civile professionnelle", "rc pro auto entrepreneur",
                    "assurance responsabilité civile pro", "devis rc pro",
                ],
                "titres": [
                    "Assurance RC Pro", "Responsabilité Civile Pro", "RC Pro Auto-Entrepreneur",
                    "Devis RC Pro Gratuit", "Protégez Votre Activité", "Conseiller Dédié",
                ],
                "descriptions": [
                    "Responsabilité civile professionnelle pour indépendants, TPE et PME. Devis gratuit.",
                    "Auto-entrepreneur ou société : un courtier compare les garanties pour vous.",
                ],
            },
        ],
    },
    {
        "nom": "JyVis | Recherche | Auto & Moto",
        "code": "GA-AUTO",
        "budget": 10,
        "groupes": [
            {
                "nom": "Auto - Malus & Résiliés",
                "url": "/devis/auto",
                "chemins": ("auto", "malus"),
                "mots_cles": [
                    "assurance auto malus", "assurance auto résilié", "assurance auto résilié non paiement",
                    "assurance jeune conducteur", "assurance auto après suspension de permis",
                    "assurance auto résiliée pour sinistre",
                ],
                "titres": [
                    "Assurance Auto Malus", "Résilié ? Nous Vous Assurons", "Jeunes Conducteurs",
                    "Devis Auto Gratuit", "Solutions pour Profils Malus", "Conseiller Dédié",
                ],
                "descriptions": [
                    "Malus, résiliation, jeune permis : un courtier cherche l'assureur qui vous accepte.",
                    "Expliquez votre situation, un conseiller vous propose une solution adaptée.",
                ],
            },
            {
                "nom": "Auto - Général",
                "url": "/devis/auto",
                "chemins": ("auto", "devis"),
                "mots_cles": [
                    "assurance auto", "devis assurance auto", "courtier assurance auto", "assurance voiture",
                    "assurance auto pas cher",
                ],
                "titres": [
                    "Assurance Auto", "Devis Auto Gratuit", "Courtier Assurance Auto",
                    "Comparez les Assureurs", "Conseiller Dédié", "Réponse Rapide",
                ],
                "descriptions": [
                    "Assurance auto au tiers ou tous risques : un courtier compare les offres pour vous.",
                    "Devis auto gratuit en ligne ou sur WhatsApp, avec un conseiller dédié.",
                ],
            },
            {
                "nom": "Moto",
                "url": "/devis/moto",
                "chemins": ("moto", "devis"),
                "mots_cles": [
                    "assurance moto", "assurance scooter", "devis assurance moto", "assurance moto jeune permis",
                    "assurance moto malus",
                ],
                "titres": [
                    "Assurance Moto et Scooter", "Devis Moto Gratuit", "Jeune Permis Moto",
                    "Comparez les Assureurs", "Conseiller Dédié", "Réponse Rapide",
                ],
                "descriptions": [
                    "Assurance moto et scooter, y compris jeunes permis et profils malus. Devis gratuit.",
                    "Un courtier indépendant compare les offres et vous répond rapidement.",
                ],
            },
        ],
    },
]

NB_TITRES, NB_DESCRIPTIONS = 15, 4
COLONNES = (
    ["Campaign", "Campaign Type", "Networks", "Budget", "Budget type", "Bid Strategy Type", "Languages",
     "Final URL suffix", "Campaign Status", "Ad Group", "Ad Group Status", "Keyword", "Criterion Type",
     "Ad type", "Final URL", "Path 1", "Path 2"]
    + [f"Headline {i}" for i in range(1, NB_TITRES + 1)]
    + [f"Description {i}" for i in range(1, NB_DESCRIPTIONS + 1)]
)

erreurs = []


def verifie(texte, limite, quoi):
    if len(texte) > limite:
        erreurs.append(f"{quoi} trop long ({len(texte)} > {limite}) : {texte}")
    return texte


lignes = []
for c in CAMPAGNES:
    base = {k: "" for k in COLONNES}
    lignes.append(base | {
        "Campaign": c["nom"], "Campaign Type": "Search", "Networks": "Google search",
        "Budget": f'{c["budget"]:.2f}', "Budget type": "Daily", "Bid Strategy Type": "Maximize conversions",
        "Languages": "fr", "Campaign Status": "Paused",
        "Final URL suffix": f'utm_source=google&utm_medium=cpc&utm_campaign={c["code"].lower()}',
    })
    for g in c["groupes"]:
        lignes.append(base | {"Campaign": c["nom"], "Ad Group": g["nom"], "Ad Group Status": "Enabled"})
        for mc in g["mots_cles"]:
            for type_ in ("Phrase", "Exact"):
                lignes.append(base | {"Campaign": c["nom"], "Ad Group": g["nom"], "Keyword": mc, "Criterion Type": type_})
        titres = list(dict.fromkeys(g["titres"] + TITRES_COMMUNS))[:NB_TITRES]
        descriptions = (g["descriptions"] + DESCRIPTIONS_COMMUNES)[:NB_DESCRIPTIONS]
        annonce = base | {
            "Campaign": c["nom"], "Ad Group": g["nom"], "Ad type": "Responsive search ad",
            "Final URL": SITE + g["url"],
            "Path 1": verifie(g["chemins"][0], 15, "Chemin"), "Path 2": verifie(g["chemins"][1], 15, "Chemin"),
        }
        for i, t in enumerate(titres, 1):
            annonce[f"Headline {i}"] = verifie(t, 30, "Titre")
        for i, d in enumerate(descriptions, 1):
            annonce[f"Description {i}"] = verifie(d, 90, "Description")
        if len(titres) < 3 or len(descriptions) < 2:
            erreurs.append(f"Annonce incomplète : {g['nom']}")
        lignes.append(annonce)

if erreurs:
    raise SystemExit("\n".join(erreurs))

sortie = ICI / "campagnes-jyvis.csv"
with sortie.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=COLONNES)
    w.writeheader()
    w.writerows(lignes)
nb_mc = sum(1 for l in lignes if l["Keyword"])
print(f"{sortie.name} : {len(CAMPAGNES)} campagnes, {sum(len(c['groupes']) for c in CAMPAGNES)} groupes, {nb_mc} mots clés")
