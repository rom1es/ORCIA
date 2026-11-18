"""Static editorial HTML pillars for standalone ORCIA showcase HTML."""

from __future__ import annotations

PILLAR_MACRO_HTML = """    <section id="pillar-macro" class="pillar-panel active"
      data-testid="showcase-pillar-macro">
      <div class="card">
        <span class="badge badge-cobalt">1.1 · Pourquoi ORCIA ?</span>
        <h2>Orchestrer Processus, Contexte documentaire et Agents spécialisés</h2>
        <p>
          ORCIA réunit dans un environnement unique les processus métiers
          structurés, le contexte documentaire vérifié de l'organisation et des
          agents spécialisés sous conduite humaine.
        </p>
      </div>
      <div class="card card-violet">
        <span class="badge badge-violet">
          1.2 · Principe Fondateur « Human-Led » (L'Humain aux Commandes)
        </span>
        <h2>Quatre garanties concrètes qui placent l'auteur humain au centre</h2>
        <div class="bento-grid">
          <div>
            <h3>✍️ Ancrages de Rédaction Humaine obligatoires (Violet)</h3>
            <p>
              L'intention initiale, les objectifs et les hypothèses structurantes
              appartiennent exclusivement à l'auteur humain.
            </p>
          </div>
          <div>
            <h3>🛑 Zéro validation machinale (« Anti-Validation Fantôme »)</h3>
            <p>
              Synthèse de décision en 4 blocs, approbation section par section
              (Approuver / Co-éditer / Contester) et temps minimal de lecture active.
            </p>
          </div>
          <div>
            <h3>⚖️ Arbitrage humain systématique en cas de dilemme</h3>
            <p>
              L'IA n'invente jamais un compromis flou : le processus se met en
              pause et présente les options à l'humain.
            </p>
          </div>
          <div>
            <h3>🛡️ Aucune modification sauvage des outils de l'entreprise</h3>
            <p>
              Actions préparées en attente d'accord humain avant toute écriture
              externe et réconciliation respectueuse des modifications humaines.
            </p>
          </div>
        </div>
      </div>
      <div class="card card-emerald">
        <span class="badge badge-emerald">
          1.3 · Double Barrière Anti-Hallucination (Déterministe + Probabiliste)
        </span>
        <h2>Stopper l'effet boule de neige dès la première étape</h2>
        <div class="bento-grid">
          <div>
            <h3>1. Barrière n°1 — Les Contrôles Déterministes (100 %, coût nul)</h3>
            <p>
              Vérification exacte de la structure du livrable, des sections
              obligatoires, des règles métiers du glossaire et des citations
              (<code>[S1]</code>, <code>[G1]</code>, <code>[O1]</code>).
            </p>
          </div>
          <div>
            <h3>2. Barrière n°2 — Les Contrôles Probabilistes Croisés</h3>
            <p>
              Interdiction pour un modèle IA d'être juge et partie (famille
              différente obligatoire), analyse sous 5 angles et purge des brouillons.
            </p>
          </div>
          <div>
            <h3>3. Barrière n°3 — La Remise en Cause Amont</h3>
            <p>
              Simulation d'impact sur les étapes suivantes et recalcul ciblé à
              partir de l'étape corrigée sans recommencer tout le processus.
            </p>
          </div>
        </div>
      </div>
      <div class="card">
        <span class="badge badge-cobalt">
          1.4 · Gouvernance par l'Organisation Réelle &amp; Packs Métiers
        </span>
        <h2>Plateforme entière ➔ Directions (BU) ➔ Espaces &amp; Packs Métiers</h2>
        <p>
          Chaque périmètre hérite des règles communes et active en 1 clic les
          Packs Métiers adaptés à son domaine.
        </p>
      </div>
    </section>"""

PILLAR_FEATURES_HTML = """    <section id="pillar-features" class="pillar-panel"
      data-testid="showcase-pillar-features">
      <div class="card">
        <span class="badge badge-violet">
          Volet A · Les 6 Dispositifs Concrets du Pilotage Humain
        </span>
        <h2>Dispositifs interactifs de pilotage humain et de fiabilité</h2>
        <div class="bento-grid">
          <div class="card"><h3>1. Carte d'Ancrage Humain (Violet)</h3></div>
          <div class="card"><h3>2. Carte d'Arbitrage en 1 Clic</h3></div>
          <div class="card"><h3>3. Grille 4 Blocs &amp; Validation par Section</h3></div>
          <div class="card"><h3>4. Simulateur d'Impact Amont &amp; Retour Ciblé</h3></div>
          <div class="card"><h3>5. Citations ([S1], [G1], [O1]) &amp; Glossaire</h3></div>
          <div class="card"><h3>6. Prise en Charge Exclusive &amp; Observation</h3></div>
        </div>
      </div>
      <div class="card">
        <span class="badge badge-cobalt">
          Volet B · Les 9 Écrans du Menu d'ORCIA expliqués un par un
        </span>
        <h2>Repères visuels et rôle de chaque écran</h2>
        <div class="bento-grid">
          <div class="card"><h3>1. ◈ Cockpit (<code>/cockpit</code>)</h3></div>
          <div class="card"><h3>2. 💬 Mon Assistant (<code>/assistant</code>)</h3></div>
          <div class="card"><h3>3. ☍ Mes Processus (<code>/processes</code>)</h3></div>
          <div class="card"><h3>4. 🤖 Mes Agents (<code>/agents</code>)</h3></div>
          <div class="card"><h3>5. 📦 Mes Espaces (<code>/spaces</code>)</h3></div>
          <div class="card"><h3>6. 📊 Suivi des Coûts (<code>/finops</code>)</h3></div>
          <div class="card"><h3>7. 📜 Journal d'Activité (<code>/activity</code>)</h3></div>
          <div class="card"><h3>8. ⚙ Configuration (<code>/settings</code>)</h3></div>
          <div class="card"><h3>9. ❓ Aide (<code>/help</code>) &amp; <code>⌘K</code></h3></div>
        </div>
      </div>
    </section>"""

PILLAR_ARCHITECTURE_HTML = """    <section id="pillar-architecture" class="pillar-panel"
      data-testid="showcase-pillar-architecture">
      <div class="card">
        <span class="badge badge-cobalt">
          3.1 · Monolithe Modulaire Hybride (TypeScript / Python 3.12+)
        </span>
        <h2>Isolation Hexagonale &amp; Contrats lint-imports</h2>
        <p>
          Stack : <code>pnpm 10.6</code>, <code>Turborepo 2.4</code>,
          <code>uv 0.13.5</code>, <code>FastAPI</code>, <code>SQLAlchemy 2.1</code>,
          <code>DBOS Transact 2.14</code>, <code>Dramatiq 2.1</code>,
          <code>PostgreSQL 18</code>, <code>pgvector 0.8.7</code>,
          <code>SeaweedFS 4.17</code>.
        </p>
      </div>
      <div class="card card-violet">
        <span class="badge badge-violet">
          3.2 · Implémentation Technique des Garanties Human-Led
        </span>
        <p>
          Signatures <code>SHA-256</code> dans <code>human_anchor_signatures</code>
          (<code>ERR_HUMAN_ANCHOR_REQUIRED</code>), <code>AdaptiveHumanGateService</code>,
          table <code>chunk_approvals</code>, verrous Redis 7.4
          <code>SET lock:step:&lt;id&gt; NX EX 900</code> (<code>ResourceLeaseService</code>),
          <code>ExternalEditRebaser</code> (<code>HUMAN_AMENDED_EXTERNAL</code>).
        </p>
      </div>
      <div class="card card-emerald">
        <span class="badge badge-emerald">
          3.3 · Mécanismes Déterministes &amp; Sandboxes Paliers 1a, 1b et 2
        </span>
        <p>
          <code>WorkflowYamlValidator</code>, <code>RunLockService</code>,
          Sandbox Palier 1a <code>Wasmtime</code> (<code>SubprocessTier1SandboxAdapter</code>),
          Compilateur <code>Text-to-Starlark</code> &amp; <code>StarlarkMechanismSandbox</code>
          O(n) anti-ReDoS, Sandbox Palier 2 <code>BimodalSandboxAdapter</code>, et
          <code>AssistantCitationAndV5GuardService</code>.
        </p>
      </div>
      <div class="card card-amber">
        <span class="badge badge-amber">
          3.4 · Mécanismes Probabilistes Gouvernés &amp; 3.5 · Sécurité
        </span>
        <p>
          <code>AgenticGateService</code>, <code>CognitiveRouterService</code>,
          <code>PostgreSQL 18</code> + <code>pgvector</code> <code>halfvec(1024)</code> +
          <code>ts_rank_cd</code> fusionnés par <code>RRF (k=60)</code>,
          <code>DBOS Transact</code>, <code>blackboard_snapshots</code>,
          <code>UpstreamChallengeAndReplayService</code>, <code>OIDC PKCE</code> +
          <code>Argon2id</code>, <code>EnvelopeVaultSecretProvider</code>,
          <code>PiiReversibleScrubber</code>.
        </p>
      </div>
    </section>"""
