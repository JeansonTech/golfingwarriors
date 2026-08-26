import streamlit as st
import pandas as pd

from database import get_connection


def get_seasons():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                year,
                active,
                created_at
            FROM seasons
            ORDER BY year DESC
            """,
            connection
        )

    finally:
        connection.close()


def create_season(name, year):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO seasons
                    (name, year, active)
                VALUES
                    (%s, %s, TRUE)
                """,
                (
                    name.strip(),
                    year
                )
            )

        connection.commit()

    finally:
        connection.close()


def set_active_season(season_id):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE seasons
                SET active = FALSE
                """
            )

            cursor.execute(
                """
                UPDATE seasons
                SET active = TRUE
                WHERE id = %s
                """,
                (season_id,)
            )

        connection.commit()

    finally:
        connection.close()


st.title("🏆 Seasons")

st.caption(
    "Manage Golfing Warriors championship seasons."
)

st.divider()


# ============================================================
# CREATE SEASON
# ============================================================

st.subheader("➕ Create Season")

with st.form(
    "create_season",
    clear_on_submit=True
):

    name = st.text_input(
        "Season Name",
        value="2026 Golfing Warriors Championship"
    )

    year = st.number_input(
        "Year",
        min_value=2020,
        max_value=2100,
        value=2026,
        step=1
    )

    create = st.form_submit_button(
        "🏆 Create Season",
        type="primary"
    )

    if create:

        if not name.strip():

            st.error(
                "Please enter a season name."
            )

        else:

            try:

                create_season(
                    name,
                    int(year)
                )

                st.success(
                    f"{name} created successfully!"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    "Unable to create season."
                )

                st.exception(error)


st.divider()


# ============================================================
# SEASON LIST
# ============================================================

st.subheader("Seasons")

seasons = get_seasons()

if seasons.empty:

    st.info(
        "No seasons have been created yet."
    )

else:

    for _, season in seasons.iterrows():

        status = (
            "🟢 Active"
            if season["active"]
            else "⚪ Inactive"
        )

        col1, col2, col3 = st.columns(
            [4, 2, 2]
        )

        with col1:

            st.write(
                f"**{season['name']}**"
            )

        with col2:

            st.write(
                f"{season['year']} — {status}"
            )

        with col3:

            if not season["active"]:

                if st.button(
                    "Make Active",
                    key=f"active_{season['id']}"
                ):

                    set_active_season(
                        season["id"]
                    )

                    st.rerun()
