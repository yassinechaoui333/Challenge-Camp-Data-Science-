"""Régressions synthétiques : variantes, ambiguïtés, contexte et provenance."""
import json
from pathlib import Path
from nlp import analyze
from test_demo import CASES


EXTRA = [
 ('Darija arabe', 'سلام، واش عندكم دوليبران ٥٠٠ ملغ؟ بغيت جوج علب', {'medicament':'Doliprane','dosage':'500 mg','quantite':2,'statut':'interprete'}),
 ('Arabizi variante', 'Salam, 3endkom Doliprane 500mg ? bghit tlata bwat', {'dosage':'500 mg','quantite':3,'statut':'interprete'}),
 ('Darija quantité 4', 'bghit rb3a bwat smecta', {'medicament':'Smecta','quantite':4}),
 ('Darija quantité 5', 'bghit khmsa bwat smecta', {'quantite':5}),
 ('Darija quantité 10', 'bghit 3chra sachets Smecta', {'quantite':10,'unite_quantite':'sachet'}),
 ('Arabe quantité 3', 'بغيت تلاتة علب سميكتا', {'quantite':3}),
 ('Arabe quantité 4', 'اريد اربع علب سميكتا', {'quantite':4}),
 ('Dual arabe', 'بغيت علبتين دوليبران 500 ملغ', {'quantite':2,'dosage':'500 mg'}),
 ('Singulier arabe', 'بغيت علبة سميكتا', {'quantite':1,'unite_quantite':'boite'}),
 ('Quantité après unité', 'bghit Smecta boita wa7da', {'quantite':1}),
 ('Deux flacons', 'Gaviscon sirop jouj 9ra3i', {'quantite':2,'unite_quantite':'flacon','forme':'sirop'}),
 ('Flacon arabe', 'بغيت جوج قراعي غافيسكون سيرو', {'medicament':'Gaviscon','quantite':2,'forme':'sirop'}),
 ('Sachets', 'Smecta 3 sachets', {'quantite':3,'unite_quantite':'sachet'}),
 ('Chiffres persans', 'Doliprane ۵۰۰ mg ۲ boites', {'dosage':'500 mg','quantite':2}),
 ('Décimale', 'Doliprane 0,5 g 1 boite', {'dosage':'0.5 g','quantite':1}),
 ('Dose collée au nom', 'Doliprane500mg', {'medicament':'Doliprane','dosage':'500 mg','quantite':None}),
 ('Concentration', 'Gaviscon sirop 250 mg/5 ml 2 flacons', {'dosage':'250 mg/5 ml','quantite':2,'forme':'sirop'}),
 ('Pas de quantité déduite', 'Doliprane 500 mg', {'dosage':'500 mg','quantite':None,'unite_quantite':None}),
 ('Pas de dosage supposé', 'Smecta jouj bwat', {'dosage':None,'quantite':2}),
 ('Aucune forme supposée', 'Ventoline disponible ?', {'forme':None}),
 ('Gélules explicites', 'Imodium gelules 2 boites', {'medicament':'Imodium','forme':'gelule','quantite':2}),
 ('Comprimés explicites', 'Doliprane comprimes 500mg', {'forme':'comprime','dosage':'500 mg'}),
 ('Diacritiques et tatweel', 'بغيت دُولـيبران ٥٠٠ ملغ', {'medicament':'Doliprane','dosage':'500 mg'}),
 ('Alias', '3andkom dolipran ?', {'medicament':'Doliprane'}),
 ('Nouveau catalogue', '3ndkom spasfon ?', {'medicament':'Spasfon'}),
 ('Autre catalogue', 'Dafalgan disponible ?', {'medicament':'Dafalgan'}),
 ('Faute à confirmer', 'wach 3ndkom doliparne 500mg jouj bwat ?', {'medicament':None,'statut':'a_clarifier','champs_manquants':['confirmation_medicament']}),
 ('Nom inconnu', 'bghit medicamentxyz', {'medicament':None,'statut':'a_clarifier','champs_manquants':['medicament']}),
 ('Préfixe trompeur', 'bghit dolipranex', {'medicament':None,'statut':'a_clarifier'}),
 ('Quantité nulle', 'Doliprane 0 boites', {'quantite':None,'statut':'a_clarifier','champs_manquants':['quantite']}),
 ('Quantité négative', 'Doliprane -2 boites', {'quantite':None,'statut':'a_clarifier','champs_manquants':['quantite']}),
 ('Quantité fractionnaire', 'Doliprane 1.5 boites', {'quantite':None,'statut':'a_clarifier','champs_manquants':['quantite']}),
 ('Dosages contradictoires', 'Doliprane 500mg ou 1g', {'dosage':None,'statut':'a_clarifier','champs_manquants':['dosage']}),
 ('Quantités contradictoires', 'Doliprane 2 boites ou 3 boites', {'quantite':None,'statut':'a_clarifier'}),
 ('Deux médicaments', 'Bghit jouj bwat Doliprane 500mg w boita wa7da Smecta', {'statut':'interprete','medicaments':[{'medicament':'Doliprane','dosage':'500 mg','quantite':2},{'medicament':'Smecta','dosage':None,'quantite':1}]}),
 ('Deux médicaments français', '2 boites de Doliprane 500mg et 3 sachets Smecta', {'medicaments':[{'quantite':2,'dosage':'500 mg'},{'quantite':3,'dosage':None}]}),
 ('Coordination arabe', 'دوليبران 500 ملغ وسميكتا', {'statut':'interprete','medicaments':[{'medicament':'Doliprane','dosage':'500 mg'},{'medicament':'Smecta','dosage':None}]}),
 ('Attribution incertaine', 'Doliprane Smecta 2 boites', {'statut':'a_clarifier','medicaments':[{'quantite':None},{'quantite':None}]}),
 ('Alternative', 'Doliprane ou Smecta', {'statut':'a_clarifier','medicaments_alternatifs':True,'champs_manquants':['choix_medicament']}),
 ('Alternative darija', 'doliprane wla smecta', {'statut':'a_clarifier','medicaments_alternatifs':True}),
 ('Négation arabe', 'ما بغيتش دوليبران، بغيت سميكتا جوج علب', {'medicament':'Smecta','quantite':2,'medicaments_exclus':['Doliprane']}),
 ('Négation latine', 'ma bghitch Doliprane, bghit Smecta', {'medicament':'Smecta','medicaments_exclus':['Doliprane']}),
 ('Téléphone seul', 'bghit nmra dyal pharmacie', {'intentions':['telephone_pharmacie']}),
 ('Téléphone et adresse', '3afak nmra dyal pharmacie w fin kayna ?', {'intentions':['telephone_pharmacie','localisation_pharmacie'],'statut':'interprete'}),
 ('Horaires darija', 'wach pharmacie ma7loula ?', {'intentions':['horaires_pharmacie']}),
 ('Horaires arabe', 'واش الصيدلية محلولة؟', {'intentions':['horaires_pharmacie']}),
 ('Horaires français', 'Quels sont vos horaires ?', {'intentions':['horaires_pharmacie']}),
 ('Prix darija', 'bch7al Gaviscon sirop ?', {'intentions':['prix_medicament'],'medicament':'Gaviscon','forme':'sirop','prix_reel':None}),
 ('Prix arabe', 'بشحال دوليبران؟', {'intentions':['prix_medicament'],'medicament':'Doliprane'}),
 ('Prix sans médicament', 'bch7al ?', {'champs_manquants':['medicament'],'statut':'a_clarifier'}),
 ('Prix et horaires', 'bch7al Gaviscon sirop ? w wach pharmacie ma7loula ?', {'intentions':['prix_medicament','horaires_pharmacie'],'statut':'interprete'}),
 ('Localisation française', 'Où se trouve la pharmacie ?', {'intentions':['localisation_pharmacie']}),
 ('Ou conjonction', 'Doliprane ou Smecta', {'intentions':['disponibilite_medicament']}),
 ('Pas de conseil médical', 'Doliprane ch7al nakhod ?', {'statut':'a_clarifier','champs_manquants':['avis_pharmacien']}),
 ('Salutation hors périmètre', 'Salam !', {'intention':'inconnue','statut':'a_clarifier'}),
]

CONTEXT = [
 ('Compléter dosage et quantité', ['3ndkom Doliprane ?'], '500mg jouj bwat', {'medicament':'Doliprane','dosage':'500 mg','quantite':2,'contexte_utilise':True}),
 ('Préciser nom absent', ['bghit jouj bwat 500mg'], 'Doliprane', {'medicament':'Doliprane','quantite':2,'dosage':'500 mg','contexte_utilise':True}),
 ('Confirmer faute', ['wach 3ndkom doliparne 500mg jouj bwat ?'], 'Doliprane', {'medicament':'Doliprane','quantite':2,'dosage':'500 mg','statut':'interprete'}),
 ('Changement de produit', ['Doliprane 500mg 2 boites'], 'Smecta', {'medicament':'Smecta','quantite':None,'dosage':None,'contexte_utilise':False}),
 ('Changement de besoin', ['Doliprane 500mg 2 boites'], 'fin kayna pharmacie ?', {'medicaments':[],'intentions':['localisation_pharmacie'],'contexte_utilise':False}),
 ('Correction de quantité', ['Doliprane 500mg 2 boites'], 'non, 1 boite', {'medicament':'Doliprane','quantite':1,'dosage':'500 mg'}),
 ('Correction de dosage', ['Doliprane 500mg 2 boites'], 'non 1g', {'medicament':'Doliprane','quantite':2,'dosage':'1 g'}),
 ('Historique isolé', [], '500mg jouj bwat', {'medicament':None,'contexte_utilise':False,'statut':'a_clarifier'}),
 ('Nom après question prix', ['bch7al ?'], 'Smecta', {'medicament':'Smecta','intentions':['prix_medicament']}),
 ('Rejet suggestion autre produit', ['wach 3ndkom doliparne 500mg jouj bwat ?'], 'Smecta', {'medicament':'Smecta','quantite':None,'dosage':None}),
 ('Trois tours', ['bghit jouj bwat 500mg','Doliprane'], 'non, 3 boites', {'medicament':'Doliprane','quantite':3,'dosage':'500 mg','contexte_utilise':True}),
]


def subset(actual, expected, path=''):
    if isinstance(expected,dict):
        for key,value in expected.items():
            assert key in actual, path+'.'+key
            subset(actual[key],value,path+'.'+key)
    elif isinstance(expected,list):
        assert len(actual)==len(expected), f'{path}: {actual} != {expected}'
        for i,(a,e) in enumerate(zip(actual,expected)):
            subset(a,e,f'{path}[{i}]')
    else:
        assert actual==expected, f'{path}: {actual!r} != {expected!r}'


def run():
    fixtures=[]
    for text,*values in CASES:
        fixtures.append(('Régression V1',[],text,dict(zip(['intention','medicament','dosage','quantite','statut'],values))))
    fixtures += [(name,[],text,expected) for name,text,expected in EXTRA]
    fixtures += CONTEXT
    results=[]
    for name,history,text,expected in fixtures:
        result=analyze(text,history)
        error=None
        try:
            subset(result,expected)
            assert result['disponibilite_reelle'] is None and result['prix_reel'] is None
            for med in result['medicaments']:
                for proof in med['preuves']:
                    assert text[proof['debut']:proof['fin']]==proof['texte'], 'Provenance incorrecte'
        except AssertionError as e:
            error=str(e)
            print('ECHEC',name,text,error)
        results.append({'nom':name,'historique':history,'texte':text,'attendu':expected,'reussi':error is None,'erreur':error})
    report={'version':2,'total':len(results),'reussis':sum(c['reussi'] for c in results),'nature':'Régressions synthétiques. Pas de mesure sur corpus indépendant ni de validation terrain.','cas':results}
    Path(__file__).with_name('resultats_tests_v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"{report['reussis']}/{report['total']} scénarios réussis")
    assert report['reussis']==report['total']

if __name__=='__main__':
    run()
