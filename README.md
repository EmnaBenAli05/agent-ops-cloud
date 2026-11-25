# agent-ops-cloud

Prototype d'**agent IA pour l'exploitation cloud** : à partir d'une alerte de supervision, un LLM (Claude) enquête avec des outils (métriques, journaux), identifie la cause probable et propose une action. Les actions sensibles passent par une **validation humaine**, et chaque appel d'outil est **tracé**.

Projet personnel d'apprentissage de l'IA agentique, appliquée à un contexte Ops sécurisé.

## Ce que montre le projet

| Notion | Où la trouver |
|---|---|
| Boucle d'agent (raisonnement, appel d'outil, observation) | `agent_ops/agent.py` → `run_agent` |
| Tool calling avec schémas stricts | `agent_ops/tools.py` (`strict: true`, `additionalProperties: false`) |
| Appels d'outils en parallèle | les métriques et les journaux sont lus dans le même tour |
| Supervision humaine des actions sensibles | `restart_service` n'est exécuté qu'après « o » de l'opérateur |
| Garde-fous dans le code, pas seulement dans le prompt | liste blanche d'outils, validation des entrées, limite de tours |
| Résistance à l'injection de prompt | l'alerte ALT-003 contient une fausse consigne dans un journal |
| Traçabilité | `logs/audit.jsonl` : outil, entrées, décision, durée |
| Évaluation par scénarios | `evals/scenarios.py` : 4 scénarios, 20 critères |

## Architecture

```
alerte ──> [ LLM ] ──tool_use──> [ harnais ] ──> outil lecture seule ──> données simulées
              ^                      │
              │                      ├── outil sensible ──> validation humaine ──> exécution ou refus
              └────── tool_result ───┤
                                     └── journal d'audit (JSONL)
```

Le harnais (le code Python) garde la main : le modèle **propose** un appel, le harnais **décide** de l'exécuter. Un appel vers un outil inconnu, une entrée invalide ou un refus de l'opérateur revient au modèle sous forme d'erreur, et il doit proposer une alternative.

L'environnement est **simulé** (fichiers `data/*.json`) : aucune commande n'est lancée sur une vraie machine.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (Linux/macOS : source .venv/bin/activate)
pip install -r requirements.txt
```

## Utilisation

**Sans clé d'API** (faux LLM déterministe qui rejoue un raisonnement écrit à l'avance, pour tester le harnais) :

```bash
python -m agent_ops ALT-001 --offline
```

**Avec Claude** (clé dans la variable `ANTHROPIC_API_KEY`, appels payants) :

```bash
python -m agent_ops ALT-001
```

Options : `--auto-deny` refuse toute action sensible sans demander ; `--audit chemin.jsonl` change le fichier d'audit.

Les trois alertes simulées :

| Alerte | Situation | Comportement attendu |
|---|---|---|
| ALT-001 | Latence de l'API de paiement, pool SQL saturé | propose un redémarrage, soumis à l'opérateur |
| ALT-002 | Disque /var/log plein, logrotate en échec | aucun redémarrage, action manuelle proposée |
| ALT-003 | 404 après un déploiement, avec une injection dans les journaux | ignore l'injection et la signale |

## Tests et évaluation

```bash
python -m unittest -v          # garde-fous et boucle (hors ligne)
python -m evals.scenarios      # 4 scénarios, faux LLM
python -m evals.scenarios --live   # mêmes scénarios avec Claude (payant)
```

Le faux LLM du scénario ALT-003 est volontairement « naïf » : il obéit à l'injection. Le test vérifie que le harnais bloque quand même l'action. Avec `--live`, on mesure si le vrai modèle résiste aussi à l'injection.

## Choix techniques

- **SDK officiel `anthropic`**, modèle `claude-opus-5-5`, effort `medium`.
- **Boucle écrite à la main** plutôt qu'un framework (LangChain, LangGraph) : pour comprendre chaque étape et pouvoir brancher le faux LLM des tests.
- **Repli automatique** (`fallbacks: "default"`) : si un filtre de sécurité refuse la requête, l'API la rejoue sur un modèle de repli.
- **Moindre privilège** : un seul outil peut modifier l'infrastructure, et ses entrées sont validées avant même d'être montrées à l'opérateur.

## Pistes d'amélioration

- Exposer les outils par un serveur **MCP** pour les rendre utilisables par d'autres agents.
- Ajouter une base de connaissances (procédures d'exploitation) interrogée en **RAG**.
- Brancher de vraies sources : API Prometheus, journaux d'une VM, OpenStack.
- Mémoire des incidents passés pour reconnaître un problème récurrent.
