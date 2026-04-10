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
print("Connected to MySQL.")

# ── 2. SELECT MATCH ───────────────────────────────────────────────────────────
# Usage: python3 analyze_match.py <match_id>
# If no argument given, lists available matches and exits.

def list_matches():
    cursor.execute("""
        SELECT m.match_id, m.player1, m.player2, m.tournament,
               m.match_date, m.round, m.surface,
               COUNT(p.id) AS total_points
        FROM matches m
        LEFT JOIN points p ON m.match_id = p.match_id
        GROUP BY m.match_id
        ORDER BY m.match_date DESC
    """)
    rows = cursor.fetchall()
    print("\n=== AVAILABLE MATCHES ===")
    print(f"{'ID':<5} {'Date':<12} {'Player 1':<25} {'Player 2':<25} {'Tournament':<35} {'Rd':<6} {'Pts'}")
    print("-" * 115)
    for r in rows:
        print(f"{r['match_id']:<5} {str(r['match_date']):<12} {str(r['player1']):<25} {str(r['player2']):<25} {str(r['tournament']):<35} {str(r['round']):<6} {r['total_points']}")
    print("\nRun: python3 analyze_match.py <match_id>")

if len(sys.argv) < 2:
    list_matches()
    cursor.close()
    conn.close()
    sys.exit(0)

MATCH_ID = int(sys.argv[1])

# ── 3. GET MATCH INFO ─────────────────────────────────────────────────────────
cursor.execute("SELECT * FROM matches WHERE match_id = %s", (MATCH_ID,))
match = cursor.fetchone()
if not match:
    print(f"No match found with ID {MATCH_ID}.")
    sys.exit(1)

p1 = match["player1"]
p2 = match["player2"]

def pct(a, b):
    return f"{100*a/b:.1f}%" if b else "N/A"

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ── 4. PRINT HEADER ───────────────────────────────────────────────────────────
print(f"\n{'*'*60}")
print(f"  MATCH REPORT  —  Match ID {MATCH_ID}")
print(f"  {p1}  vs  {p2}")
print(f"  {match['tournament']}  |  {match['match_date']}  |  {match['round']}  |  {match['surface']}")
print(f"{'*'*60}")

# ── 5. TOTAL POINTS ───────────────────────────────────────────────────────────
section("POINTS WON")
cursor.execute("""
    SELECT point_winner, COUNT(*) AS pts
    FROM points WHERE match_id = %s
    GROUP BY point_winner
""", (MATCH_ID,))
pts_won = {r["point_winner"]: r["pts"] for r in cursor.fetchall()}
total_pts = sum(pts_won.values())
for player in [p1, p2]:
    won = pts_won.get(player, 0)
    print(f"  {player:<30} {won:>4} pts  ({pct(won, total_pts)})")

# ── 6. SERVE STATS ────────────────────────────────────────────────────────────
section("SERVE STATS")

for player in [p1, p2]:
    cursor.execute("""
        SELECT
            COUNT(*) AS total_points,
            COUNT(*) AS first_serve_attempts,
            SUM(serve_number = 1) AS first_serves_in,
            SUM(serve_number = 2) AS second_serve_points,
            SUM(outcome = 'ace') AS aces,
            SUM(outcome = 'double_fault') AS double_faults,
            SUM(outcome = 'unreturnable') AS unreturnables
        FROM points
        WHERE match_id = %s AND server = %s
    """, (MATCH_ID, player))
    s = cursor.fetchone()

    # Points won on 1st and 2nd serve
    cursor.execute("""
        SELECT serve_number, COUNT(*) AS total, SUM(point_winner = %s) AS won
        FROM points
        WHERE match_id = %s AND server = %s AND serve_number IN (1,2)
        GROUP BY serve_number
    """, (player, MATCH_ID, player))
    serve_rows = {r["serve_number"]: r for r in cursor.fetchall()}
    s1 = serve_rows.get(1, {"total": 0, "won": 0})
    s2 = serve_rows.get(2, {"total": 0, "won": 0})

    print(f"\n  {player}")
    print(f"    1st Serve In:        {pct(s['first_serves_in'] or 0, s['first_serve_attempts'] or 1)}  ({s['first_serves_in']}/{s['first_serve_attempts']})")
    print(f"    1st Serve Pts Won:   {pct(s1['won'], s1['total'])}  ({s1['won']}/{s1['total']})")
    print(f"    2nd Serve Pts Won:   {pct(s2['won'], s2['total'])}  ({s2['won']}/{s2['total']})")
    print(f"    Aces:                {s['aces']}")
    print(f"    Double Faults:       {s['double_faults']}")
    print(f"    Unreturnables:       {s['unreturnables']}")

# ── 7. SERVE DIRECTION ────────────────────────────────────────────────────────
section("SERVE DIRECTION (1st Serve)")

for player in [p1, p2]:
    cursor.execute("""
        SELECT serve_dir, COUNT(*) AS cnt
        FROM points
        WHERE match_id = %s AND server = %s AND serve_number = 1
          AND serve_dir IS NOT NULL AND serve_dir != 'unknown'
        GROUP BY serve_dir
        ORDER BY cnt DESC
    """, (MATCH_ID, player))
    rows = cursor.fetchall()
    total = sum(r["cnt"] for r in rows)
    print(f"\n  {player}")
    for r in rows:
        print(f"    {r['serve_dir']:<10}  {r['cnt']:>3}  ({pct(r['cnt'], total)})")

# ── 8. RETURN STATS ───────────────────────────────────────────────────────────
section("RETURN STATS (Points Won on Opponent's Serve)")

for player in [p1, p2]:
    cursor.execute("""
        SELECT
            SUM(serve_number = 1) AS faced_1st,
            SUM(serve_number = 1 AND point_winner = %s) AS won_on_1st,
            SUM(serve_number = 2) AS faced_2nd,
            SUM(serve_number = 2 AND point_winner = %s) AS won_on_2nd
        FROM points
        WHERE match_id = %s AND returner = %s
    """, (player, player, MATCH_ID, player))
    r = cursor.fetchone()
    print(f"\n  {player} (as returner)")
    print(f"    Return Pts Won on 1st:  {pct(r['won_on_1st'] or 0, r['faced_1st'] or 1)}  ({r['won_on_1st']}/{r['faced_1st']})")
    print(f"    Return Pts Won on 2nd:  {pct(r['won_on_2nd'] or 0, r['faced_2nd'] or 1)}  ({r['won_on_2nd']}/{r['faced_2nd']})")

# ── 9. RALLY LENGTH ───────────────────────────────────────────────────────────
section("RALLY LENGTH")

cursor.execute("""
    SELECT
        AVG(rally_length) AS avg_rally,
        SUM(rally_length <= 2) AS short_0_2,
        SUM(rally_length BETWEEN 3 AND 6) AS medium_3_6,
        SUM(rally_length >= 7) AS long_7plus,
        COUNT(*) AS total
    FROM points
    WHERE match_id = %s
""", (MATCH_ID,))
r = cursor.fetchone()
print(f"\n  Avg Rally Length:  {r['avg_rally']:.1f} shots")
print(f"  0-2 shots:         {r['short_0_2']}  ({pct(r['short_0_2'], r['total'])})")
print(f"  3-6 shots:         {r['medium_3_6']}  ({pct(r['medium_3_6'], r['total'])})")
print(f"  7+ shots:          {r['long_7plus']}  ({pct(r['long_7plus'], r['total'])})")

# Winner of short vs long rallies per player
print()
for player in [p1, p2]:
    cursor.execute("""
        SELECT
            SUM(rally_length <= 2 AND point_winner = %s) AS won_short,
            SUM(rally_length <= 2) AS total_short,
            SUM(rally_length >= 7 AND point_winner = %s) AS won_long,
            SUM(rally_length >= 7) AS total_long
        FROM points WHERE match_id = %s
    """, (player, player, MATCH_ID))
    r = cursor.fetchone()
    print(f"  {player}")
    print(f"    Won short rallies (0-2):  {pct(r['won_short'] or 0, r['total_short'] or 1)}  ({r['won_short']}/{r['total_short']})")
    print(f"    Won long  rallies (7+):   {pct(r['won_long'] or 0, r['total_long'] or 1)}  ({r['won_long']}/{r['total_long']})")

# ── 10. OUTCOME BREAKDOWN ─────────────────────────────────────────────────────
section("POINT OUTCOME BREAKDOWN")

cursor.execute("""
    SELECT outcome,
           CASE WHEN outcome IN ('unforced_error', 'double_fault') THEN error_maker ELSE point_winner END AS point_winner,
           COUNT(*) AS cnt
    FROM points
    WHERE match_id = %s
    GROUP BY outcome, CASE WHEN outcome IN ('unforced_error', 'double_fault') THEN error_maker ELSE point_winner END
    ORDER BY outcome
""", (MATCH_ID,))
rows = cursor.fetchall()

outcomes = {}
for r in rows:
    o = r["outcome"]
    # Merge double faults into unforced errors
    if o == "double_fault":
        o = "unforced_error"
    if o in ("ace", "unreturnable"):
        o = "winner"
    if o not in outcomes:
        outcomes[o] = {}
    player = r["point_winner"]
    outcomes[o][player] = outcomes[o].get(player, 0) + r["cnt"]

print(f"\n  {'Outcome':<22} {p1[:20]:<22} {p2[:20]:<22}")
print(f"  {'-'*64}")
for outcome, winners in sorted(outcomes.items()):
    v1 = winners.get(p1, 0)
    v2 = winners.get(p2, 0)
    print(f"  {outcome:<22} {v1:<22} {v2:<22}")

# ── 11. LAST SHOT (WINNERS) ───────────────────────────────────────────────────
section("SHOT TYPE ON WINNERS")

cursor.execute("""
    SELECT point_winner, last_shot, COUNT(*) AS cnt
    FROM points
    WHERE match_id = %s AND outcome IN ('winner', 'ace', 'unreturnable')
      AND last_shot IS NOT NULL
    GROUP BY point_winner, last_shot
    ORDER BY point_winner, cnt DESC
""", (MATCH_ID,))
rows = cursor.fetchall()

current = None
for r in rows:
    if r["point_winner"] != current:
        current = r["point_winner"]
        print(f"\n  {current}")
    print(f"    {r['last_shot']:<25}  {r['cnt']}")

# ── 12. UNFORCED ERRORS BY SHOT TYPE ─────────────────────────────────────────
section("UNFORCED ERRORS BY SHOT TYPE")

cursor.execute("""
    SELECT error_maker AS player, last_shot, COUNT(*) AS cnt
    FROM points
    WHERE match_id = %s AND outcome = 'unforced_error'
      AND last_shot IS NOT NULL
    GROUP BY error_maker, last_shot
    ORDER BY error_maker, cnt DESC
""", (MATCH_ID,))
rows = cursor.fetchall()

current = None
for r in rows:
    if r["player"] != current:
        current = r["player"]
        print(f"\n  {current}")
    print(f"    {r['last_shot']:<25}  {r['cnt']}")

# ── 13. GAME ENDING BREAKDOWN ─────────────────────────────────────────────────
section("HOW GAMES ENDED")

cursor.execute("""
    SELECT
        CASE WHEN gm_winner = 1 THEN p1_name
             WHEN gm_winner = 2 THEN p2_name
        END AS game_winner,
        CASE WHEN outcome IN ('winner', 'ace', 'unreturnable') THEN 'winner'
             ELSE outcome
        END AS ending,
        COUNT(*) AS cnt
    FROM points
    JOIN (SELECT %s AS p1_name, %s AS p2_name) AS names
    WHERE match_id = %s AND gm_winner != 0
    GROUP BY game_winner, ending
    ORDER BY game_winner, cnt DESC
""", (p1, p2, MATCH_ID))
rows = cursor.fetchall()

current = None
for r in rows:
    if r["game_winner"] != current:
        current = r["game_winner"]
        print(f"\n  {current} won the game with:")
    print(f"    {r['ending']:<30}  {r['cnt']}")




# ── DONE ──────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  End of report.")
print(f"{'='*60}\n")

cursor.close()
conn.close()