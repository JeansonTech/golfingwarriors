from decimal import Decimal, ROUND_HALF_UP


# ============================================================
# HANDICAP FUNCTIONS
# ============================================================

def round_handicap(handicap):
    """
    Convert an event handicap to the whole-number handicap
    used for stroke allocation.

    Uses normal half-up rounding rather than Python's
    banker's rounding.
    """

    value = Decimal(str(handicap))

    return int(
        value.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def strokes_received(handicap, stroke_index):
    """
    Determine the number of handicap strokes received
    on a particular hole.

    Positive handicap:
        10 = one stroke on SI 1-10
        19 = two strokes on SI 1, one stroke elsewhere
        42 = three strokes on SI 1-6,
             two strokes on SI 7-18
        64 = four strokes on SI 1-10,
             three strokes on SI 11-18

    Plus handicap:
        +1 gives one stroke back on SI 18
        +2 gives strokes back on SI 18 and 17
    """

    handicap = round_handicap(handicap)

    stroke_index = int(stroke_index)

    # --------------------------------------------------------
    # NORMAL HANDICAP
    # --------------------------------------------------------

    if handicap >= 0:

        full_rounds = handicap // 18
        remainder = handicap % 18

        strokes = full_rounds

        if remainder > 0 and stroke_index <= remainder:
            strokes += 1

        return strokes

    # --------------------------------------------------------
    # PLUS HANDICAP
    # --------------------------------------------------------

    plus_handicap = abs(handicap)

    full_rounds = plus_handicap // 18
    remainder = plus_handicap % 18

    strokes = full_rounds

    # Plus strokes are given back starting at SI 18,
    # then SI 17, SI 16, etc.

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
    Calculate the player's net score on a hole.
    """

    strokes = strokes_received(
        handicap,
        stroke_index
    )

    return int(gross_score) - strokes


def calculate_ips_points(
    gross_score,
    par,
    handicap,
    stroke_index
):
    """
    Calculate Golfing Warriors IPS points.

    Net Eagle or better = 4
    Net Birdie = 3
    Net Par = 2
    Net Bogey = 1
    Net Double Bogey or worse = 0
    """

    net_score = calculate_net_score(
        gross_score,
        handicap,
        stroke_index
    )

    difference = net_score - int(par)

    if difference <= -2:
        return 4

    if difference == -1:
        return 3

    if difference == 0:
        return 2

    if difference == 1:
        return 1

    return 0


# ============================================================
# PLAYER ROUND CALCULATION
# ============================================================

def calculate_player_round(
    player,
    holes,
    scores
):
    """
    Calculate the current round totals for one player.

    Returns both complete and partial-round information.
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

        par = int(hole["par"])

        stroke_index = int(
            hole["stroke_index"]
        )

        strokes = strokes_received(
            handicap,
            stroke_index
        )

        net = gross - strokes

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

    completed = len(hole_results)

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
        h for h in hole_results
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
        h for h in hole_results
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
        "player_id": int(player["player_id"]),
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
    Rank players after all 18 holes.

    NET:
        Lower is better.

    IPS:
        Higher is better.

    Tie breakers:
        1. Main score
        2. Last 6
        3. Last 3
        4. Last hole
    """

    completed_results = [
        result
        for result in results
        if result["completed"] == 18
    ]

    if event_format == "NET":

        ordered = sorted(
            completed_results,
            key=lambda result: (
                result["net_total"],
                result["last_6_net"],
                result["last_3_net"],
                result["last_hole_net"]
                if result["last_hole_net"] is not None
                else 999
            )
        )

    else:

        ordered = sorted(
            completed_results,
            key=lambda result: (
                -result["ips_total"],
                -result["last_6_ips"],
                -result["last_3_ips"],
                -result["last_hole_ips"]
                if result["last_hole_ips"] is not None
                else 999
            )
        )

    return ordered


# ============================================================
# RANKING POINT ALLOCATION
# ============================================================

def allocate_ranking_points(
    ranked_results,
    ranking_points
):
    """
    Allocate ranking points.

    Tied players share the average of the points
    for the positions they occupy.

    Example:

        2nd = 300
        3rd = 150

        If two players tie for 2nd:

        (300 + 150) / 2 = 225 each
    """

    if not ranked_results:
        return []

    output = []

    index = 0

    while index < len(ranked_results):

        current = ranked_results[index]

        # ----------------------------------------------------
        # Determine tie group
        # ----------------------------------------------------

        tie_group = [current]

        next_index = index + 1

        while next_index < len(ranked_results):

            other = ranked_results[next_index]

            if (
                current["net_total"]
                == other["net_total"]
                and current["last_6_net"]
                == other["last_6_net"]
                and current["last_3_net"]
                == other["last_3_net"]
                and current["last_hole_net"]
                == other["last_hole_net"]
            ):

                tie_group.append(other)

                next_index += 1

            else:

                break

        # ----------------------------------------------------
        # Positions occupied by the tie
        # ----------------------------------------------------

        first_position = index + 1

        last_position = (
            first_position
            + len(tie_group)
            - 1
        )

        positions = range(
            first_position,
            last_position + 1
        )

        points = [
            float(
                ranking_points.get(
                    position,
                    0
                )
            )
            for position in positions
        ]

        average_points = (
            sum(points) / len(points)
            if points
            else 0
        )

        # ----------------------------------------------------
        # Assign
        # ----------------------------------------------------

        for player in tie_group:

            player_copy = player.copy()

            player_copy[
                "final_position"
            ] = first_position

            player_copy[
                "ranking_points"
            ] = average_points

            output.append(
                player_copy
            )

        index = next_index

    return output
