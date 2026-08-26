import streamlit as st
import pandas as pd

from database import get_connection
from auth import render_admin_sidebar, require_admin


st.set_page_config(
    page_title="Golfing Warriors - Ranking Settings",
    page_icon="⚙️",
    layout="wide"
)


# ============================================================
# DEFAULT RANKING POINTS
# ============================================================

DEFAULT_POINTS = {
    1: 500,
    2: 300,
    3: 150,
    4: 75,
    5: 50,
    6: 30,
    7: 20,
    8: 15,
}


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_ranking_settings():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                position,
                points,
                active
            FROM ranking_settings
            ORDER BY position
            """,
            connection
        )

    finally:

        connection.close()


def save_ranking_settings(
    settings
):

    require_admin()

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # ------------------------------------------------
            # IMPORTANT
            #
            # We are NOT changing historical event results.
            #
            # ranking_settings is only the allocation template
            # used when NEW events are finalized.
            # ------------------------------------------------

            for position, points in settings.items():

                cursor.execute(
                    """
                    UPDATE ranking_settings
                    SET
                        points = %s,
                        active = TRUE
                    WHERE position = %s
                    """,
                    (
                        float(points),
                        int(position)
                    )
                )

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


def initialise_ranking_settings():

    require_admin()

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            for position in range(1, 31):

                points = DEFAULT_POINTS.get(
                    position,
                    0
                )

                cursor.execute(
                    """
                    INSERT INTO ranking_settings
                        (
                            position,
                            points,
                            active
                        )
                    VALUES
                        (%s, %s, TRUE)

                    ON CONFLICT (position)
                    DO NOTHING
                    """,
                    (
                        int(position),
                        float(points)
                    )
                )

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# ============================================================
# PAGE
# ============================================================

st.title(
    "⚙️ Ranking Points Settings"
)

st.caption(
    "Control how Golfing Warriors championship "
    "points are awarded for each finishing position."
)

is_admin = render_admin_sidebar()

st.divider()


# ============================================================
# INITIALISE SETTINGS
# ============================================================

if is_admin:

    try:

        initialise_ranking_settings()

    except Exception as error:

        st.error(
            "Unable to initialise ranking settings."
        )

        st.exception(error)

        st.stop()


settings_df = get_ranking_settings()


if settings_df.empty:

    st.error(
        "No ranking settings are available."
    )

    st.stop()


# ============================================================
# INFORMATION
# ============================================================

st.info(
    """
    **How ranking points work**

    Ranking points are awarded when an event is finalized.

    Changing these settings does **not** change points
    already awarded to completed events.

    New events will use the current settings.
    """
)


# ============================================================
# CURRENT SETTINGS
# ============================================================

st.subheader(
    "🏆 Current Ranking Allocation"
)


st.caption(
    "Positions 1–30 are available. "
    "Set a position to 0 if you don't want "
    "it to receive ranking points."
)


# ============================================================
# CURRENT ALLOCATION / EDIT SETTINGS
# ============================================================

if not is_admin:

    st.caption(
        "👀 Viewer mode — ranking settings are read-only. "
        "Enter Admin Mode in the sidebar to make changes."
    )

    public_df = settings_df.copy()
    public_df["Position"] = public_df["position"].astype(int)
    public_df["Ranking Points"] = public_df["points"].astype(float)
    public_df = public_df[["Position", "Ranking Points"]]

    st.dataframe(
        public_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ranking Points": st.column_config.NumberColumn(
                "Ranking Points",
                format="%.0f"
            )
        }
    )

else:

    # ========================================================
    # EDIT SETTINGS
    # ========================================================

    edited_settings = {}

    for _, row in settings_df.iterrows():

        position = int(
            row["position"]
        )

        current_points = float(
            row["points"]
        )

        col1, col2, col3 = st.columns(
            [1, 3, 2]
        )

        with col1:

            if position == 1:

                st.markdown(
                    "### 🥇"
                )

            elif position == 2:

                st.markdown(
                    "### 🥈"
                )

            elif position == 3:

                st.markdown(
                    "### 🥉"
                )

            else:

                st.markdown(
                    f"### {position}"
                )

        with col2:

            suffix = (
                "st" if position == 1
                else "nd" if position == 2
                else "rd" if position == 3
                else "th"
            )

            st.write(
                f"**{position}{suffix} Place**"
            )

        with col3:

            points = st.number_input(
                "Points",
                min_value=0.0,
                max_value=100000.0,
                value=current_points,
                step=5.0,
                key=f"ranking_points_{position}",
                label_visibility="collapsed"
            )

            edited_settings[
                position
            ] = points

    # ========================================================
    # PREVIEW
    # ========================================================

    st.divider()

    st.subheader(
        "👀 Preview"
    )

    preview_rows = []

    for position in sorted(
        edited_settings.keys()
    ):

        points = edited_settings[
            position
        ]

        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"
        else:
            medal = ""

        preview_rows.append(
            {
                "Position":
                    f"{medal} {position}",
                "Ranking Points":
                    float(points)
            }
        )

    preview_df = pd.DataFrame(
        preview_rows
    )

    st.dataframe(
        preview_df,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # SAVE
    # ========================================================

    st.divider()

    st.subheader(
        "💾 Save Changes"
    )

    if st.button(
        "💾 Save Ranking Allocation",
        type="primary",
        use_container_width=True
    ):

        try:

            save_ranking_settings(
                edited_settings
            )

            st.success(
                "🏆 Ranking allocation updated successfully!"
            )

            st.info(
                "These settings will be used for "
                "future event finalizations. "
                "Existing event results have not changed."
            )

            st.rerun()

        except Exception as error:

            st.error(
                "Unable to save ranking settings."
            )

            st.exception(error)

    # ========================================================
    # RESET
    # ========================================================

    st.divider()

    st.subheader(
        "🔄 Reset to Default"
    )

    st.caption(
        "This restores the original Golfing Warriors "
        "ranking allocation."
    )

    if st.button(
        "🔄 Reset to 500 / 300 / 150 System",
        use_container_width=True
    ):

        try:

            save_ranking_settings(
                {
                    position:
                        DEFAULT_POINTS.get(
                            position,
                            0
                        )
                    for position in range(1, 31)
                }
            )

            st.success(
                "Ranking allocation restored to default."
            )

            st.rerun()

        except Exception as error:

            st.error(
                "Unable to reset ranking settings."
            )

            st.exception(error)
