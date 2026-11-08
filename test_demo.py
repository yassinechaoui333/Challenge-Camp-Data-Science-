import json
from pathlib import Path
from app import analyze

CASES = [
 ('Avez-vous 2 boîtes de Doliprane 500 mg ?', 'disponibilite_medicament', 'Doliprane', '500 mg', 2, 'interprete'),
 ('واش عندكم دوليبران 500 mg جوج علب؟', 'disponibilite_medicament', 'Doliprane', '500 mg', 2, 'interprete'),
 ('هل يتوفر دوليبران ٥٠٠ ملغ؟', 'disponibilite_medicament', 'Doliprane', '500 mg', None, 'interprete'),
 ('3ndkom smecta ?', 'disponibilite_medicament', 'Smecta', None, None, 'interprete'),
 ('kayn ventoline ?', 'disponibilite_medicament', 'Ventoline', None, None, 'interprete'),
 ('Efferalgan disponible ?', 'disponibilite_medicament', 'Efferalgan', None, None, 'interprete'),
 ('بغيت سميكتا', 'disponibilite_medicament', 'Smecta', None, None, 'interprete'),
 ('Doliprane 1 g', 'disponibilite_medicament', 'Doliprane', '1 g', None, 'interprete'),
 ('Quel est le numéro de la pharmacie ?', 'telephone_pharmacie', None, None, None, 'interprete'),
 ('ما هو رقم هاتف الصيدلية؟', 'telephone_pharmacie', None, None, None, 'interprete'),
 ('nmra pharmacie ?', 'telephone_pharmacie', None, None, None, 'interprete'),
 ('Où est la pharmacie ?', 'localisation_pharmacie', None, None, None, 'interprete'),
 ('fin kayna pharmacie ?', 'localisation_pharmacie', None, None, None, 'interprete'),
 ('أين توجد الصيدلية؟', 'localisation_pharmacie', None, None, None, 'interprete'),
 ('bghit dwa', 'disponibilite_medicament', None, None, None, 'a_clarifier'),
 ('bonjour', 'inconnue', None, None, None, 'a_clarifier'),
 ('Avez-vous Doliprane et Smecta ?', 'disponibilite_medicament', None, None, None, 'interprete'),
 ('Téléphone et adresse pharmacie', 'demandes_multiples', None, None, None, 'interprete'),
 ('Doliprane 500 mg', 'disponibilite_medicament', 'Doliprane', '500 mg', None, 'interprete'),
 ('Avez-vous 3 boites de smecta ?', 'disponibilite_medicament', 'Smecta', None, 3, 'interprete'),
]

def run():
    keys = ['intention','medicament','dosage','quantite','statut']
    results = []
    for text, *expected in CASES:
        result = analyze(text)
        actual = [result[k] for k in keys]
        ok = actual == expected
        results.append({'texte':text,'attendu':dict(zip(keys,expected)),'obtenu':dict(zip(keys,actual)),'reussi':ok})
        if not ok:
            print('ECHEC', text, expected, actual)
    report = {'total':len(results),'reussis':sum(r['reussi'] for r in results),'nature':'Cas synthétiques fonctionnels, sans validation terrain','cas':results}
    Path(__file__).with_name('resultats_tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"{report['reussis']}/{report['total']} cas réussis")
    assert report['reussis'] == report['total']

if __name__ == '__main__':
    run()
