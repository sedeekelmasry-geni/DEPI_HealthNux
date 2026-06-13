from nicegui import ui
import pandas as pd
import sys
sys.path.append("..")
from google.cloud import bigquery
from google.oauth2 import service_account
from Components.Navigation import navigation_bar
from Pages.Settings_Page.Dr_List_Tab import render_doctors_tab
from Pages.Settings_Page.Dr_Time_Table_Tab import render_timetable_tab
import Cache

SERVICE_ACCOUNT_FILE = "../Keys/BigQueryKey.json"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE
)

bq_client = bigquery.Client(
    credentials=credentials,
    project="depihealthnux"
)


def get_labs():

    if Cache.LABS_CACHE is None:

        print(
            'Loading Labs Cache...'
        )

        Cache.LABS_CACHE = pd.DataFrame()

    return Cache.LABS_CACHE

def get_scans():

    if Cache.SCANS_CACHE is None:

        Cache.SCANS_CACHE = pd.DataFrame()

    return Cache.SCANS_CACHE

@ui.page('/settings')
def settings_page():
    if Cache.CURRENT_USER is None:

        ui.navigate.to('/')

        return
    navigation_bar(
    active='settings'
    )
    with ui.column().classes(
    'w-full p-4 gap-4'
    ):

        ui.label(
            '⚙️ System Settings'
        ).classes(
            'text-4xl font-bold'
        )

        ui.label(
            'Master Data Configuration'
        ).classes(
            'text-gray-500 text-lg'
        )

        tabs = ui.tabs().classes(
            'w-full'
        )

    with tabs:

        tab_dr = ui.tab(
            '👨‍⚕️ Dr. List'
        )

        tab_timetable = ui.tab(
            '📅 Dr Timetable'
        )


    with ui.tab_panels(
        tabs,
        value=tab_dr
    ).classes(
        'w-full'
    ):

        with ui.tab_panel(tab_dr):

                render_doctors_tab()

        # =====================================================
        # TIMETABLE
        # =====================================================

        with ui.tab_panel(tab_timetable):

            render_timetable_tab()



    # =========================================
    # SCROLL TO TOP
    # =========================================

    ui.button(
        icon='keyboard_arrow_up',
        on_click=lambda:
        ui.run_javascript(
            '''
            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });
            '''
        )
    ).props(
        'round color=primary'
    ).style(
        '''
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 9999;
        '''
    )