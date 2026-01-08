import scrapy
from whiskyscraper.items import WhiskyscraperItem
from urllib.parse import urljoin

class ArchiveSpider(scrapy.Spider):
    name = "archive_news"
    allowed_domains = ["nbcnews.com"]
    start_urls = ["https://www.nbcnews.com/archive"]

    def parse(self, response):
        """
        Entry point: Parses the main archive page to find Year links.
        Example URL: https://www.nbcnews.com/archive
        """
        # Select all month/year links from the archive page
        # Based on previous structure inspection, they look like /archive/articles/YYYY
        year_links = response.css('body').re(r'"(https://www.nbcnews.com/archive/articles/\d{4})"')
        
        # If regex doesn't catch them, try standard CSS (fallback based on standard sitemaps)
        if not year_links:
             year_links = response.css('a[href*="/archive/articles/"]::attr(href)').getall()

        for link in set(year_links):
            yield response.follow(link, callback=self.parse_year)

    def parse_year(self, response):
        """
        Parses a Year page to find Month links.
        Example URL: https://www.nbcnews.com/archive/articles/2024
        """
        # Links to months, e.g., /archive/articles/2024/january
        month_links = response.css('a[href*="/archive/articles/"]::attr(href)').getall()
        
        for link in set(month_links):
             # Ensure we don't go back up to the year or archive root if the structure is nested weirdly
             # Month links are typically longer than the current year link
             abs_link = urljoin(response.url, link)
             if len(abs_link) > len(response.url):
                yield response.follow(link, callback=self.parse_month)

    def parse_month(self, response):
        """
        Parses a Month page to find Article links.
        Example URL: https://www.nbcnews.com/archive/articles/2024/january
        """
        # Article links usually don't have 'archive' in the path, or they end in specific patterns
        # We look for links that look like articles.
        all_links = response.css('a::attr(href)').getall()
        
        for link in all_links:
            # Basic filter for article links vs navigation
            # NBC articles often have 'rcna' or 'ncna' + digits at the end, or are just standard news links
            if '/archive/' not in link and ('nbcnews.com' in link or link.startswith('/')):
                 # Make absolute if relative
                 abs_link = urljoin(response.url, link)
                 if 'nbcnews.com' in abs_link:
                    yield scrapy.Request(abs_link, callback=self.parse_article)

    def parse_article(self, response):
        """
        Extracts data from the article page.
        """
        # Skip if not an article (e.g. video page or category page that slipped through)
        if response.status != 200:
            return

        item = WhiskyscraperItem()
        item['link'] = response.url
        item['source'] = 'NBC News'

        # Title
        title = response.css('h1::text').get()
        if not title:
            title = response.css('article a, .headline a, h2 a, h3 a::text').get() # Fallback from news_spider
        if title:
            item['title'] = title.strip()

        # Date
        date = response.css('time::attr(datetime)').get()
        if not date:
            date = response.css('time::text').get()
        if date:
            item['date'] = date.strip()

        # Summary / Content
        # Trying a few common selectors for content text
        summary = response.css('p.lede::text, .article-body p:first-child::text').get()
        if not summary:
             summary = response.css('article p::text').get()
        
        if summary:
            item['summary'] = summary.strip()

        # Only yield if we have at least a title and link
        if item.get('title'):
            yield item
