import os, sqlite3, json, zipfile, shutil, math, random, webbrowser, threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

BASE=Path(__file__).parent.resolve(); STORE=BASE/'storage'; PROD=STORE/'products'; PREV=STORE/'previews'; DB=STORE/'digitalmint.db'
for p in (STORE,PROD,PREV): p.mkdir(parents=True,exist_ok=True)
app=Flask(__name__); app.secret_key='digitalmint-ai-local-premium'
MARKETPLACES=['Etsy','Creative Market','Gumroad','Payhip','Shopify']
PRODUCTS={
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
FONTS=['Helvetica','Times-Roman','Courier','Helvetica-Bold']; STYLES=['Minimal Luxury','Modern Editorial','Elegant Soft','Bold Premium','Clean Productivity']

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    with conn() as c:
        c.execute('''create table if not exists products(id integer primary key, name text, niche text, language text, format text, pages integer, primary_color text, secondary_color text, font text, style text, marketplace text, category text, product_type text, title_seo text, description_seo text, tags text, price text, file_name text, folder text, zip_path text, preview_path text, created_at text, updated_at text, history text)''')
init_db()

def slug(s):
    return ''.join(ch.lower() if ch.isalnum() else '-' for ch in s).strip('-').replace('--','-')[:80]

def hex_to_rgb(h):
    h=(h or '#d4af37').lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4)) if len(h)==6 else (212,175,55)

def text_lines(kind, niche, language):
    lang_it=language.lower().startswith('it')
    base={
      'Planner':['Visione','Priorità','Programma','Azioni','Riflessione'],
      'Journal':['Intenzione','Gratitudine','Pensieri','Lezioni','Prossimi passi'],
      'Workbook':['Obiettivo','Esercizio guidato','Strategia','Checklist','Implementazione'],
      'Finanza':['Entrate','Uscite','Risparmio','Debiti','Riepilogo'],
      'Kids':['Colora','Traccia','Conta','Osserva','Crea'],
      'Fitness':['Allenamento','Nutrizione','Idratazione','Progressi','Recupero']}
    en={k:['Vision','Priorities','Schedule','Actions','Reflection'] for k in base}
    return base.get(kind, ['Obiettivo','Note','Piano','Risultati','Revisione']) if lang_it else en.get(kind, ['Goal','Notes','Plan','Results','Review'])

def seo(data):
    pt=data['product_type']; niche=data['niche']; market=data['marketplace']
    title=f'{pt} {niche} Printable, Premium Digital Download for {market}'[:135]
    desc=f'Premium {pt} creato per la nicchia {niche}: PDF pronto alla vendita con copertina, pagine ordinate, mockup e file organizzati. Ideale per clienti che cercano un prodotto digitale elegante, stampabile e immediatamente utilizzabile su {market}.'
    seeds=[pt,niche,'printable','digital planner','pdf download','instant download','minimal','premium','organizer','template','editable style','gift','productivity','small business','modern']
    tags=[]
    for s in seeds:
        t=s.lower()[:20]
        if t not in tags: tags.append(t)
    price={'Etsy':'9.90','Creative Market':'17.00','Gumroad':'19.00','Payhip':'14.00','Shopify':'24.00'}.get(market,'12.00')
    return title,desc,tags[:13],price

def make_cover(path,data,w=1600,h=2200):
    pc=hex_to_rgb(data['primary_color']); sc=hex_to_rgb(data['secondary_color'])
    img=Image.new('RGB',(w,h),(8,8,10)); d=ImageDraw.Draw(img)
    for y in range(h):
        r=int(pc[0]*(1-y/h)+12*y/h); g=int(pc[1]*(1-y/h)+12*y/h); b=int(pc[2]*(1-y/h)+14*y/h); d.line([(0,y),(w,y)],fill=(r,g,b))
    rng=random.Random(data['name']+data['product_type']+str(datetime.now()))
    for i in range(18):
        x=rng.randint(-200,w); y=rng.randint(-200,h); rr=rng.randint(120,420)
        d.ellipse((x,y,x+rr,y+rr),outline=sc,width=rng.randint(3,8))
    try: f1=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',92); f2=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',42)
    except: f1=f2=None
    d.rounded_rectangle((120,150,w-120,h-150),radius=55,outline=sc,width=8)
    d.text((160,260),data['marketplace'].upper(),fill=(255,255,255),font=f2)
    d.text((160,760),data['name'][:24],fill=(255,255,255),font=f1)
    d.text((160,900),data['product_type'],fill=sc,font=f2)
    d.text((160,h-360),f"{data['pages']} pagine • {data['style']}",fill=(245,245,245),font=f2)
    img.save(path,'PNG')

def make_mockups(folder,cover,data):
    out=[]; cover_img=Image.open(cover).resize((520,715))
    for i in range(1,6):
        bg=Image.new('RGB',(1400,1000),(245,242,235) if i%2 else (18,18,20)); bg=bg.filter(ImageFilter.GaussianBlur(0))
        d=ImageDraw.Draw(bg); accent=hex_to_rgb(data['secondary_color'])
        d.rounded_rectangle((95,80,1305,920),35,fill=(255,255,255) if i%2 else (28,28,32),outline=accent,width=3)
        angle=[-8,-3,0,5,8][i-1]; c=cover_img.rotate(angle,expand=True,fillcolor=(0,0,0,0))
        bg.paste(c,(170+i*35,155),c if c.mode=='RGBA' else None)
        d.text((780,260),f'Mockup {i}',fill=accent)
        d.text((780,330),data['name'],fill=(20,20,20) if i%2 else (255,255,255))
        d.text((780,390),data['product_type'],fill=(90,90,90) if i%2 else (220,220,220))
        p=folder/f'mockup_{i}.png'; bg.save(p); out.append(p)
    return out

def make_pdf(path,cover,data):
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=16*mm,bottomMargin=16*mm)
    styles=getSampleStyleSheet(); pc=colors.HexColor(data['primary_color']); sc=colors.HexColor(data['secondary_color'])
    styles.add(ParagraphStyle('GoldTitle',fontName='Helvetica-Bold',fontSize=22,textColor=pc,spaceAfter=8))
    story=[RLImage(str(cover), width=150*mm, height=206*mm), PageBreak(), Paragraph(data['name'],styles['GoldTitle']),Paragraph(f"{data['product_type']} • {data['niche']}",styles['Heading2']),Spacer(1,8)]
    story.append(Paragraph('Indice',styles['Heading1'])); sections=text_lines(data['category'],data['niche'],data['language'])
    for i,s in enumerate(sections,1): story.append(Paragraph(f'{i}. {s}',styles['Normal']))
    story.append(PageBreak())
    pages=max(1,int(data['pages']))
    for p in range(1,pages+1):
        title=sections[(p-1)%len(sections)]
        story.append(Paragraph(title,styles['GoldTitle']))
        rows=[]
        if data['category']=='Finanza' or 'Budget' in data['product_type']:
            rows=[['Voce','Previsto','Reale','Note']]+[['','€','€',''] for _ in range(12)]
        elif data['category']=='Kids' or 'Coloring' in data['product_type']:
            rows=[['Attività creativa', 'Spazio completamento']]+[[f'Esercizio {i}',''] for i in range(1,9)]
        elif data['category']=='Journal':
            rows=[['Prompt','Risposta']]+[[q,''] for q in ['Oggi apprezzo','Ho imparato','Domani scelgo','Una nota gentile']]
        else:
            rows=[['Area','Dettagli','Completato']]+[[s,'','□'] for s in sections]
        t=Table(rows,colWidths=[50*mm,75*mm,35*mm] if len(rows[0])==3 else None,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pc),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.4,colors.lightgrey),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#faf7ef')]),('FONT',(0,0),(-1,0),'Helvetica-Bold'),('VALIGN',(0,0),(-1,-1),'TOP'),('MINROWHEIGHT',(0,1),(-1,-1),12*mm)]))
        story += [Paragraph(f'Pagina {p} di {pages}',styles['Normal']),Spacer(1,8),t]
        if p<pages: story.append(PageBreak())
    doc.build(story, onFirstPage=lambda c,d: footer(c,d,data), onLaterPages=lambda c,d: footer(c,d,data))

def footer(c,d,data):
    c.setStrokeColor(colors.HexColor(data['secondary_color'])); c.line(18*mm,12*mm,192*mm,12*mm); c.setFont('Helvetica',8); c.drawRightString(192*mm,8*mm,data['name'])

def build_product(data, existing_id=None):
    title,desc,tags,price=seo(data); now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'); fname=slug(data['name']+'-'+data['product_type']+'-'+now.replace(':','-'))
    folder=PROD/fname; folder.mkdir(parents=True,exist_ok=True)
    cover=folder/'cover.png'; make_cover(cover,data)
    pdf=folder/(fname+'.pdf'); make_pdf(pdf,cover,data)
    mocks=make_mockups(folder,cover,data)
    preview=PREV/(fname+'_preview.png'); shutil.copyfile(mocks[0],preview)
    seo_path=folder/'seo.json'; seo_path.write_text(json.dumps({'title':title,'description':desc,'tags':tags,'category':data['category'],'price':price},ensure_ascii=False,indent=2),encoding='utf-8')
    readme=folder/'README.txt'; readme.write_text(f"DIGITALMINT AI\nProdotto: {data['name']}\nTipo: {data['product_type']}\nMarketplace: {data['marketplace']}\nFile inclusi: PDF, cover PNG, 5 mockup PNG, anteprima, SEO.\nPrezzo consigliato: €{price}\n",encoding='utf-8')
    zip_path=folder/(fname+'.zip')
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in [pdf,cover,seo_path,readme,preview]+mocks: z.write(f,arcname=f.name)
    rec=(data['name'],data['niche'],data['language'],data['format'],int(data['pages']),data['primary_color'],data['secondary_color'],data['font'],data['style'],data['marketplace'],data['category'],data['product_type'],title,desc,json.dumps(tags),price,fname,str(folder),str(zip_path),str(preview),now,now,json.dumps([f'Generato {now}']))
    with conn() as c:
        if existing_id:
            c.execute('delete from products where id=?',(existing_id,))
        c.execute('insert into products(name,niche,language,format,pages,primary_color,secondary_color,font,style,marketplace,category,product_type,title_seo,description_seo,tags,price,file_name,folder,zip_path,preview_path,created_at,updated_at,history) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',rec)
        return c.execute('select last_insert_rowid()').fetchone()[0]

def form_data(src):
    cat=src.get('category','Planner'); return {'name':src.get('name') or src.get('product_type','Digital Product'),'niche':src.get('niche','Productivity'),'language':src.get('language','Italiano'),'format':src.get('format','A4 PDF'),'pages':int(src.get('pages',24)),'primary_color':src.get('primary_color','#0b0b0d'),'secondary_color':src.get('secondary_color','#d4af37'),'font':src.get('font','Helvetica'),'style':src.get('style','Minimal Luxury'),'marketplace':src.get('marketplace','Etsy'),'category':cat,'product_type':src.get('product_type',PRODUCTS.get(cat,PRODUCTS['Planner'])[0])}

@app.route('/',methods=['GET','POST'])
def index():
    if request.method=='POST':
        pid=build_product(form_data(request.form)); flash('Prodotto generato con successo.'); return redirect(url_for('detail',pid=pid))
    with conn() as c:
        stats={'count':c.execute('select count(*) from products').fetchone()[0], 'space':sum(f.stat().st_size for f in PROD.rglob('*') if f.is_file())//1024}
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
@app.route('/regen/<int:pid>',methods=['POST'])
def regen(pid):
    with conn() as c: r=dict(c.execute('select * from products where id=?',(pid,)).fetchone())
    nid=build_product(r); flash('Prodotto rigenerato.'); return redirect(url_for('detail',pid=nid))
@app.route('/duplicate/<int:pid>',methods=['POST'])
def dup(pid):
    with conn() as c: r=dict(c.execute('select * from products where id=?',(pid,)).fetchone())
    r['name']=r['name']+' Copy'; nid=build_product(r); flash('Prodotto duplicato.'); return redirect(url_for('detail',pid=nid))
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
