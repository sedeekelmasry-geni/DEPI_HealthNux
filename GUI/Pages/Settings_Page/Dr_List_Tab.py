
from nicegui import ui
import pandas as pd
import Cache
from sqlalchemy import create_engine, text
import sys
sys.path.append("..")
from Keys.PostGresKey import POSTGRES_URL
DATABASE_URL = POSTGRES_URL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

def safe_notify(client, message, color='positive'):

    try:

        with client:

            ui.notify(
                message,
                color=color
            )

    except Exception as e:

        print(f'Notification Error: {e}')

def get_doctors():

    if Cache.DOCTORS_CACHE is None:

        print(
            'Loading Doctors Cache...'
        )

        with engine.connect() as conn:

            df = pd.read_sql(

                """

                SELECT

                    dr_code,
                    speciality,
                    dr_name,
                    email,
                    visit_fee,
                    active_dr,
                    joining_date

                FROM dr_list

                ORDER BY dr_name

                """,

                conn

            )

        Cache.DOCTORS_CACHE = df.copy()

    return Cache.DOCTORS_CACHE

# =====================================================
# DR LIST
# =====================================================
def generate_next_doctor_code():

    df = Cache.DOCTORS_CACHE

    if len(df) == 0:

        return "Dr001"

    numbers = []

    for code in df["dr_code"]:

        try:

            numbers.append(
                int(
                    str(code).replace(
                        "Dr",
                        ""
                    )
                )
            )

        except:

            pass

    next_no = max(numbers) + 1

    return f"Dr{next_no:03d}"

def doctor_form(doctor=None):

    specialities = sorted(
        Cache.DOCTORS_CACHE[
            'speciality'
        ].dropna().unique()
    )

    with ui.column().classes(
        'w-full gap-3'
    ):

        with ui.row().classes(
            'w-full gap-3'
        ):

            dr_name = ui.input(
                'Doctor Name',
                value=(
                    doctor["dr_name"]
                    if doctor is not None
                    else ''
                )
            ).classes(
                'flex-1'
            )

            speciality = ui.select(
                specialities,
                value=(
                    doctor["speciality"]
                    if doctor is not None
                    else None
                ),
                label='speciality',
                with_input=True
            ).classes(
                'flex-1'
            )

        with ui.row().classes(
            'w-full gap-3'
        ):

            email = ui.input(
                'email',
                value=(
                    doctor["email"]
                    if doctor is not None
                    else ''
                )
            ).classes(
                'flex-1'
            )

            visit_fee = ui.number(
                'Visit fee',
                value=(
                    doctor["visit_fee"]
                    if doctor is not None
                    else 0
                )
            ).classes(
                'flex-1'
            )

        with ui.row().classes(
            'w-full gap-3'
        ):

            active_dr = ui.select(
                [
                    'Active',
                    'NotActive'
                ],
                value=(
                    doctor["active_dr"]
                    if doctor is not None
                    else 'Active'
                ),
                label='Status'
            ).classes(
                'flex-1'
            )

            joining_date = ui.input(
                'joining date',
                value=(
                    str(doctor["joining_date"])
                    if doctor is not None
                    else str(pd.Timestamp.today().date())
                )
            ).classes(
                'flex-1'
            )

            with ui.menu().props(
                'no-parent-event'
            ) as date_menu:

                ui.date().bind_value(
                    joining_date
                )

            joining_date.add_slot(
                'append'
            )

            with joining_date:
                ui.icon(
                    'event'
                ).on(
                    'click',
                    date_menu.open
                )

    return {
        "dr_name": dr_name,
        "speciality": speciality,
        "email": email,
        "visit_fee": visit_fee,
        "active_dr": active_dr,
        "joining_date": joining_date,
    }

def render_doctors_tab():

    doctors_df = get_doctors()

    def refresh_doctors_data():

        nonlocal doctors_df

        Cache.DOCTORS_CACHE = None

        doctors_df = get_doctors()

        refresh_doctors_view()

    def open_add_doctor_dialog():

        with ui.dialog() as dialog:

            with ui.card().classes(
                'w-[800px] max-w-full p-6 rounded-2xl'
            ):

                ui.label(
                    '➕ Add New Doctor'
                ).classes(
                    'text-2xl font-bold'
                )

                # =================================
                # REUSABLE FORM
                # =================================

                fields = doctor_form()

                # =================================
                # SAVE
                # =================================

                def save_doctor():
                    client = dialog.client
                    if not fields[
                        "dr_name"
                    ].value:

                        ui.notify(
                            'Doctor Name Required',
                            color='negative'
                        )

                        return

                    doctor_code = (
                        generate_next_doctor_code()
                    )

                    new_row = {

                        "dr_code":
                            doctor_code,

                        "speciality":
                            fields[
                                "speciality"
                            ].value,

                        "dr_name":
                            fields[
                                "dr_name"
                            ].value,

                        "email":
                            fields[
                                "email"
                            ].value,

                        "visit_fee":
                            int(
                                fields[
                                    "visit_fee"
                                ].value
                                or 0
                            ),

                        "active_dr":
                            fields[
                                "active_dr"
                            ].value,

                        "joining_date":
                            pd.to_datetime(
                                fields["joining_date"].value
                            ).date()
                    }

                    # =============================
                    # INSERT TO postgresql
                    # =============================

                    with engine.begin() as conn:

                        conn.execute(

                            text("""

                            INSERT INTO dr_list

                            (

                                dr_code,
                                speciality,
                                dr_name,
                                email,
                                visit_fee,
                                active_dr,
                                joining_date

                            )

                            VALUES

                            (

                                :dr_code,
                                :speciality,
                                :dr_name,
                                :email,
                                :visit_fee,
                                :active_dr,
                                :joining_date

                            )

                            """),

                            new_row

                        )



                    # =============================
                    # UPDATE CACHE
                    # =============================

                    Cache.DOCTORS_CACHE = pd.concat(

                        [

                            Cache.DOCTORS_CACHE,

                            pd.DataFrame(
                                [new_row]
                            )

                        ],

                        ignore_index=True

                    )

                    # =============================
                    # REFRESH VIEW
                    # =============================

                    refresh_doctors_data()

                    dialog.close()

                    safe_notify(
                        client,
                        f'{fields["dr_name"].value} Added Successfully',
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
                        on_click=save_doctor
                    ).props(
                        'unelevated color=primary'
                    )

        dialog.open()


    def open_edit_doctor_dialog(
            doctor
    ):

        with ui.dialog() as dialog:
            client = dialog.client
            with ui.card().classes(
                'w-[800px] max-w-full p-6 rounded-2xl'
            ):

                ui.label(
                    f'✏️ Edit {doctor["dr_name"]}'
                ).classes(
                    'text-2xl font-bold'
                )

                fields = doctor_form(
                    doctor
                )

                def save_changes():

                    updated_row = {

                        "dr_code":
                            doctor["dr_code"],

                        "speciality":
                            fields[
                                "speciality"
                            ].value,

                        "dr_name":
                            fields[
                                "dr_name"
                            ].value,

                        "email":
                            fields[
                                "email"
                            ].value,

                        "visit_fee":
                            int(
                                fields[
                                    "visit_fee"
                                ].value or 0
                            ),

                        "active_dr":
                            fields[
                                "active_dr"
                            ].value,

                        "joining_date":
                            pd.to_datetime(
                                fields["joining_date"].value
                            ).date()
                    }

                    with engine.begin() as conn:

                        conn.execute(

                            text("""

                            UPDATE dr_list

                            SET

                                speciality = :speciality,
                                dr_name = :dr_name,
                                email = :email,
                                visit_fee = :visit_fee,
                                active_dr = :active_dr,
                                joining_date = :joining_date

                            WHERE

                                dr_code = :dr_code

                            """

                            ),

                            updated_row

                        )

                    cache_df = Cache.DOCTORS_CACHE.copy()

                    idx = cache_df[
                        cache_df["dr_code"]
                        ==
                        doctor["dr_code"]
                    ].index[0]

                    cache_df.loc[
                        idx
                    ] = updated_row

                    Cache.DOCTORS_CACHE = cache_df
                    
                    refresh_doctors_data()

                    dialog.close()
                    
                    safe_notify(
                        client,
                        f'{updated_row["dr_name"]} Updated',
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
                        'Save Changes',
                        icon='save',
                        on_click=save_changes
                    ).props(
                        'unelevated color=primary'
                    )

        dialog.open()


    def open_delete_doctor_dialog(
            doctor
    ):

        with ui.dialog() as dialog:

            with ui.card().classes(
                'p-6 w-[500px]'
            ):

                ui.label(
                    '⚠️ Delete Doctor'
                ).classes(
                    'text-2xl font-bold'
                )

                ui.label(
                    f'Are you sure you want to delete {doctor["dr_name"]}?'
                )

                ui.separator()

                def confirm_delete():
                    client = dialog.client
                    try:
                        with engine.begin() as conn:

                            conn.execute(

                                text("""

                                DELETE FROM dr_list

                                WHERE dr_code = :code

                                """

                                ),

                                {
                                    "code":
                                        doctor["dr_code"]
                                }

                            )

                    except Exception as e:

                        safe_notify(
                            client,
                            str(e),
                            'negative'
                        )

                        return

                    Cache.DOCTORS_CACHE = (

                        Cache.DOCTORS_CACHE[

                            Cache.DOCTORS_CACHE[
                                "dr_code"
                            ]

                            !=

                            doctor["dr_code"]

                        ]

                    ).copy()

                    refresh_doctors_data()

                    dialog.close()

                    safe_notify(
                        client,
                        f'{doctor["dr_name"]} Deleted Successfully',
                        'positive'
                    )

                with ui.row().classes(
                    'justify-end w-full'
                ):

                    ui.button(
                        'Cancel',
                        on_click=dialog.close
                    )

                    ui.button(
                        'Delete',
                        color='negative',
                        on_click=confirm_delete
                    )

        dialog.open()


    
    doctors_df = get_doctors()

    # =========================================
    # TOOLBAR
    # =========================================

    with ui.card().classes(
        'w-full p-4 rounded-2xl shadow-sm'
    ):

        with ui.row().classes(
            'w-full items-center gap-2'
        ):

            doctor_search = ui.input(
                placeholder='Search Doctor...'
            ).props(
                'outlined'
            ).classes(
                'flex-1'
            )

            clear_btn = ui.button(
                icon='clear'
            ).props(
                'flat round'
            )

            ui.button(
                'Add Doctor',
                icon='add',
                on_click=open_add_doctor_dialog
            ).props(
                'unelevated color=primary'
            )

    # =========================================
    # STATS
    # =========================================

    with ui.row().classes(
        'w-full gap-4'
    ):

        total_card = ui.card().classes(
            'p-4 flex-1 rounded-2xl shadow-sm'
        )

        active_card = ui.card().classes(
            'p-4 flex-1 rounded-2xl shadow-sm'
        )

        inactive_card = ui.card().classes(
            'p-4 flex-1 rounded-2xl shadow-sm'
        )

        speciality_card = ui.card().classes(
            'p-4 flex-1 rounded-2xl shadow-sm'
        )

    doctors_container = ui.column().classes(
        'w-full'
    )

    # =========================================
    # REFRESH
    # =========================================

    def refresh_doctors_view():

        doctors_container.clear()

        keyword = str(
            doctor_search.value or ''
        ).lower().strip()

        if keyword:

            filtered_df = doctors_df[

                doctors_df[
                    'dr_name'
                ].astype(
                    str
                ).str.lower().str.contains(
                    keyword,
                    na=False
                )

                |

                doctors_df[
                    'speciality'
                ].astype(
                    str
                ).str.lower().str.contains(
                    keyword,
                    na=False
                )

                |

                doctors_df[
                    'dr_code'
                ].astype(
                    str
                ).str.lower().str.contains(
                    keyword,
                    na=False
                )
            ]

        else:

            filtered_df = doctors_df

        # =====================================
        # MAIN STATS
        # =====================================

        active_count = len(

            filtered_df[

                filtered_df[
                    'active_dr'
                ].astype(
                    str
                ).str.strip().str.upper()

                ==

                'ACTIVE'
            ]
        )

        inactive_count = len(

            filtered_df[

                filtered_df[
                    'active_dr'
                ].astype(
                    str
                ).str.strip().str.upper()

                ==

                'NOTACTIVE'
            ]
        )

        total_count = len(
            filtered_df
        )

        speciality_count = len(

            filtered_df[
                'speciality'
            ].dropna().unique()

        )

        total_card.clear()
        active_card.clear()
        inactive_card.clear()
        speciality_card.clear()

        with total_card:

            ui.label(
                '👨‍⚕️ Total Doctors'
            )

            ui.label(
                str(total_count)
            ).classes(
                'text-4xl font-bold'
            )

        with active_card:

            ui.label(
                '🟢 Active'
            )

            ui.label(
                str(active_count)
            ).classes(
                'text-4xl font-bold text-green-600'
            )

        with inactive_card:

            ui.label(
                '🔴 Inactive'
            )

            ui.label(
                str(inactive_count)
            ).classes(
                'text-4xl font-bold text-red-600'
            )

        with speciality_card:

            ui.label(
                '🩺 Specialities'
            )

            ui.label(
                str(speciality_count)
            ).classes(
                'text-4xl font-bold'
            )

        # =====================================
        # GROUP BY speciality
        # =====================================

        grouped = dict(
            tuple(
                filtered_df.groupby(
                    'speciality'
                )
            )
        )

        with doctors_container:

            for index, speciality in enumerate(

                    sorted(
                        grouped.keys()
                    )

            ):

                speciality_df = grouped[
                    speciality
                ]

                speciality_df = speciality_df.copy()

                speciality_df[
                    "_sort_active"
                ] = speciality_df[
                    "active_dr"
                ].astype(
                    str
                ).str.upper().eq(
                    "ACTIVE"
                )

                speciality_df = speciality_df.sort_values(
                    by="_sort_active",
                    ascending=False
                )

                speciality_active = len(

                    speciality_df[

                        speciality_df[
                            "active_dr"
                        ].astype(
                            str
                        ).str.upper()

                        ==

                        "ACTIVE"
                    ]
                )

                speciality_inactive = (

                    len(
                        speciality_df
                    )

                    -

                    speciality_active
                )

                title = (

                    f'🩺 {speciality} '
                    f'({len(speciality_df)} Total | '
                    f'🟢 {speciality_active} | '
                    f'🔴 {speciality_inactive})'

                )

                with ui.card().classes(
                    'w-full rounded-2xl shadow-sm'
                ):

                    with ui.expansion(
                        title,
                        value=(
                            index == 0
                        )
                    ).classes(
                        'w-full'
                    ):

                        for _, doctor in speciality_df.iterrows():

                            active = (

                                str(
                                    doctor[
                                        'active_dr'
                                    ]
                                ).strip().upper()

                                ==

                                'ACTIVE'
                            )

                            border_color = (

                                'border-l-8 border-green-500'

                                if active

                                else

                                'border-l-8 border-red-400'
                            )

                            with ui.card().classes(

                                f'''

                                w-full
                                mb-2
                                rounded-xl
                                {border_color}

                                '''

                            ):

                                with ui.expansion(

                                    doctor[
                                        'dr_name'
                                    ]

                                ).classes(
                                    'w-full'
                                ):

                                    ui.badge(

                                        'Active'

                                        if active

                                        else

                                        'Inactive'

                                    ).props(

                                        'color=positive'

                                        if active

                                        else

                                        'color=negative'
                                    )

                                    with ui.grid(
                                        columns=2
                                    ).classes(
                                        'w-full mt-4'
                                    ):

                                        ui.label(
                                            f'code: {doctor["dr_code"]}'
                                        )

                                        ui.label(
                                            f'fee: {doctor["visit_fee"]}'
                                        )

                                        ui.label(
                                            f'email: {doctor["email"]}'
                                        )

                                        ui.label(
                                            f'speciality: {doctor["speciality"]}'
                                        )

                                        ui.label(
                                            f'joining date: {doctor["joining_date"]}'
                                        )

                                    ui.separator()

                                    with ui.row():

                                        ui.button(
                                            'Edit',
                                            icon='edit',
                                            on_click=lambda d=doctor:
                                            open_edit_doctor_dialog(
                                                d
                                            )
                                        ).props(
                                            'unelevated color=primary'
                                        )

                                        ui.button(
                                            'Delete',
                                            icon='delete',
                                            on_click=lambda d=doctor:
                                            open_delete_doctor_dialog(
                                                d
                                            )
                                        ).props(
                                            'unelevated color=negative'
                                        )

    refresh_doctors_view()

    doctor_search.on(
        'keyup',
        lambda e:
        refresh_doctors_view()
    )

    clear_btn.on(
        'click',
        lambda: (
            setattr(
                doctor_search,
                'value',
                ''
            ),
            refresh_doctors_view()
        )
    )