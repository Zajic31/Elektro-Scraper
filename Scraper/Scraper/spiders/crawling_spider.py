from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json

class DatartSpider(CrawlSpider):
    name = "dtrspider"
    allowed_domains = ["datart.cz"]
    start_urls = ["https://www.datart.cz/"]

    rules = (
        Rule(LinkExtractor(allow=r".*lokator-apple.*"), callback="parse_item"),
        )

    def parse_item(self, response):

        data_attr = response.css(
            ".product-detail__bottom-bar.js-product-detail-bottom-bar::attr(data-gtm-data-product)").get()

        if data_attr:

            data_json = json.loads(data_attr.replace("&quot;", '"'))
            item_name = data_json.get("item_name")
        else:
            item_name = None

        yield {
            "title": item_name
        }