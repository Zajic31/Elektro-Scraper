from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json

class DatartSpider(CrawlSpider):
    name = "dtrspider"
    allowed_domains = ["datart.cz"]
    start_urls = ["https://www.datart.cz/"]

    rules = (
        Rule(LinkExtractor(allow=(r"/[a-z0-9-]+\.html$", r"/[a-z0-9-]+/strana-[0-9]+\.html$"), deny=(r"-[0-9a-z]{5,}\.html$")), callback="parse_list", follow=True),
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

            # extrakt jmena
            if data_attr:
                try:
                    data_json = json.loads(data_attr.replace("&quot;", '"'))
                    item_name = data_json.get("item_name")
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to decode JSON for a product box.")
                    pass
            # extrakt ceny
            item_price = product_box.css('[data-product-price]::attr(data-product-price)').get()

            # vysledny yield
            if item_name:
                yield_item = {
                    "title": item_name
                }
                
                # pokud extraknul cenu, prida se cena do yieldu
                if item_price:
                    yield_item["price"] = item_price
                
                yield yield_item