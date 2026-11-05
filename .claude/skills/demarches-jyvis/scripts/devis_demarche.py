#!/usr/bin/env python3
"""Devis de démarche carte grise / permis de conduire — charte JyVis Assurances.

Usage :
  python3 devis_demarche.py donnees.json sortie.pdf
  python3 devis_demarche.py --liste          # affiche toutes les démarches
Modèles de données : exemples/carte_grise.json et exemples/permis.json.

Ce script produit uniquement le DEVIS de prise en charge de la démarche.
Les titres officiels (carte grise, permis) sont délivrés par l'ANTS ;
on ne modifie jamais un document existant.
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

# Montants nationaux (à revérifier sur service-public.fr / ANTS avant envoi).
Y4_GESTION = 11.00
Y5_ACHEMINEMENT = 2.76
TIMBRE_PERMIS_PERTE = 25.00

ID = "Pièce d'identité"
DOM = "Justificatif de domicile < 6 mois"
MANDAT = "Mandat d'immatriculation cerfa 13757"
CG = "Carte grise actuelle"
PERMIS = "Permis de conduire (recto-verso)"
PHOTO = "e-photo d'identité (code ANTS)"
ASSU = "Attestation d'assurance du véhicule"
CT = "Contrôle technique < 6 mois (véhicule > 4 ans)"

# code -> (libellé, famille, règle de taxes, pièces)
#   règles : "Y1" = Y.1 + Y.4 + Y.5 (+ Y.6) ; "Y45" = Y.4 + Y.5 ; "Y5" = Y.5 seule ;
#            "GRATUIT" ; "TIMBRE25" = timbre fiscal 25 €
CATALOGUE = {
    # ---------------- CARTE GRISE ----------------
    "cg_changement_titulaire": ("Changement de titulaire", "cg", "Y1",
        [ID, DOM, PERMIS, MANDAT, "Carte grise barrée « vendu le … » et signée",
         "Certificat de cession cerfa 15776 + code de cession", CT, ASSU,
         "Demande d'immatriculation cerfa 13750"]),
    "cg_changement_adresse": ("Changement d'adresse", "cg", "ADRESSE",
        [ID, DOM, MANDAT, CG]),
    "cg_duplicata": ("Duplicata (perte, vol, détérioration)", "cg", "Y45",
        [ID, DOM, PERMIS, MANDAT, "Déclaration de perte (cerfa 13753) ou récépissé de vol",
         "Contrôle technique en cours de validité"]),
    "cg_etat_civil": ("Changement d'état civil (nom, mariage…)", "cg", "Y45",
        [ID, DOM, MANDAT, CG, "Acte d'état civil justifiant le changement"]),
    "cg_cotitulaire": ("Ajout / retrait d'un cotitulaire", "cg", "Y1",
        [ID + " de chaque titulaire", DOM, MANDAT, CG,
         "Accord écrit de chaque titulaire", CT, "Demande cerfa 13750"]),
    "cg_modification_technique": ("Modification technique du véhicule", "cg", "Y45",
        [ID, DOM, MANDAT, CG, "Procès-verbal de réception (DREAL) ou attestation constructeur",
         "Contrôle technique"]),
    "cg_correction_erreur": ("Correction d'une erreur sur la carte grise", "cg", "Y5",
        [ID, MANDAT, CG, "Justificatif de la donnée exacte"]),
    "cg_import": ("Immatriculation d'un véhicule importé", "cg", "Y1",
        [ID, DOM, PERMIS, MANDAT, "Titre d'immatriculation étranger", "Facture ou certificat de cession",
         "Certificat de conformité (COC)", "Quitus fiscal (achat UE) ou 846A (hors UE)", CT, ASSU]),
    "cg_succession": ("Carte grise après succession", "cg", "Y1",
        [ID + " de l'héritier", DOM, MANDAT, CG, "Acte de décès",
         "Attestation de dévolution successorale / acte notarié",
         "Accord des cohéritiers", CT, ASSU]),
    "cg_declaration_cession": ("Déclaration de cession (vendeur)", "cg", "GRATUIT",
        [ID, "Certificat de cession cerfa 15776 signé par les deux parties", CG]),
    # ---------------- PERMIS DE CONDUIRE ----------------
    "pc_perte": ("Duplicata de permis — perte", "pc", "TIMBRE25",
        [ID, DOM, PHOTO, "Déclaration de perte (faite en ligne lors de la demande)"]),
    "pc_vol": ("Duplicata de permis — vol", "pc", "GRATUIT",
        [ID, DOM, PHOTO, "Récépissé de déclaration de vol (police / gendarmerie)"]),
    "pc_deterioration": ("Remplacement d'un permis détérioré", "pc", "GRATUIT",
        [ID, DOM, PHOTO, "Permis détérioré (à restituer)"]),
    "pc_renouvellement": ("Renouvellement (fin de validité du titre)", "pc", "GRATUIT",
        [ID, DOM, PHOTO, PERMIS]),
    "pc_etat_civil": ("Changement d'état civil sur le permis", "pc", "GRATUIT",
        [ID + " (nouveau nom)", DOM, PHOTO, PERMIS, "Acte d'état civil justifiant le changement"]),
    "pc_medical": ("Renouvellement après avis médical (pros C/D, suivi)", "pc", "GRATUIT",
        [ID, DOM, PHOTO, PERMIS, "Avis du médecin agréé (cerfa 14880) — consultation à la charge du client"]),
    "pc_echange_etranger": ("Échange d'un permis étranger", "pc", "GRATUIT",
        [ID + " / titre de séjour", DOM, PHOTO, "Permis étranger + traduction officielle",
         "Attestation de droits à conduire < 3 mois (si exigée)"]),
    "pc_apres_suspension": ("Restitution / nouveau permis après suspension ou annulation", "pc", "GRATUIT",
        [ID, DOM, PHOTO, "Décision de suspension / annulation",
         "Avis médical favorable + tests psychotechniques si exigés"]),
}

FAMILLES = {"cg": "CARTE GRISE", "pc": "PERMIS DE CONDUIRE"}


def eur(v):
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")


def calcul(d):
    """Retourne les lignes de taxes officielles, le total taxes, les frais JyVis et le total."""
    _, fam, regle, _ = CATALOGUE[d["demarche"]]
    lignes = []
    if regle == "Y1":
        v = d.get("vehicule", {})
        cv, taux = v.get("puissance_fiscale", 0), d.get("taux_regional_cv", 0)
        y1, note = cv * taux, f"{cv} CV × {eur(taux)}"
        if v.get("electrique"):
            y1, note = 0.0, "véhicule électrique — exonéré"
        elif v.get("age_ans", 0) >= 10:
            y1, note = y1 / 2, note + " ÷ 2 (> 10 ans)"
        lignes += [(f"Taxe régionale Y.1 ({note})", y1),
                   ("Taxe de gestion Y.4", Y4_GESTION),
                   ("Redevance d'acheminement Y.5", Y5_ACHEMINEMENT)]
        if d.get("malus_y6"):
            lignes.append(("Malus / taxe Y.6", float(d["malus_y6"])))
    elif regle == "Y45":
        lignes += [("Taxe de gestion Y.4", Y4_GESTION),
                   ("Redevance d'acheminement Y.5", Y5_ACHEMINEMENT)]
    elif regle == "Y5":
        lignes.append(("Redevance d'acheminement Y.5", Y5_ACHEMINEMENT))
    elif regle == "ADRESSE":
        if d.get("nouvelle_carte"):
            lignes.append(("Redevance d'acheminement Y.5 (nouvelle carte)", Y5_ACHEMINEMENT))
        else:
            lignes.append(("Mise à jour SIV (étiquette) — gratuit", 0.0))
    elif regle == "TIMBRE25":
        lignes.append(("Timbre fiscal (perte de permis)", TIMBRE_PERMIS_PERTE))
    else:
        lignes.append(("Démarche gratuite auprès de l'ANTS", 0.0))
    taxes = round(sum(v for _, v in lignes), 2)
    frais = float(d.get("frais_service", 0))
    return lignes, taxes, frais, round(taxes + frais, 2)


class Doc:
    def __init__(self, path, d):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.d = d
        self.lib, self.fam, _, self.pieces = CATALOGUE[d["demarche"]]
        self.y = H

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
        c.drawRightString(r, H - 26 * mm, f"DEVIS {FAMILLES[self.fam]}")
        c.setFont("Helvetica", 8.5)
        c.drawRightString(r, H - 33 * mm, f"N° {d['numero']}")
        c.drawRightString(r, H - 38 * mm, f"Date : {d['date']}")
        c.drawRightString(r, H - 43 * mm, f"Validité : {d['validite']}")
        self.y = H - hh - 10 * mm
        titre = f"Offre {self.lib}"
        size = 15
        while c.stringWidth(titre, "Helvetica-Bold", size) > W - 2 * M - 60 * mm and size > 10:
            size -= 0.5
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", size)
        c.drawString(M, self.y, titre)
        c.setFillColor(GREY); c.setFont("Helvetica", 9)
        c.drawString(M, self.y - 5.5 * mm,
                     "Démarche réalisée pour votre compte auprès de l'ANTS")
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
                val, size, room = str(val), 8.5, cw * 0.58 - 5 * mm
                while c.stringWidth(val, "Helvetica-Bold", size) > room and size > 6:
                    size -= 0.25
                c.setFillColor(NAVY_DARK); c.setFont("Helvetica-Bold", size)
                c.drawString(x + cw * 0.42, self.y - lh + 1.8 * mm, val)
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

    def build(self):
        d, c = self.d, self.c
        lignes, taxes, frais, total = calcul(d)
        self.header()

        t = d["titulaire"]
        self.section("Client")
        self.table([("Nom / Raison sociale", t["nom"]), ("Adresse", t["adresse"]),
                    ("Téléphone", t.get("tel", "—")), ("E-mail", t.get("mail", "—"))], cols=1)

        if self.fam == "cg":
            v = d["vehicule"]
            self.section("Véhicule (carte grise actuelle)")
            self.table([
                ("Immatriculation (A)", v.get("immatriculation", "—")),
                ("Marque (D.1)", v.get("marque", "—")),
                ("Modèle (D.3)", v.get("modele", "—")),
                ("VIN (E)", v.get("vin", "—")),
                ("1re mise en circ. (B)", v.get("date_mec", "—")),
                ("Puissance fiscale (P.6)", f"{v.get('puissance_fiscale', '—')} CV"),
                ("Énergie (P.3)", v.get("energie", "—")),
                ("Ancien titulaire", d.get("ancien_titulaire", "—")),
            ])
        else:
            p = d["permis"]
            self.section("Permis de conduire")
            self.table([
                ("N° de permis", p.get("numero", "—")),
                ("Catégories", p.get("categories", "—")),
                ("Date de délivrance", p.get("date_delivrance", "—")),
                ("Délivré par", p.get("delivre_par", "—")),
                ("Date de naissance", p.get("date_naissance", "—")),
                ("Motif", p.get("motif", self.lib)),
            ])

        self.section("Détail des frais officiels")
        rows = [(lab, eur(val)) for lab, val in lignes]
        rows.append(("Frais de service JyVis (montage du dossier + suivi)", eur(frais)))
        self.table(rows, cols=1)

        self.cards([("FRAIS OFFICIELS", eur(taxes), True),
                    ("FRAIS DE SERVICE", eur(frais), False),
                    ("TOTAL À RÉGLER", eur(total), False)])

        bh = 15 * mm
        c.setFillColor(colors.white); c.setStrokeColor(NAVY); c.setLineWidth(1.2)
        c.roundRect(M, self.y - bh, W - 2 * M, bh, 2 * mm, stroke=1, fill=1)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10.5)
        c.drawString(M + 4 * mm, self.y - 5.5 * mm, f"Paiement à la signature : {eur(total)}")
        c.setFillColor(GREY); c.setFont("Helvetica", 7.8)
        c.drawString(M + 4 * mm, self.y - 10.5 * mm,
                     "La démarche n'est déposée auprès de l'ANTS qu'après signature du présent "
                     "devis, du mandat et réception du paiement.")
        self.y -= bh + 5 * mm

        self.section("Pièces à fournir")
        pieces = d.get("pieces") or self.pieces
        c.setFont("Helvetica", 8)
        half = math.ceil(len(pieces) / 2)
        cw = (W - 2 * M) / 2
        y0 = self.y - 4.5 * mm
        for i, txt in enumerate(pieces):
            col, row = divmod(i, half)
            x, yy = M + 3 * mm + col * cw, y0 - row * 4.6 * mm
            c.setStrokeColor(NAVY); c.setLineWidth(0.6)
            c.rect(x, yy - 0.3 * mm, 2.6 * mm, 2.6 * mm, stroke=1, fill=0)
            c.setFillColor(NAVY_DARK); c.setFont("Helvetica", 8 if len(txt) < 52 else 7)
            c.drawString(x + 4.5 * mm, yy, txt)
        self.y = y0 - half * 4.6 * mm - 3 * mm

        sh = min(24 * mm, self.y - 16 * mm)
        sw = (W - 2 * M - 6 * mm) / 2
        partner = d.get("partenaire", {}).get("nom", "PARTENAIRE").upper()
        for i, (t1, t2) in enumerate((("BON POUR ACCORD", "Le client — date, nom et signature"),
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


if __name__ == "__main__":
    if sys.argv[1:] == ["--liste"]:
        for code, (lib, fam, regle, _) in CATALOGUE.items():
            print(f"{code:28} {FAMILLES[fam]:20} {regle:9} {lib}")
        sys.exit()
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    if data.get("demarche") not in CATALOGUE:
        sys.exit(f"Démarche inconnue : {data.get('demarche')} (voir --liste)")
    total = Doc(sys.argv[2], data).build()
    print(f"PDF généré : {sys.argv[2]} — total {eur(total)}")
