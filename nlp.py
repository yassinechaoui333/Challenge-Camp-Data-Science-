"""Analyse explicable français / darija / Arabizi, sans modèle externe.

Les variantes sont explicites, les ressemblances orthographiques restent des
suggestions. Les preuves renvoient aux caractères du message d'origine.
"""
import re
import unicodedata
from difflib import SequenceMatcher

CATALOG = {
    'Doliprane': ['doliprane', 'dolipran', 'doli', 'دوليبران', 'دوليبرين', 'دوليبغان'],
    'Efferalgan': ['efferalgan', 'eferalgan', 'ايفيرالغان', 'ايفرالغان', 'إيفيرالغان'],
    'Smecta': ['smecta', 'smekta', 'سميكتا', 'سميكطا'],
    'Ventoline': ['ventoline', 'ventolin', 'فونتولين', 'فنتولين', 'فانطولين'],
    'Gaviscon': ['gaviscon', 'gaviskon', 'غافيسكون', 'جافيسكون'],
    'Spasfon': ['spasfon', 'سباسفون', 'سْباسفون'],
    'Dafalgan': ['dafalgan', 'دافالغان', 'دافالكان'],
    'Imodium': ['imodium', 'ايموديوم', 'إيموديوم'],
    'Losartan': ['losartan', 'لوسارتان'],
}


def normalized_with_map(text):
    chars, offsets = [], []
    translate = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹إأآٱى', '01234567890123456789ااااي')
    for i, char in enumerate(text):
        for c in unicodedata.normalize('NFKD', char.lower().translate(translate)):
            if unicodedata.category(c) != 'Mn' and c != 'ـ':
                chars.append(c)
                offsets.append(i)
    return ''.join(chars), offsets


def normalize(text):
    return normalized_with_map(text)[0]


def evidence(text, offsets, match, kind, value):
    start, end = offsets[match.start()], offsets[match.end() - 1] + 1
    return {'champ': kind, 'texte': text[start:end], 'debut': start, 'fin': end, 'valeur': value}


NUMBERS = {
    1: ['une', 'un', 'wahed', 'wa7ed', 'wa7da', 'wahda', 'واحد', 'واحدة', 'وحده'],
    2: ['deux', 'jouj', 'juj', 'joj', 'jوج', 'جوج', 'اثنين', 'اثنتين'],
    3: ['trois', 'tlata', 'tleta', 'ثلاث', 'ثلاثة', 'تلاتة'],
    4: ['quatre', 'rb3a', 'reb3a', 'ربعة', 'اربعة', 'اربع'],
    5: ['cinq', 'khmsa', 'khamsa', 'خمسة', 'خمس', 'خمسه'],
    6: ['six', 'setta', 'ستة', 'ست'],
    7: ['sept', 'seb3a', 'سبعة', 'سبع'],
    8: ['huit', 'tmenya', 'تمانية', 'ثمانية', 'ثمان'],
    9: ['neuf', 'tes3a', 'تسعة', 'تسع'],
    10: ['dix', '3chra', '3echra', 'عشرة', 'عشر'],
}
NUMBER_LOOKUP = {normalize(word): number for number, words in NUMBERS.items() for word in words}
NUMBER = r'(?:[+-]?\d{1,3}(?:[.,]\d+)?|' + '|'.join(sorted(map(re.escape, NUMBER_LOOKUP), key=len, reverse=True)) + ')'
UNITS = {
    'boite': r'boites?|bwat|bwate|boitat|boita|boit|علبة|علبه|علب|بواط|بواطة|باكية|باكيات|pakya|pakyat',
    'flacon': r'flacons?|9r3a|9ra3i|قرعة|قراعي|قنينة|قنينات',
    'sachet': r'sachets?|sachiyat|اكياس|كيس|ساشيات|ساشي',
    'tube': r'tubes?|تيوب|انبوب',
}
UNIT_PATTERN = '|'.join(f'(?:{pattern})' for pattern in UNITS.values())
FORMS = {
    'sirop': r'sirop|siro|شراب|سيرو',
    'comprime': r'comprimes?|9rass|9ras|اقراص|قرص|قراص',
    'gelule': r'gelules?|كبسولات|كبسولة',
    'creme': r'creme|كريم',
    'suppositoire': r'suppositoires?|تحاميل',
    'spray': r'spray|بخاخ',
}
DOSE = re.compile(r'(?<![\d.,])(\d+(?:[.,]\d+)?)(?:\s*)(mg|mcg|µg|g|ml|ملغ|ميليغرام|مغ|غرام|غ|مل)(?:\s*/\s*(\d+(?:[.,]\d+)?)\s*(ml|مل))?(?![a-z\u0621-\u064a])')

INTENTS = {
    'telephone_pharmacie': r'\b(?:telephone|tel|numero|num|contact|nmra|nemra|noumra|ra9m)\b|هاتف|نمرة|نمره|رقم',
    'localisation_pharmacie': r'\b(?:adresse|localisation|localiser|fin|fine|fen|win)\b|\bou\s+(?:est|se trouve)\b|فين|اين|عنوان|موقع',
    'horaires_pharmacie': r'\b(?:horaires?|ouvrez|fermez|ouvert[e]?|ferme[e]?|ma7loula|me7loula|mahloula|wa9tach|imta|tseddo|t7ello)\b|محلولة|محلول|مفتوح|مفتوحة|توقيت|اوقات|وقتاش|كتحلو|كتسدو',
    'prix_medicament': r'\b(?:prix|tarif|combien|bch7al|bche7al|bchhal|taman|tamane|ch7al\s+(?:dayr|dayra|taman))\b|بشحال|ثمن|سعر|شحال داير',
}
AVAILABILITY = r'\b(?:disponible|dispo|avez|stock|kayn|kayna|kayen|kaynin|3ndkom|3andkom|3endkom|andkom|3ndkum|3ndk|3andk)\b|كاين|عندكم|عندك|متوفر|يتوفر'
WANT = r'\b(?:bghit|brit|baghi|bghina|wach|wash)\b|بغيت|باغي|واش|اريد'
NEGATION = r'\b(?:ma\s*bghitch|mabghitch|machi|pas\s+de|sans)\b|ما\s*بغيتش|ماشي|بلا'
MEDICAL = r'\b(?:posologie|effets? secondaires?|ch7al\s+(?:nakhod|nakhd)|dose\s+(?:prendre|pour))\b|شحال\s*ناخد|اعراض جانبية|جرعة مناسبة'
LABELS = {'disponibilite_medicament':'Disponibilité', 'telephone_pharmacie':'Téléphone', 'localisation_pharmacie':'Localisation', 'horaires_pharmacie':'Horaires', 'prix_medicament':'Prix', 'conseil_medical':'Conseil du pharmacien'}


def language_hint(n):
    if re.search(r'[\u0600-\u06ff]', n):
        return 'arabe_darija'
    if re.search(r'\b(?:wach|wash|bghit|brit|jouj|joj|juj|3ndkom|3andkom|3endkom|3ndk|fin|kayn|kayna|bch7al|tlata|nmra)\b', n):
        return 'darija_latin'
    return 'francais_ou_autre'


def localize(key, lang):
    messages = {
        'medicament': ('Quel médicament souhaitez-vous demander ?', 'شنو سميت الدوا اللي بغيتي؟', 'Chno smit dwa li bghiti ?'),
        'inconnue': ('Souhaitez-vous un médicament, un prix ou une information sur la pharmacie ?', 'بغيتي دوا، الثمن ولا معلومات على الصيدلية؟', 'Bghiti dwa, taman wla ma3loumat 3la pharmacie ?'),
        'ambigu': ('Précisez le dosage ou la quantité de chaque médicament séparément.', 'وضح لينا التركيز ولا الكمية ديال كل دوا بوحدو.', 'Wdde7 dosage wla lkemya dyal kol dwa bo7do.'),
        'alternative': ('Quel médicament souhaitez-vous retenir parmi ces choix ?', 'شنو الدوا اللي بغيتي تختار من هادو؟', 'Chno dwa li bghiti tkhtar men had l2ikhtiyarat ?'),
        'quantite': ('Indiquez une quantité positive avec son unité, par exemple « 2 boîtes ».', 'شحال من علبة بغيتي؟ كتب مثلا جوج علب.', 'Ch7al men boita bghiti ? Kteb jouj bwat par exemple.'),
        'medical': ('Pour une posologie ou un conseil médical, contactez votre pharmacien.', 'بالنسبة للجرعة ولا النصيحة الطبية، سول الصيدلي.', '3la ljr3a wla nassi7a tibbiya, swel pharmacien.'),
        'ok': ('Demande structurée. La pharmacie doit confirmer les informations réelles.', 'فهمنا الطلب ديالك. الصيدلية خاصها تأكد المعلومات.', 'Fhemna talab dyalek. Pharmacie khas-ha t2ekked lma3loumat.'),
    }
    return messages[key][{'francais_ou_autre':0, 'arabe_darija':1, 'darija_latin':2}[lang]]


def extract_fields(text, n, offsets, start, end):
    """Renvoie les mentions d'une seule portion, sans confondre mg et boîtes."""
    found, proofs, ambiguities = {}, [], []
    for match in DOSE.finditer(n, start, end):
        unit = {'ملغ':'mg','ميليغرام':'mg','مغ':'mg','غرام':'g','غ':'g','مل':'ml','µg':'mcg'}.get(match[2],match[2])
        val = match[1].replace(',', '.') + ' ' + unit
        if match[3]:
            val += '/' + match[3].replace(',', '.') + ' ml'
        if 'dosage' in found and found['dosage'] != val:
            ambiguities.append('dosage')
        found['dosage'] = val
        proofs.append(evidence(text, offsets, match, 'dosage', val))
    quantities, quantity_spans = [], []
    patterns = [rf'(?<![\w.,+-])({NUMBER})\s*({UNIT_PATTERN})(?!\w)', rf'(?<!\w)({UNIT_PATTERN})\s+(?:dyal\s+|ديال\s+)?({NUMBER})(?!\w)']
    for index, pattern in enumerate(patterns):
        for match in re.finditer(pattern, n[start:end]):
            absolute = re.compile(pattern).match(n, start + match.start(), end)
            number, unit_text = (match[1], match[2]) if index == 0 else (match[2], match[1])
            if re.fullmatch(r'[+-]?\d+(?:[.,]\d+)?',number):
                value=float(number.replace(',','.'))
                number=int(value) if value.is_integer() else None
            else:
                number=NUMBER_LOOKUP[number]
            unit = next(key for key, pattern in UNITS.items() if re.fullmatch(pattern, unit_text))
            quantities.append((number, unit))
            quantity_spans.append((absolute.start(),absolute.end()))
            proofs.append(evidence(text, offsets, absolute, 'quantite', number))
    for match in re.finditer(r'(?<!\w)(?:boita|boite|علبة|قرعة|flacon|sachet|tube)(?!\w)',n[start:end]):
        a,b=start+match.start(),start+match.end()
        if not any(x <= a < y for x,y in quantity_spans):
            unit=next(key for key,pattern in UNITS.items() if re.fullmatch(pattern,match[0]))
            absolute=re.compile(re.escape(match[0])).match(n,a,end)
            quantities.append((1,unit))
            proofs.append(evidence(text,offsets,absolute,'quantite',1))
    # Le dual arabe exprime explicitement deux unités, même sans chiffre.
    for match in re.finditer(r'علبتين|علبتان|قرعتين|قنينتين', n[start:end]):
        absolute = re.compile(r'علبتين|علبتان|قرعتين|قنينتين').match(n, start + match.start(), end)
        unit = 'boite' if match[0].startswith('علب') else 'flacon'
        quantities.append((2, unit))
        proofs.append(evidence(text, offsets, absolute, 'quantite', 2))
    if quantities:
        if len(set(quantities)) > 1 or quantities[0][0] is None or quantities[0][0] <= 0:
            ambiguities.append('quantite')
        else:
            found['quantite'], found['unite_quantite'] = quantities[0]
    for form, pattern in FORMS.items():
        match = re.search(rf'(?<!\w)(?:{pattern})(?!\w)', n[start:end])
        if match:
            absolute = re.compile(rf'(?:{pattern})').match(n, start + match.start(), end)
            if 'forme' in found and found['forme'] != form:
                ambiguities.append('forme')
            found['forme'] = form
            proofs.append(evidence(text, offsets, absolute, 'forme', form))
    for field in set(ambiguities):
        found[field] = None
        if field == 'quantite':
            found['unite_quantite'] = None
    return found, proofs, sorted(set(ambiguities))


def spelling_suggestions(n, recognized_spans):
    suggestions = []
    for token in re.finditer(r'[a-z\u0621-\u064a]{5,}', n):
        if any(a <= token.start() < b for a,b in recognized_spans):
            continue
        scores = []
        for name, aliases in CATALOG.items():
            score = max(SequenceMatcher(None, token[0], normalize(a)).ratio() for a in aliases if len(normalize(a)) >= 5)
            if score >= .82 and abs(len(token[0])-len(normalize(name))) <= 3:
                scores.append((score, name))
        if scores:
            scores.sort(reverse=True)
            suggestions.append({'mention':token[0], 'candidats':[name for _,name in scores[:2]], 'confirmation_requise':True})
    return suggestions


def _analyze(text, previous=None):
    n, offsets = normalized_with_map(text)
    lang = language_hint(n)
    meds, excluded, spans = [], [], []
    candidates = []
    for name, aliases in CATALOG.items():
        pattern = r'(?<!\w)(?:و)?(?:' + '|'.join(sorted((re.escape(normalize(a)) for a in aliases),key=len,reverse=True)) + r')(?=$|[^\w]|\d)'
        for match in re.finditer(pattern, n):
            candidates.append((match.start(), match.end(), name, match))
    candidates.sort()
    for start, end, name, match in candidates:
        if any(a <= start < b for a,b in spans):
            continue
        spans.append((start,end))
        before = re.split(r'[,،;.!؟?]|\b(?:mais|walakin|bghit)\b|ولكن|بغيت(?!ش)', n[:start])[-1]
        if re.search(NEGATION,before):
            excluded.append(name)
        else:
            meds.append({'medicament':name,'dosage':None,'quantite':None,'unite_quantite':None,'forme':None,'origine':'message','preuves':[evidence(text,offsets,match,'medicament',name)],'_start':start,'_end':end})
    suggestions = spelling_suggestions(n,spans)
    intent_matches = []
    for intent, pattern in INTENTS.items():
        match = re.search(pattern,n)
        if match:
            intent_matches.append((match.start(),intent))
    if re.search(MEDICAL,n):
        intent_matches.append((0,'conseil_medical'))
    availability = re.search(AVAILABILITY,n)
    if availability and (meds or not intent_matches):
        intent_matches.append((availability.start(),'disponibilite_medicament'))
    elif meds and not any(i in ('prix_medicament','conseil_medical') for _,i in intent_matches):
        intent_matches.append((meds[0]['_start'],'disponibilite_medicament'))
    elif not intent_matches and re.search(WANT,n):
        intent_matches.append((0,'disponibilite_medicament'))
    intents = list(dict.fromkeys(i for _,i in sorted(intent_matches)))
    ambiguities = []
    alternatives = False
    # Une coordination explicite sépare les champs : « X 500 mg et Y 1 g ».
    # Sans séparation fiable, on laisse les champs en attente au lieu de les attribuer.
    if len(meds) == 1:
        fields, proofs, ambiguities = extract_fields(text,n,offsets,0,len(n))
        # Les mentions d'un médicament explicitement exclu ne doivent pas contaminer le suivant.
        if excluded:
            fields, proofs, ambiguities = extract_fields(text,n,offsets,meds[0]['_start'],len(n))
        meds[0].update(fields)
        meds[0]['preuves'] += proofs
    elif len(meds) > 1:
        cuts = [0]
        for left,right in zip(meds,meds[1:]):
            between=n[left['_end']:right['_start']]
            if re.search(r'\b(?:ou|wla)\b|ولا|او',between):
                alternatives=True
            connectors=list(re.finditer(r'[,،;\n]|\bet\b|\b(?:w|ou|plus|zid)\b|\sو\s',between))
            if connectors:
                cuts.append(left['_end']+connectors[-1].end())
            elif n[right['_start']:right['_end']].startswith('و'):
                cuts.append(right['_start'])
            else:
                cuts.append(right['_start'])
                ambiguities.append('attribution_medicaments')
        cuts.append(len(n))
        for j,med in enumerate(meds):
            fields,proofs,problems=extract_fields(text,n,offsets,cuts[j],cuts[j+1])
            med.update(fields)
            med['preuves'] += proofs
            ambiguities += problems
        if 'attribution_medicaments' in ambiguities:
            for med in meds:
                for field in ('dosage','quantite','unite_quantite','forme'):
                    med[field]=None
    loose,loose_proofs,loose_problems=extract_fields(text,n,offsets,0,len(n))
    used_context=False
    # Contexte limité à une intention médicament et à un seul produit.
    if previous and not meds and not suggestions and not excluded and 'conseil_medical' not in intents:
        previous_intents=previous.get('intentions',[])
        med_intents=[i for i in previous_intents if i in ('disponibilite_medicament','prix_medicament')]
        followup=bool(loose) or not intents or all(i in med_intents for i in intents)
        if med_intents and followup and not any(i not in med_intents for i in intents):
            old=previous.get('medicaments',[])
            if len(old)==1 and loose:
                med={k:v for k,v in old[0].items() if k!='preuves'}
                med['origine']='contexte'
                med['preuves']=loose_proofs
                med.update(loose)
                meds=[med]
                intents=intents or med_intents
                ambiguities+=loose_problems
                used_context=True
    # Réponse à « quel médicament ? » : récupérer uniquement les champs explicitement
    # donnés pendant la demande incomplète, jamais ceux d'un autre médicament nommé.
    suggested_before=[name for s in (previous or {}).get('suggestions',[]) for name in s['candidats']]
    if previous and len(meds)==1 and not previous.get('medicaments') and any(k in previous.get('champs_manquants',[]) for k in ('medicament','confirmation_medicament')) and not excluded and (not suggested_before or meds[0]['medicament'] in suggested_before):
        for key,value in previous.get('champs_en_attente',{}).items():
            if meds[0].get(key) is None and value is not None:
                meds[0][key]=value
                meds[0]['origine']='message_et_contexte'
                used_context=True
        if previous.get('intentions') and all(i in ('disponibilite_medicament','prix_medicament') for i in previous['intentions']) and not availability and not any(re.search(pattern,n) for pattern in INTENTS.values()):
            intents=previous['intentions']
            used_context=True
    for med in meds:
        med.pop('_start',None)
        med.pop('_end',None)
    missing=[]
    clarification=None
    requires_med=any(i in ('disponibilite_medicament','prix_medicament') for i in intents)
    if 'conseil_medical' in intents:
        missing.append('avis_pharmacien')
        clarification=localize('medical',lang)
    elif suggestions:
        missing.append('confirmation_medicament')
        names=', '.join(dict.fromkeys(name for s in suggestions for name in s['candidats']))
        clarification=({'arabe_darija':'واش قصدك ', 'darija_latin':'Kat9sed ', 'francais_ou_autre':'Vouliez-vous dire '}[lang]+names+' ?')
    elif alternatives:
        missing.append('choix_medicament')
        clarification=localize('alternative',lang)
    elif requires_med and not meds:
        missing.append('medicament')
        clarification=localize('medicament',lang)
    elif ambiguities:
        missing=sorted(set(ambiguities))
        clarification=localize('quantite' if missing==['quantite'] else 'ambigu',lang)
    elif not intents:
        missing.append('intention')
        clarification=localize('inconnue',lang)
    one=meds[0] if len(meds)==1 else {}
    return {
        'texte_original':text,
        'intention':intents[0] if len(intents)==1 else ('demandes_multiples' if intents else 'inconnue'),
        'intentions':intents,
        'medicament':one.get('medicament'), 'dosage':one.get('dosage'),
        'quantite':one.get('quantite'), 'unite_quantite':one.get('unite_quantite'),
        'forme':one.get('forme'), 'medicaments':meds,
        'medicaments_exclus':excluded, 'suggestions':suggestions,
        'medicaments_alternatifs':alternatives,
        'champs_manquants':missing, 'clarification':clarification,
        'reponse':clarification or localize('ok',lang),
        'statut':'a_clarifier' if missing else 'interprete',
        'indice_langue':lang, 'contexte_utilise':used_context,
        'champs_en_attente':loose if requires_med and not meds else {},
        'disponibilite_reelle':None, 'prix_reel':None,
        'mode':'demonstration_sans_connexion_pharmacie',
        'methode':'regles_et_lexique_v2',
    }


def analyze(text, historique=None):
    previous=None
    for message in historique or []:
        previous=_analyze(message,previous)
    return _analyze(text,previous)
