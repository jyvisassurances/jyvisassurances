-- Base de données des prospects WhatsApp — JyVis Assurances
-- Sans risque à relancer : rien n'est effacé.

CREATE TABLE IF NOT EXISTS prospects (
  id              BIGSERIAL PRIMARY KEY,
  wa_id           TEXT UNIQUE NOT NULL,          -- numéro WhatsApp (format international sans +)
  nom             TEXT,
  produit         TEXT,                          -- auto, moto, habitation, rc_pro, decennale, sante, prevoyance, autre
  infos           JSONB NOT NULL DEFAULT '{}',   -- informations collectées par l'agent
  resume          TEXT,                          -- résumé du besoin pour le conseiller
  score           TEXT NOT NULL DEFAULT 'froid', -- chaud, tiede, froid
  statut          TEXT NOT NULL DEFAULT 'nouveau', -- nouveau, en_cours, qualifie, rdv, devis_envoye, converti, perdu
  mode            TEXT NOT NULL DEFAULT 'ia',    -- ia (l'agent répond) ou humain (le conseiller a repris la main)
  opt_out         BOOLEAN NOT NULL DEFAULT FALSE,-- le prospect a écrit STOP
  relances        INT NOT NULL DEFAULT 0,
  alerte_envoyee  BOOLEAN NOT NULL DEFAULT FALSE,
  dernier_entrant TIMESTAMPTZ,                   -- dernier message reçu du prospect (fenêtre de 24 h WhatsApp)
  dernier_sortant TIMESTAMPTZ,
  cree_le         TIMESTAMPTZ NOT NULL DEFAULT now(),
  maj_le          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id           BIGSERIAL PRIMARY KEY,
  prospect_id  BIGINT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
  sens         TEXT NOT NULL,         -- entrant, agent, conseiller, relance
  texte        TEXT NOT NULL,
  wa_message_id TEXT UNIQUE,          -- évite de traiter deux fois le même message
  cree_le      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_prospect_idx ON messages (prospect_id, cree_le);
CREATE INDEX IF NOT EXISTS prospects_maj_idx ON prospects (maj_le DESC);

-- Provenance des prospects (campagnes Google Ads, site web…)
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS origine TEXT NOT NULL DEFAULT 'whatsapp'; -- whatsapp ou site
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS source  TEXT;  -- code de campagne (ex. GA-DECENNALE)
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS gclid   TEXT;  -- identifiant de clic Google Ads
ALTER TABLE prospects ADD COLUMN IF NOT EXISTS email   TEXT;
CREATE INDEX IF NOT EXISTS prospects_source_idx ON prospects (source);
