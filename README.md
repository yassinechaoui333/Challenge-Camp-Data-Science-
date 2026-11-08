# PharmaDarija — Challenges 1 et 2

**Chaoui Yassine et Hadir Yahya — INPT**

PharmaDarija est un prototype local d’assistance patient-pharmacie. Il comprend une demande en français, arabe ou darija et peut lire le texte d’une boîte de médicament. Les deux modules renvoient des informations structurées à travers une API et une interface web.

## Fonctionnalités

- **Challenge 1 : texte multilingue.** Intentions de disponibilité, téléphone et localisation, noms de médicaments, dosage mentionné, quantité et forme. Darija en écriture arabe ou en Arabizi, demandes successives et corrections.
- **Challenge 2 : image et OCR.** Images JPEG, PNG et WebP, OCR français/arabe, prétraitement et lectures de zones, recherche de noms dans le référentiel et confirmation des mentions.
- **Parcours commun.** Confirmer les informations de la photo, compléter la demande en darija, puis copier le résumé ou exporter le JSON.

Exemple : `3ndkom Doliprane 500 mg, jouj bwat ?` permet d’extraire **Doliprane**, **500 mg** et **2 boîtes**, avec une intention de demande de disponibilité. Le système ne consulte aucun stock réel.

## Environnement de développement

| Outil | Version requise | Utilisation |
|---|---|---|
| Python | 3.10 ou supérieur | Serveur HTTP, extraction linguistique et recherche de noms |
| Node.js | 22 ou supérieur | Exécution du moteur OCR |
| npm | Fourni avec Node.js | Installation des dépendances JavaScript |
| Git | Version récente | Récupération du dépôt |
| Navigateur | Version récente | Interface de démonstration |

Le code Python utilise uniquement la bibliothèque standard : **aucun `pip install` nécessaire**. Les versions directes JavaScript sont fixées à **Tesseract.js 7.0.0** et **sharp 0.35.5**. `package-lock.json` fixe leurs dépendances transitives. Les modèles OCR `fra` et `ara` sont inclus dans `ocr_models/`, avec leur licence Apache 2.0 et leurs empreintes.

L’installation et les tests ont été vérifiés sous Windows avec Python **3.12.14** et Node.js **24.22.1**. Les commandes Linux/macOS sont fournies pour l’installation, sans vérification native sur ces systèmes.

Installer Python et Node.js avec leur ajout au `PATH`. Aucune clé API ni base de données n’est nécessaire. Internet sert à cloner le dépôt et à installer les bibliothèques, puis le traitement fonctionne localement.

## Installation et démarrage

```bash
git clone https://github.com/yassinechaoui333/Challenge-Camp-Data-Science-.git
cd Challenge-Camp-Data-Science-
```

Vérifier les outils :

```bash
python --version
node --version
npm --version
```

### Windows — PowerShell

```powershell
python -m venv .venv
npm ci --omit=dev
.\.venv\Scripts\python.exe app.py --open
```

Si la commande `python` n’existe pas mais que le lanceur Python est installé, utiliser `py -3 -m venv .venv` pour la première commande. Il n’est pas nécessaire d’activer l’environnement virtuel pour exécuter les commandes ci-dessus.

Après cette installation, **Lancer_demo.bat** utilise automatiquement `.venv` s’il existe. **Installer_OCR.bat** permet aussi d’installer les bibliothèques avec `npm install`.

### Linux / macOS

```bash
python3 -m venv .venv
npm ci --omit=dev
.venv/bin/python app.py --open
```

Sur certaines distributions Linux, installer également le paquet système qui fournit `venv`. Le serveur écoute sur **http://127.0.0.1:8000**. Garder le terminal ouvert et utiliser **Ctrl+C** pour l’arrêter. `--open` ouvre le navigateur et peut être omis.

Le parcours texte fonctionne même sans les bibliothèques OCR. Pour le parcours photo, vérifier que `GET /health` indique `ocr.disponible: true`.

## Démonstration

1. Ouvrir l’interface et cliquer sur **Nouvelle conversation**.
2. Pour le texte seul, envoyer `3ndkom Doliprane 500 mg ?`, puis `bghit jouj bwat`. Vérifier le médicament, le dosage et les deux boîtes.
3. Pour le parcours combiné, choisir `tests_images/losartan_fourni.jpg` et cliquer sur **Lire la photo**.
4. Vérifier **Losartan**, **50 mg** et la mention **Zentiva Lab**, puis confirmer le nom et le dosage.
5. Compléter le message préparé avec `bghit jouj bwat`, analyser et exporter le JSON.

Le bouton **Essayer une fiche de test** utilise une image synthétique. Les petits caractères d’une vraie boîte peuvent rester illisibles. Le nombre de comprimés imprimé sur la boîte reste distinct du nombre de boîtes demandé par le patient.

## Organisation du code

```text
.
├── app.py                       # Serveur local et routes HTTP
├── interface.html               # Interface, conversation et confirmation photo
├── nlp.py                       # Intentions, entités, normalisation et contexte
├── vision.py                    # Validation, appel OCR et recherche de candidats
├── ocr_engine.cjs               # Traitements sharp et lectures Tesseract.js
├── reference_medicaments.json    # Référentiel pédagogique de neuf noms
├── package.json / package-lock.json
├── ocr_models/                  # Modèles français/arabe, licence et traçabilité
├── dataset/                     # 32 fiches synthétiques et manifeste
├── tests_images/                # Photo de régression Losartan
├── test_demo.py                 # Scénarios de base utilisés par test_v2.py
├── test_v2.py                   # Régressions du module texte
├── test_vision.py               # Contrat et rapprochement, sans moteur OCR
├── test_photo_losartan.py        # Régression OCR sur la photo fournie
├── evaluate_vision.py            # Évaluation OCR sur les fiches synthétiques
└── docs/
    ├── SOURCE_CODE.md           # Documentation des modules et de leur extension
    └── PROTOTYPE.md             # API, protocole d’évaluation et limites détaillées
```

La documentation du code se trouve dans [docs/SOURCE_CODE.md](docs/SOURCE_CODE.md). La description détaillée du protocole et du prototype se trouve dans [docs/PROTOTYPE.md](docs/PROTOTYPE.md).

## API

| Méthode | Route | Description |
|---|---|---|
| GET | `/` | Interface web |
| GET | `/health` | Version du service et disponibilité OCR |
| GET | `/catalog` | Noms reconnus par le lexique |
| GET | `/dataset/exemple.png` | Fiche synthétique de démonstration |
| POST | `/analyze` | Analyse d’un message et de son historique optionnel |
| POST | `/recognize` | Lecture d’une image encodée en base64 |

Corps de `POST /analyze` :

```json
{
  "text": "500mg jouj bwat",
  "historique": ["3ndkom Doliprane ?"]
}
```

Le résultat contient notamment `intention`, `intentions`, `medicament`, `medicaments`, `dosage`, `quantite`, `clarification` et `champs_manquants`. Utiliser `medicaments` pour une demande portant sur plusieurs médicaments. Le texte contient de 1 à 1 000 caractères, et l’historique au plus douze messages.

Corps de `POST /recognize` :

```json
{
  "image_base64": "BASE64_DE_L_IMAGE_SANS_PREFIXE_DATA_URL",
  "rotation_complete": false
}
```

Le résultat contient les `candidats`, les `mentions_lues`, le texte OCR, les lectures détaillées et `confirmation_requise: true`. L’image est limitée à **6 Mio**, **25 millions de pixels** et une taille minimale de **100 × 80 pixels**. Une reconnaissance s’exécute à la fois.

Exemple d’appel depuis Python, pendant que le serveur tourne :

```python
import json
from urllib.request import Request, urlopen

payload = {"text": "3ndkom Doliprane 500 mg, jouj bwat ?"}
request = Request(
    "http://127.0.0.1:8000/analyze",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urlopen(request, timeout=10) as response:
    print(json.dumps(json.load(response), ensure_ascii=False, indent=2))
```

Codes d’erreur : **400** entrée invalide, **404** route inconnue, **429** OCR occupé, **503** OCR indisponible ou délai dépassé.

## Tests et évaluation

Depuis la racine, utiliser le Python de `.venv`. Sous Windows :

```powershell
.\.venv\Scripts\python.exe -X utf8 test_v2.py
.\.venv\Scripts\python.exe -X utf8 test_vision.py
.\.venv\Scripts\python.exe -X utf8 test_photo_losartan.py
.\.venv\Scripts\python.exe -X utf8 evaluate_vision.py --full
```

Sous Linux/macOS, remplacer `.\.venv\Scripts\python.exe` par `.venv/bin/python`. Les deux premières commandes vérifient le texte et le rapprochement sans exécuter Tesseract. Les deux dernières nécessitent l’installation OCR et peuvent prendre plusieurs minutes. Les rapports JSON générés restent ignorés par Git.

Résultats du jeu de développement : **86/86** scénarios texte, **12/12** vérifications du contrat et du rapprochement, **32/32** cas image synthétiques conformes aux attentes. Le cas Losartan vérifie aussi le nom, le dosage et le laboratoire sur la photo fournie. Ces résultats ne mesurent pas la précision sur un corpus indépendant de boîtes réelles.

## Dépannage

| Problème | Vérification |
|---|---|
| `python`, `node` ou `npm` introuvable | Installer l’outil, vérifier le `PATH`, puis rouvrir le terminal. |
| OCR indisponible | Exécuter `npm ci --omit=dev` à la racine et vérifier les deux modèles dans `ocr_models/`. |
| Port 8000 occupé | Arrêter l’ancienne instance de la démo avant de relancer. |
| Ancienne interface affichée | Actualiser avec Ctrl+F5 après avoir redémarré le serveur. |
| Aucun candidat OCR | Améliorer le cadrage et la lumière, vérifier le texte lu et la présence du nom dans le référentiel. |
| Image tournée | Activer les lectures supplémentaires de rotation. |

## Périmètre et données

Le référentiel contient neuf noms : Doliprane, Efferalgan, Smecta, Ventoline, Gaviscon, Spasfon, Dafalgan, Imodium et Losartan. Le projet utilise des règles linguistiques et de l’OCR, sans entraînement de modèle de classification de boîtes. Il ne valide pas un produit commercial exact et ne fournit ni stock réel, ni prix, ni prescription. La voix reste à développer.

Les images reçues ne sont pas sauvegardées et le serveur ne consigne pas les messages. L’historique reste dans la page et accompagne les requêtes. Les exports conservent les informations choisies par l’utilisateur. Ce serveur de démonstration écoute uniquement sur l’ordinateur local.

## Références et licences tierces

- [Tesseract.js](https://github.com/naptha/tesseract.js) et [documentation de l’API](https://github.com/naptha/tesseract.js/blob/master/docs/api.md).
- [Amélioration de la qualité des images pour Tesseract](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).
- [sharp : opérations sur les images](https://sharp.pixelplumbing.com/api-operation/).
- [Modèles tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast), redistribués avec [leur licence](ocr_models/LICENSE) et [leur traçabilité](ocr_models/sources.json).

Les fiches du dossier `dataset/` sont synthétiques. La photo Losartan fournie pour le projet sert de fixture de régression. Les bibliothèques Node s’installent via npm et conservent leurs licences respectives.
