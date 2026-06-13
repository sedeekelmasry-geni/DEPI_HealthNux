
from nicegui import ui
import pandas as pd
import Cache
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import sys

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

def format_time(value):
    try:
        return pd.to_datetime(str(value)).strftime("%I:%M %p")
    except:
        return str(value)


def get_timetables():

    if Cache.TIMETABLE_CACHE is None:

        with engine.connect() as conn:

            Cache.TIMETABLE_CACHE = pd.read_sql("""

                SELECT

                    tt.time_table_key,
                    tt.dr_code,
                    dl.dr_name,
                    dl.speciality,

                    tt.day_of_week,
                    tt.scheduled_start_time,
                    tt.scheduled_end_time,

                    tt.capacity,
                    tt.is_active

                FROM dr_time_table tt

                LEFT JOIN dr_list dl
                    ON tt.dr_code = dl.dr_code

                ORDER BY
                    dl.speciality,
                    dl.dr_name

            """, conn)

    return Cache.TIMETABLE_CACHE


def refresh_timetable_cache():
    Cache.TIMETABLE_CACHE = None
    return get_timetables()


def timetable_form(record=None):

    doctors_df = Cache.DOCTORS_CACHE.copy()

    specialities = sorted(
        doctors_df["speciality"]
        .dropna()
        .unique()
    )

    with ui.column().classes('w-full gap-3'):

        speciality = ui.select(
            specialities,
            label='Speciality',
            value=(record["speciality"] if record is not None else None)
        ).classes('w-full')

        doctor = ui.select({}, label='Doctor').classes('w-full')

        def load_doctors():

            filtered = doctors_df[
                (doctors_df["speciality"] == speciality.value)
                &
                (
                    doctors_df["active_dr"]
                    .astype(str)
                    .str.upper()
                    .eq("ACTIVE")
                )
            ]

            doctor.options = {
                r["dr_code"]: r["dr_name"]
                for _, r in filtered.iterrows()
            }

            doctor.update()

        speciality.on(
            'update:model-value',
            lambda e: load_doctors()
        )

        load_doctors()

        if record is not None:
            doctor.value = record["dr_code"]

        day = ui.select(
            list(DAY_ORDER.keys()),
            label='Day',
            value=(record["day_of_week"] if record is not None else None)
        ).classes('w-full')

        start_time = ui.input(
            'Start Time',
            value=(str(record["scheduled_start_time"]) if record is not None else "")
        ).props('type=time')

        end_time = ui.input(
            'End Time',
            value=(str(record["scheduled_end_time"]) if record is not None else "")
        ).props('type=time')

        def auto_end():
            try:
                if start_time.value:
                    dt = datetime.strptime(start_time.value, "%H:%M")
                    end_time.value = (dt + timedelta(hours=1)).strftime("%H:%M")
            except:
                pass

        if record is None:
            start_time.on(
                'update:model-value',
                lambda e: auto_end()
            )

        capacity = ui.number(
            'Capacity',
            value=(record["capacity"] if record is not None else 0)
        )

        status_value = 'Active'

        if record is not None:

            if str(record["is_active"]).upper() in [
                'TRUE',
                'ACTIVE',
                '1'
            ]:

                status_value = 'Active'

            else:

                status_value = 'NotActive'



        status = ui.select(
            ['Active', 'NotActive'],
            value=status_value,
            label='Status'
        )

    return {
        "doctor": doctor,
        "day": day,
        "start_time": start_time,
        "end_time": end_time,
        "capacity": capacity,
        "status": status,
    }


def render_timetable_tab():

    timetable_df = get_timetables()

    def refresh_doctors_TimeTable_data():

        nonlocal timetable_df

        Cache.TIMETABLE_CACHE = None

        timetable_df = get_timetables()

        refresh(False)

    
    def open_delete_dialog(row):
       
        with ui.dialog() as dialog:
            client = dialog.client
            with ui.card():

                ui.label('Delete Timetable?')

                def delete():
                    with engine.begin() as conn:

                        conn.execute(
                            text("""
                                DELETE FROM dr_time_table
                                WHERE time_table_key = :id
                            """),
                            {"id": row["time_table_key"]}
                        )

                    dialog.close()
                    refresh_doctors_TimeTable_data()
                    safe_notify(client,
                        'Timetable Deleted',
                        'positive'
                    )
                ui.button('Delete', on_click=delete)

        dialog.open()

    def open_edit_dialog(row):
        
        with ui.dialog() as dialog:
            client = dialog.client
            with ui.card().classes('w-[700px]'):

                fields = timetable_form(row)

                def save():

                    with engine.begin() as conn:

                        conn.execute(
                            text("""
                                UPDATE dr_time_table
                                SET
                                    day_of_week=:day,
                                    scheduled_start_time=:start,
                                    scheduled_end_time=:end,
                                    capacity=:capacity,
                                    is_active=:status
                                WHERE time_table_key=:id
                            """),
                            {
                                "id": row["time_table_key"],
                                "day": fields["day"].value,
                                "start": fields["start_time"].value,
                                "end": fields["end_time"].value,
                                "capacity": int(fields["capacity"].value or 0),
                                "status": fields["status"].value,
                            }
                        )

                    dialog.close()
                    refresh_doctors_TimeTable_data()
                    safe_notify(
                        client,
                        'Timetable Updated',
                        'positive'
                    )

                ui.separator()

                with ui.row().classes(
                    'justify-end w-full'
                ):

                    ui.button(
                        'Cancel',
                        on_click=dialog.close
                    )

                    ui.button(
                        'Save',
                        icon='save',
                        on_click=save
                    ).props(
                        'unelevated color=primary'
                    )

        dialog.open()

    def open_add_dialog():

        with ui.dialog() as dialog:

            client = dialog.client

            with ui.card().classes(
                'w-[800px] max-w-full p-6 rounded-2xl'
            ):

                ui.label(
                    '➕ Add Timetable'
                ).classes(
                    'text-2xl font-bold'
                )

                fields = timetable_form()

                def save():

                    if not fields["doctor"].value:

                        safe_notify(
                            client,
                            'Doctor Required',
                            'negative'
                        )

                        return

                    # ==========================
                    # DUPLICATE CHECK
                    # ==========================

                    with engine.connect() as conn:

                        duplicate = pd.read_sql(

                            """

                            SELECT *

                            FROM dr_time_table

                            WHERE

                                dr_code = %(dr_code)s

                                AND

                                day_of_week = %(day)s

                                AND

                                scheduled_start_time = %(start)s

                            """,

                            conn,

                            params={

                                "dr_code":
                                    fields["doctor"].value,

                                "day":
                                    fields["day"].value,

                                "start":
                                    fields["start_time"].value

                            }

                        )

                    if len(duplicate) > 0:

                        safe_notify(
                            client,
                            'Duplicate Timetable',
                            'negative'
                        )

                        return

                    new_row = {

                        "dr_code":
                            fields["doctor"].value,

                        "day_of_week":
                            fields["day"].value,

                        "scheduled_start_time":
                            fields["start_time"].value,

                        "scheduled_end_time":
                            fields["end_time"].value,

                        "capacity":
                            int(
                                fields["capacity"].value
                                or 0
                            ),

                        "is_active":
                            fields["status"].value

                    }

                    with engine.begin() as conn:

                        conn.execute(

                            text("""

                            INSERT INTO dr_time_table

                            (

                                dr_code,
                                day_of_week,
                                scheduled_start_time,
                                scheduled_end_time,
                                capacity,
                                is_active

                            )

                            VALUES

                            (

                                :dr_code,
                                :day_of_week,
                                :scheduled_start_time,
                                :scheduled_end_time,
                                :capacity,
                                :is_active

                            )

                            """),

                            new_row

                        )
                    # =============================
                    # UPDATE CACHE
                    # =============================

                    Cache.TIMETABLE_CACHE = pd.concat(

                        [

                            Cache.TIMETABLE_CACHE,

                            pd.DataFrame(
                                [new_row]
                            )

                        ],

                        ignore_index=True

                    )

                    # =============================
                    # REFRESH VIEW
                    # =============================

                    refresh_doctors_TimeTable_data()

                    dialog.close()

                    
                    safe_notify(
                        client,
                        'Timetable Added',
                        'positive'
                    )

                ui.separator()

                with ui.row().classes(
                    'justify-end w-full'
                ):

                    ui.button(
                        'Cancel',
                        on_click=dialog.close
                    )

                    ui.button(
                        'Save',
                        icon='save',
                        on_click=save
                    ).props(
                        'unelevated color=primary'
                    )

        dialog.open()

    # =========================================
    # TOOLBAR
    # =========================================

    with ui.card().classes(
        'w-full p-4 rounded-2xl shadow-sm'
    ):

        with ui.row().classes(
            'w-full items-center gap-2'
        ):

            search = ui.input(
                placeholder='Search Doctor...'
            ).props(
                'outlined clearable'
            ).classes(
                'flex-1'
            )

            def clear_search():

                search.value = ''

                refresh()

            clear_btn = ui.button(
                icon='clear'
            ).props(
                'flat round'
            )

            ui.button(
                'Add Timetable',
                icon='add',
                on_click=open_add_dialog
            ).props(
                'unelevated color=primary'
            )

    container = ui.column().classes(
        'w-full'
    )

    # =========================================
    # REFRESH
    # =========================================

    def refresh(search_only=False):

        nonlocal timetable_df
        
        if not search_only:
            timetable_df = refresh_timetable_cache()

        container.clear()

        keyword = str(
            search.value or ''
        ).lower().strip()

        if keyword:

            timetable_filtered = timetable_df[

                timetable_df[
                    "dr_name"
                ].astype(
                    str
                ).str.lower().str.contains(
                    keyword,
                    na=False
                )

                |

                timetable_df[
                    "speciality"
                ].astype(
                    str
                ).str.lower().str.contains(
                    keyword,
                    na=False
                )

                |

                timetable_df[
                    "dr_code"
                ].astype(
                    str
                ).str.lower().str.contains(
                    keyword,
                    na=False
                )

            ]

        else:

            timetable_filtered = timetable_df

        grouped_specialities = dict(

            tuple(

                timetable_filtered.groupby(
                    "speciality"
                )

            )

        )

        with container:

            for speciality in sorted(

                grouped_specialities.keys()

            ):

                speciality_df = grouped_specialities[
                    speciality
                ]

                title = (

                    f"🩺 {speciality} "
                    f"({len(speciality_df)})"

                )

                with ui.card().classes(
                    'w-full rounded-2xl shadow-sm'
                ):

                    with ui.expansion(
                        title
                    ).classes(
                        'w-full'
                    ):

                        doctor_groups = dict(

                            tuple(

                                speciality_df.groupby(
                                    "dr_name"
                                )

                            )

                        )

                        for doctor_name in sorted(
                            doctor_groups.keys()
                        ):

                            doctor_df = doctor_groups[
                                doctor_name
                            ]

                            doctor_df = doctor_df.copy()

                            doctor_df["_sort_day"] = (

                                doctor_df[
                                    "day_of_week"
                                ].map(
                                    DAY_ORDER
                                )

                            )

                            doctor_df = doctor_df.sort_values(
                                ["_sort_day", "scheduled_start_time"]
                            )

                            days_text = " | ".join(

                                doctor_df[
                                    "day_of_week"
                                ]

                                .dropna()

                                .unique()

                            )

                            with ui.card().classes(

                                '''

                                w-full
                                mb-2
                                rounded-xl
                                border-l-8
                                border-green-500

                                '''

                            ):

                                with ui.expansion(

                                    f"{doctor_name} ({days_text})"

                                ).classes(
                                    'w-full'
                                ):

                                    for _, row in doctor_df.iterrows():

                                        active = (

                                            str(
                                                row[
                                                    "is_active"
                                                ]
                                            ).upper()

                                            in

                                            [
                                                "ACTIVE",
                                                "TRUE"
                                            ]

                                        )

                                        ui.separator()

                                        ui.badge(

                                            "Active"

                                            if active

                                            else

                                            "Inactive"

                                        ).props(

                                            "color=positive"

                                            if active

                                            else

                                            "color=negative"

                                        )

                                        with ui.grid(
                                            columns=2
                                        ).classes(
                                            'w-full mt-4'
                                        ):

                                            ui.label(
                                                f'Day: {row["day_of_week"]}'
                                            )

                                            ui.label(
                                                f'Capacity: {row["capacity"]}'
                                            )

                                            ui.label(

                                                f'Start: '

                                                f'{format_time(row["scheduled_start_time"])}'

                                            )

                                            ui.label(

                                                f'End: '

                                                f'{format_time(row["scheduled_end_time"])}'

                                            )

                                        with ui.row():

                                            ui.button(
                                                'Edit',
                                                icon='edit',
                                                on_click=lambda r=row:
                                                open_edit_dialog(r)
                                            ).props(
                                                'unelevated color=primary'
                                            )

                                            ui.button(
                                                'Delete',
                                                icon='delete',
                                                on_click=lambda r=row:
                                                open_delete_dialog(r)
                                            ).props(
                                                'unelevated color=negative'
                                            )
    refresh()

    search.on(
        'keyup',
        lambda e: refresh(True)
    )

    clear_btn.on(
    'click',
    lambda: (
        setattr(
            search,
            'value',
            ''
        ),
        refresh()
    )
)