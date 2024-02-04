
import scrapy
from scrapy.exceptions import CloseSpider
import json
import re
import logging

def no_accent_vietnamese(s):
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ]', 'A', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ÌÍỊỈĨ]', 'I', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ƯỪỨỰỬỮÙÚỤỦŨ]', 'U', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[ỲÝỴỶỸ]', 'Y', s)
    s = re.sub(r'[Đ]', 'D', s)
    s = re.sub(r'[đ]', 'd', s)
    #ư = u + u'\u031b'
    #ơ = o + u'\u031b'
    special_char = u'\u031b'
    marks_list = [special_char, u'\u0300', u'\u0301', u'\u0302', u'\u0303', u'\u0306',u'\u0309', u'\u0323']

    for mark in marks_list:
        s = s.replace(mark, '')

    return s


class CovidSpider(scrapy.Spider):
    name = 'covid'
    allowed_domains = ['web.archive.org']
    start_urls = ['https://web.archive.org/web/20210501070355/https://ncov.moh.gov.vn/vi/web/guest/dong-thoi-gian?p_p_id=com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_nf7Qy5mlPXqs&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_nf7Qy5mlPXqs_delta=10&p_r_p_resetCur=false&_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_nf7Qy5mlPXqs_cur=1']

    STEP = 1
    CUR_PAGE = 1

    def start_requests(self):
        # Xử lý trang đầu tiên trước khi bắt đầu crawl các trang khác
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # Chech stop point
        if response.xpath("//div[@id='livewebInfo']/p[1]/text()").get() == 'This page is not available on the web':
            raise CloseSpider('NO MORE!')
        
        # Xử lý thông tin trang hiện tại ở đây

        dates = response.xpath("//div[contains(@class,'timeline-detail')]")
        for date in dates:
            try:
                # NAV(date) bi loi

                # Lay thoi gian
                time = date.xpath(".//div[1]/h3/text()").get()
                
                # Lay tong so ca nhiem moi, trong the <p> thu 2
                p2 = date.xpath(".//div[2]/p[2]/text()").get()

                # So ca nhiem tung thanh pho, trong the <p> thu 3
                p3 = date.xpath(".//div[2]/p[3]/text()").get()

                # Doi khi khong co the <p> thu 3, so ca nhiem tung thanh pho nam trong <p> thu 2, nen em ket hop p2 va p3
                # NAV() da duoc chinh sua de loai bo them ki tu dac biet \u031b
                content = no_accent_vietnamese(p2 + p3) if p3 else no_accent_vietnamese(p2)
                new_case = re.search(r' (\d+(\.\d+)?) CA MAC MOI', content, re.IGNORECASE).group(1)
                
                # Tim cac theo format: "<ten tinh/thanh pho> (<so ca nhiem>)"
                # (TP.) la danh rieng cho HCM
                # [A-Z]{1}[a-z]+ la 1 tu trong ten tinh/thanh pho, gom 1 chu in hoa va nhieu chu thuong
                # (- )* de match duoc tinh Ba Ria - Vung Tau
                # \((\d+)\) de match duoc so ca nhiem moi nhu: (5), (25),...
                cities = re.findall(r"((TP. )*([A-Z]{1}[a-z]+ (- )*)+)\(([\d\.]+)\)", content)

                
                # Truong hop tat so ca nhiem moi o cung 1 tinh/thanh pho
                # Tim theo format: "tai <ten tinh/thanh pho>."
                # regex duoc chinh sua 1 chut de phu hop.
                if len(cities) == 0:
                    cities = re.findall(r"tai(( TP.)*(( -)* [A-Z]{1}[a-z]+)+)\.", content)
                    # convert phan tu duy nhat trong cities sang list, de them duoc so ca nhiem
                    logging.info(cities)
                    cities = [list(cities[0])]
                    cities[0].append(new_case)

                yield {
                    "time": time,
                    "newcase": int(new_case),
                    # city[0] la group 1 trong regex, chua ten tinh/thanh pho. 
                    # city[-1] la group cuoi trong regex, chua so ca nhiem moi.
                    "city_case": [{"city": city[0].strip(), "case": int(city[-1])} for city in cities]
                }
            except:
                logging.info(f'{time}: No info in this piece of data.')
            
        # Kiểm tra xem có đủ trang để crawl chưa
        self.CUR_PAGE += self.STEP

        next_page_url = f'https://web.archive.org/web/20210501070355/https://ncov.moh.gov.vn/vi/web/guest/dong-thoi-gian?p_p_id=com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_nf7Qy5mlPXqs&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_nf7Qy5mlPXqs_delta=10&p_r_p_resetCur=false&_com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_nf7Qy5mlPXqs_cur={self.CUR_PAGE}'
        yield scrapy.Request(url=next_page_url, callback=self.parse)



