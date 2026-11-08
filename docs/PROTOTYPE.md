## Démonstration de trois minutes

1. Cliquer sur **Essayer une fiche de test**, puis **Lire la photo**.
2. Montrer le nom proposé, le dosage lu et le texte OCR. La fiche est artificielle et explicitement étiquetée.
3. Confirmer le nom, le dosage et éventuellement la forme. Cliquer sur **Confirmer et préparer le message**.
4. Compléter le message avec `bghit jouj bwat` ou `بغيت جوج علب` et cliquer sur **Analyser le message**.
5. Montrer les champs JSON, les deux boîtes demandées et la provenance photo confirmée.
6. Envoyer `non, 3 boites` pour corriger la quantité.
7. Copier le résumé ou télécharger le JSON.

Une vraie photo peut remplacer la fiche de test. Utiliser une seule boîte, bien cadrée, avec le nom et le dosage lisibles. Formats acceptés : JPEG, PNG et WebP, jusqu’à 6 Mio et 25 millions de pixels. La photo doit mesurer au moins 100 × 80 pixels. L’option de rotation essaie des quarts de tour supplémentaires.

**Le nombre de comprimés, sachets ou unités imprimé sur une boîte ne devient jamais une quantité demandée par le patient.** Le module photo renvoie `quantite_patient: null`. Le patient précise cette quantité dans son message.

## Architecture

### Texte

`interface.html` envoie le message et les précédents messages à `/analyze`. `nlp.py` normalise la langue, reconnaît les intentions, extrait les champs et gère le contexte. Le module prend en charge les variantes prévues de darija et d’Arabizi, les nombres écrits, les alias et les clarifications. Le contexte est limité à douze messages précédents.

### Image

`/recognize` valide l’image puis appelle localement `ocr_engine.cjs` :

1. Décodage et correction de l’orientation EXIF.
2. Redimensionnement limité à 2 400 pixels par côté.
3. Lecture OCR de l’original et d’une version en gris avec contraste et netteté améliorés.
4. OCR Tesseract avec les modèles `fra` et `ara`.
5. En option, lectures après rotations de 90, 180 et 270 degrés.
6. Rapprochement des noms avec `reference_medicaments.json` et conservation des mentions lues.

Le prétraitement relève de la vision par ordinateur. Aucun classificateur visuel de boîtes n’a été entraîné. Les couleurs, logos et formes d’emballage ne suffisent pas à valider le produit.

### Confirmation

L’interface affiche les candidats, le texte OCR et les mentions à vérifier. Le patient confirme avant de préparer le message. Si plusieurs noms apparaissent, aucun dosage n’est attribué automatiquement à un nom. Si les lectures proposent plusieurs dosages, le patient doit choisir ou ne rien préciser.

La confirmation prépare un message modifiable. Elle ne passe pas de commande et ne confirme aucun stock. L’interface conserve une provenance photo dans l’export final si le médicament du message correspond au nom confirmé. Cette provenance décrit une confirmation utilisateur, pas une preuve d’identité du produit.

## Référentiel

`reference_medicaments.json` contient neuf noms : Doliprane, Efferalgan, Smecta, Ventoline, Gaviscon, Spasfon, Dafalgan, Imodium et Losartan, avec des variantes arabes et latines.

Chaque entrée possède un identifiant local. Les dosages commerciaux, conditionnements et stocks restent absents. Le référentiel pédagogique ne remplace pas une base officielle de médicaments. Les mentions de dosage affichées proviennent du texte OCR, pas d’une vérification de conformité au référentiel.

Le score de rapprochement sur 100 mesure une similarité de nom. Il n’est pas une probabilité de bonne identification et les seuils n’ont pas été calibrés sur un corpus réel. La confiance fournie par l’OCR est également distincte de la fiabilité de l’identification.

## API

### GET /health

État du service, version 4 et disponibilité de l’OCR.

### GET /catalog

Noms du catalogue pédagogique.

### POST /analyze

```json
{
  "text": "500mg jouj bwat",
  "historique": ["3ndkom Doliprane ?"]
}
```

`text` contient entre 1 et 1 000 caractères. `historique` est facultatif et contient au plus douze messages de 1 à 1 000 caractères. Les résultats incluent `intentions`, `medicaments`, `clarification`, `champs_manquants` et `contexte_utilise`. Avec plusieurs médicaments, utiliser la liste `medicaments`.

### POST /recognize

```json
{
  "image_base64": "CONTENU_BASE64_SANS_PREFIXE_DATA_URL",
  "rotation_complete": false
}
```

Réponse : `statut`, `candidats`, `lectures_ocr`, `qualite`, `confirmation_requise`, `niveau_identification` et `quantite_patient`. Les états possibles comprennent `a_confirmer`, `ambigu` et `non_reconnu`. L’absence de candidat peut correspondre à un nom hors catalogue ou à une image insuffisamment lisible.

Erreurs : 400 pour une entrée ou une image invalide, 404 pour une route inconnue, 429 si une autre reconnaissance est en cours, 503 si le moteur manque ou dépasse le délai. Les traitements OCR sont séquentiels pour limiter la charge.

Les applications externes appellent `/recognize`, font confirmer les mentions, puis transmettent le message composé à `/analyze`. Les endpoints ne stockent pas d’état patient sur le serveur. Le champ `provenance_photo` de l’export de démonstration est ajouté par l’interface après confirmation.

## Dataset et évaluation

Le dossier `dataset` contient **32 fiches texte synthétiques** et leur manifeste. Ce ne sont pas des photographies d’emballages commerciaux.

Le jeu comprend huit noms en lecture nette, huit recadrages qui conservent le nom, huit rotations à 90 degrés, deux flous modérés, deux éclairages réduits, deux textes uniquement arabes, un nom hors catalogue et une image vide. Les fiches utilisent des caractères rendus par le navigateur pour conserver la composition arabe. Le flou, la luminosité et le recadrage sont des transformations déterministes. Les empreintes SHA-256 figurent dans le manifeste.

Commandes, à exécuter à la racine du dépôt :

```text
python test_v2.py
python test_vision.py
python evaluate_vision.py --full
```

Résultats obtenus pendant la préparation :

- 86 scénarios de régression texte réussis sur 86.
- 12 vérifications du rapprochement et du contrat image réussies sur 12.
- 32 cas image synthétiques conformes aux attentes sur 32, y compris deux cas où aucun nom ne devait être proposé.

Le rapport image mesure le **premier nom proposé** par rapport au nom attendu, pas l’identité complète d’un médicament. Il comporte le texte OCR, le temps mesuré et le résultat par condition. Les résultats sont enregistrés dans `resultats_ocr_complet.json` et `resultats_tests_v2.json`.

Ces essais forment un jeu de développement synthétique. Il n’y a pas de séparation apprentissage/test puisqu’aucun modèle n’est entraîné. Les résultats ne permettent d’estimer ni la précision sur de vraies boîtes, ni la robustesse à une forte occlusion, à une perspective extrême ou à tous les éclairages.

Pour une évaluation terrain, collecter des photos autorisées, annoter le produit et ses mentions, prévoir des cas hors catalogue, et séparer les prises de vue par boîte physique entre développement et test. Le dossier `dataset/README.md` décrit le protocole proposé.

## Données et limites

Les photos sont traitées localement et ne sont pas sauvegardées. Les messages ne sont pas consignés par le serveur. L’historique et la provenance photo restent en mémoire dans la page. Un export conserve les informations que l’utilisateur choisit de télécharger.

Il n’y a ni base de stocks, ni prix réel, ni annuaire connecté. La voix reste à intégrer. Les demandes de posologie et de conseil médical sont dirigées vers le pharmacien. Un nom reconnu ne permet pas de décider de la prise ou de la substitution d’un médicament.

## Sources techniques et licences

- Tesseract, qualité des images : https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Tesseract.js, API et modèles locaux : https://github.com/naptha/tesseract.js/blob/master/docs/api.md
- sharp, traitements d’image : https://sharp.pixelplumbing.com/api-operation/
- Modèles officiels `tessdata_fast` : https://github.com/tesseract-ocr/tessdata_fast
- Rasa, intentions et entités : https://legacy-docs-oss.rasa.com/docs/rasa/next/generating-nlu-data/

Les modèles `fra.traineddata` et `ara.traineddata` sont fournis avec leur licence Apache 2.0 dans `ocr_models/LICENSE` et leur traçabilité dans `ocr_models/sources.json`. Les bibliothèques Node ne sont pas redistribuées dans l’archive et s’installent via `package.json`. Les images de test sont des créations synthétiques du projet.


## Correctif OCR : photo de Losartan fournie par l’utilisateur

Le moteur agrandit désormais les petites images et ajoute une lecture française séparée. Lorsque la lecture globale est insuffisante, il détecte des zones de texte par composantes connexes, les recadre puis les lit séparément. Des essais complémentaires de contraste et de canal couleur restent disponibles pour les images difficiles.

Le nom Losartan a été ajouté au référentiel et au module texte. Sur `tests_images/losartan_fourni.jpg`, l’essai de régression attend Losartan, une suggestion de dosage de 50 mg et la mention de laboratoire Zentiva Lab. Il ne valide pas une présentation commerciale exacte. Les petites mentions de conditionnement peuvent rester non extraites.

Les mentions de dosage dont une lecture atteint le seuil heuristique de confiance OCR de 65 sont proposées en priorité. Les lectures plus faibles restent accessibles dans `dosages_lus_toutes_passes` et `mentions_lues.dosages_ecartes`. Ce filtrage n’est pas une garantie de justesse et ne constitue pas une probabilité clinique. Des lectures plausibles contradictoires restent proposées au choix, avec confirmation obligatoire.

L’API distingue une lecture insuffisante d’un nom absent ou incertain dans le référentiel. Les mentions extraites restent visibles même si aucun nom n’est proposé. `texte_ocr` décrit une lecture globale et `texte_ocr_zones` décrit les zones localisées.

Le conditionnement imprimé, s’il est lu, reste séparé de la quantité demandée par le patient. Le nombre seul « 28 » n’est pas interprété comme « 28 comprimés » si l’unité n’est pas suffisamment lue.

Test supplémentaire : `python test_photo_losartan.py`. Cette photo fournie par l’utilisateur est un cas de développement et de régression, pas un corpus indépendant. Les rapports antérieurs sur 32 fiches synthétiques décrivent ce jeu, et non une mesure de reconnaissance généralisée sur de vraies boîtes.
