import streamlit as st
import pandas as pd

from database import get_connection


st.set_page_config(
    page_title="Golfing Warriors - Courses",
    page_icon="⛳",
    layout="wide"
)


def get_courses():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                location,
                active
            FROM courses
            ORDER BY name
            """,
            connection
        )

    finally:

        connection.close()


def create_course(
    name,
    location,
    holes
):

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # Create course
            cursor.execute(
                """
                INSERT INTO courses
                    (
                        name,
                        location
                    )
                VALUES
                    (%s, %s)
                RETURNING id
                """,
                (
                    name.strip(),
                    location.strip()
                    if location
                    else None
                )
            )

            course_id = cursor.fetchone()[0]

            # Add 18 holes
            for hole in holes:

                cursor.execute(
                    """
                    INSERT INTO course_holes
                        (
                            course_id,
                            hole_number,
                            par,
                            stroke_index
                        )
                    VALUES
                        (%s, %s, %s, %s)
                    """,
                    (
                        int(course_id),
                        int(hole["hole"]),
                        int(hole["par"]),
                        int(hole["stroke_index"])
                    )
                )

        connection.commit()

    finally:

        connection.close()


st.title("⛳ Courses")

st.caption(
    "Manage the golf courses used by "
    "Golfing Warriors."
)

st.divider()


# ============================================================
# CREATE COURSE
# ============================================================

st.subheader("➕ Add Golf Course")

course_name = st.text_input(
    "Course Name",
    placeholder="e.g. Mokopane Golf Club"
)

course_location = st.text_input(
    "Location",
    placeholder="Optional"
)

st.write("### Hole Information")

st.caption(
    "Enter the par and stroke index for each hole. "
    "Stroke Index must be unique from 1 to 18."
)


holes = []

header1, header2, header3 = st.columns(
    [1, 1, 2]
)

with header1:
    st.markdown("**Hole**")

with header2:
    st.markdown("**Par**")

with header3:
    st.markdown("**Stroke Index**")


for hole_number in range(1, 19):

    col1, col2, col3 = st.columns(
        [1, 1, 2]
    )

    with col1:

        st.write(
            f"**{hole_number}**"
        )

    with col2:

        par = st.number_input(
            f"Par {hole_number}",
            min_value=3,
            max_value=6,
            value=4,
            step=1,
            key=f"course_par_{hole_number}",
            label_visibility="collapsed"
        )

    with col3:

        stroke_index = st.number_input(
            f"SI {hole_number}",
            min_value=1,
            max_value=18,
            value=hole_number,
            step=1,
            key=f"course_si_{hole_number}",
            label_visibility="collapsed"
        )

    holes.append(
        {
            "hole": hole_number,
            "par": par,
            "stroke_index": stroke_index
        }
    )


st.divider()


# ============================================================
# VALIDATION
# ============================================================

errors = []

stroke_indexes = [
    hole["stroke_index"]
    for hole in holes
]

if len(set(stroke_indexes)) != 18:

    errors.append(
        "Stroke Index values must contain every "
        "number from 1 to 18 exactly once."
    )

if sorted(stroke_indexes) != list(
    range(1, 19)
):

    errors.append(
        "Stroke Index must be exactly 1 through 18."
    )


# ============================================================
# CREATE
# ============================================================

if errors:

    for error in errors:

        st.error(error)

else:

    st.success(
        "Course hole information is valid."
    )

    if st.button(
        "⛳ Save Golf Course",
        type="primary"
    ):

        if not course_name.strip():

            st.error(
                "Please enter a course name."
            )

        else:

            try:

                create_course(
                    course_name,
                    course_location,
                    holes
                )

                st.success(
                    f"{course_name} has been saved!"
                )

                st.rerun()

            except Exception as error:

                st.error(
                    "Unable to save the course."
                )

                st.exception(error)


st.divider()


# ============================================================
# EXISTING COURSES
# ============================================================

st.subheader("Existing Courses")

courses = get_courses()

if courses.empty:

    st.info(
        "No courses have been added yet."
    )

else:

    for _, course in courses.iterrows():

        status = (
            "🟢 Active"
            if course["active"]
            else "⚪ Inactive"
        )

        location = (
            course["location"]
            if pd.notna(course["location"])
            else ""
        )

        st.write(
            f"**{course['name']}**"
            f" — {location} — {status}"
        )
