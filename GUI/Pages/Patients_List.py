from nicegui import ui
from sqlalchemy import create_engine, text
from fpdf import FPDF
import sys
sys.path.append("..")
from Keys.PostGresKey import POSTGRES_URL
from Components.Navigation import navigation_bar
import pandas as pd
import os
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
import numpy as np
import Cache
# =====================================================
# POSTGRESQL
# =====================================================
DATABASE_URL = POSTGRES_URL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)
# =====================================================
# Big Query
# =====================================================
SERVICE_ACCOUNT_FILE = "../Keys/BigQueryKey.json"
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE
)
bq_client = bigquery.Client(
    credentials=credentials,
    project="depihealthnux"
)

def load_patients():

    query = """
    SELECT *
    FROM patients_list
    ORDER BY patient_name
    """

    return pd.read_sql(
        query,
        engine
    )
def get_patients():

        if Cache.PATIENTS_CACHE is None:

            print(
                'Loading Patients Cache...'
            )

            Cache.PATIENTS_CACHE = (
                load_patients()
            )

        return Cache.PATIENTS_CACHE 
def get_icd_cache():

        if Cache.ICD_DF_CACHE is None:

            print(
                'Loading ICD Cache...'
            )

            icd_df = bq_client.query("""

            SELECT

                ICD_Main_Disease_Code,
                ICD_Main_Disease_Description,
                ICD_Chronic

            FROM depihealthnux.Depihealthnux_Main.ICD_Codes

            WHERE ICD_Chronic = TRUE

            """).to_dataframe()

            icd_options = {}

            icd_lookup = {}

            for _, row in icd_df.iterrows():

                display_text = (
                    f'{row["ICD_Main_Disease_Code"]} | '
                    f'{row["ICD_Main_Disease_Description"]}'
                )

                icd_options[
                    row["ICD_Main_Disease_Code"]
                ] = display_text

                icd_lookup[
                    row["ICD_Main_Disease_Code"]
                ] = row[
                    "ICD_Main_Disease_Description"
                ]

            Cache.ICD_DF_CACHE = icd_df

            Cache.ICD_OPTIONS_CACHE = (
                icd_options
            )

            Cache.ICD_LOOKUP_CACHE = (
                icd_lookup
            )

        return (
            Cache.ICD_DF_CACHE,
            Cache.ICD_OPTIONS_CACHE,
            Cache.ICD_LOOKUP_CACHE
        )
(
    ICD_DF,
    ICD_OPTIONS,
    ICD_LOOKUP
) = get_icd_cache()
def format_chronic_conditions(codes):

    if not codes:
        return "-"

    return "\n".join(

        f"{code} - {Cache.ICD_LOOKUP_CACHE.get(code, code)}"

        for code in codes
    )

# =====================================================
# GLOBAL STATE
# =====================================================

patients = get_patients()
opened_patients = []
selected_patient = None
patient_cards_container = None
tabs_container = None
details_container = None
search_input = None

@ui.page('/patients')

def patients_page():
    navigation_bar(
    active='patients'
)
    if Cache.CURRENT_USER is None:

        ui.navigate.to('/')

        return

    # =====================================================
    # SAFE NOTIFY
    # =====================================================

    def safe_notify(client, message, color='positive'):

        try:

            with client:

                ui.notify(
                    message,
                    color=color
                )

        except Exception as e:

            print(f'Notification Error: {e}')
    # =====================================================
    # CSS
    # =====================================================
    def section_expansion(
        title,
        **kwargs
    ):

        return ui.expansion(
            title,
            **kwargs
        ).classes(
            'w-full section-expansion'
        )


    ui.add_head_html("""

    <style>

    .section-expansion .q-item__label {
        font-size: 14px !important;
        font-weight: 700 !important;
    }

    </style>

    """)


    # =====================================================
    # LOAD PATIENTS
    # =====================================================
   
    
    


    # =====================================================
    # Dropdown Constants
    # =====================================================
    GENDER_OPTIONS = [
        "Male",
        "Female"
    ]

    OCCUPATION_OPTIONS = [
        "Office Based Work",
        "Manual Work",
        "Both"
    ]

    SMOKER_OPTIONS = [
        "Active",
        "Passive",
        "No"
    ]

    BLOOD_GROUP_OPTIONS = [
        "A+","A-",
        "B+","B-",
        "AB+","AB-",
        "O+","O-"
    ]
    # =====================================================
    # BMI Categorization
    # =====================================================
    def get_bmi_category(bmi):

        if bmi is None:
            return None

        if bmi < 18.5:
            return "Underweight"

        elif bmi < 25:
            return "Normal"

        elif bmi < 30:
            return "Overweight"

        else:
            return "Obese"


    # =====================================================
    # REFRESH PATIENT LIST
    # =====================================================

    def refresh_patient_list():

        patient_cards_container.clear()

        keyword = str(
            search_input.value or ''
        ).strip().lower()

        filtered = patients[

            patients["patient_name"]

            .fillna("")

            .astype(str)

            .str.lower()

            .str.contains(
                keyword,
                na=False
            )

            |

            patients["phone_number"]

            .fillna("")

            .astype(str)

            .str.lower()

            .str.contains(
                keyword,
                na=False
            )

            |

            (

                patients["national_id"]

                .fillna("")

                .astype(str)

                .str.lower()

                ==

                keyword

            )

        ]

        with patient_cards_container:

            for _, patient in filtered.iterrows():

                with ui.card().classes(
                    'w-full p-4 rounded-2xl shadow-sm hover:shadow-md transition'
                ):

                    with ui.row().classes(
                        'w-full items-center justify-between'
                    ):

                        with ui.column().classes(
                            'gap-1'
                        ):

                            ui.label(
                                patient["patient_name"]
                            ).classes(
                                'text-xl font-bold'
                            )

                            ui.label(
                                str(
                                    patient["phone_number"]
                                )
                            ).classes(
                                'text-gray-500'
                            )

                            current_patient = patient.copy()

                            ui.button(

                                icon='visibility',

                                on_click=lambda p=current_patient:
                                open_patient(p)

                            ).props(
                                'flat round'
                            )
    # =====================================================
    # REFRESH TABS
    # =====================================================

    def refresh_tabs():

        tabs_container.clear()

        with tabs_container:

            with ui.row().classes(
                'gap-2 flex-wrap'
            ):
                for patient in opened_patients:
                    active = (
                            selected_patient
                            and
                            selected_patient["patient_u_id"]
                            == patient["patient_u_id"]
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
                        lambda p=patient:
                        open_patient(p)
                    )

                    with tab_card:
                        with ui.row().classes(
                                'items-center gap-2'
                        ):
                            ui.label(
                                patient["patient_name"][:15]
                            ).classes(
                                'font-bold'
                            )

                            ui.button(
                                icon='close',
                                on_click=lambda p=patient:
                                close_patient(p)
                            ).props(
                                'flat round dense'
                            )

    # =====================================================
    # EMPTY DETAILS
    # =====================================================

    def empty_details():

        details_container.clear()

        with details_container:

            with ui.column().classes(
                'w-full h-[500px] items-center justify-center'
            ):

                ui.icon(
                    'person_search'
                ).classes(
                    'text-8xl text-gray-400'
                )

                ui.label(
                    'Select a patient'
                ).classes(
                    'text-4xl font-bold text-gray-500'
                )

    # =====================================================
    # INFO CARD
    # =====================================================

    def info_card(title, value):

        with ui.card().classes(
            'p-4 rounded-2xl bg-gray-50 shadow-sm'
        ):

            ui.label(title).classes(
                'font-bold text-gray-500'
            )

            ui.label(
                value if value else "-"
            ).classes(
                'text-M'
            ).style(
                'white-space: pre-line'
            )

    # =====================================================
    # SHOW DETAILS
    # =====================================================

    def show_patient_details(patient):

        details_container.clear()

        with details_container:

            with ui.card().classes(
                'w-full p-8 rounded-3xl shadow-sm max-w-[1800px]'
            ):

                with ui.row().classes(
                    'w-full justify-between items-start'
                ):

                    with ui.column():

                        ui.label(
                            patient["patient_name"]
                        ).classes(
                            'text-2xl font-bold'
                        )

                        ui.label(
                            patient["patient_u_id"]
                        ).classes(
                            'text-gray-500 text-lg'
                        )

                    with ui.row().classes(
                        'gap-2'
                    ):

                        ui.button(
                            icon='edit',
                            on_click=lambda:
                            open_edit_dialog(patient)
                        ).props(
                            'flat round'
                        )

                        ui.button(
                            icon='delete',
                            color='red',
                            on_click=lambda:
                            open_delete_dialog(patient)
                        ).props(
                            'flat round'
                        )

                        ui.button(
                            icon='picture_as_pdf',
                            color='green',
                            on_click=lambda:
                            generate_pdf(patient)
                        ).props(
                            'flat round'
                        )

                ui.separator()

                # =====================================================
                # PERSONAL INFORMATION
                # =====================================================

                with section_expansion(
                        '👤 Personal Information',

                        value=True
                ).classes(
                    'w-full'

                ):

                    with ui.grid(
                            columns=2
                    ).classes(
                        'w-full gap-4'
                    ):
                        info_card(
                            '🆔 Patient ID',
                            patient.get("patient_u_id")
                        )

                        info_card(
                            '👤 Patient Name',
                            patient.get("patient_name")
                        )

                        info_card(
                            '🆔 National ID',
                            patient.get("national_id")
                        )

                        info_card(
                            '⚧ Gender',
                            patient.get("gender")
                        )

                        info_card(
                            '📞 Phone Number',
                            patient.get("phone_number")
                        )

                        info_card(
                            '🏠 Address',
                            patient.get("address_area")
                        )

                        info_card(
                            '🚨 Emergency Contact',
                            patient.get("emergency_contact")
                        )

                # =====================================================
                # LIFESTYLE
                # =====================================================

                ui.separator()

                with section_expansion(
                        '🏃 Lifestyle & Risk Factors',

                ).classes(
                    'w-full'
                ):

                    with ui.grid(
                            columns=2
                    ).classes(
                        'w-full gap-4'
                    ):
                        info_card(
                            '📏 Height (cm)',
                            patient.get("ht")
                        )

                        info_card(
                            '⚖️ BMI',
                            patient.get("bmi")
                        )

                        info_card(
                            '📊 BMI Category',
                            patient.get("bmi_category")
                        )

                        info_card(
                            '🚬 Smoking Status',
                            'Yes'
                            if patient.get("smoker")
                            else 'No'
                        )

                        info_card(
                            '💼 Occupation Type',
                            patient.get("occupation_type")
                        )

                        info_card(
                            '📝 Occupation Details',
                            patient.get("occupation_details")
                        )

                # =====================================================
                # MEDICAL INFORMATION
                # =====================================================

                ui.separator()

                with section_expansion(
                        '🩺 Medical Information',

                ).classes(
                    'w-full'

                ):

                    with ui.grid(
                            columns=2
                    ).classes(
                        'w-full gap-4'
                    ):

                        info_card(
                            '🩸 Blood Group',
                            patient.get("blood_group")
                        )

                        info_card(
                            '⚠️ Allergies',
                            patient.get("allergies")
                        )

                    with ui.expansion(
                            '❤️ Chronic Conditions',
                            value=True
                    ).classes(
                        'w-full mt-4 font-bold'
                    ).style(
                        '''
                        border: 1px solid #f9a8d4;
                        border-radius: 16px;
                        background-color: #fdf2f8;
                        '''
                    ):

                        chronic_text = format_chronic_conditions(
                            patient.get(
                                "chronic_conditions"
                            )
                        )

                        if chronic_text and chronic_text != "-":

                            ui.label(
                                chronic_text
                            ).style(
                                'white-space: pre-line'
                            )

                        else:

                            ui.label(
                                'No chronic conditions recorded'
                            ).classes(
                                'text-gray-500 italic'
                            )

                # =====================================================
                # DATES
                # =====================================================

                ui.separator()

                with section_expansion(
                        '📅 Timeline & Visits',

                ).classes(
                    'w-full'

                ):

                    with ui.grid(
                            columns=2
                    ).classes(
                        'w-full gap-4'
                    ):
                        info_card(
                            '📅 Profile Creation Date',
                            patient.get("profile_creation_date")
                        )

                        info_card(
                            '📅 First Visit Date',
                            patient.get("first_visit_date")
                        )

                        info_card(
                            '📅 Last Visit Date',
                            patient.get("last_visit_date")
                        )

    # =====================================================
    # OPEN PATIENT
    # =====================================================

    def open_patient(patient):

        global selected_patient

        if hasattr(
            patient,
            "to_dict"
        ):

            patient = patient.to_dict()

        exists = any(

            p["patient_u_id"]

            ==

            patient["patient_u_id"]

            for p in opened_patients

        )

        if not exists:

            opened_patients.append(
                patient
            )

        selected_patient = patient

        refresh_tabs()

        show_patient_details(
            patient
        )

    # =====================================================
    # CLOSE PATIENT
    # =====================================================

    def close_patient(patient):

        global selected_patient

        if hasattr(
            patient,
            "to_dict"
        ):

            patient = patient.to_dict()

        opened_patients[:] = [

            p for p in opened_patients

            if p["patient_u_id"]
            != patient["patient_u_id"]

        ]

        if (

            selected_patient

            and

            selected_patient["patient_u_id"]
            == patient["patient_u_id"]

        ):

            if opened_patients:

                selected_patient = (
                    opened_patients[0]
                )

                show_patient_details(
                    selected_patient
                )

            else:

                selected_patient = None

                empty_details()

        refresh_tabs()

    # =====================================================
    # ADD PATIENT
    # =====================================================

    def open_add_dialog():

        with ui.dialog() as dialog, ui.card().classes(
            'w-[500px] p-6 rounded-3xl'
        ):

            ui.label(
                'Add Patient'
            ).classes(
                'text-3xl font-bold'
            )

            patient_name = ui.input(
                'Patient Name'
            ).classes('w-full')

            national_id = ui.input(
                'National ID'
            ).classes('w-full')

            phone = ui.input(
                'Phone Number'
            ).classes('w-full')

            address = ui.input(
                'Address Area'
            ).classes('w-full')

            gender = ui.select(
                ['Male', 'Female'],
                label='Gender'
            ).classes(
                'w-full'
            )

            height = ui.number(
                'Height (cm)'
            ).classes(
                'w-full'
            )

            bmi = ui.input(
                'BMI'
            ).props(
                'readonly'
            ).classes(
                'w-full'
            )

            bmi_category = ui.input(
                'BMI Category'
            ).props(
                'readonly'
            ).classes(
                'w-full'
            )

            occupation_type = ui.select(
                [
                    'Office Based Work',
                    'Manual Work',
                    'Both'
                ],
                label='Occupation Type'
            ).classes(
                'w-full'
            )

            occupation_details = ui.input(
                'Occupation Details'
            ).classes(
                'w-full'
            )

            smoker = ui.select(
                [
                    'Yes',
                    'No'
                ],
                label='Smoker'
            ).classes(
                'w-full'
            )

            allergies = ui.input(
                'Allergies'
            ).classes(
                'w-full'
            )

            ui.label(
                'Chronic Conditions'
            ).classes(
                'font-bold'
            )

            chronic = ui.select(
                options=ICD_OPTIONS,
                multiple=True
            ).props(
                'use-input use-chips fill-input'
            ).classes(
                'w-full'
            )

            blood_group = ui.select(
                [
                    'A+',
                    'A-',
                    'B+',
                    'B-',
                    'AB+',
                    'AB-',
                    'O+',
                    'O-'
                ],
                label='Blood Group'
            ).classes(
                'w-full'
            )

            emergency_contact = ui.input(
                'Emergency Contact (Name - Phone)'
            ).classes(
                'w-full'
            )

            def save():

                client = ui.context.client

                new_patient = {

                    "patient_name":
                        patient_name.value,

                    "phone_number":
                        phone.value,

                    "national_id":
                        national_id.value,

                    "address_area":
                        address.value,

                    "gender":
                        gender.value,

                    "ht":
                        height.value,

                    "bmi":
                        None,

                    "bmi_category":
                        None,

                    "occupation_type":
                        occupation_type.value,

                    "occupation_details":
                        occupation_details.value,

                    "smoker": (
                        True
                        if smoker.value == "Yes"
                        else False
                    ),

                    "allergies":
                        allergies.value,

                    "chronic_conditions":
                        (chronic.value or []),

                    "blood_group":
                        blood_group.value,

                    "emergency_contact":
                        emergency_contact.value,

                    "profile_creation_date":
                        datetime.now().date(),

                    "first_visit_date":
                        None,

                    "last_visit_date":
                        None
                }

                with engine.connect() as conn:
                    result = conn.execute(

                        text("""

                        INSERT INTO patients_list
                        (
                            patient_name,
                            national_id,
                            phone_number,
                            address_area,
                            gender,
                            ht,
                            bmi,
                            bmi_category,
                            occupation_type,
                            occupation_details,
                            smoker,
                            allergies,
                            chronic_conditions,
                            blood_group,
                            emergency_contact,
                            profile_creation_date,
                            first_visit_date,
                            last_visit_date
                        )

                        VALUES
                        (
                            :patient_name,
                            :national_id,
                            :phone_number,
                            :address_area,
                            :gender,
                            :ht,
                            :bmi,
                            :bmi_category,
                            :occupation_type,
                            :occupation_details,
                            :smoker,
                            :allergies,
                            :chronic_conditions,
                            :blood_group,
                            :emergency_contact,
                            :profile_creation_date,
                            :first_visit_date,
                            :last_visit_date
                        )

                        RETURNING patient_u_id

                        """),

                        new_patient
                    )

                    generated_id = result.scalar()

                    conn.commit()

                new_patient["patient_u_id"] = generated_id
                Cache.PATIENTS_CACHE = pd.concat(
                        [

                            Cache.PATIENTS_CACHE,

                            pd.DataFrame(
                                [new_patient]
                            )

                        ],

                        ignore_index=True

                    )
                refresh_patient_list()
                open_patient(new_patient)

                safe_notify(
                    client,
                    'Patient added successfully',
                    'positive'
                )

                dialog.close()

            with ui.row().classes(
                'w-full justify-end'
            ):

                ui.button(
                    'Cancel',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                ui.button(
                    'Save',
                    on_click=save
                )

        dialog.open()

    # =====================================================
    # EDIT PATIENT
    # =====================================================

    def open_edit_dialog(patient):

        with ui.dialog() as dialog, ui.card().classes(
            'w-[500px] p-6 rounded-3xl'
        ):

            ui.label(
                'Edit Patient'
            ).classes(
                'text-3xl font-bold'
            )

            name = ui.input(
                'Patient Name',
                value=patient.get("patient_name")
            ).classes(
                'w-full'
            )

            national_id = ui.input(
                'National ID',
                value=patient.get("national_id")
            ).classes(
                'w-full'
            )

            phone = ui.input(
                'Phone Number',
                value=patient.get("phone_number")
            ).classes(
                'w-full'
            )

            address = ui.input(
                'Address Area',
                value=patient.get("address_area")
            ).classes(
                'w-full'
            )

            gender = ui.select(
                ['Male', 'Female'],
                label='Gender',
                value=patient.get("gender") or None
            ).classes(
                'w-full'
            )

            height = ui.number(
                'Height (cm)',
                value=(
                    None
                    if pd.isna(patient.get("ht"))
                    else patient.get("ht")
                )
            ).classes(
                'w-full'
            )

            bmi = ui.input(
                'BMI',
                value=str(patient.get("bmi") or "")
            ).props(
                'readonly'
            ).classes(
                'w-full'
            )

            bmi_category = ui.input(
                'BMI Category',
                value=patient.get("bmi_category")
            ).props(
                'readonly'
            ).classes(
                'w-full'
            )

            occupation_type = ui.select(
                [
                    'Office Based Work',
                    'Manual Work',
                    'Both'
                ],
                label='Occupation Type',
                value=patient.get("occupation_type") or None
            ).classes(
                'w-full'
            )

            occupation_details = ui.input(
                'Occupation Details',
                value=patient.get("occupation_details")
            ).classes(
                'w-full'
            )

            smoker = ui.select(
                ['Yes','No'],
                label='Smoking Status',
                value=(
                    'Yes'
                    if patient.get("smoker") is True
                    else 'No'
                    if patient.get("smoker") is False
                    else None
                )
            ).classes(
                'w-full'
            )

            allergies = ui.input(
                'Allergies',
                value=patient.get("allergies")
            ).classes(
                'w-full'
            )

            ui.label(
                'Chronic Conditions'
            ).classes(
                'font-bold'
            )

            chronic = ui.select(
                options=ICD_OPTIONS,
                multiple=True,
                value=patient.get("chronic_conditions") or []
            ).props(
                'use-input use-chips fill-input'
            ).classes(
                'w-full'
            )

            blood_group = ui.select(
                [
                    'A+',
                    'A-',
                    'B+',
                    'B-',
                    'AB+',
                    'AB-',
                    'O+',
                    'O-'
                ],
                label='Blood Group',
                value=patient.get("blood_group") or None
            ).classes(
                'w-full'
            )

            emergency_contact = ui.input(
                'Emergency Contact (Name - Phone)',
                value=patient.get("emergency_contact")
            ).classes(
                'w-full'
            )

            def save():

                client = ui.context.client

                updated_data = {

                    "patient_name":
                        name.value,

                    "national_id":
                        national_id.value,

                    "phone_number":
                        phone.value,

                    "address_area":
                        address.value,

                    "gender":
                        gender.value,

                    "ht":
                        height.value,

                    "bmi":
                        None,

                    "bmi_category":
                        None,

                    "occupation_type":
                        occupation_type.value,

                    "occupation_details":
                        occupation_details.value,

                    "smoker": (
                        True
                        if smoker.value == "Yes"
                        else False
                    ),

                    "allergies":
                        allergies.value,

                    "chronic_conditions":
                        (chronic.value or []),

                    "blood_group":
                        blood_group.value,

                    "emergency_contact":
                        emergency_contact.value,

                    "patient_u_id":
                        patient["patient_u_id"]
                }

                with engine.connect() as conn:

                    conn.execute(

                        text("""

                        UPDATE patients_list

                        SET

                            patient_name = :patient_name,

                            national_id = :national_id,

                            phone_number = :phone_number,

                            address_area = :address_area,

                            gender = :gender,

                            ht = :ht,

                            bmi = :bmi,

                            bmi_category = :bmi_category,

                            occupation_type = :occupation_type,

                            occupation_details = :occupation_details,

                            smoker = :smoker,

                            allergies = :allergies,

                            chronic_conditions = :chronic_conditions,

                            blood_group = :blood_group,

                            emergency_contact = :emergency_contact

                        WHERE patient_u_id = :patient_u_id

                        """),

                        updated_data
                    )

                    conn.commit()

                patient.update(
                    updated_data
                )

                refresh_patient_list()

                refresh_tabs()

                show_patient_details(
                    patient
                )

                safe_notify(
                    client,
                    'Patient updated successfully',
                    'positive'
                )

                dialog.close()

            with ui.row().classes(
                'w-full justify-end'
            ):

                ui.button(
                    'Cancel',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                ui.button(
                    'Save',
                    on_click=save
                )

        dialog.open()

    # =====================================================
    # DELETE PATIENT
    # =====================================================

    def open_delete_dialog(patient):

        with ui.dialog() as dialog, ui.card().classes(
            'w-[400px] p-6 rounded-3xl'
        ):

            ui.label(
                'Delete Patient'
            ).classes(
                'text-3xl font-bold text-red-500'
            )

            ui.label(
                f'Are you sure you want to delete {patient["patient_name"]}?'
            )

            def delete():

                client = ui.context.client
                patient_id = patient["patient_u_id"]

                with engine.connect() as conn:

                    conn.execute(

                        text("""

                        DELETE FROM patients_list

                        WHERE patient_u_id = :patient_u_id

                        """),

                        {

                            "patient_u_id":
                            patient["patient_u_id"]
                        }
                    )

                    conn.commit()

                Cache.PATIENTS_CACHE = Cache.PATIENTS_CACHE[

                    Cache.PATIENTS_CACHE["patient_u_id"]

                    !=

                    patient_id

                ]

                close_patient(
                    patient
                )

                refresh_patient_list()

                safe_notify(
                    client,
                    'Patient deleted successfully',
                    'negative'
                )

                dialog.close()

            with ui.row().classes(
                'w-full justify-end'
            ):

                ui.button(
                    'Cancel',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                ui.button(
                    'Delete',
                    color='red',
                    on_click=delete
                )

        dialog.open()

    # =====================================================
    # PDF
    # =====================================================
    def generate_pdf(patient):

        client = ui.context.client

        # =====================================================
        # HELPERS
        # =====================================================

        def clean_value(value):

            if (
                value is None
                or str(value).lower() == 'nan'
                or str(value).strip() == ''
            ):
                return '-'

            return str(value)

        def pdf_section_title(pdf, title):

            pdf.ln(4)

            pdf.set_fill_color(
                230,
                240,
                255
            )

            pdf.set_font(
                'Helvetica',
                'B',
                14
            )

            pdf.cell(
                0,
                10,
                title,
                new_x="LMARGIN",
                new_y="NEXT",
                fill=True
            )

            pdf.ln(2)

        def pdf_field(pdf, label, value):

            pdf.set_font(
                'Helvetica',
                'B',
                12
            )

            pdf.cell(
                0,
                8,
                f'{label}:',
                new_x="LMARGIN",
                new_y="NEXT"
            )

            pdf.set_font(
                'Helvetica',
                '',
                12
            )

            pdf.multi_cell(
                0,
                8,
                clean_value(value)
            )

            pdf.ln(2)

        # =====================================================
        # PDF
        # =====================================================

        pdf = FPDF()

        pdf.set_auto_page_break(
            auto=True,
            margin=15
        )

        pdf.add_page()

        # =====================================================
        # HEADER
        # =====================================================

        pdf.set_font(
            'Helvetica',
            'B',
            22
        )

        pdf.cell(
            0,
            12,
            'Patient Medical Profile',
            new_x="LMARGIN",
            new_y="NEXT",
            align='C'
        )

        pdf.ln(5)

        # =====================================================
        # PERSONAL INFORMATION
        # =====================================================

        pdf_section_title(
            pdf,
            'PERSONAL INFORMATION'
        )

        pdf_field(
            pdf,
            'Patient ID',
            patient.get("patient_u_id")
        )

        pdf_field(
            pdf,
            'Patient Name',
            patient.get("patient_name")
        )

        pdf_field(
            pdf,
            'National ID',
            patient.get("national_id")
        )

        pdf_field(
            pdf,
            'Gender',
            patient.get("gender")
        )

        pdf_field(
            pdf,
            'Phone Number',
            patient.get("phone_number")
        )

        pdf_field(
            pdf,
            'Address',
            patient.get("address_area")
        )

        pdf_field(
            pdf,
            'Emergency Contact',
            patient.get("emergency_contact")
        )

        # =====================================================
        # LIFESTYLE & RISK FACTORS
        # =====================================================

        pdf_section_title(
            pdf,
            'LIFESTYLE & RISK FACTORS'
        )

        pdf_field(
            pdf,
            'Height (cm)',
            patient.get("ht")
        )

        pdf_field(
            pdf,
            'BMI',
            patient.get("bmi")
        )

        pdf_field(
            pdf,
            'BMI Category',
            patient.get("bmi_category")
        )

        pdf_field(
            pdf,
            'Smoker',
            (
                'Yes'
                if patient.get("smoker") is True
                else 'No'
                if patient.get("smoker") is False
                else '-'
            )
        )

        pdf_field(
            pdf,
            'Occupation Type',
            patient.get("occupation_type")
        )

        pdf_field(
            pdf,
            'Occupation Details',
            patient.get("occupation_details")
        )

        # =====================================================
        # MEDICAL INFORMATION
        # =====================================================

        pdf_section_title(
            pdf,
            'MEDICAL INFORMATION'
        )

        pdf_field(
            pdf,
            'Blood Group',
            patient.get("blood_group")
        )

        pdf_field(
            pdf,
            'Allergies',
            patient.get("allergies")
        )

        chronic_conditions = format_chronic_conditions(
            patient.get(
                "chronic_conditions"
            )
        )

        pdf_field(
            pdf,
            'Chronic Conditions',
            chronic_conditions
        )

        # =====================================================
        # TIMELINE & VISITS
        # =====================================================

        pdf_section_title(
            pdf,
            'TIMELINE & VISITS'
        )

        pdf_field(
            pdf,
            'Profile Creation Date',
            patient.get("profile_creation_date")
        )

        pdf_field(
            pdf,
            'First Visit Date',
            patient.get("first_visit_date")
        )

        pdf_field(
            pdf,
            'Last Visit Date',
            patient.get("last_visit_date")
        )

        # =====================================================
        # SAVE PDF
        # =====================================================

        folder = 'generated_pdfs'

        os.makedirs(
            folder,
            exist_ok=True
        )

        file_path = os.path.join(
            folder,
            f'{patient["patient_u_id"]}.pdf'
        )

        pdf.output(
            file_path
        )

        safe_notify(
            client,
            f'PDF Saved Successfully\n{os.path.abspath(file_path)}',
            'positive'
        )
    # =====================================================
    # PAGE STYLE
    # =====================================================

    ui.query('body').style(
        'background-color: #f5f7fb'
    )

    # =====================================================
    # MAIN LAYOUT
    # =====================================================

    with ui.column().classes(
        'w-full p-4 gap-4'
    ):

        ui.label(
            '🏥 Clinic Management System'
        ).classes(
            'text-6xl font-bold'
        )

        with ui.row().classes(
            'w-full items-center gap-4'
        ):
            def clear_search():
                search_input.value = ''

                refresh_patient_list()

                toggle_clear_button()
            def toggle_clear_button():

                if str(search_input.value or '').strip():

                    clear_btn.visible = True

                else:

                    clear_btn.visible = False


            search_input = ui.input(
                placeholder='Search patient...'
            ).props(
                'outlined'
            ).classes(
                'flex-1'
            )

            search_input.on(
                'keyup',
                lambda e: (
                    refresh_patient_list(),
                    toggle_clear_button()
                )
            )
            clear_btn = ui.button(
                icon='close',
                on_click=clear_search
            ).props(
                'flat round'
            ).classes(
                'transition-all duration-300'
            )

            clear_btn.visible = False
            ui.button(
                'Add Patient',
                icon='add',
                on_click=open_add_dialog
            )

        with ui.row().classes(
            'w-full gap-4 items-start'
        ):

            patient_cards_container = ui.column().classes(
                'w-[350px] gap-4'
            )

            with ui.column().classes(
                'flex-1 gap-4'
            ):

                tabs_container = ui.column()

                details_container = ui.column().classes(
                    'w-full'
                )

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
        'fab color=primary'
    ).style(
        '''
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 9999;
        '''
    )

    # =====================================================
    # INITIALIZE
    # =====================================================

    refresh_patient_list()

    empty_details()
