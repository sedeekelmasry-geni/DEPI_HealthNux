from nicegui import ui
import Pages.Patients_List
from Components.Navigation import navigation_bar
import Pages.Settings_Page.Settings
import Pages.Visits_Page.Visits
from Pages.Settings_Page.Dr_List_Tab import render_doctors_tab
from Pages.Settings_Page.Dr_List_Tab import get_doctors
import Cache

@ui.page('/home')

def home_page():
    if Cache.CURRENT_USER is None:

        ui.navigate.to('/')

        return
    # =====================================================
    # PAGE STYLE
    # =====================================================

    ui.query('body').style(
        '''
        background:
        linear-gradient(
            135deg,
            #f5f7fb 0%,
            #eef4ff 100%
        );
        '''
    )

    # =====================================================
    # NAVIGATION FUNCTIONS
    # =====================================================

    def open_patients():

        ui.navigate.to(
            '/patients'
        )

    def open_visits():

        ui.navigate.to(
            '/visits'
        )

    def open_payments():

        ui.notify(
            'Payments Page Coming Soon'
        )

    def open_settings():

        ui.navigate.to(
            '/settings'
        )

    # =====================================================
    # MAIN PAGE
    # =====================================================

    with ui.column().classes(
        'w-full items-center justify-center'
    ).style(
        'min-height:100vh'
    ):

        ui.icon(
            'local_hospital'
        ).classes(
            'text-8xl text-blue-600'
        )

        ui.label(
            'DEPI HealthNux'
        ).classes(
            'text-6xl font-bold'
        )

        ui.label(
            'Clinic Management Platform'
        ).classes(
            'text-xl text-gray-500 mb-8'
        )
        ui.label(
            f'Welcome {Cache.CURRENT_USER["email"]}'
        )
        with ui.row().classes(
            'justify-center gap-8 flex-wrap'
        ):

            # =====================================================
            # PATIENTS
            # =====================================================

            with ui.card().classes(
                '''
                w-72
                h-56
                rounded-3xl
                shadow-lg
                cursor-pointer
                hover:shadow-2xl
                transition
                items-center
                justify-center
                '''
            ).on(
                'click',
                open_patients
            ):

                ui.icon(
                    'people'
                ).classes(
                    'text-7xl text-blue-600'
                )

                ui.label(
                    'Patients'
                ).classes(
                    'text-2xl font-bold mt-4'
                )

                ui.label(
                    'Patient Database & Medical Profiles'
                ).classes(
                    'text-center text-gray-500'
                )

            # =====================================================
            # VISITS
            # =====================================================

            with ui.card().classes(
                '''
                w-72
                h-56
                rounded-3xl
                shadow-lg
                cursor-pointer
                hover:shadow-2xl
                transition
                items-center
                justify-center
                '''
            ).on(
                'click',
                open_visits
            ):

                ui.icon(
                    'event'
                ).classes(
                    'text-7xl text-green-600'
                )

                ui.label(
                    'Visits'
                ).classes(
                    'text-2xl font-bold mt-4'
                )

                ui.label(
                    'Available , Booked & Completed Visits'
                ).classes(
                    'text-center text-gray-500'
                )

            # =====================================================
            # PAYMENTS
            # =====================================================

            with ui.card().classes(
                '''
                w-72
                h-56
                rounded-3xl
                shadow-lg
                cursor-pointer
                hover:shadow-2xl
                transition
                items-center
                justify-center
                '''
            ).on(
                'click',
                open_payments
            ):

                ui.icon(
                    'payments'
                ).classes(
                    'text-7xl text-orange-600'
                )

                ui.label(
                    'Payments'
                ).classes(
                    'text-2xl font-bold mt-4'
                )

                ui.label(
                    'Billing & Financial Reports'
                ).classes(
                    'text-center text-gray-500'
                )

            # =====================================================
            # SETTINGS
            # =====================================================

            with ui.card().classes(
                '''
                w-72
                h-56
                rounded-3xl
                shadow-lg
                cursor-pointer
                hover:shadow-2xl
                transition
                items-center
                justify-center
                '''
            ).on(
                'click',
                open_settings
            ):

                ui.icon(
                    'settings'
                ).classes(
                    'text-7xl text-purple-600'
                )

                ui.label(
                    'Settings'
                ).classes(
                    'text-2xl font-bold mt-4'
                )

                ui.label(
                    'Doctors, ICD Codes & Configuration'
                ).classes(
                    'text-center text-gray-500'
                )

    # =====================================================
    # IMPORT PAGES
    # =====================================================
    
    from Pages.Patients_List import (
        load_patients,
        get_icd_cache
    )

    Cache.PATIENTS_CACHE = load_patients()

    get_icd_cache()
    print(
        'Preloading Settings Data...'
    )

    get_doctors()

    print(
        'Settings Cache Loaded'
        )   
    # =====================================================
    # RUN
    # =====================================================

