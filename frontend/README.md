# Frontend - La Grande Consultation de la Jeunesse

Bienvenue dans le dépôt du frontend du projet La Grande Consultation de la Jeunesse.
Pour la procédure d'Onboarding, (cliquez ici)[ONBOARDING.md]

## Architecture

### Stack technique

Le projet est basé sur (Astro)[https://astro.build/], un framework axé sur la haute-performance, l'overhead minimal et la simplicité d'utilisation.
Il utilise (Tailwind)[https://tailwindcss.com/] pour le CSS, et (D3)[https://d3js.org/] pour la création de graphiques.
Pour la partie scripts, le projet utilise simplement des scripts TypeScript (supporté nativement par Astro) sans framework complexe (React, Vue..) car non nécessaires, et afin d'optimiser au maximum le chargement des pages.

### Structure du projet

├── public
│ └── files
└── src
├── components
├── layout
├── pages
├── scripts
└── styles

### public/

Dans ce dossier se trouvera uniquement les icônes d'onglet:

- favicon.svg (standard moderne)
- favicon.ico (compatibilité avec les anciens navigateurs)
- appple-touch-icon.png (pour les appareils iOS)

#### public/files/

Dans ce dossier se trouvera tous les fichiers servis par le site via des liens directs (ex. fichiers PDF).

### src/

#### components/

Le dossier qui contiendra tous les composants Astro réutilisables (comme la topbar, les boutons, etc...)

#### layout/

Ce dossier contiendra uniquement le layout global qui sera présent sur toutes les pages (présence de la topbar, footer...).

#### pages/

Le dossier principal qui contiendra l'ensemble des pages sur lesquelles les utilisateurices pourront naviguer (/accueil, /je-m-engage...).

#### scripts/

L'ensemble des fichiers TypeScript qui contiendront les logiques à exécuter côté client (notamment la logique des graphes et de leurs filtres).

#### styles/

Le dossier qui contient l'ensemble des fichiers CSS pour définir le style et le theming du site.
