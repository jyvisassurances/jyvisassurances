#!/usr/bin/env python3
"""Génère les workflows n8n de l'agent WhatsApp JyVis Assurances.

Usage : python3 build.py
Les fichiers sont écrits dans workflows/. La source des consignes de l'agent est
prompt-agent.md : après l'avoir modifié, relancez ce script puis l'installation.
"""
import json
import pathlib
import uuid

ICI = pathlib.Path(__file__).parent
SORTIE = ICI / "workflows"
PROMPT = (ICI / "prompt-agent.md").read_text(encoding="utf-8")

PG_CRED = {"postgres": {"id": "jyvisPostgres0001", "name": "JyVis Postgres"}}
SMTP_CRED = {"smtp": {"id": "jyvisSmtp00000001", "name": "JyVis SMTP"}}

# Uuid stable pour chaque webhook (même URL après réimport).
NS = uuid.UUID("7f1c6a52-3f7e-4c43-9b8a-1f0f5c2d9a10")


def wid(nom):
    return str(uuid.uuid5(NS, nom))


def node(nom, type_, version, pos, params, **extra):
    n = {
        "id": wid("node:" + nom),
        "name": nom,
        "type": type_,
        "typeVersion": version,
        "position": list(pos),
        "parameters": params,
    }
    n.update(extra)
    return n


def code(nom, pos, js, **extra):
    return node(nom, "n8n-nodes-base.code", 2, pos, {"jsCode": js.strip() + "\n"}, **extra)


def webhook(nom, pos, methode, chemin, reponse):
    return node(
        nom, "n8n-nodes-base.webhook", 2, pos,
        {"httpMethod": methode, "path": chemin, "responseMode": reponse, "options": {}},
        webhookId=wid("webhook:" + methode + chemin),
    )


def sql(nom, pos, requete, params_expr, **extra):
    return node(
        nom, "n8n-nodes-base.postgres", 2.6, pos,
        {
            "operation": "executeQuery",
            "query": requete.strip(),
            "options": {"queryReplacement": "={{ " + params_expr + " }}"},
        },
        credentials=PG_CRED, **extra,
    )


def si(nom, pos, expression):
    """Nœud IF : sortie 0 si l'expression est vraie, 1 sinon."""
    return node(
        nom, "n8n-nodes-base.if", 2.2, pos,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [{
                    "id": wid("cond:" + nom),
                    "leftValue": "={{ " + expression + " }}",
                    "rightValue": "",
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                }],
                "combinator": "and",
            },
            "looseTypeValidation": True,
            "options": {},
        },
    )


def repondre(nom, pos, code_http, corps="", entetes=None, type_reponse="text"):
    opts = {"responseCode": code_http}
    if entetes:
        opts["responseHeaders"] = {"entries": [{"name": k, "value": v} for k, v in entetes.items()]}
    params = {"respondWith": type_reponse, "options": opts}
    if type_reponse == "text":
        params["responseBody"] = corps
    return node(nom, "n8n-nodes-base.respondToWebhook", 1.1, pos, params)


def envoi_whatsapp(nom, pos):
    """Envoie $json.reponse au numéro $json.wa_id via l'API WhatsApp Cloud."""
    return node(
        nom, "n8n-nodes-base.httpRequest", 4.2, pos,
        {
            "method": "POST",
            "url": "=https://graph.facebook.com/{{ $env.GRAPH_API_VERSION || 'v23.0' }}/{{ $env.WHATSAPP_PHONE_NUMBER_ID }}/messages",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Authorization", "value": "=Bearer {{ $env.WHATSAPP_ACCESS_TOKEN }}"},
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ messaging_product: 'whatsapp', recipient_type: 'individual', to: $json.wa_id, type: 'text', text: { preview_url: false, body: $json.reponse } }) }}",
            "options": {"timeout": 30000},
        },
        retryOnFail=True, maxTries=3, waitBetweenTries=2000, onError="continueRegularOutput",
    )


def workflow(id_, nom, nodes, liens):
    connexions = {}
    for src, sortie, dst in liens:
        main = connexions.setdefault(src, {"main": []})["main"]
        while len(main) <= sortie:
            main.append([])
        main[sortie].append({"node": dst, "type": "main", "index": 0})
    return {
        "id": id_,
        "name": nom,
        "active": False,
        "nodes": nodes,
        "connections": connexions,
        "settings": {"executionOrder": "v1", "timezone": "Europe/Paris", "saveDataSuccessExecution": "all"},
        "pinData": {},
    }


# ---------------------------------------------------------------- schéma de réponse de l'agent
SCHEMA = {
    "type": "object",
    "properties": {
        "reponse": {"type": "string"},
        "produit": {"type": "string", "enum": ["auto", "moto", "habitation", "rc_pro", "decennale", "sante", "prevoyance", "autre", "inconnu"]},
        "nom": {"type": "string"},
        "infos": {"type": "array", "items": {
            "type": "object",
            "properties": {"cle": {"type": "string"}, "valeur": {"type": "string"}},
            "required": ["cle", "valeur"],
            "additionalProperties": False,
        }},
        "resume": {"type": "string"},
        "score": {"type": "string", "enum": ["chaud", "tiede", "froid"]},
        "statut": {"type": "string", "enum": ["en_cours", "qualifie"]},
        "transfert_conseiller": {"type": "boolean"},
    },
    "required": ["reponse", "produit", "nom", "infos", "resume", "score", "statut", "transfert_conseiller"],
    "additionalProperties": False,
}

MSG_SECOURS = "Merci pour votre message. Un conseiller JyVis Assurances revient vers vous très rapidement."

# ======================================================================= 1. Agent WhatsApp
JS_VERIF = r"""
const q = $input.first().json.query || {};
const ok = q['hub.mode'] === 'subscribe' && !!$env.WHATSAPP_VERIFY_TOKEN && q['hub.verify_token'] === $env.WHATSAPP_VERIFY_TOKEN;
return [{ json: { ok, challenge: ok ? String(q['hub.challenge'] ?? '') : 'Forbidden' } }];
"""

JS_EXTRAIRE = r"""
// 1) Authenticité : signature HMAC envoyée par Meta avec le secret de l'application.
const crypto = require('crypto');
const item = $input.first();
const secret = $env.WHATSAPP_APP_SECRET || '';
const signature = String(item.json.headers?.['x-hub-signature-256'] || '');
if (!secret || !item.binary?.data) return [];
const brut = await this.helpers.getBinaryDataBuffer(0, 'data');
const attendu = 'sha256=' + crypto.createHmac('sha256', secret).update(brut).digest('hex');
const a = Buffer.from(signature), b = Buffer.from(attendu);
if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return [];

// 2) Extraction des messages (les accusés de lecture / statuts sont ignorés).
const corps = JSON.parse(brut.toString('utf8'));
const sorties = [];
for (const entree of corps.entry || []) {
  for (const changement of entree.changes || []) {
    const v = changement.value || {};
    if (String(v.metadata?.phone_number_id) !== String($env.WHATSAPP_PHONE_NUMBER_ID)) continue;
    const noms = Object.fromEntries((v.contacts || []).map(c => [c.wa_id, c.profile?.name || '']));
    for (const m of v.messages || []) {
      let texte;
      switch (m.type) {
        case 'text': texte = m.text?.body; break;
        case 'button': texte = m.button?.text; break;
        case 'interactive': texte = m.interactive?.button_reply?.title || m.interactive?.list_reply?.title; break;
        case 'audio': texte = '[audio reçu]'; break;
        case 'image': texte = '[photo reçue]' + (m.image?.caption ? ' ' + m.image.caption : ''); break;
        case 'video': texte = '[vidéo reçue]' + (m.video?.caption ? ' ' + m.video.caption : ''); break;
        case 'document': texte = '[document reçu]' + (m.document?.caption ? ' ' + m.document.caption : ''); break;
        case 'location': texte = '[localisation reçue]'; break;
        case 'sticker': case 'reaction': continue;
        default: texte = '[message non pris en charge]';
      }
      texte = String(texte || '').slice(0, 4000);
      if (!texte) continue;
      sorties.push({ json: {
        wa_id: String(m.from),
        nom: noms[m.from] || '',
        texte,
        message_id: String(m.id),
        stop: /^\s*(stop|arr[eê]t|d[ée]sinscription)\s*$/i.test(texte),
        start: /^\s*(start|reprendre)\s*$/i.test(texte),
      } });
    }
  }
}
return sorties;
"""

SQL_ENREGISTRER = """
WITH p AS (
  INSERT INTO prospects (wa_id, nom, dernier_entrant, opt_out)
  VALUES ($1, NULLIF($2, ''), now(), $5::boolean)
  ON CONFLICT (wa_id) DO UPDATE SET
    nom = COALESCE(prospects.nom, EXCLUDED.nom),
    dernier_entrant = now(),
    relances = 0,
    opt_out = CASE WHEN $6::boolean THEN false ELSE prospects.opt_out OR EXCLUDED.opt_out END,
    maj_le = now()
  RETURNING id, wa_id, mode, opt_out
), m AS (
  INSERT INTO messages (prospect_id, sens, texte, wa_message_id)
  SELECT p.id, 'entrant', $3, $4 FROM p
  ON CONFLICT (wa_message_id) DO NOTHING
  RETURNING id
)
SELECT p.id AS prospect_id, p.wa_id, p.mode, p.opt_out,
       (SELECT id FROM m) AS message_id,
       $5::boolean AS stop, $6::boolean AS start
FROM p;
"""

JS_TRIER = r"""
const sorties = [];
for (const { json: r } of $input.all()) {
  if (!r.message_id) continue;                       // message déjà traité (Meta renvoie parfois)
  const base = { prospect_id: r.prospect_id, wa_id: r.wa_id, message_id: r.message_id };
  if (r.stop) {
    sorties.push({ json: { ...base, route: 'direct', reponse: "C'est noté, vous ne recevrez plus de messages de JyVis Assurances. Écrivez START si vous souhaitez reprendre." } });
  } else if (r.start) {
    sorties.push({ json: { ...base, route: 'direct', reponse: "Bienvenue à nouveau ! Dites-moi en quoi JyVis Assurances peut vous aider." } });
  } else if (!r.opt_out && r.mode === 'ia') {
    sorties.push({ json: { ...base, route: 'claude' } });
  }
  // mode « humain » : le conseiller répond depuis le tableau de bord, l'agent se tait.
}
return sorties;
"""

SQL_CHARGER = """
SELECT p.id AS prospect_id, p.wa_id, p.nom, p.produit, p.infos, p.resume, p.score, p.statut, p.mode, p.opt_out,
       (SELECT max(id) FROM messages WHERE prospect_id = p.id AND sens = 'entrant') = $2::bigint AS dernier,
       COALESCE((SELECT json_agg(h ORDER BY h.cree_le, h.id) FROM (
          SELECT id, sens, texte, cree_le FROM messages WHERE prospect_id = p.id
          ORDER BY cree_le DESC, id DESC LIMIT 40) h), '[]'::json) AS historique
FROM prospects p WHERE p.id = $1::bigint;
"""

JS_PREPARER = r"""
const PROMPT = __PROMPT__;
const SCHEMA = __SCHEMA__;
const systeme = PROMPT
  .replace('{{ORIAS}}', $env.CABINET_ORIAS || 'non renseigné')
  .replace('{{HORAIRES}}', $env.CABINET_HORAIRES || 'du lundi au vendredi, 9 h - 18 h');

const sorties = [];
for (const { json: p } of $input.all()) {
  // Plusieurs messages envoyés d'affilée : seule la dernière exécution répond, avec tout l'historique.
  if (!p.dernier || p.mode !== 'ia' || p.opt_out) continue;

  const messages = [];
  for (const m of p.historique || []) {
    const role = m.sens === 'entrant' ? 'user' : 'assistant';
    const texte = m.sens === 'conseiller' ? '[Message du conseiller] ' + m.texte : m.texte;
    const dernier = messages[messages.length - 1];
    if (dernier && dernier.role === role) dernier.content += '\n' + texte;
    else messages.push({ role, content: texte });
  }
  while (messages.length && messages[0].role !== 'user') messages.shift();
  if (!messages.length || messages[messages.length - 1].role !== 'user') continue;

  const fiche = { nom: p.nom, produit: p.produit, infos: p.infos, resume: p.resume, score: p.score, statut: p.statut };
  sorties.push({ json: {
    prospect_id: p.prospect_id,
    wa_id: p.wa_id,
    fiche,
    requete: {
      model: $env.CLAUDE_MODEL || 'claude-opus-5-5',
      max_tokens: 8000,
      fallbacks: 'default',
      output_config: { effort: 'low', format: { type: 'json_schema', schema: SCHEMA } },
      system: [
        { type: 'text', text: systeme, cache_control: { type: 'ephemeral' } },
        { type: 'text', text: 'Fiche actuelle du prospect (JSON) : ' + JSON.stringify(fiche) },
      ],
      messages,
    },
  } });
}
return sorties;
"""

JS_LIRE = r"""
const SECOURS = __SECOURS__;
const sorties = [];
const items = $input.all();
for (let i = 0; i < items.length; i++) {
  const r = items[i].json;
  const ctx = $('Préparer l’appel à Claude').itemMatching(i).json;
  let d = null, erreur = '';
  if (r.error) erreur = 'API Claude : ' + String(r.error.message || JSON.stringify(r.error)).slice(0, 200);
  else if (r.stop_reason === 'refusal') erreur = 'Claude a refusé de répondre';
  else if (r.stop_reason === 'max_tokens') erreur = 'Réponse de Claude tronquée';
  else {
    const bloc = (r.content || []).find(b => b.type === 'text');
    try { d = JSON.parse(bloc.text); } catch (e) { erreur = 'Réponse de Claude illisible'; }
  }
  if (!d || !String(d.reponse || '').trim()) {
    d = { reponse: SECOURS, transfert_conseiller: true, infos: [] };
    erreur = erreur || 'Réponse vide';
  }
  const infos = {};
  for (const x of d.infos || []) if (x.cle) infos[x.cle] = x.valeur;
  sorties.push({ json: {
    prospect_id: ctx.prospect_id,
    wa_id: ctx.wa_id,
    reponse: String(d.reponse).slice(0, 4000),
    sens: 'agent',
    nom: d.nom || '',
    produit: d.produit && d.produit !== 'inconnu' ? d.produit : '',
    infos,
    resume: (d.resume || '') + (erreur ? ' [Incident agent : ' + erreur + ']' : ''),
    score: d.score || '',
    statut: d.statut || '',
    transfert: !!d.transfert_conseiller,
  } });
}
return sorties;
"""

JS_NORMALISER = r"""
return $input.all().map(({ json: j }) => ({ json: {
  prospect_id: j.prospect_id, wa_id: j.wa_id, reponse: j.reponse, sens: j.sens || 'agent',
  nom: j.nom || '', produit: j.produit || '', infos: j.infos || {}, resume: j.resume || '',
  score: j.score || '', statut: j.statut || '', transfert: !!j.transfert,
} }));
"""

SQL_MAJ = """
WITH avant AS (SELECT alerte_envoyee FROM prospects WHERE id = $1::bigint),
u AS (
  UPDATE prospects SET
    nom = COALESCE(NULLIF($2, ''), nom),
    produit = COALESCE(NULLIF($3, ''), produit),
    infos = infos || $4::jsonb,
    resume = COALESCE(NULLIF($5, ''), resume),
    score = COALESCE(NULLIF($6, ''), score),
    statut = CASE WHEN statut IN ('nouveau', 'en_cours', 'qualifie') AND NULLIF($7, '') IS NOT NULL THEN $7
                  WHEN statut = 'nouveau' THEN 'en_cours' ELSE statut END,
    mode = CASE WHEN $8::boolean THEN 'humain' ELSE mode END,
    alerte_envoyee = alerte_envoyee OR $8::boolean OR $6 = 'chaud',
    dernier_sortant = CASE WHEN $10::boolean THEN now() ELSE dernier_sortant END,
    maj_le = now()
  WHERE id = $1::bigint
  RETURNING *
), m AS (
  INSERT INTO messages (prospect_id, sens, texte)
  VALUES ($1::bigint, $9, CASE WHEN $10::boolean THEN $11 ELSE '[NON ENVOYÉ] ' || $11 END)
)
SELECT u.id, u.wa_id, u.nom, u.produit, u.resume, u.score, u.statut, u.infos,
       (NOT (SELECT alerte_envoyee FROM avant)) AND ($8::boolean OR $6 = 'chaud') AS doit_alerter
FROM u;
"""

# Paramètres : on lit le message préparé (avant l'envoi) et le résultat de l'envoi ($json).
PARAMS_MAJ = (
    "(() => { const m = $('Message à envoyer').item.json; const envoye = !!($json.messages && $json.messages[0] && $json.messages[0].id);"
    " return [m.prospect_id, m.nom, m.produit, JSON.stringify(m.infos || {}), m.resume, m.score, m.statut,"
    " m.transfert || !envoye, m.sens, envoye, m.reponse]; })()"
)

JS_EMAIL = r"""
const echap = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
return $input.all().map(({ json: p }) => {
  const infos = Object.entries(p.infos || {}).map(([k, v]) => `<li><b>${echap(k)}</b> : ${echap(v)}</li>`).join('');
  const lien = `https://${$env.N8N_HOST}/webhook/jyvis?id=${p.id}`;
  return { json: {
    sujet: `[JyVis WhatsApp] Prospect ${p.score === 'chaud' ? 'CHAUD' : 'à reprendre'} : ${p.nom || '+' + p.wa_id}`,
    html: `<p><b>${echap(p.nom || 'Prospect')}</b> (+${echap(p.wa_id)}) — ${echap(p.produit || 'produit non précisé')}, score <b>${echap(p.score)}</b>.</p>
<p>${echap(p.resume)}</p><ul>${infos}</ul><p><a href="${lien}">Ouvrir la conversation</a></p>`,
  } };
});
"""

agent = workflow(
    "jyvisWaAgent00001", "JyVis – Agent WhatsApp",
    [
        webhook("WhatsApp – vérification", (0, 0), "GET", "whatsapp", "responseNode"),
        code("Vérifier le jeton Meta", (240, 0), JS_VERIF),
        repondre("Répondre à Meta", (480, 0), "={{ $json.ok ? 200 : 403 }}", "={{ $json.challenge }}"),

        dict(webhook("WhatsApp – messages", (0, 300), "POST", "whatsapp", "onReceived"),
             parameters={"httpMethod": "POST", "path": "whatsapp", "responseMode": "onReceived", "options": {"rawBody": True}}),
        code("Contrôler et extraire", (240, 300), JS_EXTRAIRE),
        sql("Enregistrer le message reçu", (480, 300), SQL_ENREGISTRER,
            "[$json.wa_id, $json.nom, $json.texte, $json.message_id, $json.stop, $json.start]"),
        code("Trier", (720, 300), JS_TRIER),
        si("Réponse automatique ?", (960, 300), "$json.route === 'direct'"),
        node("Attendre la fin de saisie", "n8n-nodes-base.wait", 1.1, (1200, 420), {"amount": 8}),
        sql("Charger la conversation", (1440, 420), SQL_CHARGER, "[$json.prospect_id, $json.message_id]"),
        code("Préparer l’appel à Claude", (1680, 420),
             JS_PREPARER.replace("__PROMPT__", json.dumps(PROMPT, ensure_ascii=False))
                        .replace("__SCHEMA__", json.dumps(SCHEMA))),
        node(
            "Claude", "n8n-nodes-base.httpRequest", 4.2, (1920, 420),
            {
                "method": "POST",
                "url": "https://api.anthropic.com/v1/messages",
                "sendHeaders": True,
                "headerParameters": {"parameters": [
                    {"name": "x-api-key", "value": "={{ $env.ANTHROPIC_API_KEY }}"},
                    {"name": "anthropic-version", "value": "2026-10-21"},
                    {"name": "anthropic-beta", "value": "server-side-fallback-2026-07-01"},
                ]},
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ JSON.stringify($json.requete) }}",
                "options": {"timeout": 180000},
            },
            retryOnFail=True, maxTries=3, waitBetweenTries=5000, onError="continueRegularOutput",
        ),
        code("Lire la réponse de Claude", (2160, 420), JS_LIRE.replace("__SECOURS__", json.dumps(MSG_SECOURS, ensure_ascii=False))),
        code("Message à envoyer", (2400, 300), JS_NORMALISER),
        envoi_whatsapp("Envoyer sur WhatsApp", (2640, 300)),
        sql("Mettre à jour la fiche", (2880, 300), SQL_MAJ, PARAMS_MAJ),
        si("Alerter le conseiller ?", (3120, 300), "$json.doit_alerter === true && !!$env.CONSEILLER_EMAIL"),
        code("Préparer l’alerte", (3360, 300), JS_EMAIL),
        node(
            "E-mail au conseiller", "n8n-nodes-base.emailSend", 2.1, (3600, 300),
            {
                "fromEmail": "={{ $env.SMTP_FROM || $env.SMTP_USER }}",
                "toEmail": "={{ $env.CONSEILLER_EMAIL }}",
                "subject": "={{ $json.sujet }}",
                "emailFormat": "html",
                "html": "={{ $json.html }}",
                "options": {},
            },
            credentials=SMTP_CRED, onError="continueRegularOutput",
        ),
    ],
    [
        ("WhatsApp – vérification", 0, "Vérifier le jeton Meta"),
        ("Vérifier le jeton Meta", 0, "Répondre à Meta"),
        ("WhatsApp – messages", 0, "Contrôler et extraire"),
        ("Contrôler et extraire", 0, "Enregistrer le message reçu"),
        ("Enregistrer le message reçu", 0, "Trier"),
        ("Trier", 0, "Réponse automatique ?"),
        ("Réponse automatique ?", 0, "Message à envoyer"),
        ("Réponse automatique ?", 1, "Attendre la fin de saisie"),
        ("Attendre la fin de saisie", 0, "Charger la conversation"),
        ("Charger la conversation", 0, "Préparer l’appel à Claude"),
        ("Préparer l’appel à Claude", 0, "Claude"),
        ("Claude", 0, "Lire la réponse de Claude"),
        ("Lire la réponse de Claude", 0, "Message à envoyer"),
        ("Message à envoyer", 0, "Envoyer sur WhatsApp"),
        ("Envoyer sur WhatsApp", 0, "Mettre à jour la fiche"),
        ("Mettre à jour la fiche", 0, "Alerter le conseiller ?"),
        ("Alerter le conseiller ?", 0, "Préparer l’alerte"),
        ("Préparer l’alerte", 0, "E-mail au conseiller"),
    ],
)

# ======================================================================= 2. Relances
SQL_A_RELANCER = """
SELECT id AS prospect_id, wa_id, nom FROM prospects
WHERE mode = 'ia' AND NOT opt_out AND relances = 0
  AND statut IN ('nouveau', 'en_cours')
  AND dernier_sortant > dernier_entrant
  AND dernier_sortant < now() - interval '3 hours'
  AND dernier_entrant > now() - interval '23 hours'      -- fenêtre gratuite de 24 h de WhatsApp
  AND extract(hour FROM now() AT TIME ZONE 'Europe/Paris') BETWEEN 9 AND 19
LIMIT 50;
"""

JS_RELANCE = r"""
return $input.all().filter(i => i.json.wa_id).map(({ json: p }) => {
  const prenom = String(p.nom || '').split(' ')[0];
  return { json: {
    prospect_id: p.prospect_id, wa_id: p.wa_id, sens: 'relance',
    reponse: `Bonjour${prenom ? ' ' + prenom : ''}, je reviens vers vous pour votre demande d'assurance. Souhaitez-vous que nous continuions ? Il ne me manque que quelques informations pour transmettre votre dossier à un conseiller JyVis Assurances.`,
  } };
});
"""

SQL_RELANCE_FAITE = """
WITH u AS (
  UPDATE prospects SET relances = relances + 1,
    dernier_sortant = CASE WHEN $2::boolean THEN now() ELSE dernier_sortant END, maj_le = now()
  WHERE id = $1::bigint RETURNING id
)
INSERT INTO messages (prospect_id, sens, texte)
SELECT id, 'relance', CASE WHEN $2::boolean THEN $3 ELSE '[NON ENVOYÉ] ' || $3 END FROM u
RETURNING id;
"""

relances = workflow(
    "jyvisWaRelance001", "JyVis – Relances WhatsApp",
    [
        node("Toutes les heures", "n8n-nodes-base.scheduleTrigger", 1.2, (0, 0),
             {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}}),
        sql("Prospects à relancer", (240, 0), SQL_A_RELANCER, "[]"),
        code("Texte de relance", (480, 0), JS_RELANCE),
        envoi_whatsapp("Envoyer sur WhatsApp", (720, 0)),
        sql("Noter la relance", (960, 0), SQL_RELANCE_FAITE,
            "(() => { const m = $('Texte de relance').item.json; return [m.prospect_id, !!($json.messages && $json.messages[0] && $json.messages[0].id), m.reponse]; })()"),
    ],
    [
        ("Toutes les heures", 0, "Prospects à relancer"),
        ("Prospects à relancer", 0, "Texte de relance"),
        ("Texte de relance", 0, "Envoyer sur WhatsApp"),
        ("Envoyer sur WhatsApp", 0, "Noter la relance"),
    ],
)
# La requête « Prospects à relancer » n'a pas de paramètre.
relances["nodes"][1]["parameters"]["options"] = {}

# ======================================================================= 3. Tableau de bord
JS_AUTH = r"""
// Accès protégé par identifiant / mot de passe (variables TABLEAU_UTILISATEUR et TABLEAU_MOT_DE_PASSE).
const crypto = require('crypto');
function egal(a, b) {
  const x = crypto.createHash('sha256').update(String(a)).digest();
  const y = crypto.createHash('sha256').update(String(b)).digest();
  return crypto.timingSafeEqual(x, y);
}
const j = $input.first().json;
const h = String(j.headers?.authorization || '');
let ok = false;
if ($env.TABLEAU_MOT_DE_PASSE && h.startsWith('Basic ')) {
  const [u, ...reste] = Buffer.from(h.slice(6), 'base64').toString('utf8').split(':');
  ok = egal(u, $env.TABLEAU_UTILISATEUR || 'jyvis') & egal(reste.join(':'), $env.TABLEAU_MOT_DE_PASSE);
}
__SUITE__
"""

SUITE_PAGE = r"""
const id = /^\d{1,18}$/.test(String(j.query?.id || '')) ? String(j.query.id) : '';
return [{ json: { ok: !!ok, id, erreur: String(j.query?.erreur || '') } }];
"""

SUITE_ACTION = r"""
// Protection contre les requêtes envoyées depuis un autre site.
const origine = String(j.headers?.origin || j.headers?.referer || '');
if (!origine.startsWith('https://' + $env.N8N_HOST)) ok = false;
const b = j.body || {};
const id = /^\d{1,18}$/.test(String(b.id || '')) ? String(b.id) : '';
const action = ['repondre', 'humain', 'ia', 'statut'].includes(b.action) ? b.action : '';
const statut = ['nouveau', 'en_cours', 'qualifie', 'rdv', 'devis_envoye', 'converti', 'perdu'].includes(b.statut) ? b.statut : '';
const texte = String(b.texte || '').trim().slice(0, 4000);
if (!id || !action || (action === 'repondre' && !texte) || (action === 'statut' && !statut)) ok = false;
return [{ json: { ok: !!ok, id, action, statut, texte } }];
"""

SQL_TABLEAU = """
SELECT
  (SELECT COALESCE(json_agg(p ORDER BY p.maj_le DESC), '[]'::json) FROM (
     SELECT id, wa_id, nom, produit, score, statut, mode, opt_out, resume, maj_le, dernier_entrant
     FROM prospects ORDER BY maj_le DESC LIMIT 300) p) AS prospects,
  (SELECT row_to_json(x) FROM prospects x WHERE x.id = NULLIF($1, '')::bigint) AS fiche,
  (SELECT COALESCE(json_agg(m ORDER BY m.cree_le, m.id), '[]'::json)
     FROM messages m WHERE m.prospect_id = NULLIF($1, '')::bigint) AS messages,
  (SELECT json_build_object(
     'total', count(*),
     'semaine', count(*) FILTER (WHERE cree_le > now() - interval '7 days'),
     'chauds', count(*) FILTER (WHERE score = 'chaud' AND statut NOT IN ('converti', 'perdu')),
     'a_reprendre', count(*) FILTER (WHERE mode = 'humain' AND statut NOT IN ('converti', 'perdu')),
     'convertis', count(*) FILTER (WHERE statut = 'converti')) FROM prospects) AS stats;
"""

JS_PAGE = r"""
const d = $input.first().json;
const ctx = $('Contrôle d’accès').first().json;
const e = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const date = s => s ? new Date(s).toLocaleString('fr-FR', { timeZone: 'Europe/Paris', dateStyle: 'short', timeStyle: 'short' }) : '';
const STATUTS = { nouveau: 'Nouveau', en_cours: 'En cours', qualifie: 'Qualifié', rdv: 'RDV', devis_envoye: 'Devis envoyé', converti: 'Converti', perdu: 'Perdu' };
const s = d.stats || {};
const lignes = (d.prospects || []).map(p => `
  <a class="ligne ${String(p.id) === ctx.id ? 'actif' : ''}" href="?id=${p.id}">
    <span class="nom">${e(p.nom || '+' + p.wa_id)}</span>
    <span class="pastille ${e(p.score)}">${e({ tiede: 'tiède' }[p.score] || p.score)}</span>
    ${p.mode === 'humain' ? '<span class="pastille humain">à reprendre</span>' : ''}
    ${p.opt_out ? '<span class="pastille stop">STOP</span>' : ''}
    <span class="meta">${e(p.produit || '—')} · ${e(STATUTS[p.statut] || p.statut)} · ${date(p.maj_le)}</span>
  </a>`).join('') || '<p class="vide">Aucun prospect pour le moment.</p>';

let detail = '<div class="vide">Sélectionnez un prospect.</div>';
const f = d.fiche;
if (f) {
  const fenetre = f.dernier_entrant && (Date.now() - new Date(f.dernier_entrant).getTime()) < 24 * 3600 * 1000;
  const infos = Object.entries(f.infos || {}).map(([k, v]) => `<dt>${e(k)}</dt><dd>${e(v)}</dd>`).join('');
  const bulles = (d.messages || []).map(m => `
    <div class="bulle ${m.sens === 'entrant' ? 'in' : 'out'}">
      <div class="qui">${{ entrant: e(f.nom || 'Prospect'), agent: 'Agent IA', conseiller: 'Conseiller', relance: 'Relance auto' }[m.sens] || e(m.sens)} · ${date(m.cree_le)}</div>
      ${e(m.texte).replace(/\n/g, '<br>')}
    </div>`).join('');
  const optionsStatut = Object.entries(STATUTS).map(([k, v]) => `<option value="${k}" ${f.statut === k ? 'selected' : ''}>${v}</option>`).join('');
  detail = `
    <div class="entete">
      <div><h2>${e(f.nom || 'Prospect')}</h2><a href="https://wa.me/${e(f.wa_id)}" target="_blank" rel="noopener">+${e(f.wa_id)}</a></div>
      <div class="actions">
        <form method="post" action="jyvis-action"><input type="hidden" name="id" value="${f.id}">
          ${f.mode === 'ia'
            ? '<button name="action" value="humain">Reprendre la main</button>'
            : '<button name="action" value="ia">Rendre la main à l’agent IA</button>'}
        </form>
        <form method="post" action="jyvis-action"><input type="hidden" name="id" value="${f.id}"><input type="hidden" name="action" value="statut">
          <select name="statut" onchange="this.form.submit()">${optionsStatut}</select>
        </form>
      </div>
    </div>
    <p class="resume">${e(f.resume || 'Pas encore de résumé.')}</p>
    ${infos ? `<dl>${infos}</dl>` : ''}
    <div class="fil">${bulles}</div>
    ${f.opt_out ? '<p class="alerte">Ce prospect a demandé à ne plus recevoir de messages.</p>'
      : fenetre ? `<form method="post" action="jyvis-action" class="envoi"><input type="hidden" name="id" value="${f.id}"><input type="hidden" name="action" value="repondre">
          <textarea name="texte" rows="3" required placeholder="Votre réponse (l’agent IA s’arrête pour ce prospect)"></textarea><button>Envoyer</button></form>`
      : '<p class="alerte">Plus de 24 h depuis son dernier message : WhatsApp n’autorise plus de message libre. Appelez le prospect ou attendez qu’il réécrive.</p>'}`;
}

const html = `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JyVis – Prospects WhatsApp</title>
<style>
:root{--bleu:#0b2a4a;--fond:#f4f6f9;--carte:#fff;--texte:#1b2430;--gris:#6b7685;--bord:#dde3ea;--vert:#1f8f5f;--orange:#c97a12;--rouge:#c0392b}
@media (prefers-color-scheme:dark){:root{--fond:#0f141a;--carte:#18202a;--texte:#e6ebf1;--gris:#94a0ae;--bord:#2a3542}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--fond);color:var(--texte)}
header{background:var(--bleu);color:#fff;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
header h1{margin:0;font-size:18px}.stats{display:flex;gap:16px;flex-wrap:wrap;font-size:13px}.stats b{font-size:17px;display:block}
main{display:grid;grid-template-columns:minmax(260px,360px) 1fr;gap:16px;padding:16px;max-width:1300px;margin:auto}
.liste,.detail{background:var(--carte);border:1px solid var(--bord);border-radius:10px}
.liste{max-height:calc(100vh - 120px);overflow:auto}.ligne{display:block;padding:10px 14px;border-bottom:1px solid var(--bord);color:inherit;text-decoration:none}
.ligne.actif,.ligne:hover{background:rgba(11,42,74,.08)}.nom{font-weight:600;margin-right:6px}.meta{display:block;color:var(--gris);font-size:13px}
.pastille{font-size:11px;padding:1px 7px;border-radius:9px;color:#fff;background:var(--gris);margin-right:4px}.chaud{background:var(--rouge)}.tiede{background:var(--orange)}.froid{background:#5b7a99}.humain{background:var(--vert)}.stop{background:#000}
.detail{padding:16px;min-width:0}.entete{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.entete h2{margin:0}.actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
button,select{font:inherit;padding:7px 12px;border-radius:7px;border:1px solid var(--bord);background:var(--bleu);color:#fff;cursor:pointer}select{background:var(--carte);color:var(--texte)}
.resume{background:rgba(11,42,74,.06);padding:10px;border-radius:8px}dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:14px}dt{color:var(--gris)}dd{margin:0}
.fil{display:flex;flex-direction:column;gap:8px;margin:16px 0}.bulle{max-width:80%;padding:8px 12px;border-radius:10px;word-wrap:break-word}.in{align-self:flex-start;background:rgba(127,127,127,.12)}.out{align-self:flex-end;background:rgba(31,143,95,.15)}
.qui{font-size:12px;color:var(--gris)}.envoi{display:flex;gap:8px}.envoi textarea{flex:1;font:inherit;padding:8px;border-radius:7px;border:1px solid var(--bord);background:var(--carte);color:var(--texte)}
.alerte{background:rgba(192,57,43,.12);padding:10px;border-radius:8px}.vide{color:var(--gris);padding:24px;text-align:center}
@media (max-width:760px){main{grid-template-columns:1fr;padding:12px}.liste{max-height:40vh}.bulle{max-width:92%}.envoi{flex-direction:column}}
</style></head><body>
<header><h1>JyVis Assurances · Prospects WhatsApp</h1>
<div class="stats"><span><b>${s.total ?? 0}</b>prospects</span><span><b>${s.semaine ?? 0}</b>cette semaine</span><span><b>${s.chauds ?? 0}</b>chauds</span><span><b>${s.a_reprendre ?? 0}</b>à reprendre</span><span><b>${s.convertis ?? 0}</b>convertis</span></div></header>
${ctx.erreur ? '<p class="alerte" style="margin:16px">Le message n’a pas pu être envoyé par WhatsApp (fenêtre de 24 h dépassée ou numéro invalide).</p>' : ''}
<main><nav class="liste">${lignes}</nav><section class="detail">${detail}</section></main>
</body></html>`;
return [{ json: { html } }];
"""

SQL_ACTION = """
WITH u AS (
  UPDATE prospects SET
    mode = CASE $2 WHEN 'humain' THEN 'humain' WHEN 'ia' THEN 'ia' ELSE mode END,
    alerte_envoyee = CASE WHEN $2 = 'ia' THEN false ELSE alerte_envoyee END,
    statut = CASE WHEN $2 = 'statut' THEN $3 ELSE statut END,
    maj_le = now()
  WHERE id = $1::bigint
  RETURNING id
)
SELECT $1::bigint AS id, (SELECT count(*) FROM u) AS modifie;
"""

# Toujours une ligne : wa_id est vide si le prospect n'existe pas ou a écrit STOP (l'envoi échoue alors proprement).
SQL_PROSPECT = "SELECT $1::bigint AS prospect_id, COALESCE((SELECT wa_id FROM prospects WHERE id = $1::bigint AND NOT opt_out), '') AS wa_id;"

SQL_CONSEILLER = """
WITH u AS (
  UPDATE prospects SET mode = 'humain',
    dernier_sortant = CASE WHEN $2::boolean THEN now() ELSE dernier_sortant END, maj_le = now()
  WHERE id = $1::bigint RETURNING id
)
, i AS (
  INSERT INTO messages (prospect_id, sens, texte)
  SELECT id, 'conseiller', CASE WHEN $2::boolean THEN $3 ELSE '[NON ENVOYÉ] ' || $3 END FROM u
  RETURNING id
)
SELECT $1::bigint AS id, $2::boolean AND EXISTS (SELECT 1 FROM i) AS envoye;
"""

DEMANDE_AUTH = {"WWW-Authenticate": 'Basic realm="JyVis Assurances", charset="UTF-8"'}

tableau = workflow(
    "jyvisWaTableau001", "JyVis – Tableau de bord WhatsApp",
    [
        webhook("Page tableau de bord", (0, 0), "GET", "jyvis", "responseNode"),
        code("Contrôle d’accès", (240, 0), JS_AUTH.replace("__SUITE__", SUITE_PAGE)),
        si("Accès autorisé ?", (480, 0), "$json.ok === true"),
        sql("Charger les prospects", (720, -100), SQL_TABLEAU, "[$json.id]"),
        code("Construire la page", (960, -100), JS_PAGE),
        repondre("Afficher la page", (1200, -100), 200, "={{ $json.html }}", {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}),
        repondre("Refuser l’accès", (720, 120), 401, "Accès refusé", DEMANDE_AUTH),

        webhook("Action du conseiller", (0, 400), "POST", "jyvis-action", "responseNode"),
        code("Contrôle de l’action", (240, 400), JS_AUTH.replace("__SUITE__", SUITE_ACTION)),
        si("Action autorisée ?", (480, 400), "$json.ok === true"),
        si("Répondre au prospect ?", (720, 300), "$json.action === 'repondre'"),
        sql("Retrouver le prospect", (960, 200), SQL_PROSPECT, "[$json.id]"),
        code("Message du conseiller", (1200, 200),
             "const t = $('Contrôle de l’action').first().json.texte;\n"
             "return $input.all().map(i => ({ json: { prospect_id: i.json.prospect_id, wa_id: i.json.wa_id, reponse: t } }));"),
        si("Destinataire valide ?", (1440, 200), "!!$json.wa_id"),
        envoi_whatsapp("Envoyer sur WhatsApp", (1680, 120)),
        sql("Noter la réponse", (1920, 200), SQL_CONSEILLER,
            "(() => { const m = $('Message du conseiller').item.json; return [m.prospect_id, !!($json.messages && $json.messages[0] && $json.messages[0].id), m.reponse]; })()"),
        repondre("Retour après envoi", (2160, 200), 303, "", {"Location": "=jyvis?id={{ $json.id }}{{ $json.envoye ? '' : '&erreur=1' }}"}, "noData"),
        sql("Appliquer l’action", (960, 420), SQL_ACTION, "[$json.id, $json.action, $json.statut]"),
        repondre("Retour à la fiche", (1200, 420), 303, "", {"Location": "=jyvis?id={{ $json.id }}"}, "noData"),
        repondre("Refuser l’action", (720, 560), 401, "Accès refusé", DEMANDE_AUTH),
    ],
    [
        ("Page tableau de bord", 0, "Contrôle d’accès"),
        ("Contrôle d’accès", 0, "Accès autorisé ?"),
        ("Accès autorisé ?", 0, "Charger les prospects"),
        ("Accès autorisé ?", 1, "Refuser l’accès"),
        ("Charger les prospects", 0, "Construire la page"),
        ("Construire la page", 0, "Afficher la page"),
        ("Action du conseiller", 0, "Contrôle de l’action"),
        ("Contrôle de l’action", 0, "Action autorisée ?"),
        ("Action autorisée ?", 0, "Répondre au prospect ?"),
        ("Action autorisée ?", 1, "Refuser l’action"),
        ("Répondre au prospect ?", 0, "Retrouver le prospect"),
        ("Répondre au prospect ?", 1, "Appliquer l’action"),
        ("Retrouver le prospect", 0, "Message du conseiller"),
        ("Message du conseiller", 0, "Destinataire valide ?"),
        ("Destinataire valide ?", 0, "Envoyer sur WhatsApp"),
        ("Destinataire valide ?", 1, "Noter la réponse"),
        ("Envoyer sur WhatsApp", 0, "Noter la réponse"),
        ("Noter la réponse", 0, "Retour après envoi"),
        ("Appliquer l’action", 0, "Retour à la fiche"),
    ],
)

SORTIE.mkdir(exist_ok=True)
for wf, fichier in [(agent, "agent-whatsapp.json"), (relances, "relances-whatsapp.json"), (tableau, "tableau-de-bord.json")]:
    (SORTIE / fichier).write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("écrit", SORTIE / fichier)
