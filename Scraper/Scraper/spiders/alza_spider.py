from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json

class AlzaSpider(CrawlSpider):
    name = "alzaspider"
    allowed_domains = ["alza.cz"]
    start_urls = ["https://www.alza.cz/"]
