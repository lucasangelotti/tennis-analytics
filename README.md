# 🎾 Tennis Analytics Pipeline

A point-by-point tennis match analysis system built with Python and MySQL. Parses raw match charting notation from [Jeff Sackmann's MatchChart](https://github.com/JeffSackmann/tennis_MatchChartingProject) format, loads structured data into a relational database, and generates detailed match and player reports.

---

## Overview

This project processes `.xlsm` match chart files, decodes each point's serve direction, rally sequence, shot types, and outcome, then stores everything in MySQL for SQL-based analysis. Built as part of a sports analytics portfolio focused on the ATP Challenger circuit.

**Matches charted:** 4  
**Tour level:** ATP Challenger  
**Surface:** Clay

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3 | Data parsing and pipeline scripting |
| openpyxl | Reading `.xlsm` MatchChart files |
| pandas | Data cleaning and CSV export |
| MySQL | Relational storage and SQL analysis |
| mysql-connector-python | Python ↔ MySQL interface |
| python-dotenv | Secure credential management |

---

## Project Structure

```
tennis-analytics/
├── data/                        # Raw .xlsm files and parsed CSVs (gitignored)
├── parse_match.py               # Decodes MatchChart notation → CSV
├── to_mysql.py                  # Loads CSV into MySQL
├── analyze_match.py             # Generates per-match report from MySQL
├── analyze_player.py            # Generates cross-match player report from MySQL
├── .env                         # DB credentials (gitignored)
├── .gitignore
└── README.md
```

---

## Database Schema

```sql
matches
├── match_id      INT  PK
├── player1       VARCHAR(50)
├── player2       VARCHAR(50)
├── tournament    VARCHAR(100)
├── match_date    DATE
├── round         VARCHAR(10)
├── surface       VARCHAR(20)
└── court         VARCHAR(50)

points
├── id             INT  PK
├── match_id       INT  FK → matches
├── point          INT
├── server         VARCHAR(50)
├── returner       VARCHAR(50)
├── serve_number   INT
├── serve_dir      VARCHAR(20)    -- wide / body / T
├── serve_dir_2nd  VARCHAR(20)
├── first_fault    VARCHAR(20)
├── rally_length   INT
├── last_shot      VARCHAR(30)    -- forehand / backhand / etc.
├── outcome        VARCHAR(20)    -- ace / winner / forced_error / etc.
├── is_ace         BOOLEAN
├── error_loc      VARCHAR(20)    -- net / wide / deep
├── point_winner   VARCHAR(50)
├── error_maker    VARCHAR(50)
├── set1           INT
├── set2           INT
├── gm1            INT
├── gm2            INT
├── point_score    VARCHAR(10)    -- 0-0 / 30-40 / AD-40 etc.
├── gm_winner      INT            -- 0 = not last point, 1 = p1 won game, 2 = p2
├── set_winner     INT            -- 0 = not last point, 1 = p1 won set, 2 = p2
├── return_depth   VARCHAR(10)    -- short / mid / deep
├── raw_1st        VARCHAR(100)   -- original 1st serve notation preserved
└── raw_2nd        VARCHAR(100)   -- original 2nd serve notation preserved
```

---

## How to Use

### 1. Parse a match
```bash
python3 parse_match.py "data/MatchChart 2026 Tournament Player1 Player2.xlsm"
```
Reads the `.xlsm` file, decodes every point, and saves `data/match_parsed.csv`.

### 2. Load into MySQL
```bash
python3 to_mysql.py "data/MatchChart 2026 Tournament Player1 Player2.xlsm"
```
Inserts match metadata and all parsed points into the database.

### 3. Analyze a match
```bash
# List all matches
python3 analyze_match.py

# Report for a specific match
python3 analyze_match.py <match_id>
```

### 4. Analyze a player across matches
```bash
# List all players
python3 analyze_player.py

# Full player report across all charted matches
python3 analyze_player.py "Player Name"
```

---

## Adding a New Match

1. Chart the match using Jeff Sackmann's MatchChart `.xlsm` template
2. Save the file into the `data/` folder
3. Run the two pipeline commands in order:

```bash
python3 parse_match.py "data/MatchChart 2026 Tournament Player1 Player2.xlsm"
python3 to_mysql.py "data/MatchChart 2026 Tournament Player1 Player2.xlsm"
```

4. List all matches in the database to find the new match ID:

```bash
python3 analyze_match.py
```

5. Run the report for the new match:

```bash
python3 analyze_match.py <match_id>
```

> **Note:** Never run `to_mysql.py` twice on the same file — it will insert a duplicate match record.

---

## What the Reports Cover

### Match Report (`analyze_match.py`)
- Points won totals
- 1st and 2nd serve % and points won
- Serve direction breakdown (wide / body / T)
- Return points won on 1st and 2nd serve
- Rally length distribution and win rate by length
- Point outcome breakdown (ace, winner, forced error, unforced error)
- Shot type on winners
- Unforced errors by shot type
- How games ended (winner / forced error / unforced error)

### Player Report (`analyze_player.py`)
- Aggregated stats across all charted matches
- Overall points won
- Serve stats and direction tendencies with win rate per direction
- Return stats on 1st and 2nd serve
- Rally length win rate (short / medium / long)
- Unforced errors by shot type and location (net / wide / deep)
- Return depth analysis (short / mid / deep) and win rate per depth
- How games end when player wins vs loses

---

## Sample Output

```
************************************************************
  MATCH REPORT  —  Match ID 18
  Juan Pablo Varillas  vs  Felipe Meligeni Alves
  Dove Men+Care Concepcion  |  2026-01-27  |  R32  |  Clay
************************************************************

============================================================
  POINTS WON
============================================================
  Juan Pablo Varillas              40 pts  (53.3%)
  Felipe Meligeni Alves            35 pts  (46.7%)

============================================================
  SERVE STATS
============================================================
  Juan Pablo Varillas
    1st Serve In:        45.7%  (16/35)
    1st Serve Pts Won:   87.5%  (14/16)
    2nd Serve Pts Won:   52.6%  (10/19)
    Aces:                2
    Double Faults:       2
    Unreturnables:       1

  Felipe Meligeni Alves
    1st Serve In:        45.0%  (18/40)
    1st Serve Pts Won:   66.7%  (12/18)
    2nd Serve Pts Won:   54.5%  (12/22)
    Aces:                0
    Double Faults:       1
    Unreturnables:       1

============================================================
  POINT OUTCOME BREAKDOWN
============================================================
  Outcome                Juan Pablo Varillas    Felipe Meligeni Alves
  -------------------------------------------------------------------
  forced_error           12                     9
  unforced_error         12                     21
  winner                 7                      14

============================================================
  HOW GAMES ENDED
============================================================
  Juan Pablo Varillas won the game with:
    unforced_error                  4
    winner                          2
    forced_error                    1

  Felipe Meligeni Alves won the game with:
    unforced_error                  2
    winner                          2
    forced_error                    1
```

---

## MatchChart Notation

Each point is encoded in Jeff Sackmann's notation system:

| Code | Meaning |
|---|---|
| `6*` | Ace down the T |
| `4d` | Wide serve, fault (deep) |
| `5f29b1*` | Body serve, forehand return crosscourt (depth 9), backhand winner down the line |
| `6f37b3n@` | T serve, forehand return to backhand (depth 7), backhand into net (unforced error) |

Direction: `4` = wide, `5` = body, `6` = T  
Shot types: `f` = forehand, `b` = backhand, `s` = backhand slice, `v` = forehand volley...  
Return depth: `7` = short, `8` = mid, `9` = deep  
Outcomes: `*` = winner, `#` = forced error, `@` = unforced error

---

## Data Source

Match charting files use Jeff Sackmann's [Tennis Match Charting Project](https://github.com/JeffSackmann/tennis_MatchChartingProject) format. All matches were manually charted by Lucas Angelotti from live/recorded ATP Challenger matches.

---

## Author

**Lucas Angelotti**  
CS Graduate · Tennis Coach · Aspiring Sports Data Analyst  
[github.com/lucasangelotti](https://github.com/lucasangelotti)
