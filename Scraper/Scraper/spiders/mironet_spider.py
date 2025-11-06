from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json

class MironetSpider(CrawlSpider):
    name = "mironetspider"
    allowed_domains = ["mironet.cz"]
    start_urls = ["https://www.mironet.cz/"]
