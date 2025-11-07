from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json 
# json je zde ponechán pro konzistenci s dtrspider

class MironetSpider(CrawlSpider):
    name = "mironetspider"
    allowed_domains = ["mironet.cz"]
    # 🎯 DOČASNÁ ZMĚNA PRO TESTOVÁNÍ: Startujeme přímo na stránce kategorie s produkty.
    start_urls = ["https://www.mironet.cz/telefony/mobilni-telefony+c10737/"] 
    # Po ověření funkčnosti vraťte na: start_urls = ["https://www.mironet.cz/telefony/mobilni-telefony+c10737/"]

    rules = (
        # Povoluje stránky jako /telefony/mobilni-telefony+c10737/ a stránkování (?page=X)
        Rule(LinkExtractor(allow=(r"/[a-z0-9-]+\+c[0-9]+/?($|\?.+$)", r"/[a-z0-9-]+/?($|\?.+$)")), 
             callback="parse_list", 
             follow=True),
    )
    
    def parse_list(self, response):
        # Tato kontrola zde není specificky nutná (jako u Datartu), ale ponechána pro případné budoucí blokování
        # if "/nechtena-stranka.html" in response.url:
        #     self.logger.info(f"Ignoruji nechtenou stranku: {response.url}")
        #     return
            
        # aplikuje se na vsechny produkty v ramci html kodu
        # 🎯 Selektor: Najdeme všechny kontejnery, které obsahují název produktu
        product_names_divs = response.css('div.nazev')

        if not product_names_divs:
            self.logger.warning(f"Na stránce {response.url} nebyly nalezeny žádné prvky s názvem produktu (div.nazev).")
            return

        for name_div in product_names_divs:
            
            # 🎯 OPRAVENÝ ANCESTOR/RODIČ: Hledáme nejbližšího společného PŘEDKA s třídou, 
            # která obvykle obaluje produktový box.
            product_box = name_div.xpath('./ancestor::div[@class="product-wrap" or @class="item-large-screen" or @class="item-box" or @class="product-box"]')
            
            if not product_box:
                continue 
            
            product_box = product_box[0] 
            
            # Inicializace polí
            item_name = None
            item_price = None
            item_link = None
            item_rating = None
            item_category = None

            # --- EXTRAKCE ---

            # extrakt linku a jmena z hlavního <a> tagu
            name_link_tag = name_div.css('a') # Hledáme <a> v div.nazev
            
            # extrakt jmena
            if name_link_tag:
                item_name = name_link_tag.css('::text').get()
            
            # extrakt ceny
            # Hledáme uvnitř nalezeného 'product_box'
            price_text = product_box.css('.item-cena .item-b-cena::text').get()
            if price_text:
                # Odstraní měnu, mezery a převede na číslo
                item_price = price_text.replace(' Kč', '').replace(' ', '').strip()
                try:
                    item_price = float(item_price)
                except ValueError:
                    item_price = None 
            
            # extrakt linku na produkt
            if name_link_tag:
                item_link = name_link_tag.css('::attr(href)').get()
                if item_link:
                    item_link = response.urljoin(item_link.strip())

            # extrakt hodnoceni (Není dostupné přes jednoduché CSS, proto None)
            item_rating = None
            
            # extrakt kategorie (Není dostupné přes GTM JSON, proto None)
            item_category = None


            # --- VÝSLEDKOVÝ YIELD ---
            # vysledny yield
            if item_name and item_price is not None:
                yield_item = {
                    "title": item_name.strip()
                }
                
                # pokud extraknul cenu, prida se cena do yieldu
                if item_price:
                    yield_item["price"] = item_price
                
                # pokud extraknul link na produkt, prida se cena do yieldu
                if item_link:
                    yield_item["link"] = item_link

                # pokud extraknul hodnoceni, prida se cena do yieldu
                if item_rating:
                    yield_item["rating"] = item_rating
                
                # pokud extraknul kategorii, prida se cena do yieldu
                if item_category:
                    yield_item["category"] = item_category
                
                # Zajištění, že se do yieldu dostanou i prázdná/None pole
                if 'rating' not in yield_item:
                    yield_item['rating'] = None
                if 'category' not in yield_item:
                    yield_item['category'] = None

                yield yield_item