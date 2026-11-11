# Guide : des réponses brutes aux carnets, étape par étape, et chaque fonction expliquée

Ce guide accompagne les deux carnets du projet (`notebooks/`) et les quatre modules Python (`src/`).
Il a deux parties : le **parcours** (dans quel ordre on arrive aux carnets, et pourquoi) puis la **référence** (ce que fait chaque fonction).



## 1. Vue d'ensemble

```
export Tally (xlsx)                                   src/
        │                                  ┌───────────────────────────┐
        ▼                                  │ common.py                 │  statistiques partagées
  load ──► discover_questions ──► …        │ charts.py                 │  tous les graphiques
        │                                  │ geo.py                    │  départements et régions
        ▼                                  │ grande_consultation.py    │  analyses GC
  explode_text_answers                     └───────────────────────────┘
        │
        ▼                                  notebooks/
  recode ──► tableau nettoyé `d`           ├─ grande_consultation.ipynb   analyse complète + export Excel
        │                                  └─ gc_graphiques.ipynb         un graphique par cellule
        ├─► tableaux à plat
        ├─► croisements
        └─► graphiques (charts.py)
```

Principe de conception : **les calculs sont dans `src/`, les carnets ne font qu'appeler**. Un carnet = quelques paramètres, un chargement (section 0), puis une cellule par résultat. Ainsi, une règle (par exemple le seuil `MIN_N`) se corrige à un seul endroit.

Arborescence utile :

| Chemin | Rôle |
| --- | --- |
| `src/common.py` | Normalisation de texte, tris, découpage des choix multiples, Wilson |
| `src/charts.py` | Barres simples, empilées, groupées, panneaux, sauvegarde PNG, **carte de France** (`map_france`) |
| `src/geo.py` | Géographie : code département d'une réponse, comptages par département et par région, noms |
| `resources/geo/france.json` | Contours simplifiés des 101 départements et 18 régions (métropole + outre-mer), fichier fourni |
| `tools/build_geo.py` | Script de construction **ponctuelle** de ce fichier (a besoin de `shapely`, inutile pour les carnets) |
| `src/grande_consultation.py` | Chargement, reconnaissance des questions, recodage, tableaux, croisements de la Grande Consultation (script **et** bibliothèque pour les carnets) |
| `notebooks/` | Les deux carnets |
| `modeles/marges_gc_modele.xlsx` | Modèle de marges pour la pondération (à remplir) |

## 2. Traitement, étape par étape

### Étape 1. Mettre en place l'environnement
On installe dans son environnement `requirements-dev.txt`, qui inclut `requirements.txt` (pandas, numpy, scikit-learn, openpyxl).


### Étape 2. Déposer l'export et régler les paramètres
On place l'export dans `data/gc_reponses.xlsx`. Dans chaque carnet, la première cellule contient les paramètres (en MAJUSCULES) : `DATA_PATH`, `OUTPUT_DIR`, `SAVE`, `SHOW_CI`.

### Étape 3. Charger les réponses et retirer les soumissions en double
Fonction : `load(path)`.
`load` supprime les `Submission ID` répétés et affiche le nombre retiré. Attention : un **`Respondent ID` répété** n'est pas forcément un doublon -> la cellule de diagnostic (comparaison des Q24 à Q28) sert à décider.

### Étape 4. Reconnaître les questions
Fonctions : `question_number`, `discover_questions`, `check_structure`.
Les en-têtes de l'export ressemblent à `24. Quel âge avez-vous ?`. On repère le numéro au début de l'en-tête et on **regroupe les colonnes d'une même question**. Une question qui a une colonne « texte » plus une colonne par option (`question (option)`) est de type **multiple** ; une question à une seule colonne est **single** (ou **text** pour la question ouverte Q13).
`check_structure` s'arrête avec un message qui dit *quelles* questions manquent et montre les premières colonnes non reconnues.

### Étape 5. Éclater les choix multiples exportés en une seule colonne de texte
Fonctions : `explode_text_answers`, `split_protected`, `split_choices`, `split_outside_parentheses` (dans `common.py`), `normalize_other`.
Certaines questions à choix multiples (Q1, Q2, Q5 et celles dont l'intitulé annonce « choix maximum ») sont exportées en une cellule `A, B, C`. On les coupe aux virgules **hors parenthèses**, on crée une colonne vrai/faux par option, et on mémorise l'**ordre** des réponses (utile pour le classement de la Q5).

- une option qui contient une virgule ne doit pas devenir deux faux choix : la liste `COMMA_OPTIONS` les protège ;
- « Autre : blabla, blabla » créerait de faux choix : on ne garde que les options vues dans des réponses sans « Autre ».
Variante : `export_boolean_columns` écrit une copie de l'export avec ces colonnes vrai/faux, dans le format d'un export Tally complet.

### Étape 6. Recoder : passer des libellés aux scores et au tableau nettoyé
Fonction : `recode(df, qs)`.
Elle fabrique le tableau `d` (une ligne par répondant·e) :
- un **score** pour chaque question ordinale (`Q3_score` : « Non, pas du tout » = 1 … « Oui, tout à fait » = 4) à l'aide des échelles `LIKERT_AGREEMENT`, `LIKERT_IMPORTANCE`, `READING`. « Je ne sais pas » ne reçoit **pas** de score ;
- l'âge et la **tranche d'âge** (15-17 / 18-22 / 23-24), les variables de profil (`PROFILE`), l'indicateur Île-de-France ;
- une copie nettoyée des réponses à choix unique (`Q19`, `Q23`…) pour les croisements.
Info : un libellé qui change dans l'export ne casse pas le calcul en silence ; il est renvoyé dans `unmapped` et affiché (« libellés non reconnus pour le score »).

### Étape 7. Les tableaux à plat avec leur incertitude
Fonctions : `frequency_tables` (choix unique), `multiple_choice_tables` (choix multiples), `ranking_table` (Q5), `wilson`.
Pour chaque réponse : effectif, base, pourcentage et **intervalle de confiance à 95 % de Wilson**. La base est le nombre de personnes qui ont répondu à *cette* question (pas le total). 

### Étape 8. Croiser deux questions
Fonctions : `cross` (une paire), `simple_crossings` (toutes les questions × tous les profils), `multiple_crossings`, `options_by_profile`, `compare_options`.
On compare la répartition d'une question selon les groupes d'une autre. Règles appliquées partout : les modalités « Je préfère ne pas répondre » sont écartées, les lignes de moins de `MIN_N` = 20 personnes sont écartées **et nommées**, et l'on ne conclut jamais sur un groupe trop petit.

### Étape 9. Les profils types
Fonction : `typical_profiles`.
`typical_profiles` fait une classification hiérarchique (Ward) sur les scores, choisit le nombre de profils (3 à 5) par la **silhouette**, et prévient si la structure est faible (< 0,25).

### Étape 10. Les graphiques
Module `charts.py` : `bars`, `stacked`, `grouped`, `panels`, `long_from_tables`, `save_figure`. Règles graphiques identiques partout : bleu pour une mesure simple, bleu + orange pour deux séries, une seule teinte du clair au foncé pour une échelle ordonnée, **gris** pour « sans avis » toujours en dernier, **base écrite sur chaque graphique**, barres d'erreur optionnelles (`SHOW_CI`).

### Étape 10 bis. La carte des réponses par département et par région
Fonctions : `geo.department_code`, `geo.count_by_department`, `geo.count_by_region`, `charts.map_france`, `regions`.
La Q28 donne « 75 - Paris » : `department_code` lit le code (gère `2A`/`2B`, `974`, les codes à un chiffre). `count_by_department` compte les réponses par code , `count_by_region` additionne les départements par région. `map_france` dessine la métropole, un **zoom sur l'Île-de-France** (Paris et la petite couronne sont minuscules à l'échelle de la France) et l'outre-mer en encarts.
Règle de confidentialité : sous `min_n` réponses (10 par département, 20 par région) la zone reste **grise et sans chiffre**. 

### Étape 11. Assembler les carnets, exporter, vérifier
Chaque carnet : section 0 (paramètres + chargement + petites fonctions d'aide), puis une cellule par graphique ou tableau, terminée par `finish("nom")` qui affiche et, si `SAVE = True`, enregistre un PNG à 200 dpi. Le carnet principal exporte `resultats.xlsx` (un onglet par analyse) et `donnees_propres.csv`.


## 3. Référence des fonctions

Dans ces tableaux, « Entrée » et « Sortie » décrivent ce que reçoit et renvoie la fonction.

### 3.1 `src/common.py`

| Fonction | Rôle | Entrée → Sortie | À savoir |
| --- | --- | --- | --- |
| `normalize(s)` | Rend deux libellés comparables : minuscules, sans accents, ... | texte → texte | Sert à repérer des colonnes et à ordonner par mots-clés. |
| `order_by_list(values, order)` | Trie selon une liste **exacte**. | listes → liste | Ce qui n'est pas dans `order` passe à la fin. |
| `order_by_keywords(values, keywords)` | Trie selon des **mots-clés** (normalisés). | liste de libellés, mots → liste | Un mot précédé de `^` doit être au **début** du libellé : évite que « satisfaisante » soit trouvé dans « insatisfaisante ». |
| `split_outside_parentheses(value, clean=None)` | Coupe `A, B (x, y), C` sur les virgules **hors parenthèses**. | cellule → liste | `clean` s'applique à chaque morceau (par ex. regrouper « Autre : … »). Valeur vide → `[]`. |
| `wilson(k, n, z=1.96)` | Intervalle de confiance à 95 % d'une proportion `k/n`. | entiers → (bas, haut) | Formule ci-dessous. Si `n = 0` : `(nan, nan)`. |


**Wilson.** Avec `p = k/n` et `z = 1,96` : centre = `(p + z²/2n) / (1 + z²/n)`, marge = `z·√(p(1−p)/n + z²/4n²) / (1 + z²/n)`. Les bornes sont `centre ± marge`, bornées entre 0 et 1. Contrairement à l'intervalle « naïf » (`p ± 1,96·√(p(1−p)/n)`), il ne sort jamais de [0, 1] et reste correct pour les petits effectifs et les pourcentages proches de 0 ou 100 %.


### 3.2 `src/charts.py`

| Élément | Rôle | À savoir |
| --- | --- | --- |
| `BLUE`, `ORANGE`, `GREY`, `INK`, `INK2`, `GRID` | Palette unique du projet. | Un seul endroit pour changer une couleur. |
| `SHOW_CI` | Interrupteur **global** des barres d'erreur. | `bars(..., ci=True/False)` le surcharge pour un graphique. |
| `NO_OPINION_WORDS` | Fragments qui désignent « sans avis ». | Comparés après suppression des accents. |
| `is_no_opinion(label)` | Vrai si la modalité est « je ne sais pas / sans avis / préfère ne pas répondre ». | Détermine le gris et le placement en dernier. |
| `blue_ramp(n)` | `n` teintes de bleu, du clair au foncé. | Une échelle ordonnée n'a **qu'une** teinte : pas de rouge/vert, donc aucun jugement bon/mauvais. |
| `apply_style()` | Réglages matplotlib communs (polices, axes, couleurs). | Appelée à l'import. |
| `bars(t, label, value, low, high, title, base, n_max, sort, note, color, ax, width, highlight, ci)` | Barres horizontales ; `value` en proportion (0-1) ; `low`/`high` = colonnes des bornes de l'IC. | `sort=False` garde l'ordre du tableau (échelles, tranches d'âge) ; `highlight={étiquette: couleur}` colore une barre ; erreur claire si le tableau est vide. |
| `stacked(t, row, category, pct, order, base, title, note, ax, width)` | Une barre à 100 % par ligne. | `order` va du négatif au positif ; les valeurs < 7 % ne sont pas écrites ; renormalise chaque barre à 100 ; écrit `n = …` à côté de chaque ligne. |
| `grouped(t, category, series, value, series_order, title, base, note, n_max, ax, width)` | Plusieurs séries sur les mêmes catégories. | 2 séries : bleu + orange ; ≥ 3 séries : rampe de bleus ; catégories triées par la première série. |
| `long_from_tables(tables, questions, labels, key, category, pct)` | Assemble les tableaux à plat de plusieurs questions en un tableau long (`row`, `category`, `pct`, `base`). | Alimente `stacked` quand plusieurs questions partagent la même échelle. |
| `panels(n, ncols, width, height)` | Grille de `n` panneaux ; renvoie (figure, axes). | Les cases en trop sont masquées. |
| `save_figure(fig, name, folder, enabled)` | Enregistre un PNG (200 dpi, fond blanc) si `enabled`. | Crée le dossier ; renvoie le chemin ou `None`. |
| `map_france(counts, level, title, min_n, labels, base, note, size)` | Carte de France colorée par nombre de réponses ; `level` = `"department"` ou `"region"` ; renvoie la figure. | Zoom Île-de-France au niveau département, outre-mer en encarts, gris sous `min_n`, légende et base écrites. Fonctions internes : `_label_point`, `_draw_shapes`, `_frame`. |
| `_wrap`, `_title`, `_x_grid`, `_get_ax`, `_luminance`, `_ascii_lower` | Aides internes (retour à la ligne, titre + sous-titre « base · note », grille, création d'axe, luminance d'une couleur pour choisir texte blanc/noir). | Le préfixe `_` signale un usage interne ; `_x_grid` et `_title` sont aussi utilisés dans le carnet pour le graphique des mots. |

### 3.2 bis `src/geo.py`

| Fonction | Rôle | À savoir |
| --- | --- | --- |
| `load_geography()` | Lit `resources/geo/france.json`  | `{"departments": [...], "regions": [...]}`, chaque zone a `code`, `name`, `polygons` ; chaque département a aussi sa `region`. |
| `department_code(label)` | « 75 - Paris » → `"75"`, « 2a - … » → `"2A"`, « 1 - Ain » → `"01"`. | `None` si aucun code lisible. |
| `count_by_department(labels)` | Réponses par code de département, sur **tous** les départements de la carte (0 si aucune). | `.attrs["unknown"]` = réponses dont le code n'est pas un département connu. |
| `count_by_region(dept_counts)` | Somme par région. | Les 18 régions, 0 si aucune. |
| `names(level)` | `{code: nom}` des départements ou des régions. | |

### 3.3 `src/grande_consultation.py`

**Paramètres (haut du fichier)**

| Constante | Sens |
| --- | --- |
| `MIN_N = 20` | En dessous, un groupe est signalé « effectif trop faible » et écarté des croisements. |
| `MIN_N_DEPT = 10` | Seuil d'affichage d'un département. |
| `K_RANGE = range(3, 6)` | Nombres de profils types essayés. |
| `LIKERT_AGREEMENT`, `LIKERT_IMPORTANCE`, `READING` | Libellé → score. |
| `NO_OPINION` | Réponses jamais converties en score. |
| `ORDINALS` | Numéro de question → échelle utilisée. |
| `PROFILE` | Numéro de question → nom de la variable de profil (âge, genre, études, situation, orientation, Île-de-France). |
| `ORDERS` | Ordre d'affichage des modalités (niveau d'études, situation, orientation politique, tranche d'âge). |
| `TEXT_MULTIPLE_QS = {1, 2, 5}` | Choix multiples exportés en une colonne de texte. |
| `RANKED_QS = {5}` | Questions où l'ordre des réponses compte. |
| `AGE_BRACKETS` | Libellés des tranches d'âge (15-17 / 18-22 / 23-24), utilisés par `recode` et `ORDERS`. |
| `AGE_Q = 24`, `DEPT_Q = 28`, `FREE_TEXT_Q = 13` | Numéros de questions particulières. |
| `IDF`, `NO_ANSWER`, `STOPWORDS`, `COMMA_OPTIONS` | Départements d'Île-de-France, libellé « préfère ne pas répondre », mots vides, options à virgule à protéger. |

**Chargement et structure**

| Fonction | Rôle |
| --- | --- |
| `load(path)` | Lit l'Excel, supprime les `Submission ID` répétés et l'indique. |
| `question_number(column)` | Numéro d'une question d'après son en-tête (tolère BOM, espaces insécables, caractères invisibles) ; `None` si non numéroté. |
| `discover_questions(df)` | Regroupe les colonnes par question et renvoie `{n: {text, type, column, text_column, options, cols}}`. `type` ∈ `single`, `multiple`, `text`. |
| `check_structure(qs, df)` | Vérifie que les questions indispensables (âge, département, profils) existent ; sinon, message détaillé. |
| `normalize_other(x)` | « Autre : blabla » → « Autre ». |
| `clean_text(s)` | Nettoie le texte (espaces retirés, « Autre » regroupé). |
| `split_choices(value)` | Découpe un choix multiple en liste (virgules hors parenthèses). |
| `split_protected(value)` | Idem, en protégeant les virgules des libellés de `COMMA_OPTIONS`. |
| `explode_text_answers(df, qs)` | Crée une colonne vrai/faux par option et la liste ordonnée des réponses (`qs[n]["lists"]`). Modifie `df` et `qs`. |
| `export_boolean_columns(path, output)` | Écrit une copie de l'export avec ces colonnes, nommées `question (option)`. |
| `as_bool(s)` | Colonne `"True"/"False"` (texte ou booléen) → vrais booléens. |

**Recodage**

| Fonction | Rôle |
| --- | --- |
| `recode(df, qs)` | Construit le tableau nettoyé `d` et la liste `unmapped` des libellés non reconnus. |

**Analyses**

| Fonction | Rôle | Sortie |
| --- | --- | --- |
| `frequency_tables(df, d, qs)` | Tris à plat des questions à choix unique. | Colonnes `question, intitulé, réponse, effectif, base, %, IC95 bas, IC95 haut, non-réponse (%)`. |
| `multiple_choice_tables(df, qs)` | Tris à plat des choix multiples. | Colonne `% des répondants`, triée par effectif. |
| `ranking_table(qs)` | Q5 : % en 1re position et rang moyen. | Le rang moyen n'est pertinent que si l'export garde l'ordre de sélection. |
| `near_vs_urgent_causes(df, qs)` | Q1 (cause proche) vs Q2 (cause urgente) et écart en points. | Trié par urgence. |
| `simple_crossings(d, qs)` | Chaque question à choix unique × chaque profil. | Répartition de chaque question par groupe (onglet « Croisements »). |
| `multiple_crossings(df, d, qs)` | Chaque option de chaque choix multiple × chaque groupe. | % du groupe, avec le drapeau `effectif trop faible`. |
| `cross(d, row, column, mask, row_order, column_order, sort_by, n_min)` | Croise deux variables de `d`. | `(tableau long, résumé)`. Tableau long : `row, category, n, base, pct`. Résumé : effectif `n` et groupes écartés `dropped`. Lève une erreur claire si plus aucune ligne n'atteint `n_min`. |
| `stats_note(r)` | Phrase de sous-titre à partir du résumé de `cross`. | Mentionne toujours les groupes écartés. |
| `options_by_profile(df, d, qs, n, profile, group_order)` | Choix multiple × profil : part de chaque groupe par option, avec IC de Wilson. | `(tableau long, groupes écartés)`. |
| `compare_options(df, qs, n, mask_a, mask_b, name_a, name_b)` | Deux groupes, une option à la fois : part A, part B, écart en points. | DataFrame, une ligne par option, le plus grand écart d'abord. |
| `voting_analysis(d)` | Q23 chez les personnes en âge de voter (Q22 = « Oui »). | Base spécifique indiquée. |
| `typical_profiles(d)` | Classification (Ward), k choisi par silhouette, avec lecture de la qualité. | `(moyennes par profil, qualité, colonnes utilisées)`. Ajoute une colonne `profil` à `d`. Exige ≥ 30 personnes complètes. |
| `departments(d)` | Effectif par département « affichable ». | |
| `regions(d)` | Effectif par région (somme des départements) « affichable » (≥ `MIN_N`). | onglet « Régions » dans l'export. |
| `normalize_word(word)` | Un mot en minuscules sans accents ni ponctuation. | |
| `free_text_words(df, qs)` | Q13 : réponses les plus fréquentes (normalisées) et mots les plus fréquents (top 100). | `(réponses, mots)`. |
| `main()` | Enchaîne le tout et produit `resultats.xlsx` et `donnees_propres.csv`. | Lancé par `python src/grande_consultation.py fichier.xlsx [dossier]`. |



### 3.4 Fonctions d'aide définies dans les carnets

| Carnet | Fonction | Rôle |
| --- | --- | --- |
| `gc_graphiques` | `freq_of(n, order)` | Tableau à plat de la question `n`, dans l'ordre voulu. |
| | `scale(n)` | Modalités d'une question ordinale, du négatif au positif, puis « sans avis ». |
| | `title_of(n)` | Intitulé de la question, utilisé comme titre. |
| | `single_choice_bars(n)` / `multiple_choice_bars(n)` | Un graphique en barres complet en une ligne. |
| | `stacked_questions(ns, labels, fig_title)` | Barres empilées de plusieurs questions qui partagent la même échelle. |
| | `finish(name)` | Affiche la figure et l'enregistre en PNG si `SAVE = True`. |
| | `cross_stacked(row, column, fig_title, **kw)` | Croisement de deux questions en barres empilées. |
| | `compare_and_plot(n, fig_title)` | Comparaison de deux groupes (Q23 = Non vs Oui) sur une question à options. |
| `grande_consultation` | `freq_of(n)` | Tableau à plat de la question `n`, plus grande réponse d'abord. |
| | `plot_bars(t, title, col, n_max)` | Graphique rapide avec barres d'erreur. |


## 4. Les carnets cellule par cellule

### `grande_consultation.ipynb` : l'analyse complète
| Section | Contenu | Fonctions principales |
| --- | --- | --- |
| 0 | Paramètres, imports | |
| 1 | Chargement, structure, recodage | `load`, `discover_questions`, `check_structure`, `explode_text_answers`, `recode` |
| 2 | Qualité : valeurs manquantes | |
| 3 | Profil de l'échantillon | `frequency_tables` |
| 4 | Tris à plat (choix unique) : changer `N` | `freq_of`, `plot_bars` |
| 5 | Choix multiples, Q5, causes proches vs urgentes | `multiple_choice_tables`, `ranking_table`, `near_vs_urgent_causes` |
| 6 | Croisements questions × profil | `simple_crossings`, `multiple_crossings` |
| 7 | Intention de vote (Q23) | `voting_analysis` |
| 8 | Profils types | `typical_profiles` |
| 9 | Départements et régions | `departments`, `regions` |
| 10 | Question ouverte Q13 | `free_text_words` |
| 11 | Export Excel + CSV | |

### `gc_graphiques.ipynb` : un graphique par cellule
Section 0 : paramètres, chargement, fonctions d'aide. Section 2b : **cartes** par département et par région. Sections 1 à 12 : les 12 premiers graphiques (profil, géographie, causes, représentation, rapport au politique, lecture, acteurs, sources d'information, engagement, utilité du vote, intention de vote, mots). « Second temps » : comparer deux groupes. Sections **A à E** : les cinq croisements (vote × engagement, vote × utilité du vote, vote × confiance, sources d'information × âge, freins et leviers × intention de vote).
