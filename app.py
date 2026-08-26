import streamlit as st

from database import init_database, test_connection


st.set_page_config(
    page_title="Golfing Warriors",
    page_icon="🏌️",
    layout="wide"
)


def main():
    st.title("🏌️ Golfing Warriors")

    st.markdown(
        """
        ### Welcome to Golfing Warriors

        Your friends. Your golf. Your championship.
        """
    )

    # ---------------------------------------------------------
    # DATABASE INITIALISATION
    # ---------------------------------------------------------

    try:
        init_database()
        database_time = test_connection()

        st.success("🟢 Database connected successfully!")

        st.info(
            f"PostgreSQL is working correctly. "
            f"Server time: {database_time}"
        )

    except Exception as error:
        st.error("🔴 Database connection failed.")

        st.exception(error)

        st.stop()

    # ---------------------------------------------------------
    # TEMPORARY DASHBOARD
    # ---------------------------------------------------------

    st.divider()

    st.subheader("Golfing Warriors V1")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Players", "0")

    with col2:
        st.metric("Events", "0")

    with col3:
        st.metric("Championship Points", "0")

    st.divider()

    st.info(
        "Database foundation is ready. "
        "Player and event management will be added next."
    )


if __name__ == "__main__":
    main()
