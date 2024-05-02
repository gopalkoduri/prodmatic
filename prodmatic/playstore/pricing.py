import csv
import json
from decimal import Decimal

import requests
from bs4 import BeautifulSoup

from ..base.pricing import StorePricing


class PlayStorePricing(StorePricing):
    def __init__(self, geo_utils=None):
        super().__init__()
        self.fetch_country_to_store_currency_map()
        self.load_country_to_reference_rounded_prices(
            store_reference_prices_file="resources/playstore_reference_prices.csv"
        )

    def load_country_to_reference_rounded_prices(self, store_reference_prices_file):
        with open(store_reference_prices_file, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.map_country_to_reference_rounded_price[row["Country"]] = Decimal(int(row["Price"])) / 1000000

    def fetch_country_to_store_currency_map(self):
        """Process HTML tables to extract and transform data according to the rules."""
        data_sources = json.load(open("resources/data_sources.json"))
        region_currency_reference_url = data_sources["playstore_region_currency_reference"]
        response = requests.get(region_currency_reference_url).text
        soup = BeautifulSoup(response, "html.parser")

        tables = soup.find_all("table", class_="nice-table")

        self.map_country_to_store_currency = {}
        headers = (
            []
        )  # will be 4 items - Location, Download free apps, Make Google Play purchases and Buyer Currency and Price Range

        for index, table in enumerate(tables[:3]):
            rows = table.find_all("tr")
            if index == 0:
                # First row of the first table as header
                headers = [th.get_text().strip() for th in rows[0].find_all("th")]
                rows = rows[1:]  # Exclude the header row from data processing

            for row in rows:
                cols = row.find_all("td")
                if not cols:
                    continue  # skip rows without table data cells

                # Filter based on text color in the third column
                third_col_span = cols[2].find("span")
                if third_col_span and third_col_span.get("class"):
                    if "green-text" not in third_col_span.get("class"):
                        continue  # Exclude rows without check mark

                # Create a list of column values
                row_data = [col.get_text().strip() for i, col in enumerate(cols)]

                # Extract only the capital letters from the fourth column
                if len(row_data) > 3:
                    currency = "".join([c for c in row_data[3] if c.isupper()])
                    row_data[3] = currency

                entry = dict(zip(headers, row_data))
                country = self.countries_api.search_countries(entry["Location"])[0]
                iso_code = country.cca2

                entry_clean = {
                    "country": entry["Location"],
                    "iso2_code": iso_code,
                    "store_currency": entry["Buyer Currency and Price Range"],
                }
                self.map_country_to_store_currency[iso_code] = entry
