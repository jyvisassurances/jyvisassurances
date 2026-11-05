#!/usr/bin/env python3
"""Devis / mandat de changement de carte grise — charte JyVis Assurances.

Usage : python3 devis_carte_grise.py donnees.json sortie.pdf
Le fichier JSON suit le modèle de exemples/exemple.json.
"""
import json
import math
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

NAVY = colors.HexColor("#141B6B")
NAVY_DARK = colors.HexColor("#0E1452")
BG = colors.HexColor("#F3F5FA")
ALT = colors.HexColor("#E9EDF6")
GREY = colors.HexColor("#5A607A")
LIGHT = colors.HexColor("#C9CCE8")

W, H = A4
M = 16 * mm

# Taxes fixes ANTS (montants nationaux ; Y.1 dépend de la région, à vérifier).
Y4_GESTION = 11.00
Y5_ACHEMINEMENT = 2.76

DEMARCHES = {
    "changement_titulaire": "CHANGEMENT DE TITULAIRE",
    "changement_adresse": "CHANGEMENT D'ADRESSE",
    "duplicata": "DUPLICATA",
    "modification": "MODIFICATION DU VÉHICULE",
}


def eur(v):
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")


def calcul(d):
    """Retourne la liste des lignes de coût et le total."""
    lignes = []
    t = d["demarche"]
    cv = d["vehicule"].get("puissance_fiscale", 0)
    taux = d.get("taux_regional_cv", 0)
    if t == "changement_titulaire":
        y1 = cv * taux
        if d["vehicule"].get("electrique"):
            y1 = 0.0
        if d["vehicule"].get("age_ans", 0) >= 10:
            y1 = y1 / 2  # demi-tarif véhicule de plus de 10 ans
        lignes.append((f"Taxe régionale Y.1 ({cv} CV × {eur(taux)})", y1))
        lignes.append(("Taxe de gestion Y.4", Y4_GESTION))
        lignes.append(("Redevance d'acheminement Y.5", Y5_ACHEMINEMENT))
        malus = d.get("malus_y6", 0.0)
        if malus:
            lignes.append(("Malus / taxe Y.6", malus))
    elif t == "changement_adresse":
        if d.get("nouvelle_carte", False):  # 4e changement : nouvelle carte éditée
            lignes.append(("Redevance d'acheminement Y.5", Y5_ACHEMINEMENT))
        else:
            lignes.append(("Mise à jour SIV (étiquette) — gratuit", 0.0))
    else:
        lignes.append(("Taxe de gestion Y.4", Y4_GESTION))
        lignes.append(("Redevance d'acheminement Y.5", Y5_ACHEMINEMENT))
    taxes = round(sum(v for _, v in lignes), 2)
    frais = float(d.get("frais_service", 0))
    return lignes, taxes, frais, round(taxes + frais, 2)


class Doc:
    def __init__(self, path, d):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.d = d
        self.y = H

    # --- éléments de charte ---
    def logo(self, x, y, r, col=colors.white):
        c = self.c
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

    def header(self):
        c, d, a = self.c, self.d, self.d["agence"]
        c.setFillColor(BG); c.rect(0, 0, W, H, stroke=0, fill=1)
        c.setStrokeColor(LIGHT); c.setLineWidth(0.6)
        c.rect(8 * mm, 8 * mm, W - 16 * mm, H - 16 * mm, stroke=1, fill=0)
        hh = 62 * mm
        c.setFillColor(NAVY); c.rect(0, H - hh, W, hh, stroke=0, fill=1)
        self.logo(M + 11 * mm, H - 24 * mm, 10 * mm)
        x = M + 26 * mm
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 22)
        c.drawString(x, H - 22 * mm, "JYVIS ASSURANCES")
        c.setFillColor(LIGHT); c.setFont("Helvetica-Oblique", 9.5)
        c.drawString(x, H - 28 * mm, "« Assurer son quotidien, c'est assurer son avenir »")
        c.setFont("Helvetica", 8.5)
        c.drawString(x, H - 36 * mm, a["adresse"])
        c.drawString(x, H - 41 * mm, f"ORIAS {a['orias']}  •  Tél. {a['tel']}")
        c.drawString(x, H - 46 * mm, a["mail"])
        r = W - M
        c.setFillColor(LIGHT); c.setFont("Helvetica-Bold", 8)
        c.drawRightString(r, H - 18 * mm, "COURTIER DES PROFESSIONNELS")
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 13)
        c.drawRightString(r, H - 26 * mm, "DEVIS CARTE GRISE")
        c.setFont("Helvetica", 8.5)
        c.drawRightString(r, H - 33 * mm, f"N° {d['numero']}")
        c.drawRightString(r, H - 38 * mm, f"Date : {d['date']}")
        c.drawRightString(r, H - 43 * mm, f"Validité : {d['validite']}")
        self.y = H - hh - 10 * mm
        # titre + bloc partenaire
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 15)
        c.drawString(M, self.y, f"Offre {DEMARCHES[d['demarche']].capitalize()}")
        c.setFillColor(GREY); c.setFont("Helvetica", 9)
        c.drawString(M, self.y - 5.5 * mm,
                     "Démarche d'immatriculation réalisée pour votre compte (SIV / ANTS)")
        p = d.get("partenaire", {})
        bw, bh = 55 * mm, 15 * mm
        c.setFillColor(colors.white); c.setStrokeColor(LIGHT)
        c.roundRect(W - M - bw, self.y - 8 * mm, bw, bh, 2 * mm, stroke=1, fill=1)
        c.setFillColor(GREY); c.setFont("Helvetica-Bold", 7)
        c.drawString(W - M - bw + 3 * mm, self.y + 3 * mm, "PARTENAIRE")
        c.setFillColor(colors.HexColor(p.get("couleur", "#141B6B")))
        c.setFont("Helvetica-Bold", 11)
        c.drawString(W - M - bw + 3 * mm, self.y - 3.5 * mm, p.get("nom", "—"))
        self.y -= 15 * mm

    def section(self, titre):
        c = self.c
        c.setFillColor(NAVY); c.rect(M, self.y - 6 * mm, W - 2 * M, 6 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 9)
        c.drawString(M + 3 * mm, self.y - 4.2 * mm, titre.upper())
        self.y -= 6 * mm

    def table(self, rows, cols=2, lh=5.6 * mm):
        """rows : liste de (clé, valeur) ; affichées sur `cols` colonnes."""
        c = self.c
        cw = (W - 2 * M) / cols
        n = math.ceil(len(rows) / cols)
        for i in range(n):
            if i % 2 == 0:
                c.setFillColor(ALT); c.rect(M, self.y - lh, W - 2 * M, lh, stroke=0, fill=1)
            for j in range(cols):
                k = i + j * n
                if k >= len(rows):
                    continue
                key, val = rows[k]
                x = M + j * cw + 3 * mm
                c.setFillColor(GREY); c.setFont("Helvetica", 8)
                c.drawString(x, self.y - lh + 1.8 * mm, key)
                c.setFillColor(NAVY_DARK); c.setFont("Helvetica-Bold", 8.5)
                c.drawString(x + cw * 0.42, self.y - lh + 1.8 * mm, str(val))
            self.y -= lh
        self.y -= 3 * mm

    def cards(self, items, h=20 * mm):
        c = self.c
        gap = 4 * mm
        cw = (W - 2 * M - gap * (len(items) - 1)) / len(items)
        for i, (lab, val, full) in enumerate(items):
            x = M + i * (cw + gap)
            c.setFillColor(NAVY if full else colors.white)
            c.setStrokeColor(NAVY)
            c.roundRect(x, self.y - h, cw, h, 2 * mm, stroke=1, fill=1)
            c.setFillColor(LIGHT if full else GREY); c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x + cw / 2, self.y - 7 * mm, lab)
            c.setFillColor(colors.white if full else NAVY); c.setFont("Helvetica-Bold", 15)
            c.drawCentredString(x + cw / 2, self.y - 15 * mm, val)
        self.y -= h + 4 * mm

    def footer(self):
        c, a = self.c, self.d["agence"]
        p = self.d.get("partenaire", {}).get("nom", "PARTENAIRE")
        c.setFillColor(NAVY); c.rect(0, 0, W, 12 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Helvetica", 7.5)
        c.drawCentredString(W / 2, 4.8 * mm,
                            f"JYVIS ASSURANCES × {p.upper()}  •  {a['adresse']}  •  "
                            f"ORIAS {a['orias']}  •  {a['tel']}  •  {a['mail']}")

    # --- document ---
    def build(self):
        d, c = self.d, self.c
        lignes, taxes, frais, total = calcul(d)
        self.header()

        t = d["titulaire"]
        self.section("Nouveau titulaire")
        self.table([
            ("Nom / Raison sociale", t["nom"]),
            ("Adresse", t["adresse"]),
            ("Téléphone", t.get("tel", "—")),
            ("E-mail", t.get("mail", "—")),
        ], cols=1)

        v = d["vehicule"]
        self.section("Véhicule (carte grise actuelle)")
        self.table([
            ("Immatriculation (A)", v["immatriculation"]),
            ("Marque (D.1)", v["marque"]),
            ("Modèle (D.3)", v["modele"]),
            ("VIN (E)", v["vin"]),
            ("1re mise en circ. (B)", v["date_mec"]),
            ("Puissance fiscale (P.6)", f"{v['puissance_fiscale']} CV"),
            ("Énergie (P.3)", v.get("energie", "—")),
            ("Ancien titulaire", d.get("ancien_titulaire", "—")),
        ])

        self.section("Détail des taxes ANTS")
        rows = [(lab, eur(val)) for lab, val in lignes]
        rows.append(("Frais de service JyVis (démarche + envoi)", eur(frais)))
        self.table(rows, cols=1)

        self.cards([
            ("TAXES ANTS", eur(taxes), True),
            ("FRAIS DE SERVICE", eur(frais), False),
            ("TOTAL À RÉGLER", eur(total), False),
        ])

        # encadré paiement
        bh = 15 * mm
        c.setFillColor(colors.white); c.setStrokeColor(NAVY); c.setLineWidth(1.2)
        c.roundRect(M, self.y - bh, W - 2 * M, bh, 2 * mm, stroke=1, fill=1)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10.5)
        c.drawString(M + 4 * mm, self.y - 5.5 * mm,
                     f"Paiement à la signature : {eur(total)}")
        c.setFillColor(GREY); c.setFont("Helvetica", 7.8)
        c.drawString(M + 4 * mm, self.y - 10.5 * mm,
                     "La démarche n'est déposée sur le SIV qu'après signature du présent "
                     "devis, du mandat cerfa 13757 et réception du paiement.")
        self.y -= bh + 5 * mm

        self.section("Pièces à fournir")
        pieces = d.get("pieces") or pieces_par_defaut(d["demarche"])
        c.setFont("Helvetica", 8)
        half = math.ceil(len(pieces) / 2)
        cw = (W - 2 * M) / 2
        y0 = self.y - 4.5 * mm
        for i, p in enumerate(pieces):
            col, row = divmod(i, half)
            x, yy = M + 3 * mm + col * cw, y0 - row * 4.6 * mm
            c.setStrokeColor(NAVY); c.setLineWidth(0.6)
            c.rect(x, yy - 0.3 * mm, 2.6 * mm, 2.6 * mm, stroke=1, fill=0)
            c.setFillColor(NAVY_DARK)
            c.drawString(x + 4.5 * mm, yy, p)
        self.y = y0 - half * 4.6 * mm - 3 * mm

        # signatures
        sh = 24 * mm
        sw = (W - 2 * M - 6 * mm) / 2
        partner = d.get("partenaire", {}).get("nom", "PARTENAIRE").upper()
        for i, (t1, t2) in enumerate((
                ("BON POUR ACCORD", "Le client — date, nom et signature"),
                (f"JYVIS ASSURANCES × {partner}", "Le conseiller"))):
            x = M + i * (sw + 6 * mm)
            c.setFillColor(colors.white); c.setStrokeColor(LIGHT); c.setLineWidth(0.8)
            c.roundRect(x, self.y - sh, sw, sh, 2 * mm, stroke=1, fill=1)
            c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 8.5)
            c.drawString(x + 3 * mm, self.y - 5 * mm, t1)
            c.setFillColor(GREY); c.setFont("Helvetica", 7.5)
            c.drawString(x + 3 * mm, self.y - 9.5 * mm, t2)
        self.footer()
        c.showPage(); c.save()
        return total


def pieces_par_defaut(demarche):
    base = ["Pièce d'identité du titulaire", "Justificatif de domicile < 6 mois",
            "Permis de conduire (catégorie du véhicule)", "Mandat d'immatriculation cerfa 13757"]
    if demarche == "changement_titulaire":
        return base + ["Carte grise barrée, datée, signée « vendu le … »",
                       "Certificat de cession cerfa 15776 + code de cession",
                       "Contrôle technique < 6 mois (véhicule > 4 ans)",
                       "Attestation d'assurance du véhicule",
                       "Demande d'immatriculation cerfa 13750"]
    if demarche == "changement_adresse":
        return base + ["Carte grise actuelle (copie)"]
    if demarche == "duplicata":
        return base + ["Déclaration de perte / vol (cerfa 13753 ou récépissé)",
                       "Contrôle technique en cours de validité"]
    return base + ["Carte grise actuelle", "Justificatif de la modification"]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    total = Doc(sys.argv[2], data).build()
    print(f"PDF généré : {sys.argv[2]} — total {eur(total)}")
