def generate_ava_visits ():
    import sys
    import psycopg2
    import pandas as pd

    from datetime import date, timedelta

    sys.path.append("..")

    from Keys.PostGresKey import POSTGRES_URL

    # =========================================
    # CONFIGURATION
    # =========================================

    ROLLING_DAYS = 30

    # =========================================
    # DAY MAPPING
    # =========================================

    DAY_MAP = {

        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6

    }

    # =========================================
    # GET MATCHING DATES
    # =========================================

    def get_matching_dates_in_window(
        start_date,
        end_date,
        weekday_number
    ):

        result = []

        current = start_date

        while current <= end_date:

            if current.weekday() == weekday_number:

                result.append(current)

            current += timedelta(days=1)

        return result

    # =========================================
    # CONNECT
    # =========================================

    conn = psycopg2.connect(
        POSTGRES_URL
    )

    cursor = conn.cursor()

    # =========================================
    # LOAD ACTIVE TIMETABLES
    # =========================================

    timetable_query = """

    SELECT

        Time_Table_Key,

        Day_of_Week,

        Capacity

    FROM Dr_Time_Table

    WHERE

        UPPER(
            TRIM(Is_Active)
        ) = 'ACTIVE'

        AND Capacity > 0

    ORDER BY

        Day_of_Week,
        Time_Table_Key

    """

    timetable_df = pd.read_sql(
        timetable_query,
        conn
    )

    print(
        f"\nActive Timetables: {len(timetable_df)}"
    )

    # =========================================
    # LOAD HOLIDAYS
    # =========================================

    holiday_query = """

    SELECT

        Holiday_Date

    FROM Official_Holidays

    """

    holiday_df = pd.read_sql(
        holiday_query,
        conn
    )

    holiday_dates = set(

        pd.to_datetime(
            holiday_df["holiday_date"]
        ).dt.date

    )

    print(
        f"Holidays Loaded: {len(holiday_dates)}"
    )

    # =========================================
    # GENERATION WINDOW
    # =========================================

    today = date.today()

    generation_start = today

    generation_end = (

        today

        + timedelta(
            days=ROLLING_DAYS
        )

    )

    print("\n=================================")
    print("Generation Window")
    print("=================================")
    print(
        f"Start : {generation_start}"
    )
    print(
        f"End   : {generation_end}"
    )

    # =========================================
    # GENERATE VISITS
    # =========================================

    inserted_count = 0

    skipped_holidays = 0

    for _, row in timetable_df.iterrows():

        day_name = row["day_of_week"]

        if day_name not in DAY_MAP:

            print(
                f"Skipped Invalid Day: {day_name}"
            )
            continue

        matching_dates = get_matching_dates_in_window(

            generation_start,

            generation_end,

            DAY_MAP[
                day_name
            ]

        )

        print(

            f"{row['time_table_key']}"

            f" | "

            f"{day_name}"

            f" | "

            f"{len(matching_dates)} matching dates"

        )

        for visit_date in matching_dates:

            # ==========================
            # SKIP HOLIDAYS
            # ==========================

            if visit_date in holiday_dates:

                skipped_holidays += 1

                continue

            cursor.execute(

                """

                INSERT INTO Available_Visits

                (

                    Time_Table_Key,

                    Scheduled_Date,

                    Capacity,

                    Is_Holiday

                )

                VALUES

                (

                    %s,

                    %s,

                    %s,

                    FALSE

                )

                ON CONFLICT

                (

                    Time_Table_Key,

                    Scheduled_Date

                )

                DO NOTHING

                """,

                (

                    row[
                        "time_table_key"
                    ],

                    visit_date,


                    row[
                        "capacity"
                    ]

                )

            )

            if cursor.rowcount > 0:

                inserted_count += 1

    # =========================================
    # COMMIT
    # =========================================

    conn.commit()

    cursor.close()

    conn.close()

    # =========================================
    # SUMMARY
    # =========================================

    print("\n=================================")
    print("GENERATION SUMMARY")
    print("=================================")

    print(
        f"Visits Inserted: {inserted_count}"
    )

    print(
        f"Holidays Skipped: {skipped_holidays}"
    )

    print(
        f"Coverage Until: {generation_end}"
    )

    print("=================================")