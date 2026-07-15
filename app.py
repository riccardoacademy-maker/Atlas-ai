import os, sqlite3, json, zipfile, shutil, random, webbrowser, threading, base64, re
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.lib.units import mm

BASE = Path(__file__).parent.resolve()
STORE = BASE / 'storage'; PROD = STORE / 'products'; PREV = STORE / 'previews'; ASSETS = BASE / 'static' / 'generated_assets'
DB = STORE / 'digitalmint.db'
for p in (STORE, PROD, PREV, ASSETS): p.mkdir(parents=True, exist_ok=True)
app = Flask(__name__); app.secret_key = 'digitalmint-ai-local-premium'
MARKETPLACES = ['Etsy', 'Creative Market', 'Gumroad', 'Payhip', 'Shopify']
PRODUCTS = {
    'Planner':['Daily Planner','Weekly Planner','Monthly Planner','Yearly Planner','Business Planner','Wedding Planner','Travel Planner','Student Planner','Teacher Planner','Pregnancy Planner','Goal Planner','Life Planner'],
    'Finanza':['Budget Tracker','Savings Challenge','Expense Tracker','Debt Tracker','Finance Planner','Investment Journal'],
    'Fitness':['Fitness Planner','Workout Planner','Gym Journal','Meal Planner','Water Tracker','Weight Loss Planner','Habit Tracker'],
    'Journal':['Gratitude Journal','Reading Journal','Dream Journal','Manifestation Journal','Mental Wellness Journal','Prayer Journal','Self Care Journal'],
    'Workbook':['Business Workbook','Mindset Workbook','Study Workbook','Productivity Workbook','Self Improvement Workbook'],
    'Business':['Invoice Template','Receipt Template','Business Proposal','Contract Template','Client Intake Form','Price List'],
    'Marketing':['Instagram Templates','Pinterest Templates','Facebook Templates','Media Kit','Brand Kit','Content Planner'],
    'Kids':['Coloring Book','Activity Book','Flashcards','Alphabet Book','Math Workbook','Tracing Book'],
    'Cooking':['Recipe Book','Meal Prep Planner','Kitchen Inventory','Shopping List'],
    'Printable':['Checklist','To-do List','Calendar','Chore Chart','Cleaning Planner'],
    'Business Documents':['Resume','CV','Portfolio','Cover Letter','Invoice','Presentation','Digital Notebook']}
FONTS = ['Helvetica','Times-Roman','Courier','Helvetica-Bold']
STYLES = ['Minimal Luxury','Modern Editorial','Elegant Soft','Bold Premium','Clean Productivity']
ILLUSTRATIONS = {
    'botanical':['flower','leaf','moon','star'], 'business':['briefcase','chart','target','spark'],
    'fitness':['dumbbell','water','heart','bolt'], 'finance':['coin','wallet','chart','diamond'],
    'wedding':['ring','flower','heart','spark'], 'kids':['star','rainbow','pencil','balloon'],
    'travel':['plane','compass','map','sun'], 'productivity':['check','calendar','clock','target']}

SCHEMAS = {
    'Planner': {'intro':'Un sistema operativo personale per trasformare obiettivi in azioni misurabili.', 'sections':['Vision board','Obiettivi trimestrali','Agenda strategica','Priorità giornaliere','Revisione e miglioramento'], 'table':['Area','Obiettivo','Azione','Scadenza','Stato'], 'bonus':['Pagina brain dump','Checklist reset settimanale','Matrice priorità']},
    'Finanza': {'intro':'Un percorso finanziario guidato per monitorare entrate, uscite, risparmio e decisioni.', 'sections':['Diagnosi iniziale','Budget mensile','Tracker spese','Piano debiti','Risparmio e investimenti'], 'table':['Voce','Previsto','Reale','Differenza','Note'], 'bonus':['Sfida risparmio 30 giorni','Audit abbonamenti','Riepilogo patrimonio']},
    'Fitness': {'intro':'Un planner salute completo per allenamenti, alimentazione, idratazione e progressi.', 'sections':['Obiettivi fisici','Programma workout','Meal planning','Water tracker','Misurazioni e recupero'], 'table':['Giorno','Workout','Pasti','Acqua','Energia'], 'bonus':['Checklist borsa palestra','Tracker abitudini','Revisione progressi']},
    'Journal': {'intro':'Uno spazio elegante per riflessione, gratitudine, consapevolezza e crescita personale.', 'sections':['Intenzione','Prompt guidati','Gratitudine','Lezioni apprese','Riflessione finale'], 'table':['Prompt','Risposta','Azione gentile'], 'bonus':['Lettera al futuro','Mood tracker','Rituale serale']},
    'Workbook': {'intro':'Un workbook pratico con esercizi, esempi, checklist e azioni di implementazione.', 'sections':['Diagnosi','Framework','Esercizi guidati','Esempi applicati','Piano operativo'], 'table':['Step','Esercizio','Risultato atteso','Completato'], 'bonus':['Checklist implementazione','Template decisionale','Piano 7 giorni']},
    'Kids': {'intro':'Attività creative e progressive pensate per apprendimento, manualità e divertimento.', 'sections':['Riscaldamento creativo','Colora e osserva','Traccia e impara','Gioco logico','Premio finale'], 'table':['Attività','Obiettivo','Completato'], 'bonus':['Certificato completamento','Pagina libera creativa','Mini sfida']},
    'Business': {'intro':'Documenti professionali strutturati per comunicare valore, prezzi, accordi e processi.', 'sections':['Profilo cliente','Offerta','Termini','Consegna','Firma e follow-up'], 'table':['Sezione','Dettaglio','Responsabile','Scadenza'], 'bonus':['Checklist invio','Script email','Riepilogo cliente']},
    'Marketing': {'intro':'Sistema contenuti premium per pianificare campagne, asset visual e messaggi coerenti.', 'sections':['Brand voice','Pilastri contenuto','Calendario','Asset social','Analisi performance'], 'table':['Canale','Idea','Formato','CTA','KPI'], 'bonus':['Hook library','Checklist lancio','Mappa hashtag']},
    'Cooking': {'intro':'Organizzatore cucina per ricette, meal prep, inventario e spesa intelligente.', 'sections':['Ricette preferite','Piano settimanale','Lista spesa','Inventario','Preparazioni'], 'table':['Ricetta','Ingredienti','Tempo','Porzioni','Note'], 'bonus':['Conversioni cucina','Freezer inventory','Menu ospiti']},
    'Printable': {'intro':'Printable operativo chiaro, elegante e immediatamente utilizzabile per casa e lavoro.', 'sections':['Obiettivo','Lista principale','Routine','Controllo qualità','Chiusura'], 'table':['Elemento','Frequenza','Responsabile','Fatto'], 'bonus':['Checklist extra','Pagina note','Riepilogo']},
    'Business Documents': {'intro':'Kit documentale premium per presentare competenze, portfolio e proposte con autorevolezza.', 'sections':['Profilo','Esperienza','Risultati','Proposta','Contatto'], 'table':['Area','Contenuto','Prova','Priorità'], 'bonus':['Checklist revisione','Bio breve','Email accompagnamento']}}

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init_db():
    with conn() as c:
        c.execute('''create table if not exists products(id integer primary key, name text, niche text, language text, format text, pages integer, primary_color text, secondary_color text, font text, style text, marketplace text, category text, product_type text, title_seo text, description_seo text, tags text, price text, file_name text, folder text, zip_path text, preview_path text, created_at text, updated_at text, history text, bundle_id text, cover_config text)''')
        cols = {r[1] for r in c.execute('pragma table_info(products)')}
        if 'bundle_id' not in cols: c.execute('alter table products add column bundle_id text')
        if 'cover_config' not in cols: c.execute('alter table products add column cover_config text')
init_db()

def slug(s): return re.sub('-+', '-', ''.join(ch.lower() if ch.isalnum() else '-' for ch in s)).strip('-')[:90]
def hex_to_rgb(h):
    h = (h or '#d4af37').lstrip('#')
    return tuple(int(h[i:i+2],16) for i in (0,2,4)) if len(h) == 6 else (212,175,55)
def font(size=42, bold=False):
    paths = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    try: return ImageFont.truetype(paths[0], size)
    except Exception: return ImageFont.load_default()

def draw_icon(d, icon, x, y, s, fill, width=4):
    if icon in ('flower','spark'): 
        for a in range(0,360,60):
            dx = int(s*.32); d.ellipse((x+dx, y+dx, x+s-dx, y+s-dx), outline=fill, width=width)
        d.ellipse((x+s*.38,y+s*.38,x+s*.62,y+s*.62), fill=fill)
    elif icon in ('leaf','moon'):
        d.ellipse((x,y,x+s,y+s), outline=fill, width=width); d.ellipse((x+s*.25,y-s*.05,x+s*1.15,y+s*.85), fill=(12,12,14))
    elif icon in ('chart','target'):
        d.rectangle((x,y+s*.65,x+s*.18,y+s), fill=fill); d.rectangle((x+s*.3,y+s*.38,x+s*.48,y+s), fill=fill); d.rectangle((x+s*.6,y+s*.15,x+s*.78,y+s), fill=fill)
    elif icon in ('briefcase','wallet'):
        d.rounded_rectangle((x,y+s*.25,x+s,y+s*.85), radius=int(s*.12), outline=fill, width=width); d.line((x+s*.35,y+s*.25,x+s*.35,y+s*.1,x+s*.65,y+s*.1,x+s*.65,y+s*.25), fill=fill, width=width)
    elif icon in ('dumbbell','bolt'):
        d.line((x+s*.2,y+s*.5,x+s*.8,y+s*.5), fill=fill, width=width*2); d.rectangle((x,y+s*.3,x+s*.18,y+s*.7), fill=fill); d.rectangle((x+s*.82,y+s*.3,x+s,y+s*.7), fill=fill)
    elif icon in ('coin','diamond'):
        d.ellipse((x,y,x+s,y+s), outline=fill, width=width); d.text((x+s*.35,y+s*.18),'€',fill=fill,font=font(int(s*.42), True))
    elif icon in ('heart','ring'):
        d.text((x,y),'♡',fill=fill,font=font(s, True))
    elif icon in ('rainbow','star'):
        d.arc((x,y,x+s,y+s),180,360,fill=fill,width=width); d.arc((x+s*.15,y+s*.15,x+s*.85,y+s*.85),180,360,fill=fill,width=width)
    elif icon in ('plane','compass','map','sun'):
        d.polygon([(x,y+s*.45),(x+s,y+s*.15),(x+s*.65,y+s*.55),(x+s*.78,y+s),(x+s*.45,y+s*.68),(x+s*.15,y+s*.85)], outline=fill, fill=None)
    else:
        d.rounded_rectangle((x,y,x+s,y+s), radius=int(s*.16), outline=fill, width=width); d.line((x+s*.22,y+s*.52,x+s*.42,y+s*.72,x+s*.8,y+s*.25), fill=fill, width=width)

def palette(data):
    return {'primary':hex_to_rgb(data.get('primary_color','#0b0b0d')), 'secondary':hex_to_rgb(data.get('secondary_color','#d4af37')), 'ink':(255,255,255), 'shadow':(0,0,0)}

def seo(data):
    pt, niche, market = data['product_type'], data['niche'], data['marketplace']
    title = f'{pt} {niche} Printable, Premium Digital Download, Instant PDF for {market}'[:135]
    desc = f'{pt} premium per {niche}: include copertina professionale, introduzione, istruzioni, sezioni complete, tracker, checklist, pagine bonus, mockup e file SEO. Prodotto digitale pronto per essere caricato e venduto su {market}.'
    seeds = [pt,niche,'printable','digital download','pdf planner','instant download','premium','minimal luxury','organizer','tracker','checklist','workbook','etsy printable','self care','small business']
    tags = []
    for s in seeds:
        t = s.lower()[:20]
        if t not in tags: tags.append(t)
    price = {'Etsy':'12.90','Creative Market':'24.00','Gumroad':'27.00','Payhip':'19.00','Shopify':'34.00'}.get(market,'19.00')
    return title, desc, tags[:13], price

def make_cover(path, data, w=1800, h=2400, config=None):
    cfg = config or {}; pal = palette(data); pc, sc = pal['primary'], pal['secondary']
    bg1 = hex_to_rgb(cfg.get('bg1', data.get('primary_color','#0b0b0d'))); bg2 = hex_to_rgb(cfg.get('bg2', '#1f1a10'))
    img = Image.new('RGB',(w,h), bg1); d = ImageDraw.Draw(img, 'RGBA')
    for y in range(h):
        t = y / h; col = tuple(int(bg1[i]*(1-t)+bg2[i]*t) for i in range(3)); d.line([(0,y),(w,y)], fill=col)
    rng = random.Random((data['name'] + data['product_type'] + str(cfg)) or datetime.now().isoformat())
    for i in range(42):
        x, y = rng.randint(-300,w), rng.randint(-300,h); r = rng.randint(80,460); alpha = rng.randint(18,65)
        d.ellipse((x,y,x+r,y+r), outline=(*sc, alpha), width=rng.randint(2,8))
    for i in range(90):
        x,y = rng.randint(0,w), rng.randint(0,h); d.point((x,y), fill=(255,255,255,rng.randint(20,70)))
    d.rounded_rectangle((115,120,w-115,h-120), radius=70, outline=(*sc,210), width=7)
    d.rounded_rectangle((155,165,w-155,h-165), radius=45, outline=(255,255,255,55), width=2)
    cat = data.get('category','Planner'); group = 'productivity'
    for key in ILLUSTRATIONS:
        if key.lower() in (cat + data.get('product_type','')).lower(): group = key
    if cat == 'Finanza': group='finance'
    if cat == 'Kids': group='kids'
    if cat == 'Fitness': group='fitness'
    if cat == 'Business': group='business'
    icons = ILLUSTRATIONS.get(group, ILLUSTRATIONS['productivity'])
    for i, ic in enumerate(icons * 3):
        x = 160 + (i % 4) * 380 + rng.randint(-30,30); y = 185 + (i // 4) * 520 + rng.randint(-30,30)
        draw_icon(d, ic, x, y, rng.randint(90,150), (*sc,125), 5)
    shadow = Image.new('RGBA',(w,h),(0,0,0,0)); sd=ImageDraw.Draw(shadow); sd.rounded_rectangle((250,570,w-250,1560), radius=80, fill=(0,0,0,125)); shadow=shadow.filter(ImageFilter.GaussianBlur(35)); img=Image.alpha_composite(img.convert('RGBA'), shadow)
    d = ImageDraw.Draw(img, 'RGBA')
    d.rounded_rectangle((230,530,w-230,1520), radius=80, fill=(255,255,255,235), outline=(*sc,180), width=4)
    title = cfg.get('title') or data['name']; subtitle = cfg.get('subtitle') or f"{data['product_type']} • {data['niche']}"
    d.text((300,675), title[:30], fill=(10,10,12), font=font(int(cfg.get('title_size',100)), True))
    d.text((305,820), subtitle[:48], fill=(*pc,235), font=font(int(cfg.get('subtitle_size',42))))
    d.line((305,930,w-305,930), fill=(*sc,220), width=5)
    for idx, label in enumerate(['INTRO','TRACKER','BONUS','CHECKLIST']):
        y = 1030 + idx * 100; d.rounded_rectangle((310,y,610,y+52), radius=26, fill=(*sc,210)); d.text((650,y+5), label, fill=(25,25,28), font=font(36, True))
    d.text((300,h-360), data['marketplace'].upper(), fill=(255,255,255,230), font=font(48, True))
    d.text((300,h-285), f"{data['pages']} pagine | {data['style']}", fill=(255,255,255,215), font=font(38))
    img.convert('RGB').save(path, 'PNG', quality=95)

def make_mockups(folder, cover, data):
    out=[]; cover_img=Image.open(cover).resize((460,613)).convert('RGBA'); pal=palette(data); sc=pal['secondary']
    scenes=[('tablet',(22,22,26)),('laptop',(238,235,228)),('printed sheets',(248,246,240)),('etsy preview',(245,241,232)),('pinterest bundle',(18,18,20))]
    for i,(scene,bgcol) in enumerate(scenes,1):
        bg=Image.new('RGB',(1600,1200),bgcol); d=ImageDraw.Draw(bg,'RGBA')
        d.rectangle((0,850,1600,1200), fill=(210,198,178,255) if i!=5 else (8,8,10,255))
        if scene=='tablet':
            d.rounded_rectangle((500,165,1100,985),45,fill=(8,8,12),outline=(*sc,255),width=5); bg.paste(cover_img,(570,235),cover_img)
        elif scene=='laptop':
            d.rounded_rectangle((360,140,1240,800),30,fill=(20,20,24)); bg.paste(cover_img.resize((350,466)),(625,235),cover_img.resize((350,466))); d.rounded_rectangle((270,805,1330,890),18,fill=(60,60,66))
        elif scene=='printed sheets':
            for off,ang in [(120,-7),(260,4),(420,-2)]: bg.paste(cover_img.rotate(ang,expand=True),(off,210),cover_img.rotate(ang,expand=True))
        elif scene=='etsy preview':
            d.rounded_rectangle((95,80,1505,1120),35,fill=(255,255,255),outline=(*sc,220),width=3); bg.paste(cover_img,(190,210),cover_img); d.text((760,270),data['name'],fill=(20,20,22),font=font(58,True)); d.text((760,355),'Instant digital download',fill=(95,95,95),font=font(34)); d.rounded_rectangle((760,460,1110,540),22,fill=(*sc,255)); d.text((800,478),'Premium Bundle',fill=(20,20,22),font=font(34,True))
        else:
            for n in range(4): bg.paste(cover_img.resize((330,440)).rotate([-6,3,7,-3][n],expand=True),(190+n*270,265+n*20),cover_img.resize((330,440)).rotate([-6,3,7,-3][n],expand=True))
        d.text((70,70),f'Mockup {i}: {scene.title()}',fill=(*sc,255),font=font(42,True))
        p=folder/f'mockup_{i}.png'; bg.save(p,'PNG',quality=95); out.append(p)
    return out

def schema_for(data): return SCHEMAS.get(data.get('category'), SCHEMAS['Planner'])
def para(text, style): return Paragraph(text.replace('&','&amp;'), style)

def make_table(headers, rows, pc):
    t = Table([headers] + rows, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pc),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#d8d2c4')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#fbf8f0')]),('FONT',(0,0),(-1,0),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('MINROWHEIGHT',(0,1),(-1,-1),10*mm)]))
    return t

def make_pdf(path, cover, data):
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=15*mm,bottomMargin=16*mm)
    styles=getSampleStyleSheet(); pc=colors.HexColor(data['primary_color']); sc=colors.HexColor(data['secondary_color'])
    styles.add(ParagraphStyle('GoldTitle',fontName='Helvetica-Bold',fontSize=22,textColor=pc,spaceAfter=9,leading=26))
    styles.add(ParagraphStyle('SmallMuted',fontName='Helvetica',fontSize=9,textColor=colors.HexColor('#555555'),leading=12))
    schema=schema_for(data); story=[RLImage(str(cover), width=150*mm, height=200*mm), PageBreak()]
    story += [para(data['name'],styles['GoldTitle']), para(schema['intro'],styles['BodyText']), Spacer(1,7), para('Indice',styles['Heading1'])]
    for i,s in enumerate(['Introduzione','Istruzioni'] + schema['sections'] + ['Pagine bonus','Riepilogo finale'],1): story.append(para(f'{i}. {s}', styles['Normal']))
    story += [PageBreak(), para('Introduzione',styles['GoldTitle']), para(schema['intro'] + ' Questo prodotto è progettato per essere stampato, compilato e riutilizzato come sistema pratico.',styles['BodyText']), Spacer(1,7), para('Istruzioni',styles['Heading2'])]
    for step in ['Definisci il risultato desiderato prima di compilare le pagine.','Compila i tracker con costanza e rivedi i dati ogni settimana.','Usa le pagine bonus per personalizzare il percorso e aumentare il valore percepito.']:
        story.append(para('• '+step, styles['Normal']))
    pages=max(1,int(data['pages'])); section_pages=max(1,pages-4)
    for p in range(section_pages):
        sec=schema['sections'][p % len(schema['sections'])]; story += [PageBreak(), para(sec,styles['GoldTitle']), para(f'Esercizio {p+1}: compila questa pagina per {data["niche"]} seguendo una logica chiara, misurabile e orientata al risultato.',styles['SmallMuted']), Spacer(1,6)]
        headers=schema['table']; rows=[]
        for r in range(8 if len(headers) > 3 else 10): rows.append([f'{sec} {r+1}'] + ['' for _ in headers[1:]])
        story.append(make_table(headers, rows, pc)); story.append(Spacer(1,8)); story.append(para('Esempio professionale: scegli una riga, aggiungi un dato concreto, stabilisci una micro-azione e rivedi il risultato nella pagina riepilogo.',styles['SmallMuted']))
    story += [PageBreak(), para('Pagine bonus',styles['GoldTitle'])]
    for b in schema['bonus']: story.append(para('✓ '+b, styles['Normal']))
    story += [Spacer(1,8), make_table(['Checklist','Fatto'], [[b,'□'] for b in schema['bonus']], pc), PageBreak(), para('Riepilogo finale',styles['GoldTitle']), para('Annota risultati, lezioni apprese, prossime azioni e opportunità di miglioramento. Questo riepilogo aumenta il valore pratico del prodotto e guida l’utente verso un risultato completo.',styles['BodyText']), Spacer(1,8), make_table(['Risultato','Lezione','Prossima azione'], [['','',''] for _ in range(8)], pc)]
    doc.build(story, onFirstPage=lambda c,d: footer(c,d,data), onLaterPages=lambda c,d: footer(c,d,data))

def footer(c,d,data):
    c.setStrokeColor(colors.HexColor(data['secondary_color'])); c.line(16*mm,12*mm,194*mm,12*mm); c.setFont('Helvetica',8); c.drawRightString(194*mm,8*mm,data['name'])

def form_data(src):
    cat=src.get('category','Planner')
    return {'name':src.get('name') or src.get('product_type','Digital Product'),'niche':src.get('niche','Productivity'),'language':src.get('language','Italiano'),'format':src.get('format','A4 PDF'),'pages':int(src.get('pages',24)),'primary_color':src.get('primary_color','#0b0b0d'),'secondary_color':src.get('secondary_color','#d4af37'),'font':src.get('font','Helvetica'),'style':src.get('style','Minimal Luxury'),'marketplace':src.get('marketplace','Etsy'),'category':cat,'product_type':src.get('product_type',PRODUCTS.get(cat,PRODUCTS['Planner'])[0])}

def build_product(data, existing_id=None, bundle_id=None, cover_config=None):
    title,desc,tags,price=seo(data); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'); fname=slug(data['name']+'-'+data['product_type']+'-'+now.replace(':','-'))
    folder=PROD/fname; folder.mkdir(parents=True,exist_ok=True)
    cover=folder/'cover.png'; make_cover(cover,data,config=cover_config)
    pdf=folder/(fname+'.pdf'); make_pdf(pdf,cover,data)
    mocks=make_mockups(folder,cover,data); preview=PREV/(fname+'_preview.png'); shutil.copyfile(mocks[3],preview)
    seo_path=folder/'seo.json'; seo_path.write_text(json.dumps({'title':title,'description':desc,'tags':tags,'category':data['category'],'price':price},ensure_ascii=False,indent=2),encoding='utf-8')
    readme=folder/'README.txt'; readme.write_text(f"DIGITALMINT AI\nProdotto: {data['name']}\nTipo: {data['product_type']}\nMarketplace: {data['marketplace']}\nContenuti: copertina, introduzione, istruzioni, sezioni complete, tracker, checklist, bonus, riepilogo finale.\nFile inclusi: PDF, cover PNG, 5 mockup PNG, anteprima, SEO, README.\nPrezzo consigliato: €{price}\n",encoding='utf-8')
    zip_path=folder/(fname+'.zip')
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in [pdf,cover,seo_path,readme,preview]+mocks: z.write(f,arcname=f.name)
    rec=(data['name'],data['niche'],data['language'],data['format'],int(data['pages']),data['primary_color'],data['secondary_color'],data['font'],data['style'],data['marketplace'],data['category'],data['product_type'],title,desc,json.dumps(tags),price,fname,str(folder),str(zip_path),str(preview),now,now,json.dumps([f'Generato {now}']),bundle_id,json.dumps(cover_config or {}))
    with conn() as c:
        if existing_id: c.execute('delete from products where id=?',(existing_id,))
        c.execute('insert into products(name,niche,language,format,pages,primary_color,secondary_color,font,style,marketplace,category,product_type,title_seo,description_seo,tags,price,file_name,folder,zip_path,preview_path,created_at,updated_at,history,bundle_id,cover_config) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',rec)
        return c.execute('select last_insert_rowid()').fetchone()[0]

def generate_bundle(data, count):
    bundle_id = 'bundle-' + datetime.now().strftime('%Y%m%d%H%M%S')
    cats=list(PRODUCTS.keys()); ids=[]
    for i in range(count):
        cat=cats[i % len(cats)]; pt=PRODUCTS[cat][i % len(PRODUCTS[cat])]
        item=dict(data); item.update({'name':f"{data['name']} Vol. {i+1}", 'category':cat, 'product_type':pt})
        ids.append(build_product(item,bundle_id=bundle_id,cover_config={'bg1':data['primary_color'],'bg2':'#21160b','title':item['name']}))
    return ids

@app.route('/',methods=['GET','POST'])
def index():
    if request.method=='POST':
        data=form_data(request.form); mode=request.form.get('mode','single')
        if mode.startswith('bundle'):
            ids=generate_bundle(data,int(mode.split('-')[1])); flash(f'Bundle generato con {len(ids)} prodotti.'); return redirect(url_for('library'))
        pid=build_product(data); flash('Prodotto generato con successo.'); return redirect(url_for('detail',pid=pid))
    with conn() as c: stats={'count':c.execute('select count(*) from products').fetchone()[0], 'space':sum(f.stat().st_size for f in PROD.rglob('*') if f.is_file())//1024}
    return render_template('index.html',products=PRODUCTS,marketplaces=MARKETPLACES,fonts=FONTS,styles=STYLES,stats=stats)
@app.route('/library')
def library():
    q=request.args.get('q',''); cat=request.args.get('category',''); market=request.args.get('marketplace','')
    sql='select * from products where name like ?'; args=[f'%{q}%']
    if cat: sql+=' and category=?'; args.append(cat)
    if market: sql+=' and marketplace=?'; args.append(market)
    sql+=' order by id desc'
    with conn() as c: rows=c.execute(sql,args).fetchall()
    return render_template('library.html',rows=rows,products=PRODUCTS,marketplaces=MARKETPLACES,q=q,cat=cat,market=market)
@app.route('/product/<int:pid>')
def detail(pid):
    with conn() as c: r=c.execute('select * from products where id=?',(pid,)).fetchone()
    return render_template('detail.html',r=r,tags=json.loads(r['tags']))
@app.route('/download/<int:pid>')
def download(pid):
    with conn() as c: r=c.execute('select zip_path from products where id=?',(pid,)).fetchone()
    return send_file(r['zip_path'],as_attachment=True)
@app.route('/preview/<int:pid>')
def preview(pid):
    with conn() as c: r=c.execute('select preview_path from products where id=?',(pid,)).fetchone()
    return send_file(r['preview_path'])
@app.route('/editor',methods=['GET','POST'])
def editor():
    if request.method == 'POST':
        data=form_data(request.form); cfg={k:request.form.get(k) for k in ['title','subtitle','bg1','bg2','title_size','subtitle_size']}
        filename=slug((cfg.get('title') or data['name'])+'-custom-cover')+'.png'; path=ASSETS/filename; make_cover(path,data,config=cfg)
        flash('Copertina esportata in PNG alta qualità.'); return render_template('editor.html',products=PRODUCTS,fonts=FONTS,styles=STYLES,export=url_for('static',filename='generated_assets/'+filename))
    return render_template('editor.html',products=PRODUCTS,fonts=FONTS,styles=STYLES,export=None)
@app.route('/regen/<int:pid>',methods=['POST'])
def regen(pid):
    with conn() as c: r=dict(c.execute('select * from products where id=?',(pid,)).fetchone())
    nid=build_product(r,cover_config=json.loads(r.get('cover_config') or '{}')); flash('Prodotto rigenerato.'); return redirect(url_for('detail',pid=nid))
@app.route('/duplicate/<int:pid>',methods=['POST'])
def dup(pid):
    with conn() as c: r=dict(c.execute('select * from products where id=?',(pid,)).fetchone())
    r['name']=r['name']+' Copy'; nid=build_product(r,cover_config=json.loads(r.get('cover_config') or '{}')); flash('Prodotto duplicato.'); return redirect(url_for('detail',pid=nid))
@app.route('/delete/<int:pid>',methods=['POST'])
def delete(pid):
    with conn() as c: r=c.execute('select folder from products where id=?',(pid,)).fetchone(); c.execute('delete from products where id=?',(pid,))
    if r and Path(r['folder']).exists(): shutil.rmtree(r['folder'],ignore_errors=True)
    flash('Prodotto eliminato.'); return redirect(url_for('library'))
@app.route('/types/<cat>')
def types(cat): return jsonify(PRODUCTS.get(cat,[]))

def open_browser(): webbrowser.open('http://127.0.0.1:5000')
if __name__=='__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN')!='true': threading.Timer(1.0,open_browser).start()
    app.run(host='127.0.0.1',port=5000,debug=False)
