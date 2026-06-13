from nicegui import ui
import Cache
import Pages.Visits_Page.Booked_Visits_Tab as BVT


def navigation_bar(active='home'):

    def nav_button(
            text,
            icon,
            route,
            page_name
    ):

        active_style = (
            'unelevated color=primary'
            if active == page_name
            else 'flat'
        )

        ui.button(
            text,
            icon=icon,
            on_click=lambda:
            ui.navigate.to(route)
        ).props(
            active_style
        )


    def reset_booked_visits_state():

        BVT.booked_visits_tabs_container = None

        BVT.visit_details_container = None

        BVT.opened_visits = []

        BVT.selected_visit = None

    def logout():

        reset_booked_visits_state()
        Cache.CURRENT_USER = None

        ui.navigate.to('/')

    with ui.card().classes(
        '''
        w-full
        rounded-2xl
        shadow-sm
        p-2
        '''
    ):

        with ui.row().classes(
            '''
            w-full
            justify-between
            items-center
            '''
        ):

            ui.label(
                '🏥 DEPI HealthNux'
            ).classes(
                'text-2xl font-bold'
            )

            with ui.row().classes(
                'gap-2'
            ):

                nav_button(
                    'Home',
                    'home',
                    '/home',
                    'home'
                )

                nav_button(
                    'Patients',
                    'people',
                    '/patients',
                    'patients'
                )

                nav_button(
                    'Visits',
                    'event',
                    '/visits',
                    'visits'
                )

                nav_button(
                    'Payments',
                    'payments',
                    '/payments',
                    'payments'
                )

                nav_button(
                    'Settings',
                    'settings',
                    '/settings',
                    'settings'
                )
                ui.button(
                    icon='logout',
                    on_click=logout
                )
                