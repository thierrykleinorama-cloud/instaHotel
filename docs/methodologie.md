# METHODOLOGIE CLAUDE CODE - INSTA HOTEL PROJECT
# Regles de travail a respecter pendant tout le developpement
# Version : 1.0 - 23 fevrier 2026

---

## 1. WORKFLOW ORCHESTRATION

### 1.1 Plan Mode Default
- **Entrer en mode plan** pour TOUTE tache non triviale (3+ etapes ou decisions d'architecture)
- Si quelque chose deraille → **STOP et re-planifier immediatement** (ne pas continuer a pousser)
- Utiliser le mode plan pour les etapes de verification, pas seulement pour construire
- **Ecrire des specs detaillees en amont** pour reduire l'ambiguite

### 1.2 Subagent Strategy
- Utiliser les subagents genereusement pour garder le contexte principal propre
- Deleguer : recherche, exploration, analyses paralleles → subagents
- Pour les problemes complexes, envoyer plus de compute via subagents
- **1 tache = 1 subagent** pour une execution focalisee

### 1.3 Self-Improvement Loop
- Apres TOUTE correction de l'utilisateur → mettre a jour `tasks/lessons.md` avec le pattern
- Ecrire des regles pour soi-meme qui empechent de refaire la meme erreur
- Iterer sans relache sur ces lecons jusqu'a ce que le taux d'erreur baisse
- **Relire les lecons au debut de chaque session** sur le projet concerne

### 1.4 Verification Before Done
- **Ne jamais marquer une tache complete sans prouver qu'elle fonctionne**
- Comparer le comportement entre main et les changements quand pertinent
- Se demander : "Est-ce qu'un ingenieur senior approuverait ceci ?"
- Lancer les tests, verifier les logs, demontrer la correction

### 1.5 Demand Elegance (Balanced)
- Pour les changements non triviaux : pause et se demander "y a-t-il une facon plus elegante ?"
- Si un fix semble hacky : "Sachant tout ce que je sais maintenant, implementer la solution elegante"
- **Sauter cette etape pour les fixes simples et evidents** — ne pas sur-ingenierer
- Challenger son propre travail avant de le presenter

### 1.6 Autonomous Bug Fixing
- Quand on recoit un bug report : **le fixer directement**. Ne pas demander qu'on tienne la main.
- Pointer vers les logs, erreurs, tests qui echouent — puis les resoudre
- **Zero context-switching requis de l'utilisateur**
- Aller fixer les tests CI qui echouent sans qu'on demande comment

---

## 2. TASK MANAGEMENT

### 2.1 Plan First
Ecrire le plan dans `tasks/todo.md` avec des items cochables.

### 2.2 Verify Plan
**Check-in avec l'utilisateur avant de commencer l'implementation** pour les phases majeures.

### 2.3 Track Progress
Marquer les items completes au fur et a mesure.

### 2.4 Explain Changes
Resume haut niveau a chaque etape. Pas de dump de code sans explication.

### 2.5 Document Results
Ajouter une section "review" dans `tasks/todo.md`.

### 2.6 Capture Lessons
Mettre a jour `tasks/lessons.md` apres chaque correction.

---

## 3. CORE PRINCIPLES

### 3.1 Simplicity First
- **Faire chaque changement aussi simple que possible**
- Impact minimal sur le code existant
- Preferer la solution evidente a la solution "intelligente"

### 3.2 No Laziness
- **Trouver les causes racines**. Pas de fixes temporaires.
- Standards de developpeur senior.
- Si quelque chose ne marche pas, comprendre POURQUOI avant de fixer.

### 3.3 Minimal Impact
- Les changements ne doivent toucher que ce qui est necessaire
- **Eviter d'introduire des bugs** en modifiant du code qui fonctionnait
- Un commit = une responsabilite claire

---

## 4. CHECKLIST AVANT CHAQUE COMMIT

- [ ] Le code fonctionne (teste manuellement ou via tests)
- [ ] Pas de regression sur les fonctionnalites existantes
- [ ] Le code est lisible (noms explicites, commentaires si necessaire)
- [ ] `tasks/todo.md` mis a jour
- [ ] Si correction utilisateur → `tasks/lessons.md` mis a jour

---

## 5. ANTI-PATTERNS A EVITER

| Ne pas faire | Faire a la place |
|-----------------|---------------------|
| Demander validation avant d'essayer | Essayer, tester, puis montrer |
| Fix hacky rapide | Comprendre la cause racine |
| Gros commit monolithique | Petits commits focalises |
| Ignorer une erreur | Logger et investiguer |
| Supposer que ca marche | Prouver que ca marche |
| Redemander la meme chose | Relire lessons.md |

---

## 6. COMMUNICATION AVEC L'UTILISATEUR

### Ce que j'annonce :
- Ce que je vais faire (plan)
- Ce que j'ai fait (resultat)
- Ce qui bloque (avec analyse)
- Ce que je propose (solutions)

### Ce que je n'annonce PAS :
- Mes reflexions internes detaillees
- Du code sans contexte
- Des questions dont je peux trouver la reponse seul
- Des demandes de validation pour des choix evidents

---

*Document de methodologie - A relire au debut de chaque session*
