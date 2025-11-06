from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json

class DatartSpider(CrawlSpider):
    name = "dtrspider"
    allowed_domains = ["datart.cz"]
    start_urls = ["https://www.datart.cz/"]

    rules = (
        Rule(LinkExtractor(allow=(r"/[a-z0-9-]+\.html($|\?.+$)", r"/[a-z0-9-]+/strana-[0-9]+\.html$"), deny=(r"-[0-9a-z]{5,}\.html$", r".*/vyprodej-poslednich-kusu\.html")), callback="parse_list", follow=True),
    )
    
    def parse_list(self, response):
        # aplikuje se na vsechny produkty v ramci html kodu
        product_boxes = response.css(".product-box") 

        if not product_boxes:
            return

        for product_box in product_boxes:
            

            data_attr = product_box.css("::attr(data-gtm-data-product)").get()
            item_name = None
            item_price = None
            item_link = None
            item_rating = None
            item_category = None

            # extrakt jmena
            if data_attr:
                try:
                    data_json = json.loads(data_attr.replace("&quot;", '"'))
                    item_name = data_json.get("item_name")
                    full_category = data_json.get("item_category")

                    if full_category:
                        segments = [s.strip() for s in full_category.split('/') if s.strip()]
                        if segments:
                             item_category = segments[-1]
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to decode JSON for a product box.")
                    pass
            # extrakt ceny
            item_price = product_box.css('[data-product-price]::attr(data-product-price)').get()

            # extrakt linku na produkt
            item_link = product_box.css('a::attr(href)').get()
            if item_link:
                item_link = response.urljoin(item_link)

            # extrakt hodnoceni
            item_rating = product_box.css('.rating-wrap span.bold::text').get()
            if item_rating:
                item_rating = item_rating.strip()
            
            
            

            # vysledny yield
            if item_name:
                yield_item = {
                    "title": item_name
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

                yield yield_item