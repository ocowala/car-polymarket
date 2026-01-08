import scrapy

class WhiskyscraperItem(scrapy.Item):
    title = scrapy.Field()
    link = scrapy.Field()
    source = scrapy.Field()
    date = scrapy.Field()
    summary = scrapy.Field()
