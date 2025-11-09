from scrapy.spiders import Spider
from urllib.parse import urljoin, urlparse, parse_qs, urlunparse
from scrapy.http import Request

class PlaneoSpider(Spider):
    name = "planeospider"
    allowed_domains = ["planeo.cz"]
    
    # přepínání stránek pro zobrazení víc produktů
    OFFSET_STEP = 24

    # učení odkud budeme scrapovat
    start_urls = [
        "https://www.planeo.cz/velke-domaci-spotrebice",
        "https://www.planeo.cz/tv-foto-audio-video",
        "https://www.planeo.cz/mobily-a-chytre-hodinky",
        "https://www.planeo.cz/notebooky-pocitace-a-tablety",
        "https://www.planeo.cz/male-domaci-spotrebice",
        "https://www.planeo.cz/dilna-a-zahrada",
        "https://www.planeo.cz/herni-konzole-zabava-media",
        "https://www.planeo.cz/osvetleni",
        "https://www.planeo.cz/dum-a-domaci-potreby",
        "https://www.planeo.cz/vyhodne-sety",
        "https://www.planeo.cz/hracky",
        "https://www.planeo.cz/chytra-domacnost",
        "https://www.planeo.cz/sport-a-outdoor",
        "https://www.planeo.cz/multifunkcni-prislusenstvi",
        "https://www.planeo.cz/nabytek",
        "https://www.planeo.cz/auto-moto",
        "https://www.planeo.cz/hodinky-a-hodiny",
        "https://www.planeo.cz/hudebni-nastroje",
        "https://www.planeo.cz/kancelar-a-papirnictvi",
        "https://www.planeo.cz/potraviny",
        "https://www.planeo.cz/chovatelske-potreby",
        "https://www.planeo.cz/drogerie",
        "https://www.planeo.cz/dtest"
    ]

    def parse(self, response):
        # Extrakce produktů 
        product_tiles = response.css('.c-product--catalogue[data-gtm-product-id]')
        
        if not product_tiles:
            # Pokud na stránce nejsou produkty, ukončíme stránkování pro tuto kategorii
            self.logger.info(f"Stránkování dokončeno na URL: {response.url} (Nenalezeny žádné produkty/dlaždice)")
            return
        
        # Extrakce dat
        for tile in product_tiles:
            item_name = tile.attrib.get('data-gtm-product-name')
            item_price_gross = tile.attrib.get('data-gtm-product-price')
            item_category_raw = tile.attrib.get('data-gtm-product-item-category')
            item_brand = tile.attrib.get('data-gtm-product-brand')
            link_path = tile.css('a::attr(href)').get()
            
            item_link = urljoin(response.url, link_path) if link_path else None
            rating_value = tile.css('span[data-testid="catalogue.item.rating.value-rating"]::text').get()
            
            item_rating = float(rating_value.replace(',', '.')) if rating_value else None
            item_price = float(item_price_gross) if item_price_gross else None

            # --- VÝSLEDKOVÝ YIELD ---
            if item_name and item_price is not None and item_link:
                yield {
                    "title": item_name.strip(),
                    "price": item_price,
                    "link": item_link,
                    "rating": item_rating,
                    "category": item_category_raw
                }
                
        # Navigace na další stránku (STRÁNKOVÁNÍ POMOCÍ INKREMENTACE OFFSETU)
        
        # Zjistíme aktuální URL
        current_url = response.url
        
        # Rozparsujeme URL, abychom zjistili aktuální offset
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)
        
        # Zjistíme aktuální offset nebo nastavíme na 0
        current_offset = 0
        if 'offset' in query_params:
            try:
                current_offset = int(query_params['offset'][0])
            except ValueError:
                current_offset = 0 # Pokud je offset vadný, začneme od nuly

        # Vypočítáme nový offset
        new_offset = current_offset + self.OFFSET_STEP
        
        # Vytvoříme novou URL s novým offsetem
        query_params['offset'] = [str(new_offset)]
        
        # Znovu sestavíme query string a celou URL
        new_query = "&".join([f"{k}={v[0]}" for k, v in query_params.items()])
        
        # Vytvoříme novou URL (schéma, netloc, path, params, query, fragment)
        next_page_url = urlunparse(parsed_url._replace(query=new_query))
        
        self.logger.info(f"Vytvářím odkaz na další stránku: {next_page_url}")
        
        # Pokračujeme na novou URL
        # Použijeme Request, abychom se vyhnuli chybám v response.follow
        yield Request(url=next_page_url, callback=self.parse)