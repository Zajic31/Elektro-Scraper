import scrapy
import json


class MironetSpider(scrapy.Spider):
    name = "mironetspider"
    allowed_domains = ["mironet.cz"]

    # Základní URL kategorie – startujeme z REST API, ne z HTML
    category_id = 10737  # mobilní telefony
    base_api = "https://www.mironet.cz/rest/produkt/list/?categoryId={cat}&page={page}&limit=50"

    def start_requests(self):
        """Spouští první požadavek (stránka 1)."""
        start_url = self.base_api.format(cat=self.category_id, page=1)
        yield scrapy.Request(start_url, callback=self.parse)

    def parse(self, response):
        """Zpracuje JSON s produkty a stránkováním."""
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"❌ Neplatný JSON na URL: {response.url}")
            return

        # Seznam produktů
        products = data.get("produkty") or data.get("data") or []

        if not products:
            self.logger.warning(f"⚠️ Žádné produkty na {response.url}")
            return

        for p in products:
            yield {
                "title": p.get("nazev") or p.get("title"),
                "price": p.get("cena_s_dph") or p.get("price"),
                "link": response.urljoin(p.get("url") or ""),
                "category": p.get("kategorie_nazev") or "Mobilní telefony",
                "availability": p.get("dostupnost_text"),
            }

        # Stránkování
        current_page = data.get("page") or 1
        total_pages = data.get("totalPages") or data.get("pocet_stran") or 1

        if current_page < total_pages:
            next_page = current_page + 1
            next_url = self.base_api.format(cat=self.category_id, page=next_page)
            self.logger.info(f"➡️ Načítám stránku {next_page}/{total_pages}")
            yield scrapy.Request(next_url, callback=self.parse)
        else:
            self.logger.info(f"✅ Stránkování dokončeno ({current_page}/{total_pages})")
