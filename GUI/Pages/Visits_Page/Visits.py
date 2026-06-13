from nicegui import ui
import pandas as pd
import sys
sys.path.append("..")
from google.cloud import bigquery
from google.oauth2 import service_account
from Components.Navigation import navigation_bar
from Pages.Visits_Page.Available_Visits_Tab import render_available_visits_tab
from Pages.Visits_Page.Booked_Visits_Tab import render_booked_visits_tab
import Cache


@ui.page('/visits')
def visits_page():
    if Cache.CURRENT_USER is None:

        ui.navigate.to('/')

        return


    navigation_bar(
    active='visits'
    )
    role = Cache.CURRENT_USER["role"]
    is_doctor = role == "Doctor"

    with ui.column().classes(
    'w-full p-4 gap-4'
    ):
        tabs = ui.tabs().classes(
            'w-full'
        )

    with tabs:

        if not is_doctor:

            tab_ava_visits = ui.tab(
                '🕒 Available Visits'
            )

        tab_book_visits = ui.tab(
            '📅 Booked Visits'
        )


    default_tab = (

        tab_book_visits

        if is_doctor

        else tab_ava_visits

    )

    with ui.tab_panels(
        tabs,
        value=default_tab
    ).classes(
        'w-full'
    ):

        if not is_doctor:

            with ui.tab_panel(tab_ava_visits):

                render_available_visits_tab()


        with ui.tab_panel(tab_book_visits):

            render_booked_visits_tab()


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