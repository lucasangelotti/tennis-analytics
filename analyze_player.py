import os
import sys
import mysql.connector
from dotenv import load_dotenv

# ── 1. CONNECT ────────────────────────────────────────────────────────────────
load_dotenv()

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("DB_PASSWORD"),
    database="tennis_analytics"
)
cursor = conn.cursor(dictionary=True)

# ── 2. SELECT PLAYER ──────────────────────────────────────────────────────────
# Usage: python3 analyze_player.py "Player Name"
# If no argument given, lists all players and exits.

def list_players():
    cursor.execute("""
        SELECT DISTINCT player FROM (
            SELECT player1 AS player FROM matches
            UNION
            SELECT player2 AS player FROM matches
        ) AS all_players
        ORDER BY player
    """)
    rows = cursor.fetchall()
    print("\n=== AVAILABLE PLAYERS ===")
    for r in rows:
        print(f"  {r['player']}")
    print("\nRun: python3 analyze_player.py \"Player Name\"")

if len(sys.argv) < 2:
    list_players()
    cursor.close()
    conn.close()
    sys.exit(0)

PLAYER = sys.argv[1]

# ── 3. GET MATCHES FOR PLAYER ─────────────────────────────────────────────────
cursor.execute("""
    SELECT m.match_id, m.player1, m.player2, m.tournament,
           m.match_date, m.round, m.surface
    FROM matches m
    JOIN points p ON m.match_id = p.match_id
    WHERE m.player1 = %s OR m.player2 = %s
    GROUP BY m.match_id
    ORDER BY m.match_date DESC
""", (PLAYER, PLAYER))
matches = cursor.fetchall()

if not matches:
    print(f"No matches found for '{PLAYER}'.")
    sys.exit(1)

match_ids = [m["match_id"] for m in matches]
ids_placeholder = ",".join(["%s"] * len(match_ids))

def pct(a, b):
    return f"{100*a/b:.1f}%" if b else "N/A"

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ── 4. HEADER ─────────────────────────────────────────────────────────────────
print(f"\n{'*'*60}")
print(f"  PLAYER REPORT  —  {PLAYER}")
print(f"  {len(matches)} match(es) analyzed")
print(f"{'*'*60}")

print(f"\n  Matches:")
for m in matches:
    opponent = m["player2"] if m["player1"] == PLAYER else m["player1"]
    print(f"    [{m['match_id']}] {m['match_date']}  vs {opponent}  {m['tournament']}  {m['round']}")

# ── 5. OVERALL POINTS WON ────────────────────────────────────────────────────
section("OVERALL POINTS WON")

cursor.execute(f"""
    SELECT COUNT(*) AS total,
           SUM(point_winner = %s) AS won
    FROM points
    WHERE match_id IN ({ids_placeholder})
""", [PLAYER] + match_ids)
r = cursor.fetchone()
print(f"\n  Total points played:  {r['total']}")
print(f"  Points won:           {r['won']}  ({pct(r['won'], r['total'])})")

# ── 6. SERVE STATS ────────────────────────────────────────────────────────────
section("SERVE STATS (as server)")

cursor.execute(f"""
    SELECT
        COUNT(*) AS total_served,
        SUM(serve_number = 1) AS first_serves_in,
        SUM(serve_number = 2) AS second_serve_points,
        SUM(outcome = 'ace') AS aces,
        SUM(outcome = 'double_fault') AS double_faults,
        SUM(outcome = 'unreturnable') AS unreturnables,
        SUM(point_winner = %s AND serve_number = 1) AS won_on_1st,
        SUM(point_winner = %s AND serve_number = 2) AS won_on_2nd
    FROM points
    WHERE match_id IN ({ids_placeholder}) AND server = %s
""", [PLAYER, PLAYER] + match_ids + [PLAYER])
s = cursor.fetchone()

first_attempts = (s["first_serves_in"] or 0) + (s["second_serve_points"] or 0)
print(f"\n  1st Serve In:        {pct(s['first_serves_in'] or 0, first_attempts)}  ({s['first_serves_in']}/{first_attempts})")
print(f"  1st Serve Pts Won:   {pct(s['won_on_1st'] or 0, s['first_serves_in'] or 1)}  ({s['won_on_1st']}/{s['first_serves_in']})")
print(f"  2nd Serve Pts Won:   {pct(s['won_on_2nd'] or 0, s['second_serve_points'] or 1)}  ({s['won_on_2nd']}/{s['second_serve_points']})")
print(f"  Aces:                {s['aces']}")
print(f"  Double Faults:       {s['double_faults']}")
print(f"  Unreturnables:       {s['unreturnables']}")

# ── 7. SERVE DIRECTION ────────────────────────────────────────────────────────
section("SERVE DIRECTION TENDENCIES (1st Serve)")

cursor.execute(f"""
    SELECT serve_dir, COUNT(*) AS cnt,
           SUM(point_winner = %s) AS won
    FROM points
    WHERE match_id IN ({ids_placeholder}) AND server = %s
      AND serve_number = 1
      AND serve_dir IS NOT NULL AND serve_dir != 'unknown'
    GROUP BY serve_dir
    ORDER BY cnt DESC
""", [PLAYER] + match_ids + [PLAYER])
rows = cursor.fetchall()
total_dir = sum(r["cnt"] for r in rows)
print(f"\n  {'Direction':<12} {'Count':<8} {'% Used':<10} {'Pts Won'}")
print(f"  {'-'*45}")
for r in rows:
    print(f"  {r['serve_dir']:<12} {r['cnt']:<8} {pct(r['cnt'], total_dir):<10} {pct(r['won'] or 0, r['cnt'])}")

# ── 8. RETURN STATS ───────────────────────────────────────────────────────────
section("RETURN STATS (as returner)")

cursor.execute(f"""
    SELECT
        SUM(serve_number = 1) AS faced_1st,
        SUM(serve_number = 1 AND point_winner = %s) AS won_on_1st,
        SUM(serve_number = 2) AS faced_2nd,
        SUM(serve_number = 2 AND point_winner = %s) AS won_on_2nd
    FROM points
    WHERE match_id IN ({ids_placeholder}) AND returner = %s
""", [PLAYER, PLAYER] + match_ids + [PLAYER])
r = cursor.fetchone()
print(f"\n  Return Pts Won on 1st:  {pct(r['won_on_1st'] or 0, r['faced_1st'] or 1)}  ({r['won_on_1st']}/{r['faced_1st']})")
print(f"  Return Pts Won on 2nd:  {pct(r['won_on_2nd'] or 0, r['faced_2nd'] or 1)}  ({r['won_on_2nd']}/{r['faced_2nd']})")

# ── 9. RALLY LENGTH ───────────────────────────────────────────────────────────
section("RALLY LENGTH WIN RATE")

cursor.execute(f"""
    SELECT
        SUM(rally_length <= 2) AS total_short,
        SUM(rally_length <= 2 AND point_winner = %s) AS won_short,
        SUM(rally_length BETWEEN 3 AND 6) AS total_medium,
        SUM(rally_length BETWEEN 3 AND 6 AND point_winner = %s) AS won_medium,
        SUM(rally_length >= 7) AS total_long,
        SUM(rally_length >= 7 AND point_winner = %s) AS won_long
    FROM points
    WHERE match_id IN ({ids_placeholder})
""", [PLAYER, PLAYER, PLAYER] + match_ids)
r = cursor.fetchone()
print(f"\n  {'Range':<15} {'Played':<10} {'Won':<10} {'Win %'}")
print(f"  {'-'*45}")
print(f"  {'0-2 shots':<15} {r['total_short']:<10} {r['won_short'] or 0:<10} {pct(r['won_short'] or 0, r['total_short'] or 1)}")
print(f"  {'3-6 shots':<15} {r['total_medium']:<10} {r['won_medium'] or 0:<10} {pct(r['won_medium'] or 0, r['total_medium'] or 1)}")
print(f"  {'7+ shots':<15} {r['total_long']:<10} {r['won_long'] or 0:<10} {pct(r['won_long'] or 0, r['total_long'] or 1)}")

# ── 10. UNFORCED ERRORS BY SHOT TYPE ─────────────────────────────────────────
section("UNFORCED ERRORS BY SHOT TYPE")

cursor.execute(f"""
    SELECT last_shot, COUNT(*) AS cnt
    FROM points
    WHERE match_id IN ({ids_placeholder})
      AND error_maker = %s
      AND outcome = 'unforced_error'
      AND last_shot IS NOT NULL
    GROUP BY last_shot
    ORDER BY cnt DESC
""", match_ids + [PLAYER])
rows = cursor.fetchall()
total_ue = sum(r["cnt"] for r in rows)
print(f"\n  {'Shot':<25} {'Count':<8} {'%'}")
print(f"  {'-'*40}")
for r in rows:
    print(f"  {r['last_shot']:<25} {r['cnt']:<8} {pct(r['cnt'], total_ue)}")

# ── 11. UNFORCED ERRORS BY LOCATION ──────────────────────────────────────────
section("UNFORCED ERRORS BY LOCATION (net / wide / deep)")

cursor.execute(f"""
    SELECT error_loc, COUNT(*) AS cnt
    FROM points
    WHERE match_id IN ({ids_placeholder})
      AND error_maker = %s
      AND outcome = 'unforced_error'
      AND error_loc IS NOT NULL
    GROUP BY error_loc
    ORDER BY cnt DESC
""", match_ids + [PLAYER])
rows = cursor.fetchall()
total_loc = sum(r["cnt"] for r in rows)
print(f"\n  {'Location':<20} {'Count':<8} {'%'}")
print(f"  {'-'*35}")
for r in rows:
    print(f"  {r['error_loc']:<20} {r['cnt']:<8} {pct(r['cnt'], total_loc)}")

# ── 12. HOW GAMES END ────────────────────────────────────────────────────────
section("HOW GAMES END")

cursor.execute(f"""
    SELECT
        CASE WHEN gm_winner = 1 THEN player1
             WHEN gm_winner = 2 THEN player2
        END AS game_winner,
        CASE WHEN outcome IN ('winner','ace','unreturnable') THEN 'winner'
             WHEN outcome = 'unforced_error' THEN 'unforced_error'
             WHEN outcome = 'double_fault' THEN 'unforced_error'
             ELSE outcome
        END AS ending,
        COUNT(*) AS cnt
    FROM points
    JOIN matches ON points.match_id = matches.match_id
    WHERE points.match_id IN ({ids_placeholder}) AND gm_winner != 0
    GROUP BY game_winner, ending
    ORDER BY game_winner, cnt DESC
""", match_ids)
rows = cursor.fetchall()

won_games = {}
lost_games = {}
for r in rows:
    ending = r["ending"]
    cnt = r["cnt"]
    if r["game_winner"] == PLAYER:
        won_games[ending] = won_games.get(ending, 0) + cnt
    else:
        lost_games[ending] = lost_games.get(ending, 0) + cnt

print(f"\n  When {PLAYER} WINS the game:")
for ending, cnt in sorted(won_games.items(), key=lambda x: -x[1]):
    print(f"    {ending:<30}  {cnt}")

print(f"\n  When {PLAYER} LOSES the game:")
for ending, cnt in sorted(lost_games.items(), key=lambda x: -x[1]):
    print(f"    {ending:<30}  {cnt}")


# ── 13. RETURN DEPTH ─────────────────────────────────────────────────────────
section("RETURN DEPTH (as returner)")

cursor.execute(f"""
    SELECT return_depth, COUNT(*) AS total,
           SUM(point_winner = %s) AS won
    FROM points
    WHERE match_id IN ({ids_placeholder})
      AND returner = %s
      AND return_depth IS NOT NULL
    GROUP BY return_depth
    ORDER BY FIELD(return_depth, 'short', 'mid', 'deep')
""", [PLAYER] + match_ids + [PLAYER])
rows = cursor.fetchall()
total_ret = sum(r["total"] for r in rows)
print(f"\n  {'Depth':<12} {'Count':<8} {'% Used':<10} {'Pts Won'}")
print(f"  {'-'*45}")
depth_labels = {'short': 'short (7)', 'mid': 'mid (8)', 'deep': 'deep (9)'}
for r in rows:
    label = depth_labels.get(r["return_depth"], r["return_depth"])
    print(f"  {label:<12} {r['total']:<8} {pct(r['total'], total_ret):<10} {pct(r['won'] or 0, r['total'])}")

# ── DONE ──────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  End of report.")
print(f"{'='*60}\n")

cursor.close()
conn.close()
