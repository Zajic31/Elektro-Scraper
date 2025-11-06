from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json

class SmartySpider(CrawlSpider):
    name = "smartyospider"
    allowed_domains = ["smarty.cz"]
    start_urls = ["https://www.smarty.cz/"]
