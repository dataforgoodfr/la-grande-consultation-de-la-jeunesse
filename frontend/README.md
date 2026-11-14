# Frontend - La Grande Consultation de la Jeunesse

## Architecture

├── public
│   └── files
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

