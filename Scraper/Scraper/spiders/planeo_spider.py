from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json

class PlaneoSpider(CrawlSpider):
    name = "planeospider"
    allowed_domains = ["planeo.cz"]
    start_urls = ["https://www.planeo.cz/"]
