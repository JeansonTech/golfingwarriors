import streamlit as st
import pandas as pd

from database import get_connection


st.set_page_config(
    page_title="Golfing Warriors - Leaderboards",
    page_icon="🏆",
    layout="wide"
)


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_seasons():

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                id,
                name,
                year,
                active
            FROM seasons
            ORDER BY year DESC
            """,
            connection
        )

    finally:

        connection.close()


def get_overall_leaderboard(
    season_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                p.id AS player_id,
                p.name,

                COUNT(DISTINCT rp.event_id)
                    AS events_played,

                COUNT(
                    CASE
                        WHEN er.final_position = 1
                        THEN 1
                    END
                ) AS wins,

                COUNT(
                    CASE
                        WHEN er.final_position <= 3
                        THEN 1
                    END
                ) AS podiums,

                COALESCE(
                    SUM(rp.points),
                    0
                ) AS total_points

            FROM ranking_points rp

            INNER JOIN players p
                ON rp.player_id = p.id

            INNER JOIN events e
                ON rp.event_id = e.id

            LEFT JOIN event_results er
                ON er.event_id = rp.event_id
                AND er.player_id = rp.player_id

            WHERE
                rp.season_id = %s
                AND e.status = 'CLOSED'

            GROUP BY
                p.id,
                p.name

            ORDER BY
                total_points DESC,
                wins DESC,
                podiums DESC,
                p.name ASC
            """,
            connection,
            params=(int(season_id),)
        )

    finally:

        connection.close()


def get_net_leaderboard(
    season_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                p.id AS player_id,
                p.name,

                COUNT(er.id)
                    AS events_played,

                COUNT(
                    CASE
                        WHEN er.final_position = 1
                        THEN 1
                    END
                ) AS wins,

                AVG(er.net_total)
                    AS average_net,

                MIN(er.net_total)
                    AS best_net

            FROM event_results er

            INNER JOIN players p
                ON er.player_id = p.id

            INNER JOIN events e
                ON er.event_id = e.id

            WHERE
                e.season_id = %s
                AND e.status = 'CLOSED'
                AND e.format = 'NET'

            GROUP BY
                p.id,
                p.name

            ORDER BY
                average_net ASC,
                best_net ASC,
                wins DESC,
                p.name ASC
            """,
            connection,
            params=(int(season_id),)
        )

    finally:

        connection.close()


def get_ips_leaderboard(
    season_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                p.id AS player_id,
                p.name,

                COUNT(er.id)
                    AS events_played,

                COUNT(
                    CASE
                        WHEN er.final_position = 1
                        THEN 1
                    END
                ) AS wins,

                AVG(er.ips_total)
                    AS average_ips,

                MAX(er.ips_total)
                    AS best_ips

            FROM event_results er

            INNER JOIN players p
                ON er.player_id = p.id

            INNER JOIN events e
                ON er.event_id = e.id

            WHERE
                e.season_id = %s
                AND e.status = 'CLOSED'
                AND e.format = 'IPS'

            GROUP BY
                p.id,
                p.name

            ORDER BY
                average_ips DESC,
                best_ips DESC,
                wins DESC,
                p.name ASC
            """,
            connection,
            params=(int(season_id),)
        )

    finally:

        connection.close()


def get_player_history(
    season_id,
    player_id
):

    connection = get_connection()

    try:

        return pd.read_sql_query(
            """
            SELECT
                e.name AS event_name,
                e.event_date,
                e.format,

                c.name AS course_name,

                er.final_position,
                er.gross_total,
                er.net_total,
                er.ips_total,

                er.last_6_score,
                er.last_3_score,
                er.last_hole_score,

                er.ranking_points

            FROM event_results er

            INNER JOIN events e
                ON er.event_id = e.id

            LEFT JOIN courses c
                ON e.course_id = c.id

            WHERE
                e.season_id = %s
                AND er.player_id = %s
                AND e.status = 'CLOSED'

            ORDER BY
                e.event_date ASC,
                e.id ASC
            """,
            connection,
            params=(
                int(season_id),
                int(player_id)
            )
        )

    finally:

        connection.close()


# ============================================================
# PAGE
# ============================================================

st.title(
    "🏆 Golfing Warriors Leaderboards"
)

st.caption(
    "Track the battle for the Golfing Warriors Championship."
)

st.divider()


# ============================================================
# SEASON SELECTOR
# ============================================================

seasons = get_seasons()


if seasons.empty:

    st.warning(
        "No seasons have been created yet."
    )

    st.stop()


season_options = {}

for _, season in seasons.iterrows():

    label = (
        f"{season['name']} "
        f"({season['year']})"
    )

    if bool(season["active"]):

        label += " — ACTIVE"

    season_options[
        label
    ] = int(season["id"])


selected_season_label = st.selectbox(
    "📅 Season",
    list(
        season_options.keys()
    )
)


season_id = season_options[
    selected_season_label
]


# ============================================================
# LOAD LEADERBOARDS
# ============================================================

overall = get_overall_leaderboard(
    season_id
)

net = get_net_leaderboard(
    season_id
)

ips = get_ips_leaderboard(
    season_id
)


# ============================================================
# SUMMARY
# ============================================================

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "🏆 Overall Players",
        len(overall)
    )


with col2:

    st.metric(
        "🟢 Net Players",
        len(net)
    )


with col3:

    st.metric(
        "🔵 IPS Players",
        len(ips)
    )


# ============================================================
# TABS
# ============================================================

tab_overall, tab_net, tab_ips = st.tabs(
    [
        "🏆 Overall Championship",
        "🟢 Net",
        "🔵 IPS"
    ]
)


# ============================================================
# OVERALL CHAMPIONSHIP
# ============================================================

with tab_overall:

    st.subheader(
        "🏆 Golfing Warriors Championship"
    )

    st.caption(
        "Overall standings are determined by "
        "cumulative ranking points."
    )


    if overall.empty:

        st.info(
            "No completed events have contributed "
            "ranking points to this season yet."
        )

    else:

        overall_rows = []


        for position, (_, row) in enumerate(
            overall.iterrows(),
            start=1
        ):

            if position == 1:

                pos_display = "🥇 1"

            elif position == 2:

                pos_display = "🥈 2"

            elif position == 3:

                pos_display = "🥉 3"

            else:

                pos_display = str(
                    position
                )


            overall_rows.append(
                {
                    "Pos":
                        pos_display,

                    "Player":
                        row["name"],

                    "Events":
                        int(
                            row[
                                "events_played"
                            ]
                        ),

                    "Wins":
                        int(
                            row["wins"]
                        ),

                    "Podiums":
                        int(
                            row["podiums"]
                        ),

                    "Championship Points":
                        float(
                            row[
                                "total_points"
                            ]
                        )
                }
            )


        overall_display = pd.DataFrame(
            overall_rows
        )


        st.dataframe(
            overall_display,
            use_container_width=True,
            hide_index=True
        )


        # ----------------------------------------------------
        # CURRENT LEADER
        # ----------------------------------------------------

        leader = overall.iloc[0]


        st.success(
            f"🏆 Current Championship Leader: "
            f"**{leader['name']}** — "
            f"**{float(leader['total_points']):g} points**"
        )


# ============================================================
# NET LEADERBOARD
# ============================================================

with tab_net:

    st.subheader(
        "🟢 Net Leaderboard"
    )

    st.caption(
        "Lower average Net score is better."
    )


    if net.empty:

        st.info(
            "No completed NET events have "
            "been played this season."
        )

    else:

        net_rows = []


        for position, (_, row) in enumerate(
            net.iterrows(),
            start=1
        ):

            if position == 1:

                pos_display = "🥇 1"

            elif position == 2:

                pos_display = "🥈 2"

            elif position == 3:

                pos_display = "🥉 3"

            else:

                pos_display = str(
                    position
                )


            net_rows.append(
                {
                    "Pos":
                        pos_display,

                    "Player":
                        row["name"],

                    "Events":
                        int(
                            row[
                                "events_played"
                            ]
                        ),

                    "Wins":
                        int(
                            row["wins"]
                        ),

                    "Average Net":
                        round(
                            float(
                                row[
                                    "average_net"
                                ]
                            ),
                            2
                        ),

                    "Best Net":
                        int(
                            row[
                                "best_net"
                            ]
                        )
                }
            )


        net_display = pd.DataFrame(
            net_rows
        )


        st.dataframe(
            net_display,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# IPS LEADERBOARD
# ============================================================

with tab_ips:

    st.subheader(
        "🔵 IPS Leaderboard"
    )

    st.caption(
        "Higher average IPS is better."
    )


    if ips.empty:

        st.info(
            "No completed IPS events have "
            "been played this season."
        )

    else:

        ips_rows = []


        for position, (_, row) in enumerate(
            ips.iterrows(),
            start=1
        ):

            if position == 1:

                pos_display = "🥇 1"

            elif position == 2:

                pos_display = "🥈 2"

            elif position == 3:

                pos_display = "🥉 3"

            else:

                pos_display = str(
                    position
                )


            ips_rows.append(
                {
                    "Pos":
                        pos_display,

                    "Player":
                        row["name"],

                    "Events":
                        int(
                            row[
                                "events_played"
                            ]
                        ),

                    "Wins":
                        int(
                            row["wins"]
                        ),

                    "Average IPS":
                        round(
                            float(
                                row[
                                    "average_ips"
                                ]
                            ),
                            2
                        ),

                    "Best IPS":
                        int(
                            row[
                                "best_ips"
                            ]
                        )
                }
            )


        ips_display = pd.DataFrame(
            ips_rows
        )


        st.dataframe(
            ips_display,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PLAYER HISTORY
# ============================================================

st.divider()

st.header(
    "👤 Player Championship History"
)


all_players = set()


if not overall.empty:

    all_players.update(
        overall["name"].tolist()
    )


if not net.empty:

    all_players.update(
        net["name"].tolist()
    )


if not ips.empty:

    all_players.update(
        ips["name"].tolist()
    )


if not all_players:

    st.info(
        "There is no player history available yet."
    )

else:

    # --------------------------------------------------------
    # Get player IDs
    # --------------------------------------------------------

    connection = get_connection()

    try:

        player_lookup_df = pd.read_sql_query(
            """
            SELECT
                id,
                name
            FROM players
            ORDER BY name
            """,
            connection
        )

    finally:

        connection.close()


    player_options = {}

    for _, player in player_lookup_df.iterrows():

        if player["name"] in all_players:

            player_options[
                player["name"]
            ] = int(
                player["id"]
            )


    selected_player_name = st.selectbox(
        "Select Player",
        list(
            player_options.keys()
        )
    )


    selected_player_id = player_options[
        selected_player_name
    ]


    history = get_player_history(
        season_id,
        selected_player_id
    )


    if history.empty:

        st.info(
            "This player has no completed "
            "events in this season."
        )

    else:

        # ----------------------------------------------------
        # PLAYER SUMMARY
        # ----------------------------------------------------

        total_events = len(
            history
        )

        total_points = (
            history[
                "ranking_points"
            ]
            .sum()
        )

        wins = (
            history[
                "final_position"
            ]
            == 1
        ).sum()

        podiums = (
            history[
                "final_position"
            ]
            <= 3
        ).sum()


        summary1, summary2, summary3, summary4 = (
            st.columns(4)
        )


        with summary1:

            st.metric(
                "Events",
                int(
                    total_events
                )
            )


        with summary2:

            st.metric(
                "Wins",
                int(
                    wins
                )
            )


        with summary3:

            st.metric(
                "Podiums",
                int(
                    podiums
                )
            )


        with summary4:

            st.metric(
                "Points",
                float(
                    total_points
                )
            )


        # ----------------------------------------------------
        # HISTORY TABLE
        # ----------------------------------------------------

        st.subheader(
            f"📋 {selected_player_name}"
        )


        history_rows = []


        for _, row in history.iterrows():

            position = int(
                row[
                    "final_position"
                ]
            )


            if position == 1:

                position_display = "🥇 1"

            elif position == 2:

                position_display = "🥈 2"

            elif position == 3:

                position_display = "🥉 3"

            else:

                position_display = str(
                    position
                )


            history_rows.append(
                {
                    "Date":
                        row[
                            "event_date"
                        ],

                    "Event":
                        row[
                            "event_name"
                        ],

                    "Format":
                        row[
                            "format"
                        ],

                    "Course":
                        row[
                            "course_name"
                        ],

                    "Position":
                        position_display,

                    "Gross":
                        int(
                            row[
                                "gross_total"
                            ]
                        ),

                    "Net":
                        int(
                            row[
                                "net_total"
                            ]
                        ),

                    "IPS":
                        int(
                            row[
                                "ips_total"
                            ]
                        ),

                    "Ranking Points":
                        float(
                            row[
                                "ranking_points"
                            ]
                        )
                }
            )


        history_display = pd.DataFrame(
            history_rows
        )


        st.dataframe(
            history_display,
            use_container_width=True,
            hide_index=True
        )


        # ----------------------------------------------------
        # FORMAT STATISTICS
        # ----------------------------------------------------

        net_history = history[
            history["format"] == "NET"
        ]


        ips_history = history[
            history["format"] == "IPS"
        ]


        if not net_history.empty:

            st.subheader(
                "🟢 Net Statistics"
            )


            n1, n2, n3 = st.columns(3)


            with n1:

                st.metric(
                    "Events",
                    len(
                        net_history
                    )
                )


            with n2:

                st.metric(
                    "Average Net",
                    round(
                        net_history[
                            "net_total"
                        ].mean(),
                        2
                    )
                )


            with n3:

                st.metric(
                    "Best Net",
                    int(
                        net_history[
                            "net_total"
                        ].min()
                    )
                )


        if not ips_history.empty:

            st.subheader(
                "🔵 IPS Statistics"
            )


            i1, i2, i3 = st.columns(3)


            with i1:

                st.metric(
                    "Events",
                    len(
                        ips_history
                    )
                )


            with i2:

                st.metric(
                    "Average IPS",
                    round(
                        ips_history[
                            "ips_total"
                        ].mean(),
                        2
                    )
                )


            with i3:

                st.metric(
                    "Best IPS",
                    int(
                        ips_history[
                            "ips_total"
                        ].max()
                    )
                )
