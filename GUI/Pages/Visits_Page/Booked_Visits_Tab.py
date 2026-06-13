from nicegui import ui
import pandas as pd
import Cache
from sqlalchemy import create_engine, text
from datetime import date, timedelta
import sys
import psycopg2
sys.path.append("..")
from Keys.PostGresKey import POSTGRES_URL
from Components.Medication_Search import (search_medications)
import ast
from fpdf import FPDF
from pathlib import Path


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
DAY_COLUMNS = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday"
]
def safe_notify(client, message, color='positive'):

    try:

        with client:

            ui.notify(
                message,
                color=color
            )

    except Exception as e:

        print(f'Notification Error: {e}')

def get_icd_cache():

    if Cache.ICD_DF_CACHE is None:

        print(
            'Loading ICD Cache...'
        )

        query = """

        SELECT

            icd_main_disease_code,
            icd_main_disease_description,
            icd_chronic

        FROM icd_codes

        
        ORDER BY

            icd_main_disease_code

        """

        icd_df = pd.read_sql(

            query,

            engine

        )

        icd_options = {}

        icd_lookup = {}

        chronic_options = {}

        for _, row in icd_df.iterrows():


            display_text = (

                f'{row["icd_main_disease_code"]} | '

                f'{row["icd_main_disease_description"]}'

            )

            icd_options[

                row["icd_main_disease_code"]

            ] = display_text

            if row["icd_chronic"]:

                chronic_options[
                    row["icd_main_disease_code"]
                ] = display_text

            icd_lookup[

                row["icd_main_disease_code"]

            ] = row[

                "icd_main_disease_description"

            ]

        Cache.ICD_DF_CACHE = (
            icd_df
        )

        Cache.ICD_OPTIONS_CACHE = (
            icd_options
        )

        Cache.ICD_LOOKUP_CACHE = (
            icd_lookup
        )

        Cache.ICD_CHRONIC_OPTIONS_CACHE = (
            chronic_options
        )

    return (

        Cache.ICD_DF_CACHE,

        Cache.ICD_OPTIONS_CACHE,

        Cache.ICD_CHRONIC_OPTIONS_CACHE,

        Cache.ICD_LOOKUP_CACHE

    )

def get_labs_cache():

    if Cache.LABS_DF_CACHE is None:

        print(
            'Loading Labs Cache...'
        )

        query = """

        SELECT

            lab_code,
            lab_group,
            lab_name

        FROM labs_ref

        ORDER BY

            lab_group,
            lab_name

        """

        labs_df = pd.read_sql(
            query,
            engine
        )

        labs_options = {}

        labs_lookup = {}

        for _, row in labs_df.iterrows():

            display_text = (

                f'{row["lab_code"]} | '

                f'{row["lab_group"]} | '

                f'{row["lab_name"]}'

            )

            labs_options[
                row["lab_code"]
            ] = display_text

            labs_lookup[
                row["lab_code"]
            ] = row["lab_name"]

        Cache.LABS_DF_CACHE = labs_df

        Cache.LABS_OPTIONS_CACHE = labs_options

        Cache.LABS_LOOKUP_CACHE = labs_lookup

    return (

        Cache.LABS_DF_CACHE,

        Cache.LABS_OPTIONS_CACHE,

        Cache.LABS_LOOKUP_CACHE

    )

def get_scans_cache():

    if Cache.SCANS_DF_CACHE is None:

        print(
            'Loading Scans Cache...'
        )

        query = """

        SELECT

            scan_code,
            scan_group,
            scan_name

        FROM scans_ref

        ORDER BY

            scan_group,
            scan_name

        """

        scans_df = pd.read_sql(
            query,
            engine
        )

        scans_options = {}

        scans_lookup = {}

        for _, row in scans_df.iterrows():

            display_text = (

                f'{row["scan_code"]} | '

                f'{row["scan_group"]} | '

                f'{row["scan_name"]}'

            )

            scans_options[
                row["scan_code"]
            ] = display_text

            scans_lookup[
                row["scan_code"]
            ] = row["scan_name"]

        Cache.SCANS_DF_CACHE = scans_df

        Cache.SCANS_OPTIONS_CACHE = scans_options

        Cache.SCANS_LOOKUP_CACHE = scans_lookup

    return (

        Cache.SCANS_DF_CACHE,

        Cache.SCANS_OPTIONS_CACHE,

        Cache.SCANS_LOOKUP_CACHE

    )

def format_diagnosis_for_prescription(

    diagnosis_codes

):

    if not diagnosis_codes:

        return []

    return [

        Cache.ICD_LOOKUP_CACHE.get(
            code,
            code
        )

        for code in diagnosis_codes

    ]

def normalize_pg_array(value):

    if value is None:

        return []

    if isinstance(value, list):

        return value

    if isinstance(value, tuple):

        return list(value)

    if isinstance(value, str):

        value = value.strip()

        if value == '':

            return []

        # JSON-like
        if value.startswith('['):

            try:

                return ast.literal_eval(value)

            except:

                return []

        # PostgreSQL Array
        if value.startswith('{'):

            value = value[1:-1]

            if not value:

                return []

            return [

                x.strip().replace('"', '')

                for x in value.split(',')

            ]

    return []

def format_requested_labs(codes):

    if Cache.LABS_LOOKUP_CACHE is None:

        get_labs_cache()

    if not codes:

        return "-"

    return "\n".join(

        Cache.LABS_LOOKUP_CACHE.get(
            code,
            code
        )

        for code in codes

    )

def format_requested_scans(codes):

    if Cache.SCANS_LOOKUP_CACHE is None:

        get_scans_cache()

    if not codes:

        return "-"

    return "\n".join(

        Cache.SCANS_LOOKUP_CACHE.get(
            code,
            code
        )

        for code in codes

    )

def format_diagnosis_codes(codes):

    if Cache.ICD_LOOKUP_CACHE is None:

        get_icd_cache()

    if not codes:

        return "-"

    return "\n".join(

        f"{code} - "

        f"{Cache.ICD_LOOKUP_CACHE.get(code, code)}"

        for code in codes

    )

def format_time(value):

    try:

        return pd.to_datetime(

            str(value)

        ).strftime(

            "%I:%M %p"

        )

    except:

        return str(value)
    
opened_visits = []
selected_visit = None
booked_visits_tabs_container = None
visit_details_container = None
left_panel_container = None
visit_medications = {}

def get_booked_visits():

    if Cache.BOOKED_VISITS_CACHE is None:

        query = """

        SELECT

            bv.booking_key,
            bv.visit_key,

            bv.status,

            bv.creation_time_stamp,

            bv.chief_complaint,

            bv.diagnosis_codes,

            bv.requested_labs,

            bv.requested_scans,

            bv.doctor_notes,

            bv.consultation_timestamp,

            p.patient_u_id,
            p.patient_name,
            p.phone_number,

            dl.dr_code,
            dl.dr_name,
            dl.speciality,

            av.scheduled_date,

            COALESCE(

                av.start_time_override,

                tt.scheduled_start_time

            ) AS start_time,

            COALESCE(

                av.end_time_override,

                tt.scheduled_end_time

            ) AS end_time,

            CONCAT(

                dl.dr_name,

                ' - ',

                TO_CHAR(

                    COALESCE(

                        av.start_time_override,

                        tt.scheduled_start_time

                    ),

                    'HH12:MI AM'

                )

            ) AS shift_name

        FROM booked_visits bv

        LEFT JOIN patients_list p

            ON bv.patient_u_id =
            p.patient_u_id

        LEFT JOIN available_visits av

            ON bv.visit_key =
            av.visit_key

        LEFT JOIN dr_time_table tt

            ON av.time_table_key =
            tt.time_table_key

        LEFT JOIN dr_list dl

            ON tt.dr_code =
            dl.dr_code

        ORDER BY

            av.scheduled_date,
            start_time

        """

        df = pd.read_sql(
            query,
            engine
        )

        for col in [

            "diagnosis_codes",

            "requested_labs",

            "requested_scans"

        ]:

            if col in df.columns:

                df[col] = df[col].apply(
                    normalize_pg_array
                )

        Cache.BOOKED_VISITS_CACHE = df

    return Cache.BOOKED_VISITS_CACHE

def reload_Booked_visits():

    global bookings_df

    Cache.BOOKED_VISITS_CACHE = None

    bookings_df = get_booked_visits()

def reload_and_refresh_booked_visits():
    global selected_visit
    global opened_visits
    reload_Booked_visits()

    refresh_visit_tabs()
  
def get_chronic_diagnosis_codes(

    diagnosis_codes

):

    icd_df, _, _, _ = get_icd_cache()

    chronic_codes = set(

        icd_df[

            icd_df["ICD_Chronic"]

            ==

            True

        ][

            "ICD_Main_Disease_Code"

        ]

    )

    return [

        code

        for code in diagnosis_codes

        if code in chronic_codes

    ]
    
def reload_booked_visits_cache():

    Cache.BOOKED_VISITS_CACHE = None

    return get_booked_visits()

def get_previous_visits(

    patient_u_id,current_booking_key

):

    query = """

    SELECT

        bv.booking_key,

        bv.visit_key,

        bv.status,

        bv.chief_complaint,

        bv.diagnosis_codes,

        bv.requested_labs,

        bv.requested_scans,

        bv.doctor_notes,

        bv.consultation_timestamp,

        av.scheduled_date,

        dl.dr_name,

        dl.speciality

    FROM booked_visits bv

    LEFT JOIN available_visits av

        ON bv.visit_key =
        av.visit_key

    LEFT JOIN dr_time_table dtt

        ON av.time_table_key =
        dtt.time_table_key

    LEFT JOIN dr_list dl

        ON dtt.dr_code =
        dl.dr_code

    WHERE

        bv.patient_u_id = :patient_u_id

        AND

        bv.booking_key <> :booking_key

        AND

        bv.status = 'Completed'

    ORDER BY

        av.scheduled_date DESC

    """

    return pd.read_sql(

        text(query),

        engine,

        params={

        "patient_u_id":

        patient_u_id,

        "booking_key":

        current_booking_key

    }

    )

def render_doctor_card(row):

    card = ui.card().classes(

        '''
        w-full
        cursor-pointer
        hover:bg-blue-50
        '''

    )

    with card:

        ui.label(

            row["patient_name"]

        ).classes(

            'font-bold text-lg'

        )

        ui.label(

            row["status"]

        ).classes(

            'text-gray-500'

        )

    card.on(

        'click',

        lambda v=row.to_dict():

        open_visit(v)

    )

def update_visit_status(
    booking_key,
    new_status
):

    global opened_visits
    global selected_visit
    client = ui.context.client
    with engine.connect() as conn:

        conn.execute(

            text("""

            UPDATE booked_visits

            SET status = :status

            WHERE booking_key = :booking_key

            """),

            {

                "status": new_status,
                "booking_key": booking_key

            }

        )

        conn.commit()

    # Refresh cache

    Cache.BOOKED_VISITS_CACHE = None

    fresh_df = get_booked_visits()

    # =========================
    # UPDATE OPENED TABS
    # =========================

    for i, visit in enumerate(opened_visits):

        if visit["booking_key"] == booking_key:

            match = fresh_df[

                fresh_df["booking_key"]

                ==

                booking_key

            ]

            if not match.empty:

                opened_visits[i] = (

                    match.iloc[0]

                    .to_dict()

                )

    # =========================
    # UPDATE SELECTED VISIT
    # =========================

    if selected_visit:

        if selected_visit["booking_key"] == booking_key:

            match = fresh_df[

                fresh_df["booking_key"]

                ==

                booking_key

            ]

            if not match.empty:

                selected_visit = (

                    match.iloc[0]

                    .to_dict()

                )

    # =========================
    # REDRAW UI
    # =========================

    reload_and_refresh_booked_visits()

    if selected_visit:

        show_visit_details(
            selected_visit
        )
    refresh_left_panel()
    safe_notify(client,

        f'Visit Updated To {new_status}',

        color='positive'

    )

def get_visit_medications(

    booking_key

):

    query = """

    SELECT

        medication_name,

        medictaion_dose,

        medictaion_dose_unit,

        frequency,

        frequency_unit

    FROM rx_medications

    WHERE

        booking_key = :booking_key

    ORDER BY

        md_line_key

    """

    return pd.read_sql(

        text(query),

        engine,

        params={

            "booking_key":
                booking_key

        }

    )

def render_admin_card(row):

    card = ui.card().classes(

        '''
        w-full
        cursor-pointer
        hover:bg-blue-50
        '''

    )

    with card:
        with ui.row().classes(
            'w-full justify-between items-center'
        ):
            ui.label(

                row["patient_name"]

            ).classes(

                'font-bold'

            )

            ui.label(

                row["dr_name"]

            )

        with ui.row().classes(
            'gap-1'
        ):

            ui.button(
                icon='visibility'
            ).props(
                'flat round'
            ).on(
                'click',
                lambda v=row.to_dict():
                open_visit(v)
            )

            if row["status"] == "Booked":

                ui.button(
                    icon='login'
                ).props(
                    'flat round'
                ).on(

                'click',

                lambda bk=row["booking_key"]:

                update_visit_status(

                    bk,

                    "Checked In"

                )

                )
                ui.button(
                    icon='cancel'
                ).props(
                    'flat round'
                ).on(

                        'click',

                        lambda bk=row["booking_key"]:

                        update_visit_status(

                            bk,

                            "Cancelled"

                        )

                )

def render_doctor_group(

    dr_name,

    doctor_df

):

    with ui.expansion(

        f"{dr_name} ({len(doctor_df)})",

        value=False

    ).classes(

        'w-full'

    ):

        for _, row in doctor_df.iterrows():

            render_admin_card(
                row
            )

def render_section(

    title,
    df,
    is_admin,
    is_doctor

):

    with ui.expansion(

        f"{title} ({len(df)})",

        value=True

    ).classes(

        'w-full'

    ):

        if df.empty:

            ui.label(

                'No Appointments'

            ).classes(

                'text-grey'

            )

            return

        if is_doctor:

            for _, row in df.iterrows():

                render_doctor_card(
                    row
                )

        elif is_admin:

            doctors = df.groupby(
                "dr_name"
            )

            for dr_name, doctor_df in doctors:

                render_doctor_group(

                    dr_name,

                    doctor_df

                )

def empty_visit_details():

    global visit_details_container

    if visit_details_container is None:

        return

    try:

        visit_details_container.clear()

    except Exception:

        return

    with visit_details_container:

        with ui.column().classes(

            '''
            w-full
            h-[600px]
            items-center
            justify-center
            '''

        ):

            ui.icon(

                'event_note'

            ).classes(

                'text-8xl text-gray-400'

            )

            ui.label(

                'Select a Visit'

            ).classes(

                'text-4xl font-bold text-gray-500'

            )

def render_visit_header(
    visit
):

    with ui.card().classes(

        'w-full p-4'

    ):

        with ui.row().classes(

            'w-full gap-8'

        ):

            ui.label(
                f'Booking: {visit["booking_key"]}'
            )

            ui.label(
                f'Patient: {visit["patient_name"]}'
            )

            ui.label(
                f'Doctor: {visit["dr_name"]}'
            )

        with ui.row().classes(

            'w-full gap-8'

        ):

            ui.label(
                f'Date: {visit["scheduled_date"]}'
            )

            ui.label(
                f'Speciality: {visit["speciality"]}'
            )

            ui.label(
                f'Status: {visit["status"]}'
            )

        ui.separator()

        # ==========================
        # VITALS
        # ==========================

        with ui.row().classes(
            'gap-2'
        ):

            ui.button(

                'Add Vitals',

                icon='monitor_heart'

            )

            ui.button(

                'Previous Vitals',

                icon='history'

            )

def save_visit_consultation(

    booking_key,

    patient_u_id,

    chief_complaint,

    diagnosis_codes,

    requested_labs,

    requested_scans,

    doctor_notes

    ):
    client = ui.context.client
    
    save_visit_medications(

    booking_key,

    patient_u_id,

    get_medications_rows(
    booking_key
    )

    )

    with engine.connect() as conn:

        conn.execute(

            text("""

            UPDATE booked_visits

            SET

                chief_complaint = :chief_complaint,

                diagnosis_codes = :diagnosis_codes,

                requested_labs = :requested_labs,

                requested_scans = :requested_scans,

                doctor_notes = :doctor_notes

            WHERE

                booking_key = :booking_key

            """),

            {

                "booking_key":
                    booking_key,

                "chief_complaint":
                    chief_complaint,

                "diagnosis_codes":
                    diagnosis_codes,

                "requested_labs":
                    requested_labs,

                "requested_scans":
                    requested_scans,

                "doctor_notes":
                    doctor_notes

            }

        )

        conn.commit()

    Cache.BOOKED_VISITS_CACHE = None

    safe_notify(client,

        'Visit Saved Successfully',

        color='positive'

    )

def update_patient_chronic_conditions(

    patient_u_id,

    diagnosis_codes

    ):

    chronic_diagnosis = (

        get_chronic_diagnosis_codes(

            diagnosis_codes

        )

    )

    if not chronic_diagnosis:

        return

    with engine.connect() as conn:

        existing = conn.execute(

            text("""

            SELECT

                chronic_conditions

            FROM patients_list

            WHERE

                patient_u_id

                =

                :patient_u_id

            """),

            {

                "patient_u_id":

                patient_u_id

            }

        ).scalar()

        existing = normalize_pg_array(

            existing

        )

        updated = list(

            set(

                existing

                +

                chronic_diagnosis

            )

        )

        conn.execute(

            text("""

            UPDATE patients_list

            SET

                chronic_conditions = :conditions

            WHERE

                patient_u_id = :patient_u_id

            """),

            {

                "conditions":
                    updated,

                "patient_u_id":
                    patient_u_id

            }

        )

        conn.commit()
        Cache.PATIENTS_CACHE = None

def save_visit_medications(

    booking_key,

    patient_u_id,

    medications_rows

    ):

    with engine.connect() as conn:

        conn.execute(

            text("""

            DELETE FROM rx_medications

            WHERE

                booking_key = :booking_key

            """),

            {

                "booking_key":
                booking_key

            }

        )

        for row in medications_rows:

            if not row.get(

                "medication_name"

            ):

                continue

            conn.execute(

                text("""

                INSERT INTO rx_medications (

                    Booking_Key,

                    Patient_U_ID,

                    Medication_Name,

                    Medictaion_Dose,

                    Medictaion_Dose_Unit,

                    Frequency,

                    Frequency_Unit

                )

                VALUES (

                    :booking_key,

                    :patient_u_id,

                    :medication_name,

                    :dose,

                    :dose_unit,

                    :frequency,

                    :frequency_unit

                )

                """),

                {

                    "booking_key":
                    booking_key,

                    "patient_u_id":
                    patient_u_id,

                    "medication_name":
                    row.get(
                        "medication_name"
                    ),

                    "dose":
                    row.get(
                        "dose"
                    ),

                    "dose_unit":
                    row.get(
                        "dose_unit"
                    ),

                    "frequency":
                    row.get(
                        "frequency"
                    ),

                    "frequency_unit":
                    row.get(
                        "frequency_unit"
                    )

                }

            )

        conn.commit()

def load_visit_medications(
    booking_key
    ):

    df = get_visit_medications(
        booking_key
    )

    rows = []

    for _, med in df.iterrows():

        rows.append({

            "medication_name":
            med["medication_name"],

            "dose":
            med["medictaion_dose"],

            "dose_unit":
            med["medictaion_dose_unit"],

            "frequency":
            med["frequency"],

            "frequency_unit":
            med["frequency_unit"]

        })

    visit_medications[
        booking_key
    ] = rows

def get_visit_for_pdf(

    booking_key

    ):

    with engine.connect() as conn:

        result = conn.execute(

            text("""

            SELECT

                diagnosis_codes,
                requested_labs,
                requested_scans


            FROM booked_visits

            WHERE booking_key = :booking_key

            """),

            {

                "booking_key":

                booking_key

            }

        )

        row = result.mappings().first()

    if not row:

        return {}

    return dict(row)

def generate_prescription_pdf(
  
    visit,
    
    ):
    fresh_visit = get_visit_for_pdf(

        visit["booking_key"]

    )

    medications_df = get_visit_medications(

        visit["booking_key"]

    )
    client = ui.context.client
    # =====================================
    # CREATE FOLDER
    # =====================================

    Path(

        "Prescriptions"

    ).mkdir(

        exist_ok=True

    )

    pdf_path = (

        f"Prescriptions/"

        f"{visit['booking_key']}.pdf"

    )

    # =====================================
    # PDF
    # =====================================

    pdf = FPDF(

        orientation='P',

        unit='mm',

        format='A4'

    )

    pdf.add_page()

    pdf.set_auto_page_break(

        auto=True,

        margin=15

    )

    # =====================================
    # HEADER
    # =====================================

    pdf.set_font(

        "Arial",

        "B",

        18

    )

    pdf.cell(

        30,

        10,

        "LOGO",

        border=1,

        align="C"

    )

    pdf.cell(

        10,

        10,

        ""

    )

    pdf.set_font(

        "Arial",

        "B",

        16

    )

    pdf.cell(

        0,

        8,

        visit["dr_name"],

        ln=True

    )

    pdf.cell(

        40,

        8,

        ""

    )

    pdf.set_font(

        "Arial",

        "",

        12

    )

    pdf.cell(

        0,

        8,

        visit["speciality"],

        ln=True

    )

    pdf.ln(5)

    pdf.line(

        10,

        pdf.get_y(),

        200,

        pdf.get_y()

    )

    pdf.ln(5)

    # =====================================
    # PATIENT INFO
    # =====================================

    pdf.set_font(

        "Arial",

        "",

        12

    )

    pdf.cell(

        100,

        8,

        f"Patient: {visit['patient_name']}"

    )

    pdf.cell(

        0,

        8,

        f"Visit Date: {visit['scheduled_date']}",

        ln=True

    )

    pdf.ln(3)

    pdf.line(

        10,

        pdf.get_y(),

        200,

        pdf.get_y()

    )

    pdf.ln(5)

    # =====================================
    # DIAGNOSIS
    # =====================================
    diagnosis_codes = normalize_pg_array(

        fresh_visit.get(
            "diagnosis_codes"
        )
    )

    diagnoses = [

        Cache.ICD_LOOKUP_CACHE.get(
            code,
            code
        )

        for code in diagnosis_codes
    ]

    if diagnoses:

        pdf.set_font(

            "Arial",

            "B",

            12

        )

        pdf.cell(

            25,

            8,

            "Diagnosis:"

        )

        pdf.set_font(

            "Arial",

            "",

            12

        )

        pdf.multi_cell(

            160,

            8,

            ", ".join(

                diagnoses

            )

        )

        pdf.ln(2)

        pdf.line(

            10,

            pdf.get_y(),

            200,

            pdf.get_y()

        )

        pdf.ln(5)

    # =====================================
    # RX
    # =====================================

    pdf.set_font(

        "Arial",

        "B",

        18

    )

    pdf.cell(

        0,

        10,

        "Rx",

        ln=True

    )

    pdf.set_font(

        "Arial",

        "",

        13

    )

    for _, med in medications_df.iterrows():

        medication_name = med.get(

            "medication_name"

        )

        if not medication_name:

            continue

        dose = med.get(
            "medictaion_dose"
        ) or ""

        dose_unit = med.get(
            "medictaion_dose_unit"
        ) or ""

        frequency = med.get(

            "frequency"

        ) or ""

        frequency_unit = med.get(

            "frequency_unit"

        ) or ""

        pdf.cell(

            0,

            8,

            (

                f"{medication_name} "

                f"{dose} "

                f"{dose_unit}"

                f" - "

                f"{frequency} "

                f"{frequency_unit}"

            ),

            ln=True

        )

    pdf.ln(3)

    # =====================================
    # LABS
    # =====================================

    requested_labs = fresh_visit.get(

        "requested_labs"

    ) or []

    if requested_labs:

        pdf.line(

            10,

            pdf.get_y(),

            200,

            pdf.get_y()

        )

        pdf.ln(4)

        pdf.set_font(

            "Arial",

            "B",

            12

        )

        pdf.cell(

            0,

            8,

            "Requested Labs",

            ln=True

        )

        pdf.set_font(

            "Arial",

            "",

            11

        )

        for lab in requested_labs:

            pdf.cell(

                0,

                8,

                Cache.LABS_LOOKUP_CACHE.get(

                    lab,

                    lab

                ),

                ln=True

            )

    # =====================================
    # SCANS
    # =====================================

    requested_scans = fresh_visit.get(

        "requested_scans"

    ) or []

    if requested_scans:

        pdf.line(

            10,

            pdf.get_y(),

            200,

            pdf.get_y()

        )

        pdf.ln(4)

        pdf.set_font(

            "Arial",

            "B",

            12

        )

        pdf.cell(

            0,

            8,

            "Requested Scans",

            ln=True

        )

        pdf.set_font(

            "Arial",

            "",

            11

        )

        for scan in requested_scans:

            pdf.cell(

                0,

                8,

                Cache.SCANS_LOOKUP_CACHE.get(

                    scan,

                    scan

                ),

                ln=True

            )

    # =====================================
    # SAVE
    # =====================================

    pdf.output(

        pdf_path

    )

    safe_notify(client,

        f'Prescription Saved: {pdf_path}',

        color='positive'

    )

def complete_visit(

    booking_key,

    patient_u_id,

    chief_complaint,

    diagnosis_codes,

    requested_labs,

    requested_scans,

    doctor_notes

):
    client = ui.context.client
    # ==========================
    # SAVE VISIT FIRST
    # ==========================

    save_visit_consultation(

        booking_key,

        patient_u_id,

        chief_complaint,

        diagnosis_codes,

        requested_labs,

        requested_scans,

        doctor_notes

    )


    update_patient_chronic_conditions(

        patient_u_id,

        diagnosis_codes

    )


    save_visit_medications(

    booking_key,

    patient_u_id,

    get_medications_rows(
        booking_key
    )

    )
    # ==========================
    # COMPLETE VISIT
    # ==========================

    with engine.connect() as conn:

        conn.execute(

            text("""

            UPDATE booked_visits

            SET

                status = 'Completed',

                consultation_timestamp = NOW()

            WHERE

                booking_key = :booking_key

            """),

            {

                "booking_key":
                    booking_key

            }

        )

        conn.commit()

    Cache.BOOKED_VISITS_CACHE = None
    Cache.PATIENTS_CACHE = None

    safe_notify(client,

        'Visit Completed Successfully',

        color='positive'

    )

    update_visit_status(

        booking_key,

        "Completed"

    )

MEDICATION_DOSE_UNITS = [

    'tab',
    'cap',
    'amp',
    'ml',
    'iu',
    'cap',
    'drop',
    'puff',
    'sach'

]

MEDICATION_FREQUENCY_UNITS = [

    'Time(s) Daily',
    'Time(s) Weekly',
    'Time(s) Monthly',
    'PRN'

]

def render_visit_consultation(
    visit
    ):
    (
    _,
        ICD_OPTIONS,
        _,
        _
    ) = get_icd_cache()
    options=ICD_OPTIONS
    
    (
        _,
        LAB_OPTIONS,
        _
    ) = get_labs_cache()

    (
        _,
        SCAN_OPTIONS,
        _
    ) = get_scans_cache()

    medications_rows = get_medications_rows(

    visit["booking_key"]

    )

    if not medications_rows:

        medications_rows.append({

            "medication_name": "",

            "dose": None,

            "dose_unit": MEDICATION_DOSE_UNITS[0],

            "frequency": 1,

            "frequency_unit": MEDICATION_FREQUENCY_UNITS[0]

        })

    with ui.expansion(
                    'Visit Consultation',
                    value=True
                ).classes(
                    'w-full'
                ):

                    with ui.column().classes(

                        'w-full gap-4 p-2'

                    ):
                                        

                        # ==========================
                        # CHIEF COMPLAINT
                        # ==========================

                        chief_complaint = ui.textarea(

                            'Chief Complaint',

                            value=visit.get(
                                "chief_complaint",
                                ""
                            ) or ""

                        ).classes(
                            'w-full'
                        )

                        # ==========================
                        # DIAGNOSIS
                        # ==========================

                        diagnosis_codes = ui.select(

                            options=ICD_OPTIONS,

                            label='Diagnosis',

                            multiple=True,

                            value=visit.get(
                                "diagnosis_codes",
                                []
                            ) or []

                        ).props(

                            'use-input use-chips fill-input'
                        ).classes(
                            'w-full'
                        )

                        # ==========================
                        # LABS
                        # ==========================

                        requested_labs = ui.select(

                            options=LAB_OPTIONS,
                            label='Labs to Request',
                            multiple=True,

                            value=visit.get(
                                "requested_labs"
                            ) or []

                        ).props(

                            'use-input use-chips fill-input'

                        ).classes(

                            'w-full'

                        )

                        # ==========================
                        # SCANS
                        # ==========================

                        requested_scans = ui.select(

                            options=SCAN_OPTIONS,
                            label='Scans to Request',
                            multiple=True,

                            value=visit.get(
                                "requested_scans"
                            ) or []

                        ).props(

                            'use-input use-chips fill-input'

                        ).classes(

                            'w-full'

                        )

                        # ==========================
                        # DOCTOR NOTES
                        # ==========================

                        doctor_notes = ui.textarea(

                            'Doctor Notes',

                            value=visit.get(
                                "doctor_notes",
                                ""
                            ) or ""

                        ).classes(
                            'w-full'
                        )


                        # ==========================
                        # MEDICATIONS
                        # ==========================

                        ui.separator()

                        ui.label(

                            'Prescribed Medications'

                        ).classes(

                            'text-h6 font-bold'

                        )

                        

                        medications_container = ui.column().classes(

                            'w-full gap-2'

                        )

                        def open_medication_search_dialog(row):

                            with ui.dialog() as dialog:

                                with ui.card().classes('w-[800px]'):

                                    keyword = ui.input(
                                        'Search Medication'
                                    ).classes(
                                        'w-full'
                                    )

                                    results_container = ui.column().classes(
                                        'w-full'
                                    )

                                    def do_search():

                                        results_container.clear()

                                        drugs = search_medications(
                                            keyword.value
                                        )

                                        with results_container:

                                            for drug in drugs[:50]:

                                                ui.button(

                                                    drug,

                                                    on_click=lambda d=drug:

                                                    select_drug(
                                                        d
                                                    )

                                                ).classes(
                                                    'w-full'
                                                )

                                    def select_drug(drug):

                                        row["medication_name"] = drug

                                        render_medications()

                                        dialog.close()

                                    ui.button(

                                        'Search',

                                        icon='search',

                                        on_click=do_search

                                    )

                            dialog.open()

                        def render_medications():

                            medications_container.clear()

                            with medications_container:

                                for row in medications_rows:

                                    with ui.row().classes(

                                        'w-full items-center gap-2'

                                    ):

                                        med_name = ui.input(
                                            'Medication'
                                        ).classes(
                                            'w-72'
                                        )

                                        ui.button(
                                            icon='search',
                                            on_click=lambda r=row:
                                            open_medication_search_dialog(r)
                                        )

                                        med_name.bind_value(

                                            row,

                                            'medication_name'

                                        )

                                        dose = ui.number(

                                            'Dose',

                                            value=row.get(
                                                'dose'
                                            )

                                        ).classes(

                                            'w-24'

                                        )

                                        dose.bind_value(

                                            row,

                                            'dose'

                                        )

                                        dose_unit = ui.select(

                                            options=MEDICATION_DOSE_UNITS,

                                            value=row.get(
                                                'dose_unit'
                                            ) or MEDICATION_DOSE_UNITS[0]

                                        ).classes(

                                            'w-32'

                                        )

                                        dose_unit.bind_value(

                                            row,

                                            'dose_unit'

                                        )

                                        frequency = ui.number(

                                            'Frequency',

                                            value=row.get(
                                                'frequency',
                                                1
                                            )

                                        ).classes(

                                            'w-24'

                                        )

                                        frequency.bind_value(

                                            row,

                                            'frequency'

                                        )

                                        frequency_unit = ui.select(

                                            options=MEDICATION_FREQUENCY_UNITS,

                                            value=row.get(
                                                'frequency_unit'
                                            ) or MEDICATION_FREQUENCY_UNITS[0]

                                        ).classes(

                                            'w-36'

                                        )

                                        frequency_unit.bind_value(

                                            row,

                                            'frequency_unit'

                                        )

                                        ui.button(

                                            icon='close',

                                            on_click=lambda r=row:

                                            remove_medication_row(
                                                r
                                            )

                                        ).props(

                                            'flat round color=negative'

                                        )

                        def remove_medication_row(row):

                            if row in medications_rows:

                                medications_rows.remove(
                                    row
                                )

                            render_medications()

                        def add_medication_row(
                            booking_key
                        ):

                            medications_rows = get_medications_rows(
                                booking_key
                            )

                            medications_rows.append({

                                "medication_name": "",

                                "dose": None,

                                "dose_unit": MEDICATION_DOSE_UNITS[0],

                                "frequency": 1,

                                "frequency_unit": MEDICATION_FREQUENCY_UNITS[0]

                            })

                            render_medications()
                            

                        ui.button(

                            'Add Medication',

                            on_click=lambda:

                            add_medication_row(

                                visit["booking_key"]

                            )

                        )

                        ui.separator()


                        # ==========================
                        # ACTION BUTTONS
                        # ==========================

                        with ui.row().classes(
                            'w-full justify-end gap-2'
                        ):

                            ui.button(

                                'Save Visit',

                                icon='save',

                                on_click=lambda:

                                    save_visit_consultation(

                                        visit["booking_key"],

                                        visit["patient_u_id"],

                                        chief_complaint.value,

                                        diagnosis_codes.value,

                                        requested_labs.value,

                                        requested_scans.value,

                                        doctor_notes.value

                                    )

                            )

                            ui.button(

                                'Generate Prescription',

                                icon='picture_as_pdf',

                                color='red',

                                on_click=lambda:

                                generate_prescription_pdf(
                                    visit
                                )

                            )

                            ui.button(

                                'Complete Visit',

                                icon='task_alt',

                                color='green',

                                on_click=lambda:

                                complete_visit(

                                    visit["booking_key"],

                                    visit["patient_u_id"],

                                    chief_complaint.value,

                                    diagnosis_codes.value,

                                    requested_labs.value,

                                    requested_scans.value,

                                    doctor_notes.value

                                )

                            )

def render_patient_information(
    visit
):
    with ui.expansion(

            'Patient Information',

            value=False

        ).classes(

            'w-full'

        ):

            with ui.tabs().classes(

                'w-full'

            ) as patient_tabs:

                profile_tab = ui.tab(
                    'Patient Profile'
                )

                previous_visits_tab = ui.tab(
                    'Previous Visits'
                )

                labs_history_tab = ui.tab(
                    'Labs History'
                )

                scans_history_tab = ui.tab(
                    'Scans History'
                )

            with ui.tab_panels(

                patient_tabs,

                value=profile_tab

            ).classes(

                'w-full'

            ):
                with ui.tab_panel(

                    profile_tab

                ):
                    ui.label(

                        'Patient Profile Will Be Rendered Here'

                    ).classes(

                        'text-h6'

                    )

                with ui.tab_panel(

                    previous_visits_tab

                ):
                    previous_visits_df = (

                        get_previous_visits(

                            visit[
                                "patient_u_id"
                            ],

                            visit[
                                "booking_key"
                            ]

                        )

                    )
                    if previous_visits_df.empty:

                        ui.label(

                            'No Previous Visits'

                        )

                    else:
                        for _, old_visit in previous_visits_df.iterrows():

                            with ui.expansion(

                                f'''

                                {old_visit["scheduled_date"]}

                                |

                                {old_visit["speciality"]}

                                |

                                {old_visit["dr_name"]}

                                
                                '''

                            ).classes(

                                'w-full'

                            ):
                                

                                ui.label(

                                    f'Speciality: '

                                    f'{old_visit["speciality"]}'

                                )

                                ui.label(

                                    f'Status: '

                                    f'{old_visit["status"]}'

                                )
                                ui.separator()

                                ui.label(

                                    'Chief Complaint'

                                ).classes(

                                    'font-bold'

                                )

                                ui.label(

                                    old_visit.get(

                                        "chief_complaint",

                                        "-"

                                    ) or "-"

                                )

                                ui.separator()
                                ui.label(

                                    'Diagnosis'

                                ).classes(

                                    'font-bold'

                                )

                                ui.label(

                                    format_diagnosis_codes(

                                        old_visit.get(
                                            "diagnosis_codes"
                                        )

                                    )

                                )

                                ui.separator()
                                ui.label(

                                    'Doctor Notes'

                                ).classes(

                                    'font-bold'

                                )

                                ui.label(

                                    old_visit.get(

                                        "doctor_notes",

                                        "-"

                                    ) or "-"

                                )

                                ui.separator()

                                ui.label(

                                    'Requested Labs'

                                ).classes(

                                    'font-bold'

                                )

                                ui.label(

                                    format_requested_labs(

                                        old_visit.get(
                                            "requested_labs"
                                        )

                                    )

                                )
                                ui.separator()

                                ui.label(

                                    'Requested Scans'

                                ).classes(

                                    'font-bold'

                                )

                                ui.label(

                                    format_requested_scans(

                                        old_visit.get(
                                            "requested_scans"
                                        )

                                    )

                                )

                                ui.separator()

                                ui.label(

                                    'Medications'

                                ).classes(

                                    'font-bold'
                                )
                                medications_df = (

                                    get_visit_medications(

                                        old_visit[
                                            "booking_key"
                                        ]

                                    )

                                )
                                if medications_df.empty:

                                    ui.label(
                                        '-'
                                    )
                                for _, med in medications_df.iterrows():

                                    ui.label(

                                        f"""

                                        {med["medication_name"]}

                                        |

                                        {med["medictaion_dose"]}

                                        {med["medictaion_dose_unit"]}

                                        |

                                        {med["frequency"]}

                                        {med["frequency_unit"]}

                                        """

                                    )


                with ui.tab_panel(

                    labs_history_tab

                ):

                    ui.label(

                        'Coming Soon'

                    )
                with ui.tab_panel(

                    scans_history_tab

                ):

                    ui.label(

                        'Coming Soon'

                    )

def show_visit_details(visit):

    if visit_details_container is None:

        return

    try:

        visit_details_container.clear()

    except Exception:

        return

    
    role = Cache.CURRENT_USER["role"]

    is_admin = role in [

        "Admin",

        "Super Admin",

        "Reception"

    ]

    is_doctor = role == "Doctor"


    with visit_details_container:

        render_visit_header(
        visit
        )

        # =====================================
        # VISIT CONSULTATION
        # =====================================

        if is_doctor:
            render_visit_consultation(
        visit
        )

        # =====================================
        # PATIENT PROFILE
        # =====================================
        render_patient_information(
        visit
        )  

def get_visit_by_booking_key(
    booking_key
):

    fresh_df = get_booked_visits()

    match = fresh_df[

        fresh_df["booking_key"]

        ==

        booking_key

    ]

    if match.empty:

        return None

    visit = (

        match.iloc[0]

        .to_dict()

    )

    visit["diagnosis_codes"] = normalize_pg_array(

        visit.get(
            "diagnosis_codes"
        )

    )

    visit["requested_labs"] = normalize_pg_array(

        visit.get(
            "requested_labs"
        )

    )

    visit["requested_scans"] = normalize_pg_array(

        visit.get(
            "requested_scans"
        )

    )

    return visit

def get_medications_rows(
    booking_key
):

    if booking_key not in visit_medications:

        visit_medications[
            booking_key
        ] = []

    return visit_medications[
        booking_key
    ]

def open_visit(visit):

    global selected_visit

    fresh_visit = (

        get_visit_by_booking_key(

            visit["booking_key"]

        )

    )

    if fresh_visit:

        visit = fresh_visit

    exists = any(

        v["booking_key"]

        ==

        visit["booking_key"]

        for v in opened_visits

    )

    if not exists:

        opened_visits.append(
            visit
        )

    else:

        for i, v in enumerate(

            opened_visits

        ):

            if (

                v["booking_key"]

                ==

                visit["booking_key"]

            ):

                opened_visits[i] = visit

                break

    selected_visit = visit

    load_visit_medications(
        visit["booking_key"]
    )

    refresh_visit_tabs()

    show_visit_details(
        visit
    )

def close_visit(visit):

    global selected_visit

    opened_visits[:] = [

        v

        for v in opened_visits

        if

        v["booking_key"]

        !=

        visit["booking_key"]

    ]

    if (

        selected_visit

        and

        selected_visit["booking_key"]

        ==

        visit["booking_key"]

    ):

        if opened_visits:

            selected_visit = (

                opened_visits[0]

            )

            show_visit_details(

                selected_visit

            )

        else:

            selected_visit = None

            empty_visit_details()

    refresh_visit_tabs()

def refresh_visit_tabs():

    global booked_visits_tabs_container

    if booked_visits_tabs_container is None:

        return

    try:

        booked_visits_tabs_container.clear()

    except RuntimeError:

        return

    with booked_visits_tabs_container:

        with ui.row().classes(

            'gap-2 flex-wrap'

        ):

            for visit in opened_visits:

                active = (

                    selected_visit

                    and

                    selected_visit["booking_key"]

                    ==

                    visit["booking_key"]

                )

                bg = (

                    'bg-blue-100'

                    if active

                    else 'bg-white'

                )

                tab_card = ui.card().classes(

                    f'px-4 py-2 cursor-pointer {bg}'

                )

                tab_card.on(

                    'click',

                    lambda v=visit:

                    open_visit(v)

                )

                with tab_card:

                    with ui.row().classes(

                        'items-center gap-2'

                    ):
                        status_color = {

                            "Checked In":
                                "green",

                            "Booked":
                                "orange",

                            "Completed":
                                "blue",

                            "Cancelled":
                                "red",

                            "No Show":
                                "grey"

                        }.get(
                            visit["status"],
                            "grey"
                        )

                        ui.icon(
                            'circle'
                        ).style(
                            f'color:{status_color};font-size:12px'
                        )

                        label = ui.label(
                            visit["patient_name"][:15]
                        ).classes(
                            'font-bold'
                        )

                        ui.tooltip(
                            visit["patient_name"]
                        )

                        close_btn = ui.button(
                            icon='close'
                        ).props(
                            'flat round dense'
                        )

                        close_btn.on(

                            'click.stop',

                            lambda v=visit:
                            close_visit(v)

                        )

def refresh_left_panel():

    global left_panel_container

    if left_panel_container is None:

        return

    try:

        left_panel_container.clear()

    except Exception:

        return

    bookings_df = get_booked_visits()

    today = date.today()

    tomorrow = today + timedelta(days=1)

    bookings_df["scheduled_date"] = pd.to_datetime(
        bookings_df["scheduled_date"]
    ).dt.date

    role = Cache.CURRENT_USER["role"]

    is_admin = role in [

        "Admin",
        "Super Admin",
        "Reception"

    ]

    is_doctor = role == "Doctor"

    if is_doctor:

        bookings_df = bookings_df[

            bookings_df["dr_code"]

            ==

            Cache.CURRENT_USER["dr_code"]

        ]

    today_df = bookings_df[
        bookings_df["scheduled_date"] == today
    ]

    tomorrow_df = bookings_df[
        bookings_df["scheduled_date"] == tomorrow
    ]

    upcoming_df = bookings_df[
        bookings_df["scheduled_date"] > tomorrow
    ]

    with left_panel_container:

        render_section(
            "Today's Visits",
            today_df,
            is_admin,
            is_doctor
        )

        render_section(
            "Tomorrow's Visits",
            tomorrow_df,
            is_admin,
            is_doctor
        )

        render_section(
            "Upcoming Visits",
            upcoming_df,
            is_admin,
            is_doctor
        )

def render_booked_visits_tab():
    global bookings_df
    bookings_df = get_booked_visits()
    global opened_visits
    global selected_visit
    global left_panel_container
    today = date.today()

    tomorrow = (
        today +
        timedelta(days=1)
    )

    bookings_df[
    "scheduled_date"
        ] = pd.to_datetime(

            bookings_df[
                "scheduled_date"
            ]

        ).dt.date
    
    role = Cache.CURRENT_USER["role"]
    is_admin = role in [

    "Admin",

    "Super Admin",

    "Reception"

        ]
    is_doctor = role == "Doctor"
    if is_doctor:

        bookings_df = bookings_df[

            bookings_df["dr_code"]

            ==

            Cache.CURRENT_USER["dr_code"]

        ]
    
    today_df = bookings_df[

            bookings_df[
            "scheduled_date"
                ] == today

        ]
    
    tomorrow_df = bookings_df[

            bookings_df[
                "scheduled_date"
            ] == tomorrow

        ]
    
    upcoming_df = bookings_df[

            bookings_df[
                "scheduled_date"
            ] > tomorrow

        ]
    
    with ui.row().classes(

    'w-full gap-4 items-start'

    ):  
        # Left Section


        left_panel_container = ui.column().classes(
            'w-[450px] gap-2'
        )

        with left_panel_container:

    

            render_section(

            "Today's Visits",

            today_df,

            is_admin,

            is_doctor

            )

            render_section(

                "Tomorrow's Visits",

                tomorrow_df,

                is_admin,

                is_doctor

            )

            render_section(

                "Upcoming Visits",

                upcoming_df,

                is_admin,

                is_doctor

            )

        # Right Section
        with ui.column().classes(
                'flex-1 gap-4'
            ):

                global booked_visits_tabs_container
                global visit_details_container

                booked_visits_tabs_container = ui.column()

                visit_details_container = ui.column().classes(
                    'w-full'
                )

                if selected_visit:

                    show_visit_details(
                        selected_visit
                    )

                else:

                    empty_visit_details()



            