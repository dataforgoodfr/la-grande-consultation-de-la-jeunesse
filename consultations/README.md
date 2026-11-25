# Consultations : scripts d'analyse

Analyse des réponses au questionnaire **Grande Consultation**.

## Installation

Utilisez **l'environnement Python de votre choix** (venv, conda, uv, Python du système…), en version 3.10 ou plus.
Une fois cet environnement activé, depuis ce dossier :

```
python -m pip install -r requirements-dev.txt
python -m pytest -q          # vérifie que tout fonctionne (données simulées)
```

`requirements.txt` contient les bibliothèques d'analyse ; `requirements-dev.txt` y ajoute les carnets et les tests.
Dans VS Code, choisissez votre environnement avec `Cmd+Maj+P` > *Python: Select Interpreter*,
et comme noyau des carnets (*Select Kernel*).

## Utilisation

Déposer l'export dans `data/` (jamais versionné), puis, avec votre environnement activé :

```
python src/grande_consultation.py data/gc_reponses.xlsx resultats/gc
```

Ou dans VS Code : *Exécuter et déboguer* (`Cmd+Maj+D`), choisir la configuration, `F5`.
Le script écrit `resultats.xlsx` (un onglet par analyse) et `donnees_propres.csv` dans le dossier de sortie.

## Carnets Jupyter

Le code (fonctions, variables, commentaires) est en anglais ; les textes affichés dans les rapports et graphiques restent en français.
Un guide complet des étapes et de chaque fonction est dans `docs/guide_notebooks_et_fonctions.md`.

Deux carnets dans `notebooks/` (à ouvrir dans VS Code ou Jupyter, avec votre environnement comme noyau) :

| Carnet | Rôle |
| --- | --- |
| `grande_consultation.ipynb` | Analyse complète de la Grande Consultation, avec export Excel |
| `gc_graphiques.ipynb` | Premiers graphiques de la Grande Consultation, un par cellule |

Pour les carnets de graphiques : déposez l'export dans `data/gc_reponses.xlsx`
(ou changez `DATA_PATH` dans la première cellule), exécutez la section 0 une fois, puis les graphiques un par un.
`SAVE = True` enregistre les images dans `resultats/graphiques/`. Les fonctions de tracé communes sont dans `src/charts.py`.
Les carnets sont livrés **sans sorties** : ne les enregistrez pas exécutés si les données sont personnelles
(menu « Clear All Outputs » avant de versionner).

## Organisation

| Dossier | Contenu |
| --- | --- |
| `src/geo.py`, `resources/geo/` | Cartes : codes département, comptages par département / région, contours de la France (outre-mer inclus) |
| `src/common.py` | Fonctions partagées : intervalle de Wilson, tris, séparation des choix multiples |
| `src/grande_consultation.py` | Script d'analyse de la Grande Consultation (et bibliothèque des carnets) |
| `src/charts.py` | Fonctions de tracé communes |
| `conceptions/` | Définitions des questionnaires (PDF, xlsx) |
| `data/` | Exports bruts. **Données personnelles : ne jamais commiter** |
| `resultats/` | Sorties des scripts. Ne pas commiter non plus |
| `tests/` | Générateurs de réponses simulées et tests automatiques |

## Tests et qualité

```
python -m pytest -q          # ou Cmd+Maj+P > Tasks: Run Task > Tests
python -m ruff check src tests
```

Les tests utilisent des réponses **simulées** (`tests/gen_gc.py`), jamais de vraies données.
Toute modification de `common.py` doit repasser les tests.

## Confidentialité

Ce dossier est publié dans un dépôt **public**. Avant chaque commit, vérifier qu'aucun fichier de `data/` ou `resultats/`,
aucun export (`.xlsx`, `.csv`) et aucune sortie de carnet n'apparaît dans la liste des fichiers modifiés.

## Ajouter une nouvelle consultation

Copier `src/grande_consultation.py`, adapter les paramètres en tête de fichier (`ORDINALS`, `PROFILE`, `ORDERS`,
numéros des questions particulières), ajouter un générateur de données simulées dans `tests/`
et une configuration dans `.vscode/launch.json`.
