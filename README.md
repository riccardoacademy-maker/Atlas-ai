# DigitalMint AI

DigitalMint AI è un software Flask commerciale per generare prodotti digitali premium pronti alla vendita online. Crea PDF impaginati, copertine PNG, 5 mockup PNG, anteprima, metadati SEO, README e archivio ZIP finale.

## Avvio rapido

```bash
pip install -r requirements.txt
python app.py
```

L'app apre automaticamente `http://127.0.0.1:5000`.

Su Windows puoi avviare anche `AVVIA_WINDOWS.bat`.

## Funzioni incluse

- Generazione reale di prodotti digitali per Etsy, Creative Market, Gumroad, Payhip e Shopify.
- Categorie: Planner, Finanza, Fitness, Journal, Workbook, Business, Marketing, Kids, Cooking, Printable e Business Documents.
- PDF professionale con copertina, indice, pagine numerate e layout coerenti per categoria.
- Copertina e cinque mockup PNG generati con Pillow.
- SEO automatico: titolo, descrizione, 13 tag, categoria e prezzo consigliato.
- ZIP finale con PDF, cover, mockup, anteprima, SEO e README.
- Libreria SQLite con ricerca, filtri, download, rigenerazione, duplicazione, eliminazione, cronologia e statistiche.

## Struttura dati

I prodotti generati sono salvati in `storage/products`, le anteprime in `storage/previews` e il database in `storage/digitalmint.db`.
