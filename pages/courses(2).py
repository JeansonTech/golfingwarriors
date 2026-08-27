import streamlit as st
import pandas as pd

from database import get_connection
from auth import is_admin, require_admin


st.set_page_config(
    page_title="Golfing Warriors - Courses",
    page_icon="⛳",
    layout="wide"
)


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

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


def get_course_holes(course_id):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                hole_number,
                par,
                stroke_index
            FROM course_holes
            WHERE course_id = %s
            ORDER BY hole_number
            """,
            connection,
            params=(int(course_id),)
        )

    finally:

        connection.close()


def create_course(name, location, holes):

    require_admin()

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

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

def update_course(
    course_id,
    name,
    location,
    holes
):

    require_admin()

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # UPDATE COURSE DETAILS
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE courses
                SET
                    name = %s,
                    location = %s
                WHERE id = %s
                """,
                (
                    name.strip(),
                    location.strip()
                    if location
                    else None,
                    int(course_id)
                )
            )

            # -------------------------------------------------
            # VALIDATE STROKE INDEXES
            # -------------------------------------------------

            stroke_indexes = [
                int(hole["stroke_index"])
                for hole in holes
            ]

            if sorted(stroke_indexes) != list(
                range(1, 19)
            ):

                raise ValueError(
                    "Stroke Index must contain "
                    "every number from 1 to 18 exactly once."
                )

            # -------------------------------------------------
            # REPLACE COURSE HOLES
            #
            # We delete and recreate the 18 master holes
            # inside ONE database transaction.
            #
            # This allows Stroke Index values to be swapped
            # without triggering the UNIQUE constraint.
            # -------------------------------------------------

            cursor.execute(
                """
                DELETE FROM course_holes
                WHERE course_id = %s
                """,
                (int(course_id),)
            )

            # -------------------------------------------------
            # INSERT UPDATED HOLES
            # -------------------------------------------------

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

        # -----------------------------------------------------
        # COMMIT EVERYTHING TOGETHER
        # -----------------------------------------------------

        connection.commit()

    except Exception:

        # If anything goes wrong, restore the original course.
        connection.rollback()

        raise

    finally:

        connection.close()

# ============================================================
# PAGE
# ============================================================

st.title("⛳ Courses")

st.caption(
    "Manage the golf courses used by Golfing Warriors."
)

admin_mode = is_admin()

st.divider()


if admin_mode:

    # ============================================================
    # CREATE COURSE
    # ============================================================

    st.subheader("➕ Add Golf Course")

    course_name = st.text_input(
        "Course Name",
        placeholder="e.g. Mokopane Golf Club",
        key="new_course_name"
    )

    course_location = st.text_input(
        "Location",
        placeholder="Optional",
        key="new_course_location"
    )

    st.write("### Hole Information")

    st.caption(
        "Enter the par and stroke index for each hole."
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

            st.write(f"**{hole_number}**")

        with col2:

            par = st.number_input(
                f"Par {hole_number}",
                min_value=3,
                max_value=6,
                value=4,
                step=1,
                key=f"new_par_{hole_number}",
                label_visibility="collapsed"
            )

        with col3:

            stroke_index = st.number_input(
                f"SI {hole_number}",
                min_value=1,
                max_value=18,
                value=hole_number,
                step=1,
                key=f"new_si_{hole_number}",
                label_visibility="collapsed"
            )

        holes.append(
            {
                "hole": hole_number,
                "par": par,
                "stroke_index": stroke_index
            }
        )


    # ============================================================
    # VALIDATE NEW COURSE
    # ============================================================

    new_stroke_indexes = [
        hole["stroke_index"]
        for hole in holes
    ]

    new_course_valid = (
        sorted(new_stroke_indexes)
        == list(range(1, 19))
    )


    if not new_course_valid:

        st.error(
            "Stroke Index must contain every number "
            "from 1 to 18 exactly once."
        )

    else:

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




# ============================================================
# EXISTING COURSES
# ============================================================

st.divider()

st.subheader("⛳ Existing Courses")

courses = get_courses()

if courses.empty:

    st.info(
        "No courses have been added yet."
    )

else:

    for _, course in courses.iterrows():

        location = (
            course["location"]
            if pd.notna(course["location"])
            else ""
        )

        status = (
            "🟢 Active"
            if course["active"]
            else "⚪ Inactive"
        )

        st.markdown(
            f"### {course['name']}"
        )

        st.write(
            f"{location} — {status}"
        )

        # ----------------------------------------------------
        # COURSE HOLE INFORMATION
        # ----------------------------------------------------

        course_holes = get_course_holes(
            course["id"]
        )

        with st.expander(
            "View current hole information"
        ):

            display = course_holes.copy()

            display.columns = [
                "Hole",
                "Par",
                "Stroke Index"
            ]

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True
            )

        if admin_mode:

                    # ----------------------------------------------------
                    # EDIT COURSE
                    # ----------------------------------------------------

                    with st.expander(
                        "✏️ Edit Course"
                    ):

                        edit_name = st.text_input(
                            "Course Name",
                            value=course["name"],
                            key=f"edit_name_{course['id']}"
                        )

                        edit_location = st.text_input(
                            "Location",
                            value=(
                                course["location"]
                                if pd.notna(course["location"])
                                else ""
                            ),
                            key=f"edit_location_{course['id']}"
                        )

                        st.write("#### Edit Holes")

                        edited_holes = []

                        for _, hole in course_holes.iterrows():

                            col1, col2, col3 = st.columns(
                                [1, 1, 2]
                            )

                            with col1:

                                st.write(
                                    f"**Hole {int(hole['hole_number'])}**"
                                )

                            with col2:

                                edit_par = st.number_input(
                                    "Par",
                                    min_value=3,
                                    max_value=6,
                                    value=int(hole["par"]),
                                    step=1,
                                    key=(
                                        f"edit_par_"
                                        f"{course['id']}_"
                                        f"{hole['hole_number']}"
                                    )
                                )

                            with col3:

                                edit_si = st.number_input(
                                    "Stroke Index",
                                    min_value=1,
                                    max_value=18,
                                    value=int(
                                        hole["stroke_index"]
                                    ),
                                    step=1,
                                    key=(
                                        f"edit_si_"
                                        f"{course['id']}_"
                                        f"{hole['hole_number']}"
                                    )
                                )

                            edited_holes.append(
                                {
                                    "hole": int(
                                        hole["hole_number"]
                                    ),
                                    "par": edit_par,
                                    "stroke_index": edit_si
                                }
                            )

                        edited_si = [
                            hole["stroke_index"]
                            for hole in edited_holes
                        ]

                        if sorted(edited_si) != list(
                            range(1, 19)
                        ):

                            st.error(
                                "Stroke Index must contain "
                                "every number from 1 to 18 "
                                "exactly once."
                            )

                        else:

                            st.warning(
                                "⚠️ Editing this course will "
                                "only affect future events. "
                                "Past events retain their original "
                                "course and Stroke Index information."
                            )

                            if st.button(
                                "💾 Save Course Changes",
                                key=f"save_course_{course['id']}",
                                type="primary"
                            ):

                                try:

                                    update_course(
                                        course["id"],
                                        edit_name,
                                        edit_location,
                                        edited_holes
                                    )

                                    st.success(
                                        "Course updated successfully."
                                    )

                                    st.rerun()

                                except Exception as error:

                                    st.error(
                                        "Unable to update course."
                                    )

                                    st.exception(error)

        st.divider()
