"""OCR local et recherche de noms. Une correspondance ne valide pas un produit."""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from difflib import SequenceMatcher
from nlp import CATALOG, normalize, DOSE, FORMS

ROOT=Path(__file__).parent
MAX_IMAGE_BYTES=6*1024*1024


def node_path():
    return shutil.which('node')


def engine_check():
    node=node_path()
    if not node:
        return {'disponible':False,'detail':'Node.js requis pour le module photo.'}
    if any(not (ROOT/'ocr_models'/f'{lang}.traineddata').exists() for lang in ('fra','ara')):
        return {'disponible':False,'detail':'Modèles OCR français ou arabe absents.'}
    try:
        result=subprocess.run([node,str(ROOT/'ocr_engine.cjs')],input='{"check":true}',text=True,encoding='utf-8',capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:
            return {'disponible':False,'detail':'Dépendances OCR absentes. Exécuter npm install à la racine du projet.'}
        return json.loads(result.stdout)
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return {'disponible':False,'detail':'Le moteur OCR local ne démarre pas.'}


def read_mentions(text):
    n=normalize(text)
    doses=[]
    for match in DOSE.finditer(n):
        unit={'ملغ':'mg','ميليغرام':'mg','مغ':'mg','غرام':'g','غ':'g','مل':'ml','µg':'mcg'}.get(match[2],match[2])
        value=match[1].replace(',','.')+' '+unit
        if match[3]:
            value+='/'+match[3].replace(',','.')+' ml'
        if value not in doses:
            doses.append(value)
    forms=[form for form,pattern in FORMS.items() if re.search(rf'(?<!\w)(?:{pattern})(?!\w)',n)]
    return doses,forms


def packaging_mentions(text):
    n=normalize(text)
    units={'comprime':r'comprimes?|اقراص|قرص','gelule':r'gelules?|كبسولات|كبسولة','sachet':r'sachets?|اكياس|كيس'}
    found=[]
    for unit,pattern in units.items():
        for match in re.finditer(rf'(?<!\w)([1-9]\d{{0,2}})\s*(?:{pattern})(?!\w)',n):
            found.append({'nombre':int(match[1]),'unite':unit,'mention':match[0]})
    return found


def aggregate_mentions(ocr):
    dose_confidence={}
    forms=[]
    packages=[]
    laboratory_confidence={}
    for passage in ocr['passes']:
        doses,read_forms=read_mentions(passage['texte'])
        for dose in doses:
            dose_confidence[dose]=max(dose_confidence.get(dose,0),passage.get('confiance_ocr',0))
        for form in read_forms:
            if form not in forms:
                forms.append(form)
        for package in packaging_mentions(passage['texte']):
            if not any((p['nombre'],p['unite'])==(package['nombre'],package['unite']) for p in packages):
                packages.append(package)
        for match in re.finditer(r'\b([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]+)\s+Lab(?:o|e|s)?(?=[®:.,\s]|$)',passage['texte'],re.I):
            name=match[1]+' Lab'
            laboratory_confidence[name]=max(laboratory_confidence.get(name,0),passage.get('confiance_ocr',0))
    retained=[dose for dose,confidence in dose_confidence.items() if confidence>=65]
    if not retained:
        retained=list(dose_confidence)
    discarded=[{'dosage':dose,'confiance_ocr_max':confidence,'raison':'Lecture OCR faible, conservée dans le détail des passes.'} for dose,confidence in dose_confidence.items() if dose not in retained]
    labs=[name for name,confidence in laboratory_confidence.items() if confidence>=65]
    if not labs:
        labs=list(laboratory_confidence)
    # Une variante tronquée ne devient pas un second laboratoire distinct.
    labs=[name for name in labs if not any(name!=other and name.casefold() in other.casefold() for other in labs)]
    return {'dosages':retained,'formes':forms,'conditionnements':packages,'laboratoires':labs,'dosages_ecartes':discarded,'seuil_heuristique_dosage':65},list(dose_confidence)


def match_ocr(ocr):
    """Classe les noms, en conservant chaque lecture plutôt qu'en inventant un SKU."""
    best_by_name={}
    for passage in ocr['passes']:
        text=passage['texte']
        n=normalize(text)
        tokens=re.findall(r'[a-z\u0621-\u064a0-9]{4,}',n)
        doses,forms=read_mentions(text)
        reference=json.loads((ROOT/'reference_medicaments.json').read_text(encoding='utf8'))
        for product in reference['produits']:
            name,aliases=product['nom'],product['alias']
            exact=next((a for a in aliases if re.search(r'(?<!\w)'+re.escape(normalize(a))+r'(?!\w)',n)),None)
            similarity=1.0 if exact else max((SequenceMatcher(None,token,normalize(a)).ratio() for token in tokens for a in aliases if len(normalize(a))>=4),default=0)
            if similarity<.76:
                continue
            score=round(similarity*100)
            row={'medicament':name,'reference_id':product['id'],'score_correspondance':score,'type_correspondance':'nom_exact_ou_alias' if exact else 'nom_approchant','mention_nom':exact,'dosages_lus':doses,'formes_lues':forms,'traitement_source':passage['traitement'],'confiance_ocr':passage['confiance_ocr'],'source_reference':'reference_medicaments.json','reference_produit_exacte':False}
            previous=best_by_name.get(name)
            if previous is None or (score,passage['confiance_ocr'])>(previous['score_correspondance'],previous['confiance_ocr']):
                best_by_name[name]=row
    candidates=sorted(best_by_name.values(),key=lambda x:(-x['score_correspondance'],-x['confiance_ocr'],x['medicament']))[:3]
    mentions,all_doses=aggregate_mentions(ocr)
    selected=candidates[0] if candidates else None
    # Éviter une attribution globale si plusieurs noms de médicaments apparaissent.
    exact_names=[c for c in candidates if c['type_correspondance']=='nom_exact_ou_alias']
    if len(exact_names)>1:
        for candidate in candidates:
            candidate['dosages_lus']=[]
            candidate['formes_lues']=[]
    elif len(exact_names)==1:
        exact_names[0]['dosages_lus']=mentions['dosages']
        exact_names[0]['formes_lues']=mentions['formes']
        exact_names[0]['conditionnements_lus']=mentions['conditionnements']
        exact_names[0]['laboratoires_lus']=mentions['laboratoires']
    ambiguous=len(exact_names)>1 or (len(candidates)>1 and candidates[0]['score_correspondance']-candidates[1]['score_correspondance']<8)
    status='a_confirmer' if selected and not ambiguous else ('ambigu' if selected else 'non_reconnu')
    global_passes=[p for p in ocr['passes'] if not p['traitement'].startswith(('texte_localise_','contexte_nombre_','ligne_detectee_','zone_detail_'))]
    global_text=max(global_passes or ocr['passes'],key=lambda p:p['confiance_ocr'])['texte'] if ocr['passes'] else ''
    local_passes=sorted((p for p in ocr['passes'] if p.get('zone') and p['confiance_ocr']>=60),key=lambda p:(p['zone']['y'],p['zone']['x']))
    return {'statut':status,'candidats':candidates,'mentions_lues':mentions,'dosages_lus_toutes_passes':all_doses,'lectures_dosage_differentes':len(mentions['dosages'])>1,'confirmation_requise':True,'texte_ocr':global_text,'texte_ocr_zones':'\n'.join(p['texte'] for p in local_passes), 'lectures_ocr':ocr['passes'],'qualite':ocr.get('qualite',{}),'langues_ocr':ocr.get('langues',['fra','ara']),'moteur':ocr.get('moteur','Tesseract.js'),'nature_score':'Similarité de nom sur 100, pas une probabilité de bonne identification.','niveau_identification':'nom_de_medicament_sans_validation_du_produit','motif_non_reconnaissance':('nom_absent_ou_incertain_dans_le_referentiel' if any(len(p['texte'].strip())>=4 and p['confiance_ocr']>=45 for p in ocr['passes']) else 'lecture_insuffisante') if not selected else None,'message':('Plusieurs dosages plausibles ont été lus. Vérifiez la boîte et sélectionnez la mention correcte.' if len(mentions['dosages'])>1 and status=='a_confirmer' else 'Nom et mentions lus. Vérifiez les informations avant de préparer le message.' if status=='a_confirmer' else 'Plusieurs noms sont possibles. Photographiez une seule boîte et vérifiez les mentions.' if status=='ambigu' else 'Du texte a été lu, mais aucun nom du référentiel n’a été reconnu avec assez de précision. Les mentions extraites restent affichées.' if global_text.strip() else 'Lecture insuffisante. Recadrez la boîte ou prenez une photo plus nette.'),'quantite_patient':None,'disponibilite_reelle':None}


def recognize(image_base64,rotation_complete=False):
    if not isinstance(image_base64,str) or not image_base64:
        raise ValueError('image_base64 doit contenir une image.')
    try:
        decoded=base64.b64decode(image_base64,validate=True)
    except (ValueError,base64.binascii.Error):
        raise ValueError('Image base64 invalide.')
    if not decoded or len(decoded)>MAX_IMAGE_BYTES:
        raise ValueError('Image vide ou supérieure à 6 Mo.')
    node=node_path()
    if not node:
        raise RuntimeError('Node.js requis. Le parcours texte reste disponible.')
    try:
        completed=subprocess.run([node,str(ROOT/'ocr_engine.cjs')],input=json.dumps({'image_base64':image_base64,'rotation_complete':rotation_complete}),text=True,encoding='utf-8',capture_output=True,timeout=55,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except subprocess.TimeoutExpired:
        raise RuntimeError('Lecture trop longue. Recadrez la boîte et réessayez.')
    if completed.returncode:
        if 'Cannot find module' in completed.stderr:
            raise RuntimeError('Dépendances OCR absentes. Exécuter npm install à la racine du projet.')
        raise ValueError('Image illisible ou format non pris en charge. Utilisez JPEG, PNG ou WebP, avec une seule boîte bien cadrée.')
    return match_ocr(json.loads(completed.stdout))
