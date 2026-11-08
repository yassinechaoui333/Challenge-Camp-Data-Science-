"""Évaluation du pipeline complet sur les fiches synthétiques fournies."""
import base64,json,time,sys
from pathlib import Path
from vision import recognize

def run(full=False):
    root=Path(__file__).parent
    manifest=json.loads((root/'dataset/manifest.json').read_text(encoding='utf8'))
    rows=[]
    for case in manifest['cas']:
        if not full and case['sous_jeu']!='rapide':
            continue
        start=time.perf_counter()
        result=recognize(base64.b64encode((root/'dataset'/case['fichier']).read_bytes()).decode(),case['condition']=='rotation_90')
        found=result['candidats'][0]['medicament'] if result['candidats'] else None
        ok=found==case['nom_attendu']
        rows.append({**case,'nom_obtenu':found,'reussi':ok,'statut':result['statut'],'secondes':round(time.perf_counter()-start,2),'texte_ocr':result['texte_ocr']})
        print(f"{'OK' if ok else 'ECHEC'} {case['fichier']} : {found}",flush=True)
    summary={'total':len(rows),'noms_corrects':sum(r['reussi'] for r in rows),'nature':'Correspondance du nom sur fiches texte synthétiques. Aucun taux de reconnaissance de boîtes réelles ne peut en être déduit.','par_condition':{},'cas':rows}
    for condition in sorted(set(r['condition'] for r in rows)):
        selected=[r for r in rows if r['condition']==condition]
        summary['par_condition'][condition]={'total':len(selected),'corrects':sum(r['reussi'] for r in selected)}
    (root/('resultats_ocr_complet.json' if full else 'resultats_ocr.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(f"{summary['noms_corrects']}/{summary['total']} noms attendus retrouvés (fiches synthétiques).",flush=True)
    return summary

if __name__=='__main__':
    run('--full' in sys.argv)
