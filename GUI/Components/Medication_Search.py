from bs4 import BeautifulSoup
import requests
import urllib3

urllib3.disable_warnings()

URL = "https://www.drugeye.pharorg.com/drugeyeapp/android-search/drugeye-android-live-go.aspx"

MEDICATION_SEARCH_CACHE = {}


def search_medications(keyword):

    keyword = (keyword or "").strip()

    if len(keyword) < 3:

        return []

    if keyword in MEDICATION_SEARCH_CACHE:

        return MEDICATION_SEARCH_CACHE[keyword]

    try:

        session = requests.Session()

        r = session.get(

            URL,

            verify=False,

            timeout=30

        )

        soup = BeautifulSoup(

            r.text,

            "html.parser"

        )

        payload = {

            "__VIEWSTATE":

            soup.find(

                "input",

                {

                    "name":

                    "__VIEWSTATE"

                }

            )["value"],

            "__VIEWSTATEGENERATOR":

            soup.find(

                "input",

                {

                    "name":

                    "__VIEWSTATEGENERATOR"

                }

            )["value"],

            "__EVENTVALIDATION":

            soup.find(

                "input",

                {

                    "name":

                    "__EVENTVALIDATION"

                }

            )["value"],

            "ttt":

            keyword,

            "b1":

            "search",

            "Passgenericname":

            ""

        }

        r = session.post(

            URL,

            data=payload,

            verify=False,

            timeout=30

        )

        soup = BeautifulSoup(

            r.text,

            "html.parser"

        )

        result_table = soup.find(

            "table",

            {

                "id":

                "MyTable"

            }

        )

        if not result_table:

            return []

        drugs = []

        for row in result_table.find_all("tr"):

            try:

                cells = row.find_all("td")

                if len(cells) != 2:

                    continue

                name_font = cells[0].find(

                    "font",

                    {

                        "color":

                        "Blue"

                    }

                )

                if not name_font:

                    continue

                drug_name = name_font.get_text(

                    strip=True

                )

                drugs.append(

                    drug_name

                )

            except:

                pass

        drugs = list(

            dict.fromkeys(

                drugs

            )

        )

        MEDICATION_SEARCH_CACHE[

            keyword

        ] = drugs

        return drugs

    except:

        return []