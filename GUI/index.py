from nicegui import ui
from sqlalchemy import (
    create_engine,
    text
)
import bcrypt
import Cache
import Home
import sys
from pathlib import Path

sys.path.append(
    str(
        Path(__file__).resolve().parent.parent
    )
)

from Keys.PostGresKey import POSTGRES_URL

engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True
)

@ui.page('/')

def login_page():
    with ui.column().classes(

    '''
    w-full
    h-screen
    items-center
    justify-center
    '''

    ):

        with ui.card().classes(

            '''
            w-[500px]
            p-8
            rounded-2xl
            '''

        ):

            ui.label(

                'DEPI HealthNux'

            ).classes(

                'text-3xl font-bold'

            )

            ui.label(

                'Login'

            ).classes(

                'text-gray-500'

            )

            email = ui.input(

                'Email'

            ).classes(

                'w-full'

            )

            password = ui.input(

                'Password',

                password=True

            ).classes(

                'w-full'

            )

            def login():


                if not email.value:

                    ui.notify(
                        'Please Enter Email',
                        color='negative'
                    )
                    return

                if not password.value:

                    ui.notify(
                        'Please Enter Password',
                        color='negative'
                    )
                    return

                with engine.connect() as conn:

                    user = conn.execute(

                        text(

                            """

                            SELECT *

                            FROM users

                            WHERE

                                LOWER(email)

                                =

                                LOWER(:email)

                                AND

                                is_active = 'Active'

                            """

                        ),

                        {

                            "email":

                            email.value

                        }

                    ).mappings().first()

                if not user:

                    ui.notify(

                        'Invalid Email',

                        color='negative'

                    )

                    return
                
                if not bcrypt.checkpw(

                    password.value.encode("utf-8"),

                    user["password_hash"].encode("utf-8")

                ):

                    ui.notify(

                        'Invalid Password',

                        color='negative'

                    )

                    return
                Cache.CURRENT_USER = {

                "user_id":
                    user["user_id"],

                "email":
                    user["email"],

                "role":
                    user["role"],

                "dr_code":
                    user["dr_code"]

                }
                ui.notify(

                f'Welcome {user["email"]}',

                color='positive'

                )
                ui.navigate.to(
                '/home'
                )
        ui.button(

            'Login',

            icon='login',

            on_click=login

            ).classes(

                'w-full'

            )
        password.on(

        'keydown.enter',

        lambda e:
        login()

        )

ui.run(
    title='DEPI HealthNux',
    reload=True
)