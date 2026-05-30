# TODO List : Gestion Intelligente & Organisation des Médias

Objectif : Transformer la bibliothèque en un système auto-organisé par artiste et fournir des outils de gestion de fichiers granulaires.

### 🎨 1. Système de Classement & Nommage (Artist-Driven)
- [ ] Détecter automatiquement le champ `artiste` (ou `groupe`) dans la bibliothèque.
- [ ] Créer une logique de création automatique de sous-dossiers (`Medias/Videos/ACDC/`, `Medias/Audios/Metallica/`, etc.).
- [ ] Fallback intelligent si l'artiste n'est pas renseigné (demande création dossier ou sélection).

### 📝 2. Édition Unitaire avec Déplacement/Copie
- [ ] Intégrer les fonctions de gestion de fichiers directement dans la modale d'édition.
- [ ] Afficher le chemin interactif (`#mt-path-display`) sous les pochettes.
- [ ] Permettre à l'utilisateur de "Déplacer" physiquement le média s'il s'est trompé de dossier lors du chargement.

### 📂 3. Gestionnaire de Médias Dédié (Gestion de Masse)
- [ ] Créer une nouvelle modale pour l'organisation globale des dossiers.
- [ ] Sélection multiple pour déplacer/copier des blocs de médias vers de nouvelles arborescences.
- [ ] Intégrer les sécurités anti-conflit (WinError 183) développées dans la session précédente.

### 🎤 4. Enregistrement Audio Professionnel (Moteur ASIO/WASAPI Backend)
- [x] Intégrer les bases d'enregistrement stéréo multi-canaux (WASAPI Chrome) avec correction de latence (DelayNode) et contrôle du gain d'entrée.
- [ ] Développer le moteur d'enregistrement natif dans le Backend Python (en s'appuyant sur `sounddevice`, `soundfile` et `numpy` déjà installés).
- [ ] Permettre à l'utilisateur de choisir son moteur dans l'interface :
  - **Moteur Web (WASAPI standard)** : Simple, direct via le navigateur (avec notre correctif de canaux et le fader matériel du TMP).
  - **Moteur Natif (ASIO / WASAPI complet)** : Enregistrement de niveau professionnel via le backend Python, contournant la limite de Chrome et capturant directement les entrées physiques de la carte.
- [ ] Implémenter l'API REST de contrôle de l'enregistrement (`/api/record/start`, `/api/record/stop`, `/api/record/devices`).
- [ ] Gérer l'alignement à la milliseconde et le mixage automatique du backing track côté serveur (Python) pour une précision temporelle absolue.

---
*Fin de Session V12 : Enregistrement stéréo Chrome corrigé (Downmix résolu via getSettings) et bases ASIO backend installées.*
