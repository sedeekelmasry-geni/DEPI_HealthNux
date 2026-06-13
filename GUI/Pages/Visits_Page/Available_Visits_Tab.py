from nicegui import ui
import pandas as pd
import Cache
from sqlalchemy import create_engine, text
from datetime import date, timedelta
import sys
import psycopg2
from Components.generate_available_visits import (generate_ava_visits)
sys.path.append("..")
from Keys.PostGresKey import POSTGRES_URL

engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True
)



DAY_ORDER = {
    "Saturday": 1,
    "Sunday": 2,
    "Monday": 3,
    "Tuesday": 4,
    "Wednesday": 5,
    "Thursday": 6,
    "Friday": 7,
}

def safe_notify(client, message, color='positive'):

    try:

        with client:

            ui.notify(
                message,
                color=color
            )

    except Exception as e:

        print(f'Notification Error: {e}')

DAY_COLUMNS = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday"
]


def get_holidays():

    query = """

    SELECT

        Holiday_Date,

        Holiday_Name

    FROM Official_Holidays

    """

    with engine.connect() as conn:

        return pd.read_sql(
            query,
            conn
        )

def get_available_visits():

    if Cache.AVAILABLE_VISITS_CACHE is None:

        with engine.connect() as conn:

            Cache.AVAILABLE_VISITS_CACHE = pd.read_sql(
                """
                SELECT
                    av.visit_key,
                    av.scheduled_date,
                    av.start_time_override,
                    av.end_time_override,
                    av.capacity,
                    av.is_holiday,

                    tt.day_of_week,
                    COALESCE(

                        av.start_time_override,

                        tt.scheduled_start_time

                    )

                    AS scheduled_start_time,


                    COALESCE(

                        av.end_time_override,

                        tt.scheduled_end_time

                    )

                    AS scheduled_end_time,

                    dl.dr_name,
                    dl.speciality,
                    dl.visit_fee,

                    GREATEST(
                        0,
                        av.capacity -
                        COUNT(
                            CASE
                                WHEN bv.booking_key IS NOT NULL
                                AND bv.status <> 'Cancelled'
                                THEN bv.booking_key
                            END
                        )
                    ) AS remaining_capacity

                FROM available_visits av

                LEFT JOIN dr_time_table tt
                    ON av.time_table_key =
                    tt.time_table_key

                LEFT JOIN dr_list dl
                    ON tt.dr_code =
                    dl.dr_code

                LEFT JOIN booked_visits bv
                    ON av.visit_key =
                    bv.visit_key

                GROUP BY

                    av.visit_key,
                    av.scheduled_date,
                    av.capacity,
                    av.is_holiday,

                    tt.day_of_week,
                    tt.scheduled_start_time,
                    tt.scheduled_end_time,

                    dl.dr_name,
                    dl.speciality,
                    dl.visit_fee
                """,
                conn
            )

    return Cache.AVAILABLE_VISITS_CACHE

def get_patients():

    if Cache.PATIENTS_CACHE is None:

        with engine.connect() as conn:

            Cache.PATIENTS_CACHE = pd.read_sql(

                """

                SELECT

                    Patient_U_ID,

                    Patient_Name,

                    Phone_Number,

                    National_ID

                FROM Patients_List

                """,

                conn

            )
    print(type(Cache.PATIENTS_CACHE))
    return Cache.PATIENTS_CACHE

def refresh_available_visits_cache():

    Cache.AVAILABLE_VISITS_CACHE = None

    return get_available_visits()

def get_week_start(input_date):

    days_back = (

        input_date.weekday() + 2

    ) % 7

    return (

        input_date

        - timedelta(days=days_back)

    )


def render_available_visits_tab():

    global visits_df
    visits_df = get_available_visits()
    patients_df = get_patients()
    holidays_df = get_holidays()
    doctors_df = Cache.DOCTORS_CACHE.copy()
    active_doctors_df = doctors_df[

    doctors_df[
        "active_dr"
    ]
    .astype(str)
    .str.upper()
    ==
    "ACTIVE"

]
    speciality_options = sorted(

    active_doctors_df[
        "speciality"
    ]
    .dropna()
    .unique()

)
    doctor_options = sorted(

    active_doctors_df[
        "dr_name"
    ]
    .dropna()
    .unique()

)
    doctor_speciality_lookup = (

    active_doctors_df

    .set_index(
        "dr_name"
    )

    ["speciality"]

    .to_dict()

)
    speciality_doctors_lookup = {}

    for speciality in speciality_options:

        speciality_doctors_lookup[
            speciality
        ] = sorted(

            active_doctors_df[

                active_doctors_df[
                    "speciality"
                ]
                ==
                speciality

            ][
                "dr_name"
            ]

            .dropna()

            .unique()

    )


    current_week = {

    "start":

        get_week_start(
            date.today()
        )

        }
    
    def update_week_label():

        start = current_week["start"]

        end = (

            start

            + timedelta(days=6)

        )

        week_title.set_text(

            f"""

            Week:

            {start:%d %b %Y}

            →

            {end:%d %b %Y}

            """

        )

    def previous_week():

        current_week["start"] -= timedelta(
            days=7
        )

        update_week_label()

        refresh()

    def next_week():

        current_week["start"] += timedelta(
            days=7
        )

        update_week_label()

        refresh()

    search_mode = {
    "active": False,
    "no_results": False
        }

    def jump_to_date(target_date):

        week_start = target_date - timedelta(

            days=(target_date.weekday() + 2) % 7

        )

        current_week["start"] = week_start

        update_week_label()

        refresh()

    def jump_to_first_available():

        df = visits_df.copy()
        search_mode["active"] = True
        search_mode["no_results"] = False

        df["scheduled_date"] = pd.to_datetime(
            df["scheduled_date"]
        ).dt.date

        df = df[
            df["remaining_capacity"] > 0
        ]

        if speciality_filter.value:

            df = df[
                df["speciality"]
                ==
                speciality_filter.value
            ]

        if doctor_filter.value:

            df = df[
                df["dr_name"]
                ==
                doctor_filter.value
            ]

        if df.empty:

            search_mode["no_results"] = True

            ui.notify(
                "No Available Slots Found",
                color="warning"
            )

            refresh()

            return

        first_date = min(
            df["scheduled_date"]
        )

        jump_to_date(
            first_date
        )

    def doctor_changed():

        if not doctor_filter.value:

            speciality_filter.value = None

            doctor_filter.set_options(
                doctor_options
            )

            refresh()

            return

        speciality = doctor_speciality_lookup.get(

            doctor_filter.value

        )

        if speciality:

            speciality_filter.value = speciality

        jump_to_first_available()

    def speciality_changed():

        if not speciality_filter.value:

            doctor_filter.set_options(
                doctor_options
            )

            doctor_filter.value = None

            refresh()

            return

        filtered_doctors = (

            speciality_doctors_lookup.get(

                speciality_filter.value,

                []

            )

        )

        doctor_filter.set_options(
            filtered_doctors
        )

        doctor_filter.value = None

        jump_to_first_available()

    def clear_filters():

        speciality_filter.value = None

        doctor_filter.value = None

        doctor_filter.set_options(
            doctor_options
        )

        search_mode["active"] = False
        search_mode["no_results"] = False

        current_week["start"] = get_week_start(
            date.today()
        )

        update_week_label()

        refresh()
    
    def generate_visits_clicked():

        try:

            ui.notify(
                'Generating Visits...',
                color='info'
            )

            generate_ava_visits()

            
            reload_visits()
                              
            refresh()

            ui.notify(
                'Visits Generated Successfully',
                color='positive'
            )

        except Exception as e:

            ui.notify(
                str(e),
                color='negative'
            )

    with ui.card().classes(
        'w-full p-4 rounded-2xl'
    ):

        with ui.row().classes(
            'w-full gap-2'
        ):

            speciality_filter = ui.select(

                options=speciality_options,

                label="Speciality"

            ).props(
                'outlined clearable'
            ).classes(
                'w-48'
            )

            doctor_filter = ui.select(

                options=doctor_options,

                label="Doctor"

            ).props(
                'outlined clearable'
            ).classes(
                'flex-1'
            )
            doctor_filter.options = doctor_options
            
            ui.button(
                icon='clear'
            ).classes('h-12').on('click',
                clear_filters  )
            
            def go_to_today():

                current_week["start"] = get_week_start(
                    date.today()
                )

                update_week_label()

                reload_visits()

                refresh()

            ui.button(

                'Today',

                icon='today'

            ).classes(
                'h-12'
            ).on(
                'click',
                go_to_today
            )


            def reload_and_refresh():

                reload_visits()

                refresh()
            ui.button(

                
                icon='refresh'

            ).classes(
                'h-12'
            ).on(
                'click',
                reload_and_refresh
            )


            ui.button(
                'Generate Visits',
                icon='calendar_month'
            ).classes(
                'h-12').on('click',
                generate_visits_clicked  )
            #ui.button(
               # 'Refresh Holidays',
                #icon='refresh'
            #).classes(
             #   'h-12'   )

    with ui.card().classes(
        'w-full p-3'
        ):
    
            with ui.row().classes(
            'items-center justify-between w-full'
            ):

                ui.button(
                    icon='chevron_left',

                    on_click=previous_week
                )
                week_title = ui.label()
                
                ui.button(
                    icon='chevron_right',

                    on_click=next_week
                )


    container = ui.column().classes(
        'w-full'
    )


    def open_booking_dialog(row):

        dialog = ui.dialog()
        selected_patient = {
            "data": None
        }

        patients_df = get_patients()

        with dialog, ui.card().classes(
            '''
            w-[900px]
            
            
            '''
        ):

            ui.label(
                'Book Visit'
            ).classes(
                'text-h5 font-bold'
            )

            ui.separator()

            # =========================
            # VISIT DETAILS
            # =========================

            start_display = pd.to_datetime(
                str(row["scheduled_start_time"])
            ).strftime(
                "%I:%M %p"
            )

            end_display = pd.to_datetime(
                str(row["scheduled_end_time"])
            ).strftime(
                "%I:%M %p"
            )

            ui.label(
                f'Doctor: {row["dr_name"]}'
            )

            ui.label(
                f'Speciality: {row["speciality"]}'
            )

            ui.label(
                f'Date: {row["scheduled_date"]}'
            )

            ui.label(
                f'Time: {start_display} - {end_display}'
            )

            ui.separator()

            # =========================
            # SEARCH
            # =========================

            with ui.row().classes(
                'w-full items-center gap-2'
            ):

                search_box = ui.input(
                    'Search Patient'
                ).props(
                    'outlined'
                ).classes(
                    'flex-1'
                )


                def clear_search():

                    search_box.value = ''

                    refresh_patients()
                ui.button(

                    icon='clear',

                    on_click=clear_search

                ).props(
                    'flat round'
                )

            selected_patient_label = ui.label(
                'No Patient Selected'
            ).classes(
                'text-orange'
            )

            unselect_btn = ui.button(

                    'Unselect',

                    icon='close',

                    color='orange',

                    on_click=lambda:
                    unselect_patient()

                )

            unselect_btn.visible = False

            results_container = ui.column().classes(
                '''
                w-full
                h-[400px]
                border
                rounded-lg
                p-1
                '''
            )

            ui.separator()

            # =========================
            # BOOKING
            # =========================

            booking_status = ui.radio(

                [
                    'Booked',
                    'Checked In'
                ],

                value='Booked'

            )

            payment_container = ui.column()

            with payment_container:

                payment_type = ui.select(

                    [
                        'Cash',
                        'Insurance',
                        'Free'
                    ],

                    label='Payment Type',

                    value='Cash'

                ).classes(
                    'w-full'
                )

                payment_amount = ui.number(

                    'Payment Amount',

                    value=row.get(
                        "visit_fee",
                        0
                    )

                ).classes(
                    'w-full'
                )

            payment_container.visible = False

            # =========================
            # STATUS CHANGED
            # =========================

            def status_changed():

                payment_container.visible = (

                    booking_status.value

                    ==

                    'Checked In'

                )

            booking_status.on(
                'update:model-value',
                lambda e:
                status_changed()
            )

            def unselect_patient():

                selected_patient["data"] = None

                selected_patient_label.set_text(
                    'No Patient Selected'
                )

                unselect_btn.visible = False

                results_container.visible = True

                refresh_patients()

            # =========================
            # SELECT PATIENT
            # =========================

            def select_patient(patient):

                selected_patient[
                    "data"
                ] = patient

                selected_patient_label.set_text(

                    f'Selected: {patient["patient_name"]} '
                    f'({patient["patient_u_id"]})'

                )
                unselect_btn.visible = True
                results_container.visible = False 
            # =========================
            # SEARCH
            # =========================

            def refresh_patients():

                results_container.clear()
                                
                search_text = (

                    search_box.value

                    or

                    ""

                ).strip().lower()
                
                filtered = patients_df.copy()

                if search_text:

                    filtered = filtered[

                        filtered["patient_name"]

                        .fillna("")

                        .astype(str)

                        .str.lower()

                        .str.contains(
                            search_text,
                            na=False
                        )

                        |

                        filtered["phone_number"]

                        .fillna("")

                        .astype(str)

                        .str.contains(
                            search_text,
                            na=False
                        )

                        |

                        filtered["patient_u_id"]

                        .fillna("")

                        .astype(str)

                        .str.lower()

                        .str.contains(
                            search_text,
                            na=False
                        )

                        |

                        filtered["national_id"]

                        .fillna("")

                        .astype(str)

                        .str.contains(
                            search_text,
                            na=False
                        )

                    ]

                with results_container:

                    for _, patient in filtered.head(20).iterrows():

                        with ui.card().classes(
                            '''
                            w-full
                            p-2
                            mb-1
                            '''
                        ):
                            with ui.row().classes(
                                'w-full justify-between items-center'
                            ):
                                ui.label(
                                    patient[
                                        "patient_name"
                                    ]
                                )

                                ui.label(
                                    str(
                                        patient[
                                            "phone_number"
                                        ]
                                    )
                                )

                                ui.label(
                                    patient[
                                        "patient_u_id"
                                    ]
                                )

                                current_patient = patient.to_dict()

                                ui.button(

                                    'Select',

                                    on_click=lambda p=current_patient:
                                    select_patient(
                                        p
                                    )

                                )

            search_box.on(

                'update:model-value',

                lambda e:
                refresh_patients()

            )

            refresh_patients()

            ui.separator()

            # =========================
            # FINAL BUTTON
            # =========================


            def final_booking():
                if row["remaining_capacity"] <= 0:

                    ui.notify(

                        'No Remaining Capacity',

                        color='negative'

                    )

                    return

                if selected_patient["data"] is None:

                    ui.notify(

                        'Please Select A Patient',

                        color='negative'

                    )

                    return

                confirm_dialog = ui.dialog()

                def save_booking():

                    if selected_patient["data"] is None:

                        ui.notify(
                            'Please Select A Patient',
                            color='negative'
                        )

                        return
                    # =========================
                    # OVERBOOKING CHECK
                    # =========================

                    if row["remaining_capacity"] <= 0:

                        ui.notify(

                            'No Remaining Capacity Available',

                            color='negative'

                        )

                        return


                    # =========================
                    # DUPLICATE BOOKING CHECK
                    # =========================

                    with engine.connect() as conn:

                        existing_booking = conn.execute(

                            text("""

                            SELECT booking_key

                            FROM booked_visits

                            WHERE

                                visit_key = :visit_key

                                AND

                                patient_u_id = :patient_u_id

                                AND

                                status <> 'Cancelled'

                            LIMIT 1

                            """),

                            {

                                "visit_key":
                                    row["visit_key"],

                                "patient_u_id":
                                    selected_patient["data"][
                                        "patient_u_id"
                                    ]

                            }

                        ).scalar()

                    if existing_booking:

                        ui.notify(

                            'Patient Already Booked On This Visit',

                            color='negative'

                        )

                        return

                    with engine.connect() as conn:

                        result = conn.execute(

                            text("""

                            INSERT INTO booked_visits
                            (

                                visit_key,
                                patient_u_id,
                                status,
                                creation_by

                            )

                            VALUES
                            (

                                :visit_key,
                                :patient_u_id,
                                :status,
                                :creation_by

                            )

                            RETURNING booking_key

                            """),

                            {

                                "visit_key":
                                    row["visit_key"],

                                "patient_u_id":
                                    selected_patient["data"][
                                        "patient_u_id"
                                    ],

                                "status":
                                    booking_status.value,

                                "creation_by":
                                    "Reception"

                            }

                        )

                        booking_key = result.scalar()


                        if booking_status.value == 'Checked In':

                            conn.execute(

                                text("""

                                INSERT INTO payments
                                (

                                    booking_key,
                                    patient_u_id,
                                    payment_date,
                                    payment_type,
                                    payment_amount,
                                    payment_status

                                )

                                VALUES
                                (

                                    :booking_key,
                                    :patient_u_id,
                                    :payment_date,
                                    :payment_type,
                                    :payment_amount,
                                    :payment_status

                                )

                                """),

                                {

                                    "booking_key":
                                        booking_key,

                                    "patient_u_id":
                                        selected_patient["data"][
                                            "patient_u_id"
                                        ],

                                    "payment_date":
                                        date.today(),

                                    "payment_type":
                                        payment_type.value,

                                    "payment_amount":
                                        payment_amount.value,

                                    "payment_status":
                                        "Pending"

                                }

                            )

                        conn.commit()

                    print(
                        "BOOKING CREATED:",
                        booking_key
                        )

                    if booking_status.value == 'Checked In':

                        ui.notify(

                            f'Booking + Payment Created ({booking_key})',

                            color='positive'

                        )

                    else:

                        ui.notify(

                            f'Booking Created ({booking_key})',

                            color='positive'

                        )
                        
                    Cache.AVAILABLE_VISITS_CACHE = None
                    Cache.BOOKED_VISITS_CACHE = None
                    Cache.PAYMENTS_CACHE = None
                    Cache.PATIENTS_CACHE = None

                    global visits_df

                    visits_df = get_available_visits()
                    
                    confirm_dialog.close()

                    dialog.close()

                    reload_visits()

                    refresh()

                with confirm_dialog, ui.card().classes(
                    'w-[500px]'
                ):

                    ui.label(
                        'Confirm Booking'
                    ).classes(
                        'text-h6 font-bold'
                    )

                    ui.separator()

                    ui.label(
                        f'Patient: '
                        f'{selected_patient["data"]["patient_name"]}'
                    )

                    ui.label(
                        f'Patient ID: '
                        f'{selected_patient["data"]["patient_u_id"]}'
                    )

                    ui.label(
                        f'Doctor: {row["dr_name"]}'
                    )

                    ui.label(
                        f'Date: {row["scheduled_date"]}'
                    )

                    ui.label(
                        f'Time: '
                        f'{start_display} - {end_display}'
                    )

                    ui.label(
                        f'Status: '
                        f'{booking_status.value}'
                    )

                    if booking_status.value == 'Checked In':

                        ui.separator()

                        ui.label(
                            f'Payment Type: '
                            f'{payment_type.value}'
                        )

                        ui.label(
                            f'Amount: '
                            f'{payment_amount.value}'
                        )

                    ui.separator()

                    with ui.row().classes(
                        'w-full justify-end'
                    ):

                        ui.button(

                            'Confirm',

                            icon='check',

                            color='positive',

                            on_click=save_booking

                        )

                        ui.button(

                            'Cancel',

                            icon='close',

                            on_click=confirm_dialog.close

                        )

                confirm_dialog.open()

            ui.separator()
            with ui.row().classes(
                'w-full justify-end'
            ):

                ui.button(

                    'Confirm Booking',

                    icon='Book',

                    on_click=final_booking

                )

                ui.button(

                    'Cancel',

                    icon='close',

                    on_click=dialog.close

                )

        dialog.open()

    def open_edit_slot_dialog(row):

        dialog = ui.dialog()

        booked_count = (

            int(
                row["capacity"]
            )

            -

            int(
                row["remaining_capacity"]
            )

        )
        remaining_capacity = int(
                    row[
                        "remaining_capacity"
                    ])
        capacity = int(
            row[
                "capacity"
            ])

        with dialog, ui.card().classes(
            'w-[500px]'
        ):

            ui.label(
                'Edit Visit Slot'
            ).classes(
                'text-h6 font-bold'
            )

            ui.separator()

            ui.label(
                f'Doctor: {row["dr_name"]}'
            )

            ui.label(
                f'Speciality: {row["speciality"]}'
            )

            ui.label(
                f'Date: {row["scheduled_date"]}'
            )

            start_display = pd.to_datetime(
                str(row["scheduled_start_time"])
            ).strftime(
                "%I:%M %p"
            )

            end_display = pd.to_datetime(
                str(row["scheduled_end_time"])
            ).strftime(
                "%I:%M %p"
            )

            ui.label(
                f'Start Time: {start_display}'
            )

            ui.label(
                f'End Time: {end_display}'
            )
            ui.label(
                f'Current Setted Capacity: {capacity}'
            ).classes(
                'text-orange'
            )

            ui.label(
                f'Current Remianing Capacity: {remaining_capacity}'
            ).classes(
                'text-orange'
            )

            ui.label(
                f'Currently Booked: {booked_count}'
            ).classes(
                'text-orange'
            )

            ui.separator()

            start_time_input = ui.input(

                'Start Time',

                value=pd.to_datetime(
                    str(row["scheduled_start_time"])
                ).strftime(
                    "%H:%M"
                )

            ).props(
                'type=time outlined'
            ).classes(
                'w-full'
            )

            end_time_input = ui.input(

                'End Time',

                value=pd.to_datetime(
                    str(row["scheduled_end_time"])
                ).strftime(
                    "%H:%M"
                )

            ).props(
                'type=time outlined'
            ).classes(
                'w-full'
            )


            start_time_input.value = pd.to_datetime(
                str(
                    row["scheduled_start_time"]
                )
            ).strftime(
                "%H:%M"
            )

            end_time_input.value = pd.to_datetime(
                str(
                    row["scheduled_end_time"]
                )
            ).strftime(
                "%H:%M"
            )


            capacity_input = ui.number(

                'Change Capacity',

                value=int(
                    row["capacity"]
                )

            ).classes(
                'w-full'
            )

            holiday_switch = ui.switch(

                'Holiday',

                value=bool(
                    row["is_holiday"]
                )

            )



            def save_slot():
                client = ui.context.client
                try:

                    if int(
                        capacity_input.value
                    ) < booked_count:

                        safe_notify(client,

                            f'Capacity cannot be less than {booked_count}',

                            'negative'

                        )

                        return

                    conn = psycopg2.connect(
                        POSTGRES_URL
                    )

                    cursor = conn.cursor()

                    cursor.execute(

                        """

                        UPDATE Available_Visits

                        SET

                            Capacity = %s,

                            Is_Holiday = %s,

                            Start_Time_Override = %s,

                            End_Time_Override = %s

                        WHERE Visit_Key = %s

                        """,

                        (
                            int(capacity_input.value),

                            bool(holiday_switch.value),

                            start_time_input.value,

                            end_time_input.value,

                            row["visit_key"]
                        )

                    )

                    conn.commit()

                    cursor.close()

                    conn.close()

                    # =========================
                    # REFRESH CACHE
                    # =========================

                    reload_visits()

                    refresh()

                    dialog.close()

                    safe_notify(client,

                        'Slot Updated Successfully',

                        'positive'

                    )

                except Exception as e:

                    safe_notify(client,

                        str(e),

                        'negative'

            )
                    
            
            def reset_time():
                client = ui.context.client
                conn = psycopg2.connect(
                    POSTGRES_URL
                )

                cursor = conn.cursor()

                cursor.execute(

                    """

                    UPDATE Available_Visits

                    SET

                        Start_Time_Override = NULL,

                        End_Time_Override = NULL

                    WHERE Visit_Key = %s

                    """,

                    (

                        row["visit_key"],

                    )

                )

                conn.commit()

                cursor.close()

                conn.close()

                Cache.AVAILABLE_VISITS_CACHE = None
                safe_notify(client,

                    'Time Slot Times Have Been Reset',

                   'positive'

                )
                reload_visits()
                refresh()

                dialog.close()


            ui.separator()

            has_override = (

                pd.notna(
                    row.get(
                        "start_time_override"
                    )
                )

                or

                pd.notna(
                    row.get(
                        "end_time_override"
                    )
                )

            )

            with ui.row().classes(
                'w-full justify-end'
            ):

                if has_override:

                    ui.button(

                        'Reset Time',

                        icon='restart_alt',

                        color='orange',

                        on_click=reset_time

                    )

                ui.button(
                    'Save',
                    icon='save',
                    on_click=save_slot
                )

                ui.button(
                    'Cancel',
                    icon='close',
                    on_click=dialog.close
                )

        dialog.open()

    def open_slot_dialog(row):

        

        with ui.dialog() as dialog:

            with ui.card().classes(
                'w-[700px]'
            ):

                ui.label(
                    row["dr_name"]
                ).classes(
                    'text-xl font-bold'
                )

                ui.label(
                    row["speciality"]
                )

                ui.separator()

                ui.label(
                    f'Date: {row["scheduled_date"]}'
                )

                start_display = pd.to_datetime(
                                str(row["scheduled_start_time"])
                            ).strftime(
                                "%I:%M %p"
                            )

                end_display = pd.to_datetime(
                    str(row["scheduled_end_time"])
                ).strftime(
                    "%I:%M %p"
                )

                ui.label(
                    f'Start Time: {start_display}'
                )

                ui.label(
                    f'End Time: {end_display}'
                )

                ui.label(
                    f'Remaining: {row["remaining_capacity"]}'
                )

                ui.separator()

                with ui.row().classes(
                    'w-full justify-end'
                ):

                    ui.button(

                        'Book Visit',

                        on_click=lambda:
                        open_booking_dialog(
                            row
                        )

                    )
                    ui.button(
                        
                        icon='edit',

                        on_click=lambda:
                        open_edit_slot_dialog(
                            row
                        )
                    )

            

            dialog.open()


    def reload_visits():

        global visits_df

        Cache.AVAILABLE_VISITS_CACHE = None

        visits_df = get_available_visits()


    def refresh():

        global visits_df

        container.clear()

        df = visits_df.copy()

        if search_mode["no_results"]:

            with container:

                ui.label(
                    "No Available Slots Found"
                ).classes(
                    '''
                    text-red
                    text-h6
                    text-center
                    w-full
                    '''
                )

            return

        week_start = current_week["start"]

        week_end = (
            week_start
            + timedelta(days=6)
        )
        holiday_df = holidays_df.copy()
        holiday_df[
                "holiday_date"
            ] = pd.to_datetime(

                holiday_df[
                    "holiday_date"
                ]

            ).dt.date
        holiday_df = holiday_df[
            (holiday_df[
                    "holiday_date"
                ]
                >= week_start)

            &

            (holiday_df[
                    "holiday_date"
                ]
                <= week_end)]



        df["scheduled_date"] = pd.to_datetime(
            df["scheduled_date"]
        ).dt.date

        df = df[
            (
                df["scheduled_date"]
                >= week_start
            )
            &
            (
                df["scheduled_date"]
                <= week_end
            )
        ]


        if speciality_filter.value:

            df = df[
                df["speciality"]
                .astype(str)
                .str.contains(
                    speciality_filter.value,
                    case=False,
                    na=False
                )
            ]

        if doctor_filter.value:

            df = df[
                df["dr_name"]
                .astype(str)
                .str.contains(
                    doctor_filter.value,
                    case=False,
                    na=False
                )
            ]

        with container:

            for speciality in sorted(
                df["speciality"]
                .dropna()
                .unique()
            ):

                with ui.card().classes(
                    '''
                    w-full
                    bg-blue-50
                    border-l-4
                    border-blue-500
                    py-2
                    px-4
                    mb-2
                    '''
                ):

                    ui.label(
                        f'🩺 {speciality}'
                    ).classes(
                        'text-xl font-bold text-blue-900'
                    )

                speciality_df = df[
                    df["speciality"]
                    == speciality
                ]

                doctors = sorted(
                    speciality_df["dr_name"]
                    .dropna()
                    .unique()
                )

                with ui.grid(
                    columns=8
                ).classes(
                        '''
                        w-full
                        items-center
                        justify-center
                        align-items=start
                        
                        '''
                ):

                    ui.label(
                        'Doctor'
                    ).classes(
                        'font-bold self-center'
                    )

                    for i in range(7):

                        current_day = (

                            week_start

                            + timedelta(days=i)

                        )

                        with ui.card().classes(
                                    '''
                                    bg-blue-50
                                    w-full
                                    p-2
                                    shadow-sm
                                    '''
                                ):
                            ui.label(

                                f"""

                                {DAY_COLUMNS[i][:3]} {current_day.strftime('%d %b')}


                                """

                            ).classes(
                                '''
                                text-center
                                font-bold
                                text-blue-900
                                text-sm
                                '''
                            )




                    for idx, doctor in enumerate(doctors):

                        doctor_bg = (

                            "bg-grey-1"

                            if idx % 2 == 0

                            else

                            "bg-white"

                        )

                        with ui.column().classes(
                            f'''
                            {doctor_bg}
                            p-2
                            rounded
                            w-full
                            h-12
                            '''
                        ):

                            ui.label(
                                doctor
                            ).classes(
                                '''
                                text-left
                                font-medium
                                self-center
                                
                                '''
                            )

                        doctor_df = speciality_df[
                            speciality_df["dr_name"]
                            == doctor
                        ]
                        
                        for day_index, day in enumerate(DAY_COLUMNS):
                            current_day = (
                                week_start
                                + timedelta(days=day_index)
                                    )

                            with ui.column():

                                holiday_rows = holiday_df[

                                    holiday_df[
                                        "holiday_date"
                                    ]

                                    ==

                                    current_day

                                    ]

                                for _, holiday in holiday_rows.iterrows():

                                    ui.button(

                                            """
                                            🏖 Official Holiday

                                            """,

                                            on_click=lambda h=holiday:
                                            ui.notify(
                                                h["holiday_name"]
                                            )

                                        ).classes(

                                            '''
                                            w-full
                                            text-xs
                                            bg-orange-5
                                            text-white
					                        p-2
                                            h-12

                                            '''

                                        ).props(
                                            'dense '
                                        )


                                day_df = doctor_df[
                                    doctor_df["day_of_week"]
                                    == day
                                ]

                                for _, row in day_df.iterrows():

                                    remaining = int(
                                        row[
                                            "remaining_capacity"
                                        ]
                                    )

                                    start_time = pd.to_datetime(
                                        str(row["scheduled_start_time"])
                                    ).strftime("%I:%M %p")

                                    end_time = pd.to_datetime(
                                        str(row["scheduled_end_time"])
                                    ).strftime("%I:%M %p")
                                    if remaining > 0:

                                        ui.button(
                                            f'''
                                            {start_time}
                                            -
                                            {end_time}

                                            ({remaining})
                                            ''',
                                            on_click=
                                            lambda r=row:
                                            open_slot_dialog(
                                                r
                                            )
                                        ).classes(
                                            '''
                                            w-full
                                            text-xs
                                            h-12
                                            p-2
                                            '''
                                        ).props(
                                            'dense'
                                        )

                                    else:

                                        ui.button(
                                            f'''
                                            {start_time}
                                            -
                                            {end_time}

                                            FULL
                                            '''
                                        ).disable().classes(
                                            '''
                                            w-full
                                            text-xs
                                            h-12
                                            p-2
                                            opacity-50
                                            '''
                                        ).props(
                                            'dense'
                                        )

                                

    update_week_label()
    refresh()

    

    speciality_filter.on(

        'update:model-value',

        lambda e:
        speciality_changed()

    )

    doctor_filter.on(

        'update:model-value',

        lambda e:
        doctor_changed()

    )