// Exécuté localement. Aucun fichier image ni texte n'est envoyé sur Internet.
const fs=require('node:fs');
const path=require('node:path');
function dependency(name){return require(name)}
function textRegions(pixels,width,height){
 const seen=new Uint8Array(width*height),components=[];
 for(let y=1;y<height-1;y++)for(let x=1;x<width-1;x++){
   const start=y*width+x;if(seen[start]||pixels[start]>=115)continue;
   const stack=[start];seen[start]=1;let x0=x,x1=x,y0=y,y1=y,area=0;
   while(stack.length){const i=stack.pop(),cy=Math.floor(i/width),cx=i%width;area++;x0=Math.min(x0,cx);x1=Math.max(x1,cx);y0=Math.min(y0,cy);y1=Math.max(y1,cy);
     for(const j of [i-1,i+1,i-width,i+width])if(j>=0&&j<pixels.length&&!seen[j]&&pixels[j]<115&&Math.abs(j%width-cx)<=1){seen[j]=1;stack.push(j)}
   }
   const w=x1-x0+1,h=y1-y0+1;
   if(area>=5&&h>=5&&h<height*.23&&w>=2&&w<h*2.8&&area/(w*h)>.08)components.push({x0,x1,y0,y1,h,count:1});
 }
 const groups=[];
 for(const c of components.sort((a,b)=>a.x0-b.x0)){
   const g=groups.filter(g=>c.x0-g.x1<=Math.max(g.h,c.h)*2.5&&c.x0>=g.x0&&Math.abs((c.y0+c.y1-g.y0-g.y1)/2)<Math.max(g.h,c.h)*.4&&Math.max(g.h,c.h)/Math.min(g.h,c.h)<2.1).sort((a,b)=>Math.abs(c.x0-a.x1)-Math.abs(c.x0-b.x1))[0];
   if(g){g.x1=Math.max(g.x1,c.x1);g.y0=Math.min(g.y0,c.y0);g.y1=Math.max(g.y1,c.y1);g.h=g.y1-g.y0+1;g.count++}else groups.push({...c});
 }
 return groups.filter(g=>g.count>=2&&g.x1-g.x0>=10).sort((a,b)=>b.h-a.h).slice(0,8);
}
async function main(){
 const sharp=dependency('sharp');const {createWorker}=dependency('tesseract.js');
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 if(input.check){console.log(JSON.stringify({disponible:true,moteur:'Tesseract.js',langues:['fra','ara']}));return}
 const bytes=Buffer.from(input.image_base64,'base64');
 const meta=await sharp(bytes,{limitInputPixels:25000000,failOn:'error'}).metadata();
 if(!['jpeg','png','webp'].includes(meta.format)||meta.width<100||meta.height<80||meta.pages>1)throw Error('Image JPEG, PNG ou WebP de 100 × 80 pixels minimum attendue.');
 const oriented=await sharp(bytes,{limitInputPixels:25000000}).autoOrient().flatten({background:'#fff'}).resize({width:2400,height:2400,fit:'inside',withoutEnlargement:true}).png().toBuffer();
 const orientedMeta=await sharp(oriented).metadata();
 const longSide=Math.max(orientedMeta.width,orientedMeta.height);
 const reading=longSide<1400?await sharp(oriented).resize({width:Math.round(orientedMeta.width*Math.min(3,1800/longSide)),height:Math.round(orientedMeta.height*Math.min(3,1800/longSide)),fit:'fill',kernel:'lanczos3'}).png().toBuffer():oriented;
 const {data:gray,info}=await sharp(oriented).resize({width:600,withoutEnlargement:true}).greyscale().raw().toBuffer({resolveWithObject:true});
 let light=0,lapSum=0,lapSquared=0,count=0;
 for(const pixel of gray)light+=pixel;
 for(let y=1;y<info.height-1;y++)for(let x=1;x<info.width-1;x++){const i=y*info.width+x;const lap=4*gray[i]-gray[i-1]-gray[i+1]-gray[i-info.width]-gray[i+info.width];lapSum+=lap;lapSquared+=lap*lap;count++}
 const luminance=light/gray.length;const focus=count?lapSquared/count-(lapSum/count)**2:0;
 // Proposer des bandes de texte à partir de la projection des pixels sombres.
 // Lire chaque ligne réduit l'effet du décor, de la perspective et des colonnes.
 const {data:ink,info:inkInfo}=await sharp(oriented).greyscale().raw().toBuffer({resolveWithObject:true});
 const bands=[];let bandStart=null;
 for(let y=0;y<=inkInfo.height;y++){
   let dark=0;if(y<inkInfo.height)for(let x=Math.floor(inkInfo.width*.08);x<inkInfo.width*.93;x++)if(ink[y*inkInfo.width+x]<100)dark++;
   if(dark>=Math.max(5,inkInfo.width*.008)){if(bandStart===null)bandStart=y}
   else if(bandStart!==null){if(y-bandStart>=5&&y-bandStart<inkInfo.height*.24)bands.push({top:Math.max(0,bandStart-5),height:Math.min(inkInfo.height, y+5)-Math.max(0,bandStart-5)});bandStart=null}
 }
 const models=path.join(__dirname,'ocr_models');
 for(const lang of ['fra','ara'])if(!fs.existsSync(path.join(models,lang+'.traineddata')))throw Error('Modèle OCR absent : '+lang);
 const worker=await createWorker(['fra','ara'],1,{langPath:models,gzip:false,cacheMethod:'none',logger:()=>{}});
 const passes=[];
 try{
   const variants=[{name:'orientation_et_agrandissement',buffer:reading,psm:'11'},{name:'contraste_et_nettete',buffer:await sharp(reading).greyscale().normalise().sharpen().png().toBuffer(),psm:'6'}];
   async function read(v,languages){await worker.setParameters({tessedit_pageseg_mode:v.psm,preserve_interword_spaces:'1'});const {data}=await worker.recognize(v.buffer);passes.push({traitement:v.name,langues:languages,texte:data.text.trim(),confiance_ocr:Math.round(data.confidence||0),...(v.zone?{zone:v.zone}:{})});return data}
   for(const v of variants)await read(v,['fra','ara']);
   // Une passe française évite que la détection mixte déforme du texte latin.
   // Elle complète les lectures arabes, sans les remplacer.
   await worker.reinitialize('fra');
   await read({name:'francais_texte_disperse',buffer:reading,psm:'11'},['fra']);
   await read({name:'francais_bloc',buffer:reading,psm:'6'},['fra']);
   if(Math.max(...passes.map(p=>p.confiance_ocr))<75){
     const {data:regionPixels,info:regionInfo}=await sharp(oriented).resize({width:Math.min(900,orientedMeta.width)}).extractChannel('red').raw().toBuffer({resolveWithObject:true});
     const scale=orientedMeta.width/regionInfo.width;
     for(const [i,r]of textRegions(regionPixels,regionInfo.width,regionInfo.height).entries()){
       const left=Math.max(0,Math.floor((r.x0-5)*scale)),top=Math.max(0,Math.floor((r.y0-5)*scale));
       const width=Math.min(orientedMeta.width-left,Math.ceil((r.x1-r.x0+11)*scale)),height=Math.min(orientedMeta.height-top,Math.ceil((r.y1-r.y0+11)*scale));
       const crop=await sharp(oriented).extract({left,top,width,height}).resize({height:Math.min(350,height*4)}).extend({top:15,bottom:15,left:15,right:15,background:'white'}).png().toBuffer();
       const zone={x:left,y:top,largeur:width,hauteur:height};
       const result=await read({name:'texte_localise_'+i,buffer:crop,psm:'7',zone},['fra']);
       if(/^\s*\d{1,3}[;:.]?\s*$/.test(result.text)&&r.h<regionInfo.height*.075){
         const contextWidth=Math.min(orientedMeta.width-left,Math.ceil((r.x1-r.x0+11+r.h*6)*scale));
         const contextHeight=Math.min(orientedMeta.height-top,Math.ceil((r.y1-r.y0+11+r.h*.8)*scale));
         const context=await sharp(oriented).extract({left,top,width:contextWidth,height:contextHeight}).resize({height:contextHeight*4}).extend({top:12,bottom:12,left:12,right:12,background:'white'}).png().toBuffer();
         await read({name:'contexte_nombre_'+i,buffer:context,psm:'6',zone:{x:left,y:top,largeur:contextWidth,hauteur:contextHeight}},['fra']);
       }
     }
   }
   if(Math.max(...passes.map(p=>p.confiance_ocr))<75){
     await read({name:'canal_rouge_contraste',buffer:await sharp(reading).extractChannel('red').normalise().png().toBuffer(),psm:'11'},['fra']);
     await read({name:'canal_rouge_seuil',buffer:await sharp(reading).extractChannel('red').normalise().threshold(160).png().toBuffer(),psm:'11'},['fra']);
     for(const [i,[x,y]]of [[0,0],[.4,0],[0,.35],[.4,.35]].entries()){
       const left=Math.floor(orientedMeta.width*x),top=Math.floor(orientedMeta.height*y);
       const width=Math.min(Math.ceil(orientedMeta.width*.6),orientedMeta.width-left),height=Math.min(Math.ceil(orientedMeta.height*.65),orientedMeta.height-top);
       const tile=await sharp(oriented).extract({left,top,width,height}).resize({width:Math.min(2200,width*4)}).png().toBuffer();
       await read({name:'zone_detail_'+i,buffer:tile,psm:'11'},['fra']);
     }
   }
   for(const [i,band]of bands.sort((a,b)=>b.height-a.height).slice(0,7).entries()){
     const crop=await sharp(oriented).extract({left:Math.floor(inkInfo.width*.08),top:band.top,width:Math.floor(inkInfo.width*.85),height:band.height}).resize({width:Math.min(2400,Math.round(inkInfo.width*.85*3))}).extend({top:12,bottom:12,left:12,right:12,background:'#fff'}).png().toBuffer();
     await read({name:'ligne_detectee_'+i,buffer:crop,psm:'7'},['fra']);
   }
   await worker.reinitialize(['fra','ara']);
   // Une image tournée ne nécessite pas une nouvelle photo : tester les quarts de tour.
   if(input.rotation_complete){
     for(const angle of [90,180,270]){await worker.setParameters({tessedit_pageseg_mode:'11'});const {data}=await worker.recognize(await sharp(reading).rotate(angle).png().toBuffer());passes.push({traitement:'rotation_'+angle,langues:['fra','ara'],texte:data.text.trim(),confiance_ocr:Math.round(data.confidence||0)})}
   }
 }finally{await worker.terminate()}
 console.log(JSON.stringify({passes,qualite:{largeur:meta.width,hauteur:meta.height,luminance_moyenne:Math.round(luminance),indicateur_nettete:Math.round(focus),alertes:[...(luminance<65?['image_sombre']:[]),...(focus<45?['flou_ou_peu_de_texte']:[])],seuils:'Heuristiques non calibrées sur des photos réelles.'},moteur:'Tesseract.js 7',langues:['fra','ara']}));
}
main().catch(e=>{console.error(e.message);process.exitCode=1});
