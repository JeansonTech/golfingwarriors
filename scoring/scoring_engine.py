from decimal import Decimal, ROUND_HALF_UP


# ============================================================
# HANDICAP FUNCTIONS
# ============================================================

def round_handicap(handicap):
    """
    Convert an event handicap to a whole-number handicap
    for stroke allocation.
    """

    value = Decimal(str(handicap))

    return int(
        value.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def strokes_received(
    handicap,
    stroke_index
):
    """
    Determine handicap strokes received on a hole.

    Examples:

    HCP 10:
        SI 1-10 = 1 stroke
        SI 11-18 = 0

    HCP 19:
        SI 1 = 2 strokes
        SI 2-18 = 1 stroke

    HCP 42:
        SI 1-6 = 3 strokes
        SI 7-18 = 2 strokes

    HCP 64:
        SI 1-10 = 4 strokes
        SI 11-18 = 3 strokes
    """

    handicap = round_handicap(
        handicap
    )

    stroke_index = int(
        stroke_index
    )

    # --------------------------------------------------------
    # POSITIVE / NORMAL HANDICAP
    # --------------------------------------------------------

    if handicap >= 0:

        full_rounds = handicap // 18

        remainder = handicap % 18

        strokes = full_rounds

        if (
            remainder > 0
            and stroke_index <= remainder
        ):

            strokes += 1

        return strokes

    # --------------------------------------------------------
    # PLUS HANDICAP
    # --------------------------------------------------------

    plus_handicap = abs(
        handicap
    )

    full_rounds = plus_handicap // 18

    remainder = plus_handicap % 18

    strokes = full_rounds

    if (
        remainder > 0
        and stroke_index > 18 - remainder
    ):

        strokes += 1

    return -strokes


# ============================================================
# HOLE CALCULATIONS
# ============================================================

def calculate_net_score(
    gross_score,
    handicap,
    stroke_index
):
    """
    Calculate net score for one hole.
    """

    strokes = strokes_received(
        handicap,
        stroke_index
    )

    return (
        int(gross_score)
        - strokes
    )


def calculate_ips_points(
    gross_score,
    par,
    handicap,
    stroke_index
):
    """
    Golfing Warriors IPS scoring.

    Start at 2 points for net par and adjust by the
    number of strokes under or over par.

    Net score 2 under par = 4 points
    Net score 1 under par = 3 points
    Net par = 2 points
    Net bogey = 1 point
    Net double bogey or worse = 0 points

    There is no upper cap on IPS points. This means that
    an exceptional high-handicap hole can score more than
    4 points. For example, on a par 5, a net 2 scores 5.
    """

    net_score = calculate_net_score(
        gross_score,
        handicap,
        stroke_index
    )

    points = 2 + (
        int(par)
        - net_score
    )

    return max(0, points)


# ============================================================
# PLAYER ROUND
# ============================================================

def calculate_player_round(
    player,
    holes,
    scores
):
    """
    Calculate a player's current round.

    Scores can be incomplete during live scoring.
    """

    handicap = float(
        player["event_handicap"]
    )

    hole_results = []

    for hole in holes:

        hole_number = int(
            hole["hole_number"]
        )

        gross = scores.get(
            hole_number
        )

        if gross is None:
            continue

        gross = int(gross)

        par = int(
            hole["par"]
        )

        stroke_index = int(
            hole["stroke_index"]
        )

        strokes = strokes_received(
            handicap,
            stroke_index
        )

        net = (
            gross
            - strokes
        )

        ips = calculate_ips_points(
            gross,
            par,
            handicap,
            stroke_index
        )

        hole_results.append(
            {
                "hole": hole_number,
                "par": par,
                "stroke_index": stroke_index,
                "gross": gross,
                "strokes": strokes,
                "net": net,
                "ips": ips
            }
        )

    completed = len(
        hole_results
    )

    gross_total = sum(
        h["gross"]
        for h in hole_results
    )

    net_total = sum(
        h["net"]
        for h in hole_results
    )

    ips_total = sum(
        h["ips"]
        for h in hole_results
    )

    # --------------------------------------------------------
    # LAST 6
    # --------------------------------------------------------

    last_6 = [
        h
        for h in hole_results
        if h["hole"] >= 13
    ]

    last_6_net = sum(
        h["net"]
        for h in last_6
    )

    last_6_ips = sum(
        h["ips"]
        for h in last_6
    )

    # --------------------------------------------------------
    # LAST 3
    # --------------------------------------------------------

    last_3 = [
        h
        for h in hole_results
        if h["hole"] >= 16
    ]

    last_3_net = sum(
        h["net"]
        for h in last_3
    )

    last_3_ips = sum(
        h["ips"]
        for h in last_3
    )

    # --------------------------------------------------------
    # LAST HOLE
    # --------------------------------------------------------

    last_hole = next(
        (
            h
            for h in hole_results
            if h["hole"] == 18
        ),
        None
    )

    last_hole_net = (
        last_hole["net"]
        if last_hole
        else None
    )

    last_hole_ips = (
        last_hole["ips"]
        if last_hole
        else None
    )

    return {
        "player_id": int(
            player["player_id"]
        ),
        "name": player["name"],
        "handicap": handicap,
        "completed": completed,
        "gross_total": gross_total,
        "net_total": net_total,
        "ips_total": ips_total,
        "last_6_net": last_6_net,
        "last_6_ips": last_6_ips,
        "last_3_net": last_3_net,
        "last_3_ips": last_3_ips,
        "last_hole_net": last_hole_net,
        "last_hole_ips": last_hole_ips,
        "holes": hole_results
    }


# ============================================================
# FINAL RANKING
# ============================================================

def rank_completed_players(
    results,
    event_format
):
    """
    Rank completed players by the event's main competition format.

    NET uses lowest net strokes. IPS uses highest IPS points. Countback
    breaks ties for first only; ties at later positions remain tied.
    """
    is_net = str(event_format).upper() == "NET"
    score_key = "net_total" if is_net else "ips_total"
    tie_breakers = (
        ("last_6_net", "last_3_net", "last_hole_net")
        if is_net else
        ("last_6_ips", "last_3_ips", "last_hole_ips")
    )
    completed = [r for r in results if r["completed"] == 18]
    ranked = sorted(
        completed,
        key=lambda r: (
            int(r[score_key]) if is_net else -int(r[score_key]),
            str(r.get("name", ""))
        )
    )
    if not ranked:
        return ranked

    first_score = int(ranked[0][score_key])
    first_group = [r for r in ranked if int(r[score_key]) == first_score]
    remaining = [r for r in ranked if int(r[score_key]) != first_score]

    def countback_value(result, key):
        value = result.get(key)
        if value is None:
            return 999 if is_net else -999
        value = int(value)
        return value if is_net else -value

    first_group.sort(
        key=lambda r: (
            *(countback_value(r, key) for key in tie_breakers),
            str(r.get("name", ""))
        )
    )
    return first_group + remaining


# ============================================================
# RANKING POINTS
# ============================================================

def allocate_ranking_points(
    ranked_results,
    ranking_points,
    event_format
):
    """
    Allocate championship points by the event's main format.

    Countback separates a tie for first. Other ties share the points for
    the positions they occupy.
    """
    if not ranked_results:
        return []

    is_net = str(event_format).upper() == "NET"
    score_key = "net_total" if is_net else "ips_total"
    tie_breakers = (
        ("last_6_net", "last_3_net", "last_hole_net")
        if is_net else
        ("last_6_ips", "last_3_ips", "last_hole_ips")
    )
    first_score = int(ranked_results[0][score_key])

    def remains_tied(left, right):
        left_score = int(left[score_key])
        right_score = int(right[score_key])
        if left_score != right_score:
            return False
        if left_score != first_score:
            return True
        return all(left.get(key) == right.get(key) for key in tie_breakers)

    output = []
    index = 0
    while index < len(ranked_results):
        group = [ranked_results[index]]
        next_index = index + 1
        while next_index < len(ranked_results) and remains_tied(
            group[0], ranked_results[next_index]
        ):
            group.append(ranked_results[next_index])
            next_index += 1

        first_position = index + 1
        last_position = first_position + len(group) - 1
        points = [
            float(ranking_points.get(position, 0))
            for position in range(first_position, last_position + 1)
        ]
        average_points = sum(points) / len(points) if points else 0
        for player in group:
            row = player.copy()
            row["final_position"] = first_position
            row["ranking_points"] = average_points
            output.append(row)
        index = next_index
    return output


