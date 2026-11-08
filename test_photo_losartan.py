"""Régression sur la photo fournie par l'utilisateur, pas un benchmark."""
import base64,json
from pathlib import Path
from vision import recognize
from nlp import analyze

def run():
    root=Path(__file__).parent
    result=recognize(base64.b64encode((root/'tests_images/losartan_fourni.jpg').read_bytes()).decode())
    candidate=result['candidats'][0]
    assert candidate['medicament']=='Losartan'
    assert candidate['dosages_lus']==['50 mg']
    assert 'Zentiva Lab' in candidate['laboratoires_lus']
    assert result['confirmation_requise'] and result['quantite_patient'] is None
    assert candidate['reference_produit_exacte'] is False
    request=analyze('3ndkom Losartan 50mg ? bghit jouj bwat')
    assert request['medicament']=='Losartan' and request['quantite']==2 and request['dosage']=='50 mg'
    report={'nature':'Cas de régression utilisateur, sans estimation de performance terrain.','fichier':'tests_images/losartan_fourni.jpg','reussi':True,'resultat_ocr':result,'demande_texte':request}
    (root/'resultat_photo_losartan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('Photo utilisateur : Losartan, 50 mg, Zentiva Lab, puis 2 boîtes demandées en darija : OK')

if __name__=='__main__':
    run()
