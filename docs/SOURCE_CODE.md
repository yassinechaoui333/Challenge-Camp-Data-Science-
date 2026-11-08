# Documentation du code source

## Architecture et responsabilités

L’application n’a pas besoin de base de données. Python expose le service et coordonne les traitements. Le navigateur utilise `fetch` pour appeler l’API. Pour l’OCR, Python lance un processus Node.js et échange du JSON avec lui par l’entrée et la sortie standard.

```text
interface.html
    POST /analyze    -> app.py -> nlp.py -> JSON
    POST /recognize  -> app.py -> vision.py -> ocr_engine.cjs
                                              sharp + Tesseract.js
                                  recherche de noms -> JSON
    confirmation des mentions -> message éditable -> /analyze
```

La confirmation appartient à l’interface. `/recognize` et `/analyze` restent indépendants : le serveur ne conserve pas une session entre leurs appels.

## app.py — serveur et contrats HTTP

- `Handler.do_GET()` sert la page, l’état du service, les noms du catalogue et la fiche d’exemple.
- `Handler.do_POST()` vérifie la taille des requêtes et le format des entrées, puis appelle le module approprié.
- `Handler.ocr_lock` limite le moteur à une reconnaissance simultanée. Une seconde requête reçoit 429.
- `Handler.ocr_status` met en cache le diagnostic OCR utilisé par `/health`. Redémarrer le serveur après une installation de dépendances pour renouveler ce diagnostic.
- `Handler.log_message()` désactive la journalisation des requêtes.
- `LocalServer` empêche la réutilisation simultanée du port. Le point d’entrée écoute sur `127.0.0.1:8000` et traite l’option `--open`.

Le corps texte est limité à 64 000 octets et celui de la route image à 9 Mio, pour contenir une image de 6 Mio encodée en base64. Les données patient ne sont pas écrites dans un fichier.

## nlp.py — compréhension du texte

`analyze(text, historique=None)` est la fonction publique. Elle utilise les messages précédents pour reconstruire le contexte, puis analyse le message actuel. Le contexte vient de l’appelant et ne persiste pas dans le serveur.

Principales étapes :

1. `normalized_with_map()` normalise les accents, diacritiques et chiffres arabes/persans tout en conservant une correspondance avec les positions du texte d’origine.
2. `language_hint()` estime la langue pour choisir les messages de réponse.
3. `_analyze()` recherche les intentions, les noms et les expressions prévues par les règles.
4. `extract_fields()` extrait notamment les quantités, unités, dosages et formes à proximité des mentions de médicaments.
5. `spelling_suggestions()` propose des noms approchants à confirmer.
6. `evidence()` associe une information reconnue à son passage source. Les informations absentes ou ambiguës restent à clarifier.

Le dictionnaire `CATALOG` relie les noms canoniques aux alias arabes et latins. Les règles comprennent des formes courantes de darija et d’Arabizi, comme `3ndkom`, `bghit` et `jouj bwat`. Leur couverture dépend des variantes explicites du lexique.

Le résultat conserve des champs simples pour une demande à un médicament et une liste `medicaments` pour les demandes multiples. Un dosage mentionné ne représente pas une recommandation de prise. La disponibilité réelle reste inconnue.

## vision.py — orchestration et rapprochement

- `node_path()` recherche Node.js dans le `PATH`.
- `engine_check()` vérifie les modèles et demande au processus Node de contrôler les dépendances.
- `recognize(image_base64, rotation_complete=False)` valide le base64, limite la taille et lance le processus OCR avec un délai maximal de 55 secondes.
- `read_mentions()` extrait les dosages et formes du texte OCR normalisé.
- `packaging_mentions()` exige un nombre accompagné d’une unité textuelle pour reconnaître un conditionnement. Le nombre `28` seul ne devient pas `28 comprimés`.
- `aggregate_mentions()` réunit les mentions de plusieurs lectures. Pour les dosages, les passages de confiance OCR d’au moins 65 ont priorité lorsqu’ils existent. Les lectures faibles écartées restent dans les diagnostics. Ce seuil est heuristique.
- `match_ocr()` compare les noms et alias au référentiel, puis utilise `SequenceMatcher` pour les suggestions approchées, avec un seuil de similarité de 0,76. Il conserve au plus trois candidats.

En présence de plusieurs noms exacts, le moteur n’attribue pas automatiquement un dosage à chaque produit. Toute proposition conserve `confirmation_requise: true`, `reference_produit_exacte: false` et `quantite_patient: null`.

Les sorties distinguent `a_confirmer`, `ambigu` et `non_reconnu`. Les diagnostics conservent le texte global, les zones de texte et les passages OCR. Une similarité sur 100 n’est pas une probabilité d’identifier le produit exact.

## ocr_engine.cjs — image et OCR

Le script reçoit un objet JSON sur son entrée standard et écrit un résultat JSON sur sa sortie standard. Le mode `{"check":true}` vérifie les dépendances. En mode reconnaissance :

1. `sharp` décode l’image, valide les dimensions et le format, corrige l’orientation EXIF et aplatit la transparence sur fond blanc.
2. Le moteur limite l’image à 2 400 pixels de côté. Il agrandit les petites images avant lecture.
3. Tesseract lit des versions de l’image avec les modèles français et arabe. Des passages français séparés complètent les textes latins.
4. Si les lectures initiales sont faibles, `textRegions()` regroupe des composantes de pixels sombres en zones de texte. Le moteur recadre et relit ces zones.
5. Des passages complémentaires utilisent le contraste, un canal couleur, des tuiles et des bandes de texte. L’option `rotation_complete` ajoute les quarts de tour.
6. Le résultat contient les textes, langues, traitements et confiances OCR. Les indicateurs de luminosité et de netteté sont des heuristiques.

Les modèles restent locaux dans `ocr_models/`. Le script n’envoie pas les photos à une API externe.

## interface.html — interaction

La page contient les styles et le JavaScript de la démo. Elle gère la saisie, l’historique, l’aperçu de l’image, les appels HTTP, les erreurs, le choix des candidats et l’export JSON.

La confirmation photo prépare un message modifiable. Le champ `provenance_photo` appartient à l’export de l’interface et décrit les mentions confirmées par l’utilisateur. Il ne prouve pas l’identité d’un produit et ne constitue pas une commande.

## Référentiel et données de test

`reference_medicaments.json` contient les identifiants locaux et alias des neuf noms. Il doit rester cohérent avec `CATALOG` dans `nlp.py`. Il ne contient pas de liste validée de dosages et conditionnements commercialisés.

Le manifeste de `dataset/` décrit 32 fiches synthétiques : huit cas nets, huit recadrages, huit rotations, deux flous, deux éclairages réduits, deux cas arabes, un nom inconnu et une image vide. La photo de `tests_images/` constitue un cas réel de développement distinct.

## Modifier le projet

- **Ajouter un nom :** mettre à jour `CATALOG` et `reference_medicaments.json` avec un identifiant unique et les mêmes alias. Ajouter un scénario positif et un cas d’ambiguïté dans les tests.
- **Ajouter une variante de darija :** étendre la règle correspondante et vérifier les mots voisins pour éviter les correspondances accidentelles.
- **Modifier le moteur OCR :** conserver la distinction entre nom, dosage, conditionnement et quantité patient. Rejouer les vérifications du contrat, la photo de régression et le jeu synthétique.
- **Ajouter la voix :** développer une transcription séparée, la faire vérifier dans l’interface, puis transmettre le texte à `/analyze`. Cette fonction reste à implémenter.

Les commandes d’installation et de test sont dans le [README](../README.md). Le détail des sorties et du protocole d’évaluation figure dans [PROTOTYPE.md](PROTOTYPE.md).
