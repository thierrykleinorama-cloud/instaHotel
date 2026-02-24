import { useState } from "react";

const COLORS = {
  bg: "#0a0f1a",
  card: "#111827",
  cardHover: "#1a2332",
  accent: "#c8a96e",
  accentDim: "#a08550",
  text: "#e8e0d4",
  textDim: "#8b9ab5",
  green: "#4ade80",
  blue: "#60a5fa",
  purple: "#a78bfa",
  orange: "#fb923c",
  pink: "#f472b6",
  border: "#1e293b",
  codeBg: "#0d1117",
};

const phases = [
  {
    id: "mediatheque",
    title: "1. Médiathèque Intelligente",
    subtitle: "Le socle — Semaine 1-2",
    icon: "📸",
    color: COLORS.blue,
    description:
      "Transformer un dossier de photos en une base de données exploitable par l'IA",
    problem:
      "Tu as 500+ photos dans Google Drive ou sur ton disque. Certaines sont des chambres, d'autres la terrasse, des plats, la façade, Sitges... Impossible de savoir rapidement ce que tu as, ce qui manque, ce qui a déjà été posté.",
    solution: [
      {
        step: "Scan automatique",
        detail:
          "Un script Python parcourt ton dossier photos. Pour chaque image, il appelle Claude Vision (ou Gemini Vision) qui analyse et retourne des métadonnées structurées.",
      },
      {
        step: "Tagging multi-niveaux",
        detail:
          'Chaque photo reçoit : catégorie (chambre, commun, destination, food, expérience), sous-catégorie (chambre_deluxe, terrasse, plage_sitges...), ambiance (lumineux, intime, romantique, festif), saison (été, hiver, toute_saison), qualité Instagram (1-10), éléments clés ("mosaïque art nouveau", "vue mer", "petit-déjeuner").',
      },
      {
        step: "Stockage Supabase",
        detail:
          "Toutes les métadonnées + chemin fichier sont stockés dans une table Supabase. Tu obtiens une médiathèque cherchable, filtrable, avec des stats.",
      },
    ],
    dataModel: `Table: media_library
──────────────────────────
id              UUID
file_path       TEXT
file_name       TEXT
uploaded_at     TIMESTAMP
──────────────────────────
category        TEXT        # chambre, commun, destination...
subcategory     TEXT        # chambre_deluxe, terrasse...
ambiance        TEXT[]      # [romantique, lumineux]
season          TEXT[]      # [été, toute_saison]
elements        TEXT[]      # [mosaïque, vue_mer, balcon]
ig_quality      INTEGER     # 1-10
aspect_ratio    TEXT        # portrait, landscape, square
──────────────────────────
used_count      INTEGER     # nb fois postée
last_used_at    TIMESTAMP
status          TEXT        # available, used, archived`,
    codeExample: `# Exemple simplifié de l'indexeur
import anthropic
from supabase import create_client

client = anthropic.Anthropic()

def analyze_photo(image_path):
    """Analyse une photo avec Claude Vision"""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }},
                {"type": "text", "text": PROMPT_ANALYSE}
            ]
        }]
    )
    return parse_tags(response)  # → dict structuré

# PROMPT_ANALYSE demande à Claude de retourner
# un JSON avec tous les tags nécessaires`,
    output:
      "Une base Supabase avec toutes tes photos indexées, cherchables par catégorie, ambiance, saison, qualité. Tu sais exactement ce que tu as.",
  },
  {
    id: "strategie",
    title: "2. Moteur de Stratégie Éditoriale",
    subtitle: "Le cerveau — Semaine 2-3",
    icon: "🧠",
    color: COLORS.purple,
    description:
      "Les règles intelligentes qui décident QUOI poster et QUAND",
    problem:
      "Poster au hasard ne fonctionne pas. Il faut un mix de contenus équilibré, adapté à la saison, qui ne répète pas les mêmes photos, et qui alterne entre vendre et inspirer.",
    solution: [
      {
        step: "Calendrier éditorial paramétrable",
        detail:
          'Tu définis les règles : lundi = chambre/bâtiment, mercredi = destination Sitges, vendredi = expérience/offre. Ratio configurable (30/30/20/20). Le moteur respecte ces règles automatiquement.',
      },
      {
        step: "Contexte saisonnier",
        detail:
          "Le moteur sait qu'en juin il faut pousser les réservations été, qu'en octobre c'est le Festival de Sitges (horreur), qu'en décembre c'est Noël. Il adapte les thèmes et le ton automatiquement.",
      },
      {
        step: "Anti-répétition intelligent",
        detail:
          "Le système tracke quelles photos ont été utilisées, quand, et évite de re-poster la même chambre trop souvent. Il favorise les photos sous-utilisées à haute qualité.",
      },
      {
        step: "Sélection de médias par scoring",
        detail:
          'Pour chaque slot du calendrier, le moteur requête Supabase avec les critères (catégorie + saison + pas récemment utilisé + qualité > 7) et sélectionne le meilleur candidat.',
      },
    ],
    dataModel: `Table: editorial_calendar
──────────────────────────
id              UUID
post_date       DATE
slot_type       TEXT        # chambre, destination, experience, offre
theme           TEXT        # "festival_sitges", "été_plage"...
season_context  TEXT        # haute_saison, basse_saison
status          TEXT        # planned, generated, validated, published

Table: editorial_rules
──────────────────────────
id              UUID
day_of_week     INTEGER     # 1=lundi...7=dimanche
default_category TEXT
frequency       TEXT        # weekly, biweekly
priority        INTEGER

Table: seasonal_themes
──────────────────────────
id              UUID
start_date      DATE
end_date        DATE
theme_name      TEXT        # "festival_cinema_sitges"
hashtags        TEXT[]
mood            TEXT        # festif, romantique, culturel
cta_focus       TEXT        # "réservez pour le festival"`,
    codeExample: `# Moteur de sélection de contenu
def select_next_post(post_date, slot_type):
    """Sélectionne le meilleur média pour un slot"""
    
    # 1. Déterminer le contexte saisonnier
    season = get_season_context(post_date)
    theme = get_active_theme(post_date)
    
    # 2. Requêter la médiathèque
    candidates = supabase.table("media_library") \\
        .select("*") \\
        .eq("category", slot_type) \\
        .gte("ig_quality", 7) \\
        .order("used_count", ascending=True) \\
        .order("ig_quality", descending=True) \\
        .limit(10) \\
        .execute()
    
    # 3. Filtrer par saison si pertinent
    if season in ["été", "hiver"]:
        candidates = [c for c in candidates 
                      if season in c["season"] 
                      or "toute_saison" in c["season"]]
    
    # 4. Éviter les photos récentes (< 30 jours)
    candidates = [c for c in candidates
                  if days_since(c["last_used_at"]) > 30]
    
    # 5. Retourner le meilleur candidat
    return candidates[0] if candidates else None`,
    output:
      "Un calendrier éditorial auto-généré pour les 4 prochaines semaines, avec pour chaque jour : le type de post, la photo sélectionnée, le thème contextuel.",
  },
  {
    id: "generation",
    title: "3. Générateur de Contenu",
    subtitle: "La créativité — Semaine 3-4",
    icon: "✨",
    color: COLORS.orange,
    description:
      "Transformer une photo sélectionnée en post Instagram complet",
    problem:
      "Tu as la bonne photo pour le bon jour. Mais il faut encore : une légende engageante, des hashtags optimisés, potentiellement une variante visuelle, et pour les Reels une vidéo à partir de la photo.",
    solution: [
      {
        step: "Génération de légendes (Claude API)",
        detail:
          'Claude reçoit : la photo, ses tags, le thème du jour, le contexte saisonnier, et des exemples de tes meilleures légendes passées. Il génère 2-3 variantes de légendes multilingues (ES/EN/FR) avec CTA adapté ("lien en bio", "DM pour réserver"...).',
      },
      {
        step: "Variantes visuelles (Nano Banana Pro API)",
        detail:
          "À partir de ta photo originale + ton brand kit (logo, palette couleurs, typo), Nano Banana peut créer : des versions avec texte intégré (offre spéciale), des carrousels (même photo, angles différents), des adaptations saisonnières (filtre chaud été, froid hiver).",
      },
      {
        step: "Reels vidéo (Veo 3 API)",
        detail:
          "Pour les posts vidéo : ta photo statique est animée en clip de 8 secondes avec audio ambiant (vagues, oiseaux, musique douce). Ken Burns effect intelligent, pas un simple zoom.",
      },
      {
        step: "Hashtags optimisés",
        detail:
          "Claude génère un mix de hashtags : 5 très populaires (#boutiquehotel, #sitges), 10 moyens (#artnouveau, #mediterraneanlife), 5 niches (#sitgeslovers, #catalunyahotel). Mix optimisé pour la découvrabilité.",
      },
    ],
    dataModel: `Table: generated_content
──────────────────────────
id              UUID
calendar_id     FK → editorial_calendar
media_id        FK → media_library
──────────────────────────
caption_es      TEXT
caption_en      TEXT
caption_fr      TEXT
hashtags        TEXT[]
cta_type        TEXT        # link_bio, dm, book_now
──────────────────────────
visual_variant  TEXT        # original, text_overlay, carousel
variant_url     TEXT        # URL fichier généré
video_url       TEXT        # si Reel généré
──────────────────────────
status          TEXT        # draft, validated, published
created_at      TIMESTAMP
validated_at    TIMESTAMP
validated_by    TEXT`,
    codeExample: `# Génération de légende avec Claude
def generate_caption(media, theme, season):
    """Génère des légendes multilingues"""
    
    prompt = f"""Tu es le community manager d'un 
hôtel boutique Art Nouveau à Sitges (Barcelone).

Photo : {media['elements']}
Catégorie : {media['category']}
Ambiance : {media['ambiance']}
Thème du jour : {theme}
Saison : {season}

Génère 2 variantes de légende Instagram :
- Version courte (2-3 lignes, punch)
- Version storytelling (5-6 lignes, émotionnelle)

Chaque variante en ES, EN, FR.
Inclus un CTA naturel.
Ton : chaleureux, authentique, jamais corporate.
Inclus 20 hashtags (mix popularité)."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encode_image(media["file_path"])
                }},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    return parse_captions(response)`,
    output:
      "Pour chaque post planifié : 2-3 variantes de légendes (ES/EN/FR), hashtags optimisés, et optionnellement une variante visuelle ou un Reel vidéo.",
  },
  {
    id: "validation",
    title: "4. Dashboard de Validation",
    subtitle: "Le contrôle humain — Semaine 4",
    icon: "👁️",
    color: COLORS.green,
    description:
      "Toi (le propriétaire) valides, ajustes, ou rejettes avant publication",
    problem:
      "L'IA ne doit jamais publier sans ton accord. Tu veux voir le contenu prévu, pouvoir modifier une légende, changer une photo, et approuver en 1 clic.",
    solution: [
      {
        step: "Interface Streamlit",
        detail:
          "Un dashboard simple et visuel : tu vois la semaine à venir avec les posts prévus (photo + légende + hashtags). Vue calendrier ou vue liste.",
      },
      {
        step: "Actions rapides",
        detail:
          '3 boutons par post : ✅ Valider, ✏️ Modifier, 🔄 Régénérer (demande une nouvelle variante à l\'IA), ❌ Rejeter (le moteur propose un autre post).',
      },
      {
        step: "Preview Instagram",
        detail:
          "Aperçu qui simule le rendu Instagram (image + légende tronquée + hashtags). Tu vois exactement ce que ton audience verra.",
      },
      {
        step: "Métriques de la médiathèque",
        detail:
          "Stats : nombre de photos par catégorie, photos jamais utilisées, couverture des thèmes, gaps à combler (ex: tu n'as aucune photo de petit-déjeuner en hiver).",
      },
    ],
    dataModel: `# Pas de nouvelle table — mise à jour de 
# generated_content.status :
#   draft → validated → scheduled → published
#
# + logs des actions de validation :

Table: validation_log
──────────────────────────
id              UUID
content_id      FK → generated_content
action          TEXT    # validate, edit, regenerate, reject
edited_fields   JSONB   # {"caption_es": "nouveau texte..."}
timestamp       TIMESTAMP`,
    codeExample: `# Dashboard Streamlit simplifié
import streamlit as st

st.title("📅 Contenu Instagram — Semaine 24")

posts = get_upcoming_posts(week=24)

for post in posts:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(post["photo_url"])
        st.caption(f"📊 Qualité: {post['quality']}/10")
    
    with col2:
        st.subheader(f"{post['date']} — {post['theme']}")
        
        lang = st.radio("Langue", ["ES","EN","FR"], 
                        key=post["id"])
        caption = post[f"caption_{lang.lower()}"]
        edited = st.text_area("Légende", caption, 
                              key=f"cap_{post['id']}")
        
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Valider", key=f"v_{post['id']}"):
            validate_post(post["id"], edited)
        if c2.button("🔄 Régénérer", key=f"r_{post['id']}"):
            regenerate_post(post["id"])
        if c3.button("❌ Rejeter", key=f"x_{post['id']}"):
            reject_post(post["id"])`,
    output:
      "En 10 minutes le dimanche soir, tu valides toute la semaine de contenu. Rien ne part sans ton OK.",
  },
  {
    id: "publication",
    title: "5. Publication Automatique",
    subtitle: "Le dernier kilomètre — Semaine 5",
    icon: "🚀",
    color: COLORS.pink,
    description: "Les posts validés partent automatiquement à l'heure optimale",
    problem:
      "Une fois validé, le contenu doit être publié au bon moment sans que tu aies à y penser. Et il faut tracker les performances pour améliorer le système.",
    solution: [
      {
        step: "Scheduling via Postiz ou SocialBee API",
        detail:
          "Les posts validés sont envoyés automatiquement à l'outil de scheduling. Postiz (open-source) si tu veux le contrôle total, SocialBee si tu préfères le clé-en-main.",
      },
      {
        step: "Heures optimales",
        detail:
          "Le système apprend les meilleures heures de publication à partir des données d'engagement (Instagram Graph API). Il ajuste automatiquement les horaires.",
      },
      {
        step: "Boucle de feedback",
        detail:
          "48h après publication, le système récupère les metrics (likes, commentaires, saves, reach) et les stocke. Ces données alimentent le moteur de sélection pour améliorer les choix futurs.",
      },
      {
        step: "Réplicabilité Malaga",
        detail:
          "Tout le système est paramétrable par hôtel. Pour Malaga, tu crées une nouvelle instance avec sa propre médiathèque, ses propres règles éditoriales, son propre brand kit. Le code est identique.",
      },
    ],
    dataModel: `Table: post_performance
──────────────────────────
id              UUID
content_id      FK → generated_content
ig_post_id      TEXT
published_at    TIMESTAMP
──────────────────────────
likes           INTEGER
comments        INTEGER
saves           INTEGER
shares          INTEGER
reach           INTEGER
impressions     INTEGER
──────────────────────────
engagement_rate FLOAT   # calculé
fetched_at      TIMESTAMP

# La boucle : les posts à haut engagement 
# influencent les futurs choix du moteur
# → photos similaires priorisées
# → style de légende similaire favorisé
# → heures de publication ajustées`,
    codeExample: `# Boucle de feedback — apprentissage
def update_media_scoring():
    """Ajuste les scores en fonction des perfs"""
    
    # Récupérer les performances récentes
    perfs = supabase.table("post_performance") \\
        .select("*, generated_content(media_id)") \\
        .gte("published_at", thirty_days_ago) \\
        .execute()
    
    # Calculer les scores par catégorie/ambiance
    for perf in perfs:
        media = get_media(perf["media_id"])
        
        # Bonus si engagement au-dessus de la moyenne
        if perf["engagement_rate"] > avg_engagement:
            boost_similar_media(
                category=media["category"],
                ambiance=media["ambiance"],
                elements=media["elements"],
                boost=+1
            )
    
    # Résultat : le moteur apprend que les photos
    # "terrasse + coucher de soleil" performent 
    # mieux que "chambre + intérieur" et ajuste
    # ses futures sélections automatiquement`,
    output:
      "Un système qui se publie et s'améliore tout seul. Tu n'interviens que 10 min/semaine pour valider.",
  },
];

const techStack = [
  {
    name: "Python",
    role: "Orchestrateur",
    detail: "Script principal, logique métier, appels API",
  },
  {
    name: "Claude API",
    role: "Vision + Texte",
    detail: "Analyse photos, génération légendes multilingues",
  },
  {
    name: "Gemini API",
    role: "Visuels + Vidéo",
    detail: "Nano Banana Pro (images) + Veo 3 (Reels)",
  },
  {
    name: "Supabase",
    role: "Base de données",
    detail: "Médiathèque, calendrier, performances",
  },
  {
    name: "Streamlit",
    role: "Dashboard",
    detail: "Interface validation + analytics",
  },
  {
    name: "Postiz",
    role: "Publication",
    detail: "Scheduling + publication multi-plateforme",
  },
];

const costs = [
  { item: "Claude API (Sonnet)", usage: "~200 appels/mois", cost: "~5$" },
  {
    item: "Gemini API (Nano Banana)",
    usage: "~100 images/mois",
    cost: "~4-13$",
  },
  { item: "Gemini API (Veo 3)", usage: "~20 vidéos/mois", cost: "~25-60$" },
  { item: "Supabase", usage: "Free tier", cost: "0$" },
  { item: "Streamlit Cloud", usage: "1 app", cost: "0$" },
  { item: "Postiz (self-hosted)", usage: "Open-source", cost: "0$" },
];

function PhaseCard({ phase, isOpen, onToggle }) {
  return (
    <div
      style={{
        background: COLORS.card,
        borderRadius: 12,
        border: `1px solid ${isOpen ? phase.color : COLORS.border}`,
        marginBottom: 16,
        overflow: "hidden",
        transition: "border-color 0.3s",
      }}
    >
      <div
        onClick={onToggle}
        style={{
          padding: "20px 24px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <span style={{ fontSize: 32 }}>{phase.icon}</span>
        <div style={{ flex: 1 }}>
          <div
            style={{
              fontSize: 18,
              fontWeight: 700,
              color: COLORS.text,
              fontFamily: "'DM Sans', sans-serif",
            }}
          >
            {phase.title}
          </div>
          <div style={{ fontSize: 13, color: phase.color, marginTop: 2 }}>
            {phase.subtitle}
          </div>
        </div>
        <span
          style={{
            color: COLORS.textDim,
            fontSize: 20,
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.3s",
          }}
        >
          ▼
        </span>
      </div>

      {isOpen && (
        <div style={{ padding: "0 24px 24px" }}>
          <p
            style={{
              color: COLORS.text,
              fontSize: 15,
              lineHeight: 1.6,
              margin: "0 0 16px",
              fontStyle: "italic",
            }}
          >
            {phase.description}
          </p>

          {/* Problem */}
          <div
            style={{
              background: "#1a1520",
              borderLeft: `3px solid ${COLORS.orange}`,
              padding: "12px 16px",
              borderRadius: "0 8px 8px 0",
              marginBottom: 20,
            }}
          >
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: COLORS.orange,
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 4,
              }}
            >
              Problème à résoudre
            </div>
            <div
              style={{ color: COLORS.textDim, fontSize: 14, lineHeight: 1.5 }}
            >
              {phase.problem}
            </div>
          </div>

          {/* Steps */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: phase.color,
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 12,
              }}
            >
              Solution en détail
            </div>
            {phase.solution.map((s, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: 12,
                  marginBottom: 12,
                  alignItems: "flex-start",
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: phase.color + "22",
                    color: phase.color,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 13,
                    fontWeight: 700,
                    flexShrink: 0,
                    marginTop: 2,
                  }}
                >
                  {i + 1}
                </div>
                <div>
                  <div
                    style={{
                      color: COLORS.text,
                      fontSize: 14,
                      fontWeight: 600,
                    }}
                  >
                    {s.step}
                  </div>
                  <div
                    style={{
                      color: COLORS.textDim,
                      fontSize: 13,
                      lineHeight: 1.5,
                      marginTop: 4,
                    }}
                  >
                    {s.detail}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Data Model */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: COLORS.accent,
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 8,
              }}
            >
              Modèle de données
            </div>
            <pre
              style={{
                background: COLORS.codeBg,
                color: COLORS.textDim,
                padding: 16,
                borderRadius: 8,
                fontSize: 12,
                lineHeight: 1.5,
                overflow: "auto",
                border: `1px solid ${COLORS.border}`,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              }}
            >
              {phase.dataModel}
            </pre>
          </div>

          {/* Code Example */}
          <div style={{ marginBottom: 20 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: COLORS.green,
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 8,
              }}
            >
              Exemple de code
            </div>
            <pre
              style={{
                background: COLORS.codeBg,
                color: "#7dd3fc",
                padding: 16,
                borderRadius: 8,
                fontSize: 12,
                lineHeight: 1.5,
                overflow: "auto",
                border: `1px solid ${COLORS.border}`,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              }}
            >
              {phase.codeExample}
            </pre>
          </div>

          {/* Output */}
          <div
            style={{
              background: phase.color + "15",
              borderLeft: `3px solid ${phase.color}`,
              padding: "12px 16px",
              borderRadius: "0 8px 8px 0",
            }}
          >
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: phase.color,
                textTransform: "uppercase",
                letterSpacing: 1,
                marginBottom: 4,
              }}
            >
              Résultat obtenu
            </div>
            <div style={{ color: COLORS.text, fontSize: 14, lineHeight: 1.5 }}>
              {phase.output}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PipelineArchitecture() {
  const [openPhase, setOpenPhase] = useState("mediatheque");
  const [showCosts, setShowCosts] = useState(false);

  return (
    <div
      style={{
        background: COLORS.bg,
        minHeight: "100vh",
        color: COLORS.text,
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
        rel="stylesheet"
      />

      {/* Header */}
      <div
        style={{
          padding: "32px 24px 24px",
          borderBottom: `1px solid ${COLORS.border}`,
        }}
      >
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: COLORS.accent,
            textTransform: "uppercase",
            letterSpacing: 2,
            marginBottom: 8,
          }}
        >
          Architecture Système
        </div>
        <h1
          style={{
            fontSize: 26,
            fontWeight: 700,
            margin: 0,
            lineHeight: 1.2,
          }}
        >
          Le Cerveau Instagram
        </h1>
        <p
          style={{
            color: COLORS.textDim,
            fontSize: 15,
            margin: "8px 0 0",
            lineHeight: 1.5,
          }}
        >
          Pipeline intelligent : médiathèque → stratégie → génération →
          validation → publication
        </p>
      </div>

      {/* Flow Diagram */}
      <div style={{ padding: "20px 24px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 8,
            padding: "16px",
            background: COLORS.card,
            borderRadius: 12,
            border: `1px solid ${COLORS.border}`,
          }}
        >
          {phases.map((p, i) => (
            <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                onClick={() => setOpenPhase(p.id)}
                style={{
                  cursor: "pointer",
                  background: openPhase === p.id ? p.color + "30" : "transparent",
                  border: `2px solid ${openPhase === p.id ? p.color : COLORS.border}`,
                  borderRadius: 10,
                  padding: "8px 12px",
                  textAlign: "center",
                  transition: "all 0.2s",
                  minWidth: 50,
                }}
              >
                <div style={{ fontSize: 20 }}>{p.icon}</div>
                <div
                  style={{
                    fontSize: 10,
                    color: openPhase === p.id ? p.color : COLORS.textDim,
                    fontWeight: 600,
                    marginTop: 4,
                  }}
                >
                  {p.title.split(".")[0]}.
                </div>
              </div>
              {i < phases.length - 1 && (
                <span style={{ color: COLORS.textDim, fontSize: 18 }}>→</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Phase Details */}
      <div style={{ padding: "0 24px 24px" }}>
        {phases.map((phase) => (
          <PhaseCard
            key={phase.id}
            phase={phase}
            isOpen={openPhase === phase.id}
            onToggle={() =>
              setOpenPhase(openPhase === phase.id ? null : phase.id)
            }
          />
        ))}
      </div>

      {/* Tech Stack */}
      <div style={{ padding: "0 24px 24px" }}>
        <div
          style={{
            background: COLORS.card,
            borderRadius: 12,
            border: `1px solid ${COLORS.border}`,
            padding: 24,
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: COLORS.accent,
              textTransform: "uppercase",
              letterSpacing: 2,
              marginBottom: 16,
            }}
          >
            Stack Technique
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 12,
            }}
          >
            {techStack.map((t) => (
              <div
                key={t.name}
                style={{
                  background: COLORS.bg,
                  borderRadius: 8,
                  padding: "12px 14px",
                  border: `1px solid ${COLORS.border}`,
                }}
              >
                <div
                  style={{
                    color: COLORS.accent,
                    fontSize: 14,
                    fontWeight: 700,
                  }}
                >
                  {t.name}
                </div>
                <div
                  style={{
                    color: COLORS.text,
                    fontSize: 12,
                    fontWeight: 600,
                    marginTop: 2,
                  }}
                >
                  {t.role}
                </div>
                <div
                  style={{ color: COLORS.textDim, fontSize: 11, marginTop: 4 }}
                >
                  {t.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Costs */}
      <div style={{ padding: "0 24px 32px" }}>
        <div
          onClick={() => setShowCosts(!showCosts)}
          style={{
            background: COLORS.card,
            borderRadius: 12,
            border: `1px solid ${COLORS.border}`,
            padding: "20px 24px",
            cursor: "pointer",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: COLORS.green,
                  textTransform: "uppercase",
                  letterSpacing: 2,
                }}
              >
                Coûts mensuels estimés
              </div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  color: COLORS.text,
                  marginTop: 4,
                }}
              >
                34 — 78$ / mois
              </div>
              <div
                style={{ color: COLORS.textDim, fontSize: 13, marginTop: 2 }}
              >
                Pour ~20 posts/mois dont ~8 Reels vidéo
              </div>
            </div>
            <span
              style={{
                color: COLORS.textDim,
                fontSize: 20,
                transform: showCosts ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.3s",
              }}
            >
              ▼
            </span>
          </div>

          {showCosts && (
            <div style={{ marginTop: 16 }}>
              {costs.map((c) => (
                <div
                  key={c.item}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "8px 0",
                    borderTop: `1px solid ${COLORS.border}`,
                    fontSize: 13,
                  }}
                >
                  <div>
                    <span style={{ color: COLORS.text }}>{c.item}</span>
                    <span
                      style={{ color: COLORS.textDim, marginLeft: 8 }}
                    >
                      ({c.usage})
                    </span>
                  </div>
                  <span style={{ color: COLORS.green, fontWeight: 600 }}>
                    {c.cost}
                  </span>
                </div>
              ))}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "12px 0 0",
                  borderTop: `2px solid ${COLORS.accent}`,
                  fontSize: 14,
                  fontWeight: 700,
                  marginTop: 4,
                }}
              >
                <span>Total mensuel estimé</span>
                <span style={{ color: COLORS.accent }}>~34 — 78$</span>
              </div>
              <div
                style={{
                  color: COLORS.textDim,
                  fontSize: 12,
                  marginTop: 8,
                  fontStyle: "italic",
                }}
              >
                vs. ~100$/mois pour des outils clé-en-main type SocialBee + Canva
                Pro + Zebracat. Et surtout : réplicable gratuitement pour Malaga.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div style={{ padding: "0 24px 32px" }}>
        <div
          style={{
            background: COLORS.card,
            borderRadius: 12,
            border: `1px solid ${COLORS.border}`,
            padding: 24,
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: COLORS.accent,
              textTransform: "uppercase",
              letterSpacing: 2,
              marginBottom: 16,
            }}
          >
            Planning de développement
          </div>

          {[
            {
              week: "Sem. 1-2",
              task: "Médiathèque intelligente",
              detail: "Indexer toutes les photos existantes dans Supabase",
              color: COLORS.blue,
            },
            {
              week: "Sem. 2-3",
              task: "Moteur éditorial",
              detail: "Règles de sélection + calendrier auto-généré",
              color: COLORS.purple,
            },
            {
              week: "Sem. 3-4",
              task: "Génération contenu",
              detail: "Légendes Claude + variantes Nano Banana",
              color: COLORS.orange,
            },
            {
              week: "Sem. 4",
              task: "Dashboard Streamlit",
              detail: "Interface de validation + preview",
              color: COLORS.green,
            },
            {
              week: "Sem. 5",
              task: "Publication + feedback",
              detail: "Connexion Postiz + boucle de performance",
              color: COLORS.pink,
            },
            {
              week: "Sem. 6+",
              task: "Reels vidéo (Veo 3)",
              detail: "Ajout de la génération vidéo + audio",
              color: COLORS.accent,
            },
          ].map((item, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                gap: 16,
                alignItems: "flex-start",
                marginBottom: 16,
              }}
            >
              <div
                style={{
                  background: item.color + "22",
                  color: item.color,
                  padding: "4px 10px",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 700,
                  flexShrink: 0,
                  minWidth: 60,
                  textAlign: "center",
                }}
              >
                {item.week}
              </div>
              <div>
                <div
                  style={{
                    color: COLORS.text,
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  {item.task}
                </div>
                <div
                  style={{ color: COLORS.textDim, fontSize: 12, marginTop: 2 }}
                >
                  {item.detail}
                </div>
              </div>
            </div>
          ))}

          <div
            style={{
              marginTop: 20,
              padding: "12px 16px",
              background: COLORS.accent + "15",
              borderRadius: 8,
              fontSize: 13,
              color: COLORS.text,
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: COLORS.accent }}>En parallèle dès le jour 1 :</strong>{" "}
            Poster manuellement via SocialBee/Canva (essai gratuit). Tu ne perds
            pas de temps pendant le développement. Quand le pipeline est prêt, tu bascules.
          </div>
        </div>
      </div>
    </div>
  );
}
