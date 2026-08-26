
import streamlit as st
import pandas as pd

from database import get_connection


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Golfing Warriors - Statistics Leaderboard",
    page_icon="🏆",
    layout="wide"
)


# ============================================================
# MOBILE-FIRST STYLING
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 2rem;
        max-width: 1150px;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.22);
        border-radius: 12px;
        padding: 10px;
        background: rgba(128,128,128,0.035);
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.55rem;
            padding-right: 0.55rem;
        }

        h1 {
            font-size: 1.65rem !important;
        }

        h2 {
            font-size: 1.3rem !important;
        }

        h3 {
            font-size: 1.05rem !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.3rem;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.72rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_active_season():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                year

            FROM seasons

            WHERE active = TRUE

            ORDER BY year DESC

            LIMIT 1
            """,
            connection
        )

    finally:

        connection.close()


def get_players():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                nickname,
                active

            FROM players

            ORDER BY
                active DESC,
                name ASC
            """,
            connection
        )

    finally:

        connection.close()


def get_score_column():

    connection = get_connection()

    try:

        columns = pd.read_sql_query(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE
                table_schema = 'public'
                AND table_name = 'hole_scores'
            ORDER BY ordinal_position
            """,
            connection
        )

        available = {
            str(value).lower(): str(value)
            for value in columns["column_name"].tolist()
        }

        candidates = [
            "gross_score",
            "score",
            "strokes",
            "gross_strokes",
            "actual_score"
        ]

        for candidate in candidates:

            if candidate in available:
                return available[candidate]

        return None

    finally:

        connection.close()


def get_statistics(
    season_id=None
):

    connection = get_connection()

    try:

        score_column = get_score_column()

        if score_column is None:
            raise RuntimeError(
                "Unable to identify the hole score column."
            )

        filters = [
            "e.status = 'CLOSED'"
        ]

        params = []

        if season_id is not None:

            filters.append(
                "e.season_id = %s"
            )

            params.append(
                int(season_id)
            )

        where_clause = " AND ".join(filters)

        # score_column has been discovered from information_schema,
        # not supplied by the user, so it is safe to interpolate as
        # an SQL identifier.
        query = f"""
            SELECT
                hs.player_id,
                p.name AS player_name,
                hs.hole_number,
                hs.event_id,
                e.name AS event_name,
                e.event_date,
                eh.par,
                eh.stroke_index,
                hs.{score_column} AS score

            FROM hole_scores hs

            INNER JOIN events e
                ON hs.event_id = e.id

            INNER JOIN event_holes eh
                ON eh.event_id = hs.event_id
                AND eh.hole_number = hs.hole_number

            INNER JOIN players p
                ON p.id = hs.player_id

            WHERE
                {where_clause}

            ORDER BY
                e.event_date ASC,
                e.id ASC,
                hs.hole_number ASC
        """

        return pd.read_sql_query(
            query,
            connection,
            params=params
        )

    finally:

        connection.close()


# ============================================================
# LOAD
# ============================================================

players = get_players()
active_season = get_active_season()

if players.empty:

    st.info(
        "No players have been created yet."
    )

    st.stop()


try:

    data = get_statistics(
        None
    )

except Exception as error:

    st.error(
        "Unable to load statistics leaderboard."
    )

    st.exception(error)

    st.stop()


if data.empty:

    st.info(
        "No closed events with hole scores are available yet."
    )

    st.stop()


data["score"] = pd.to_numeric(
    data["score"],
    errors="coerce"
)

data["par"] = pd.to_numeric(
    data["par"],
    errors="coerce"
)

data = data.dropna(
    subset=["score", "par"]
)

data["to_par"] = (
    data["score"] - data["par"]
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "🏆 Golf Statistics Leaderboard"
)

st.caption(
    "The Golfing Warriors battle for bragging rights "
    "beyond championship points."
)


# ============================================================
# FILTERS
# ============================================================

season_options = {
    "All Seasons": None
}

if not active_season.empty:

    season = active_season.iloc[0]

    season_options[
        f"{season['name']} ({season['year']})"
    ] = int(
        season["id"]
    )

selected_season_label = st.selectbox(
    "🏆 Season",
    list(season_options.keys())
)

selected_season_id = season_options[
    selected_season_label
]


if selected_season_id is not None:

    data = get_statistics(
        selected_season_id
    )

    data["score"] = pd.to_numeric(
        data["score"],
        errors="coerce"
    )

    data["par"] = pd.to_numeric(
        data["par"],
        errors="coerce"
    )

    data = data.dropna(
        subset=["score", "par"]
    )

    data["to_par"] = (
        data["score"] - data["par"]
    )


if data.empty:

    st.info(
        "No completed hole scores for this season yet."
    )

    st.stop()


# ============================================================
# BUILD PLAYER STATISTICS
# ============================================================

grouped = (
    data
    .groupby(
        [
            "player_id",
            "player_name"
        ],
        as_index=False
    )
)


rows = []

for (player_id, player_name), player_data in grouped:

    holes = len(
        player_data
    )

    strokes = float(
        player_data["score"].sum()
    )

    total_par = float(
        player_data["par"].sum()
    )

    to_par = (
        player_data["to_par"]
    )

    birdies = int(
        (to_par == -1).sum()
    )

    eagles = int(
        (to_par <= -2).sum()
    )

    pars = int(
        (to_par == 0).sum()
    )

    bogeys = int(
        (to_par == 1).sum()
    )

    doubles = int(
        (to_par >= 2).sum()
    )

    rounds = (
        player_data["event_id"]
        .nunique()
    )

    average_score = (
        strokes / holes
        if holes
        else 0
    )

    average_to_par = (
        to_par.mean()
        if holes
        else 0
    )

    under_par_holes = int(
        (to_par < 0).sum()
    )

    par_percentage = (
        (pars / holes) * 100
        if holes
        else 0
    )

    birdie_rate = (
        (birdies / holes) * 100
        if holes
        else 0
    )

    rows.append(
        {
            "player_id": int(player_id),
            "Player": player_name,
            "Rounds": rounds,
            "Holes": holes,
            "Avg Score": average_score,
            "Avg vs Par": average_to_par,
            "Eagles": eagles,
            "Birdies": birdies,
            "Pars": pars,
            "Bogeys": bogeys,
            "Double+": doubles,
            "Par %": par_percentage,
            "Birdie %": birdie_rate,
            "Under Par Holes": under_par_holes
        }
    )


leaderboard = pd.DataFrame(
    rows
)


# ============================================================
# TOP SUMMARY CARDS
# ============================================================

st.divider()


def achievement_leader(
    dataframe,
    value_column,
    highest=True
):

    if dataframe.empty:
        return None

    valid = dataframe[
        dataframe[value_column] > 0
    ].copy()

    if valid.empty:
        return None

    valid = valid.sort_values(
        value_column,
        ascending=not highest
    )

    return valid.iloc[0]


best_scoring = leaderboard.sort_values(
    "Avg vs Par",
    ascending=True
).iloc[0]


birdie_leader = achievement_leader(
    leaderboard,
    "Birdies"
)


eagle_leader = achievement_leader(
    leaderboard,
    "Eagles"
)


best_par_rate = leaderboard.sort_values(
    "Par %",
    ascending=False
).iloc[0]


# ------------------------------------------------------------
# SUMMARY CARDS
# ------------------------------------------------------------

summary1, summary2 = st.columns(2)

with summary1:

    st.metric(
        "🔥 Best Avg vs Par",
        best_scoring["Player"]
    )

    st.caption(
        f"{best_scoring['Avg vs Par']:+.2f} "
        f"over {int(best_scoring['Holes'])} holes"
    )


with summary2:

    if birdie_leader is None:

        st.metric(
            "🐦 Birdie Leader",
            "No birdies yet"
        )

        st.caption(
            "Be the first Golfing Warrior to make one!"
        )

    else:

        st.metric(
            "🐦 Birdie Leader",
            birdie_leader["Player"]
        )

        st.caption(
            f"{int(birdie_leader['Birdies'])} birdies"
        )


summary3, summary4 = st.columns(2)

with summary3:

    st.metric(
        "⛳ Par Machine",
        best_par_rate["Player"]
    )

    st.caption(
        f"{best_par_rate['Par %']:.1f}% pars"
    )


with summary4:

    if eagle_leader is None:

        st.metric(
            "🦅 Eagle Leader",
            "No eagles yet"
        )

        st.caption(
            "Be the first Golfing Warrior to make one!"
        )

    else:

        st.metric(
            "🦅 Eagle Leader",
            eagle_leader["Player"]
        )

        st.caption(
            f"{int(eagle_leader['Eagles'])} eagles or better"
        )


# ============================================================
# MAIN STATISTICS TABLE
# ============================================================

st.divider()

st.header(
    "📊 All-Round Statistics"
)

display = leaderboard[
    [
        "Player",
        "Rounds",
        "Avg Score",
        "Avg vs Par",
        "Eagles",
        "Birdies",
        "Pars",
        "Bogeys",
        "Double+",
        "Par %",
        "Birdie %"
    ]
].copy()

display = display.sort_values(
    [
        "Avg vs Par",
        "Birdies"
    ],
    ascending=[
        True,
        False
    ]
)


st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Avg Score":
            st.column_config.NumberColumn(
                "Avg Score",
                format="%.2f"
            ),

        "Avg vs Par":
            st.column_config.NumberColumn(
                "Avg vs Par",
                format="%+.2f"
            ),

        "Par %":
            st.column_config.NumberColumn(
                "Par %",
                format="%.1f%%"
            ),

        "Birdie %":
            st.column_config.NumberColumn(
                "Birdie %",
                format="%.1f%%"
            )
    }
)


# ============================================================
# INDIVIDUAL STAT LEADERBOARDS
# ============================================================

st.divider()

st.header(
    "🏆 Statistics Leaders"
)


leader_tabs = st.tabs(
    [
        "🐦 Birdies",
        "🦅 Eagles",
        "⛳ Par %",
        "📈 Avg vs Par",
        "💀 Bogeys",
        "😈 Double+"
    ]
)


def show_stat_leaderboard(
    dataframe,
    sort_column,
    ascending,
    title,
    value_format,
    achievement=False,
    empty_message="No results yet."
):

    if achievement:

        valid = dataframe[
            dataframe[sort_column] > 0
        ].copy()

        if valid.empty:

            st.info(
                empty_message
            )

            return

        result = valid.sort_values(
            sort_column,
            ascending=ascending
        ).reset_index(
            drop=True
        )

    else:

        result = dataframe.sort_values(
            sort_column,
            ascending=ascending
        ).reset_index(
            drop=True
        )

    result = result.head(10)

    output = []

    for index, row in result.iterrows():

        position = index + 1

        if position == 1:
            medal = "🥇"
        elif position == 2:
            medal = "🥈"
        elif position == 3:
            medal = "🥉"
        else:
            medal = f"{position}."

        output.append(
            {
                "Pos":
                    medal,

                "Player":
                    row["Player"],

                title:
                    value_format(
                        row[sort_column]
                    ),

                "Rounds":
                    int(row["Rounds"])
            }
        )

    st.dataframe(
        pd.DataFrame(output),
        use_container_width=True,
        hide_index=True
    )


with leader_tabs[0]:

    show_stat_leaderboard(
        leaderboard,
        "Birdies",
        False,
        "Birdies",
        lambda value: f"{int(value)}",
        achievement=True,
        empty_message=(
            "🐦 **No birdies recorded yet.** "
            "Be the first Golfing Warrior to make one!"
        )
    )


with leader_tabs[1]:

    show_stat_leaderboard(
        leaderboard,
        "Eagles",
        False,
        "Eagles",
        lambda value: f"{int(value)}",
        achievement=True,
        empty_message=(
            "🦅 **No eagles recorded yet.** "
            "Be the first Golfing Warrior to make one!"
        )
    )


with leader_tabs[2]:

    show_stat_leaderboard(
        leaderboard,
        "Par %",
        False,
        "Par %",
        lambda value: f"{value:.1f}%"
    )


with leader_tabs[3]:

    show_stat_leaderboard(
        leaderboard,
        "Avg vs Par",
        True,
        "Avg vs Par",
        lambda value: f"{value:+.2f}"
    )


with leader_tabs[4]:

    show_stat_leaderboard(
        leaderboard,
        "Bogeys",
        False,
        "Bogeys",
        lambda value: f"{int(value)}",
        achievement=True,
        empty_message=(
            "😬 **No bogeys recorded yet.**"
        )
    )


with leader_tabs[5]:

    show_stat_leaderboard(
        leaderboard,
        "Double+",
        False,
        "Double+",
        lambda value: f"{int(value)}",
        achievement=True,
        empty_message=(
            "💀 **No double bogeys or worse recorded yet.**"
        )
    )


# ============================================================
# PAR 3 / 4 / 5 LEADERS
# ============================================================

st.divider()

st.header(
    "🎯 Par 3 / 4 / 5 Specialists"
)


specialist_rows = []

for (player_id, player_name), player_data in data.groupby(
    ["player_id", "player_name"]
):

    row = {
        "Player": player_name
    }

    for par_value in [3, 4, 5]:

        par_data = player_data[
            player_data["par"] == par_value
        ]

        if par_data.empty:

            row[
                f"Par {par_value} Avg"
            ] = None

        else:

            row[
                f"Par {par_value} Avg"
            ] = float(
                par_data["to_par"].mean()
            )

    specialist_rows.append(row)


specialists = pd.DataFrame(
    specialist_rows
)


spec_col1, spec_col2, spec_col3 = st.columns(3)


for column, par_value, container in [
    ("Par 3 Avg", 3, spec_col1),
    ("Par 4 Avg", 4, spec_col2),
    ("Par 5 Avg", 5, spec_col3)
]:

    with container:

        st.subheader(
            f"⛳ Par {par_value}"
        )

        subset = specialists[
            [
                "Player",
                column
            ]
        ].dropna()

        subset = subset.sort_values(
            column,
            ascending=True
        ).head(5)

        subset = subset.copy()

        subset[column] = subset[
            column
        ].map(
            lambda value: f"{value:+.2f}"
        )

        st.dataframe(
            subset,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# NAVIGATION
# ============================================================

st.divider()

nav1, nav2 = st.columns(2)

with nav1:

    if st.button(
        "⛳ Golf Statistics",
        use_container_width=True
    ):

        st.switch_page(
            "pages/golf_statistics.py"
        )


with nav2:

    if st.button(
        "🏆 Main Leaderboards",
        use_container_width=True
    ):

        st.switch_page(
            "pages/leaderboards.py"
        )


st.caption(
    "🏌️ Golfing Warriors • "
    "Your friends. Your golf. Your championship."
)
