"""Régressions du rapprochement et du contrat, sans simuler la qualité OCR."""
from vision import match_ocr,recognize,read_mentions

def fake(*texts):
    return {'passes':[{'traitement':f'lecture_{i}','texte':text,'confiance_ocr':80} for i,text in enumerate(texts)],'langues':['fra','ara']}

def run():
    checks=0
    r=match_ocr(fake('DOLIPRANE 500 mg 16 comprimes'))
    assert r['candidats'][0]['medicament']=='Doliprane'
    assert r['quantite_patient'] is None and r['confirmation_requise']
    assert not r['candidats'][0]['reference_produit_exacte']
    checks+=1
    r=match_ocr(fake('دوليبران ٥٠٠ ملغ'))
    assert r['candidats'][0]['medicament']=='Doliprane'
    assert r['candidats'][0]['dosages_lus']==['500 mg']
    checks+=1
    r=match_ocr(fake('DOLIPARNE 500mg'))
    assert r['candidats'][0]['type_correspondance']=='nom_approchant'
    assert r['confirmation_requise']
    checks+=1
    r=match_ocr(fake('Doliprane 500mg Smecta 3g'))
    assert r['statut']=='ambigu'
    assert all(not c['dosages_lus'] for c in r['candidats'])
    checks+=1
    r=match_ocr(fake('Doliprane 500mg','Doliprane 1g'))
    assert r['lectures_dosage_differentes'] and len(r['candidats'][0]['dosages_lus'])==2
    checks+=1
    for text in ('XYZEDRUG',''):
        assert match_ocr(fake(text))['statut']=='non_reconnu'
        checks+=1
    for value in (None,'','###','YWJj'):
        try:
            recognize(value)
            raise AssertionError('Image invalide acceptée')
        except ValueError:
            checks+=1
    assert read_mentions('Gaviscon sirop 250mg/5ml')==(['250 mg/5 ml'],['sirop'])
    checks+=1
    print(f'{checks}/{checks} vérifications OCR/matching réussies')
    return checks

if __name__=='__main__':
    run()
