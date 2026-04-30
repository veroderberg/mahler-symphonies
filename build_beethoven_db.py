#!/usr/bin/env python3
"""Build a SQLite database of all Beethoven symphonies."""

import sqlite3, json, csv, os

DB_PATH = os.path.join(os.path.dirname(__file__), "beethoven.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS symphonies (
    id              INTEGER PRIMARY KEY,
    number          INTEGER NOT NULL,
    key             TEXT NOT NULL,
    subtitle        TEXT,
    opus            TEXT NOT NULL,
    year_composed   TEXT NOT NULL,
    year_premiered  INTEGER,
    total_duration_min REAL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symphony_id     INTEGER NOT NULL REFERENCES symphonies(id),
    number          INTEGER NOT NULL,
    label           TEXT,
    tempo_marking   TEXT NOT NULL,
    duration_min    REAL NOT NULL,
    voices          TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS instrument_categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS instruments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    category_id INTEGER NOT NULL REFERENCES instrument_categories(id)
);

CREATE TABLE IF NOT EXISTS symphony_instruments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symphony_id   INTEGER NOT NULL REFERENCES symphonies(id),
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    count         INTEGER,
    notes         TEXT
);
"""

CATEGORIES = ["Woodwind","Brass","Percussion","Strings","Voice"]

INSTRUMENTS = [
    ("Piccolo",         "Woodwind"),
    ("Flute",           "Woodwind"),
    ("Oboe",            "Woodwind"),
    ("Clarinet",        "Woodwind"),
    ("Bassoon",         "Woodwind"),
    ("Contrabassoon",   "Woodwind"),
    ("Horn",            "Brass"),
    ("Trumpet",         "Brass"),
    ("Alto Trombone",   "Brass"),
    ("Tenor Trombone",  "Brass"),
    ("Bass Trombone",   "Brass"),
    ("Timpani",         "Percussion"),
    ("Bass Drum",       "Percussion"),
    ("Cymbals",         "Percussion"),
    ("Triangle",        "Percussion"),
    ("Violin I",        "Strings"),
    ("Violin II",       "Strings"),
    ("Viola",           "Strings"),
    ("Cello",           "Strings"),
    ("Double Bass",     "Strings"),
    ("Soprano",         "Voice"),
    ("Mezzo-soprano",   "Voice"),
    ("Tenor",           "Voice"),
    ("Baritone",        "Voice"),
    ("Mixed Chorus",    "Voice"),
]

# (id, number, key, subtitle, opus, years, premiere, total_min, notes)
SYMPHONIES = [
    (1,  1, "C major",      None,       "Op. 21",  "1795–1800", 1800, 28.0,
     "First performed at the Burgtheater, Vienna. Closest in spirit to Haydn and Mozart."),
    (2,  2, "D major",      None,       "Op. 36",  "1801–1802", 1803, 36.0,
     "Composed during the Heiligenstadt crisis. Despite personal anguish, the work is sunny and expansive."),
    (3,  3, "E-flat major", "Eroica",   "Op. 55",  "1803–1804", 1805, 53.0,
     "Originally dedicated to Napoleon; Beethoven erased the dedication on learning of the coronation. "
     "Transformative work — nearly doubled the symphony's scale. Three horns, groundbreaking at the time."),
    (4,  4, "B-flat major", None,       "Op. 60",  "1806",      1807, 37.0,
     "Composed rapidly; often overshadowed by its neighbours (3 and 5). Schumann called it 'a slender Greek maiden between two Norse giants'."),
    (5,  5, "C minor",      None,       "Op. 67",  "1804–1808", 1808, 32.0,
     "First use of piccolo, contrabassoon, and trombones in a symphony (finale only). "
     "The famous four-note motif pervades all four movements."),
    (6,  6, "F major",      "Pastoral", "Op. 68",  "1803–1808", 1808, 44.0,
     "Five movements; Beethoven's only programmatic symphony. "
     "Premiered on the same concert as the Fifth. Piccolo and two trombones enter in the storm (mvt 4)."),
    (7,  7, "A major",      None,       "Op. 92",  "1811–1812", 1813, 40.0,
     "Wagner called it 'the apotheosis of the dance'. The Allegretto (mvt 2) was encored at the premiere."),
    (8,  8, "F major",      None,       "Op. 93",  "1812",      1814, 27.0,
     "Compact and witty; Beethoven's shortest symphony. Beethoven reportedly preferred it to the Seventh."),
    (9,  9, "D minor",      "Choral",   "Op. 125", "1817–1824", 1824, 72.0,
     "Beethoven was completely deaf at the premiere. First major symphony to incorporate a full chorus and vocal soloists. "
     "Finale is a setting of Schiller's 'Ode to Joy'."),
]

# (symphony_id, number, label, tempo_marking, duration_min, voices, notes)
MOVEMENTS = [
    # --- Symphony 1 ---
    (1, 1, None, "Adagio molto — Allegro con brio",        10.0, None,
     "Slow introduction famously begins on the dominant seventh of F, not C."),
    (1, 2, None, "Andante cantabile con moto",              8.0, None,
     "Quasi-scherzo in character; passes theme through all sections."),
    (1, 3, None, "Menuetto: Allegro molto e vivace",        4.0, None,
     "In tempo this is already a scherzo in all but name."),
    (1, 4, None, "Finale: Adagio — Allegro molto e vivace", 6.0, None,
     "Humorous ascending scale in the introduction."),

    # --- Symphony 2 ---
    (2, 1, None, "Adagio molto — Allegro con brio",        13.0, None,
     "Longest first movement Beethoven had written to this point."),
    (2, 2, None, "Larghetto",                              12.0, None,
     "Song-form; one of Beethoven's most lyrical slow movements."),
    (2, 3, None, "Scherzo: Allegro",                        4.0, None,
     "First symphony to label a movement 'Scherzo' explicitly."),
    (2, 4, None, "Allegro molto",                           7.0, None,
     "Rondo with a famously abrupt ending."),

    # --- Symphony 3 ---
    (3, 1, None, "Allegro con brio",                       17.0, None,
     "Two hammer-blow E-flat chords open the movement. "
     "Development section twice as long as any previous symphony."),
    (3, 2, None, "Marcia funebre: Adagio assai",           17.0, None,
     "C minor funeral march; one of the most celebrated slow movements in the repertoire."),
    (3, 3, None, "Scherzo: Allegro vivace",                 6.0, None,
     "Three horns prominently featured; fast and playful."),
    (3, 4, None, "Finale: Allegro molto",                  13.0, None,
     "Theme-and-variations on a melody also used in the 'Prometheus' ballet."),

    # --- Symphony 4 ---
    (4, 1, None, "Adagio — Allegro vivace",                13.0, None,
     "Long, mysterious slow introduction in B-flat minor before the Allegro."),
    (4, 2, None, "Adagio",                                 10.0, None,
     "Lyrical; notable for the intricate accompaniment figure in the winds."),
    (4, 3, None, "Allegro vivace",                          6.0, None,
     "Trio section features a repeating bassoon figure."),
    (4, 4, None, "Allegro ma non troppo",                   8.0, None,
     "Perpetual-motion finale."),

    # --- Symphony 5 ---
    (5, 1, None, "Allegro con brio",                        7.0, None,
     "The 'fate motif' (short-short-short-long); entire movement derived from it."),
    (5, 2, None, "Andante con moto",                       10.0, None,
     "Double-variation form; two alternating themes."),
    (5, 3, None, "Allegro",                                 6.0, None,
     "C minor scherzo; horn theme; leads directly into the finale (attacca)."),
    (5, 4, None, "Allegro — Presto",                        9.0, None,
     "C major triumph; first use of piccolo, contrabassoon, and trombones in a symphony. "
     "Scherzo theme briefly recurs mid-movement."),

    # --- Symphony 6 ---
    (6, 1, "Awakening of cheerful feelings",
     "Allegro ma non troppo",                              12.0, None,
     "Beethoven: 'More the expression of feeling than painting'."),
    (6, 2, "Scene by the brook",
     "Andante molto mosso",                                13.0, None,
     "Flute = nightingale, oboe = quail, clarinets = cuckoo; birdsong cadenza at close."),
    (6, 3, "Merry gathering of country folk",
     "Allegro",                                             5.0, None,
     "Interrupted by the thunderstorm; attacca into mvt 4."),
    (6, 4, "Thunderstorm",
     "Allegro",                                             4.0, None,
     "Piccolo and trombones enter for the first and only time. Attacca into mvt 5."),
    (6, 5, "Shepherd's song",
     "Allegretto",                                         10.0, None,
     "F major calm; clarinet-led 'ranz des vaches' theme."),

    # --- Symphony 7 ---
    (7, 1, None, "Poco sostenuto — Vivace",                14.0, None,
     "Massive 60-bar introduction; Vivace built on a dotted-rhythm ostinato."),
    (7, 2, None, "Allegretto",                              9.0, None,
     "Funeral-march character; encored at the premiere. A minor → A major."),
    (7, 3, None, "Presto",                                  9.0, None,
     "F major; trio in D major repeated three times (unusual structure)."),
    (7, 4, None, "Allegro con brio",                        8.0, None,
     "Bacchanalian finale; driving rhythmic energy throughout."),

    # --- Symphony 8 ---
    (8, 1, None, "Allegro vivace e con brio",              10.0, None,
     "Compact sonata form; no slow introduction."),
    (8, 2, None, "Allegretto scherzando",                   4.0, None,
     "Gentle staccato winds; thought to mimic Mälzel's metronome."),
    (8, 3, None, "Tempo di Menuetto",                       5.0, None,
     "Old-fashioned minuet and trio — deliberate stylistic irony."),
    (8, 4, None, "Allegro vivace",                          8.0, None,
     "Long rondo-sonata; famous dissonant C-sharp that generates a prolonged digression."),

    # --- Symphony 9 ---
    (9, 1, None, "Allegro ma non troppo, un poco maestoso", 17.0, None,
     "D minor; opens from near-silence — bare fifths suggesting primordial emptiness."),
    (9, 2, None, "Molto vivace (Scherzo)",                  13.0, None,
     "Scherzo placed second; famous timpani solos; D minor."),
    (9, 3, None, "Adagio molto e cantabile",                16.0, None,
     "Two alternating themes; B-flat and D major. Serene and expansive."),
    (9, 4, None, "Presto — Allegro assai (Finale)",         26.0,
     "Soprano, Mezzo-soprano, Tenor, Baritone, Mixed Chorus",
     "Baritone recitative recalls themes of previous movements before 'Ode to Joy'. "
     "Schiller text set in multiple variations, fugue, and Turkish march episode."),
]

# (symphony_id, instrument_name, count, notes)
INSTRUMENTATION = [
    # ===== Symphony 1 =====
    (1, "Flute",          2, None),
    (1, "Oboe",           2, None),
    (1, "Clarinet",       2, "in C and A"),
    (1, "Bassoon",        2, None),
    (1, "Horn",           2, "in C and F"),
    (1, "Trumpet",        2, "in C"),
    (1, "Timpani",        1, "in C and G"),
    (1, "Violin I",       None, None),
    (1, "Violin II",      None, None),
    (1, "Viola",          None, None),
    (1, "Cello",          None, None),
    (1, "Double Bass",    None, None),

    # ===== Symphony 2 =====
    (2, "Flute",          2, None),
    (2, "Oboe",           2, None),
    (2, "Clarinet",       2, "in A and B-flat"),
    (2, "Bassoon",        2, None),
    (2, "Horn",           2, "in D and E"),
    (2, "Trumpet",        2, "in D"),
    (2, "Timpani",        1, "in D and A"),
    (2, "Violin I",       None, None),
    (2, "Violin II",      None, None),
    (2, "Viola",          None, None),
    (2, "Cello",          None, None),
    (2, "Double Bass",    None, None),

    # ===== Symphony 3 =====
    (3, "Flute",          2, None),
    (3, "Oboe",           2, None),
    (3, "Clarinet",       2, "in B-flat and C"),
    (3, "Bassoon",        2, None),
    (3, "Horn",           3, "in E-flat; 3 horns — unprecedented at the time"),
    (3, "Trumpet",        2, "in E-flat"),
    (3, "Timpani",        1, "in E-flat and B-flat"),
    (3, "Violin I",       None, None),
    (3, "Violin II",      None, None),
    (3, "Viola",          None, None),
    (3, "Cello",          None, None),
    (3, "Double Bass",    None, None),

    # ===== Symphony 4 =====
    (4, "Flute",          2, None),
    (4, "Oboe",           2, None),
    (4, "Clarinet",       2, "in B-flat and A"),
    (4, "Bassoon",        2, None),
    (4, "Horn",           2, "in B-flat and E-flat"),
    (4, "Trumpet",        2, "in B-flat"),
    (4, "Timpani",        1, "in B-flat and F"),
    (4, "Violin I",       None, None),
    (4, "Violin II",      None, None),
    (4, "Viola",          None, None),
    (4, "Cello",          None, None),
    (4, "Double Bass",    None, None),

    # ===== Symphony 5 =====
    (5, "Flute",          2, None),
    (5, "Piccolo",        1, "finale only (mvt 4)"),
    (5, "Oboe",           2, None),
    (5, "Clarinet",       2, "in C and B-flat"),
    (5, "Bassoon",        2, None),
    (5, "Contrabassoon",  1, "finale only (mvt 4)"),
    (5, "Horn",           2, "in E-flat and C"),
    (5, "Trumpet",        2, "in C"),
    (5, "Alto Trombone",  1, "finale only (mvt 4)"),
    (5, "Tenor Trombone", 1, "finale only (mvt 4)"),
    (5, "Bass Trombone",  1, "finale only (mvt 4)"),
    (5, "Timpani",        1, "in C and G"),
    (5, "Violin I",       None, None),
    (5, "Violin II",      None, None),
    (5, "Viola",          None, None),
    (5, "Cello",          None, None),
    (5, "Double Bass",    None, None),

    # ===== Symphony 6 =====
    (6, "Flute",          2, "flute = nightingale in mvt 2"),
    (6, "Piccolo",        1, "mvts 4–5 only (storm & finale)"),
    (6, "Oboe",           2, "oboe = quail in mvt 2"),
    (6, "Clarinet",       2, "clarinets = cuckoo in mvt 2"),
    (6, "Bassoon",        2, None),
    (6, "Horn",           2, "in F and B-flat"),
    (6, "Trumpet",        2, "in C and F"),
    (6, "Tenor Trombone", 1, "mvts 4–5 only"),
    (6, "Bass Trombone",  1, "mvts 4–5 only"),
    (6, "Timpani",        1, "in F and C"),
    (6, "Violin I",       None, None),
    (6, "Violin II",      None, None),
    (6, "Viola",          None, None),
    (6, "Cello",          None, None),
    (6, "Double Bass",    None, None),

    # ===== Symphony 7 =====
    (7, "Flute",          2, None),
    (7, "Oboe",           2, None),
    (7, "Clarinet",       2, "in A and C"),
    (7, "Bassoon",        2, None),
    (7, "Horn",           2, "in A and E"),
    (7, "Trumpet",        2, "in D and A"),
    (7, "Timpani",        1, "in A and E"),
    (7, "Violin I",       None, None),
    (7, "Violin II",      None, None),
    (7, "Viola",          None, None),
    (7, "Cello",          None, None),
    (7, "Double Bass",    None, None),

    # ===== Symphony 8 =====
    (8, "Flute",          2, None),
    (8, "Oboe",           2, None),
    (8, "Clarinet",       2, "in F and B-flat"),
    (8, "Bassoon",        2, None),
    (8, "Horn",           2, "in F and B-flat"),
    (8, "Trumpet",        2, "in F"),
    (8, "Timpani",        1, "in F and C"),
    (8, "Violin I",       None, None),
    (8, "Violin II",      None, None),
    (8, "Viola",          None, None),
    (8, "Cello",          None, None),
    (8, "Double Bass",    None, None),

    # ===== Symphony 9 =====
    (9, "Piccolo",        1, "finale only (mvt 4)"),
    (9, "Flute",          2, None),
    (9, "Oboe",           2, None),
    (9, "Clarinet",       2, "in A, B-flat, and D"),
    (9, "Bassoon",        2, None),
    (9, "Contrabassoon",  1, None),
    (9, "Horn",           4, "in D and B-flat"),
    (9, "Trumpet",        2, "in D and B-flat"),
    (9, "Alto Trombone",  1, None),
    (9, "Tenor Trombone", 1, None),
    (9, "Bass Trombone",  1, None),
    (9, "Timpani",        1, "2 players (mvt 2 — requires two timpanists)"),
    (9, "Bass Drum",      1, "finale"),
    (9, "Cymbals",        1, "finale"),
    (9, "Triangle",       1, "finale"),
    (9, "Violin I",       None, None),
    (9, "Violin II",      None, None),
    (9, "Viola",          None, None),
    (9, "Cello",          None, None),
    (9, "Double Bass",    None, None),
    (9, "Soprano",        1, "soloist (mvt 4)"),
    (9, "Mezzo-soprano",  1, "soloist (mvt 4)"),
    (9, "Tenor",          1, "soloist (mvt 4)"),
    (9, "Baritone",       1, "soloist (mvt 4)"),
    (9, "Mixed Chorus",   1, "SATB (mvt 4)"),
]

def build(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    for cat in CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO instrument_categories(name) VALUES (?)", (cat,))
    for name, cat in INSTRUMENTS:
        conn.execute(
            "INSERT OR IGNORE INTO instruments(name, category_id) "
            "SELECT ?, id FROM instrument_categories WHERE name = ?", (name, cat))

    conn.executemany(
        "INSERT OR REPLACE INTO symphonies"
        "(id,number,key,subtitle,opus,year_composed,year_premiered,total_duration_min,notes)"
        " VALUES (?,?,?,?,?,?,?,?,?)", SYMPHONIES)

    for sym_id, num, label, tempo, dur, voices, notes in MOVEMENTS:
        conn.execute(
            "INSERT INTO movements(symphony_id,number,label,tempo_marking,duration_min,voices,notes)"
            " VALUES (?,?,?,?,?,?,?)", (sym_id, num, label, tempo, dur, voices, notes))

    for sym_id, inst, count, notes in INSTRUMENTATION:
        conn.execute(
            "INSERT INTO symphony_instruments(symphony_id,instrument_id,count,notes) "
            "SELECT ?,id,?,? FROM instruments WHERE name=?", (sym_id, count, notes, inst))

    conn.commit(); conn.close()
    print(f"Database written to {db_path}")

def export_json(db_path, out_path):
    conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row
    data = []
    for row in conn.execute("SELECT * FROM symphonies ORDER BY number"):
        sym = dict(row); sid = sym["id"]
        sym["movements"] = [dict(m) for m in conn.execute(
            "SELECT number,label,tempo_marking,duration_min,voices,notes "
            "FROM movements WHERE symphony_id=? ORDER BY number", (sid,))]
        sym["instrumentation"] = [dict(i) for i in conn.execute(
            """SELECT ic.name cat, inst.name instrument, si.count, si.notes
               FROM symphony_instruments si
               JOIN instruments inst ON inst.id=si.instrument_id
               JOIN instrument_categories ic ON ic.id=inst.category_id
               WHERE si.symphony_id=? ORDER BY ic.id, inst.id""", (sid,))]
        data.append(sym)
    conn.close()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"JSON exported to {out_path}")

def export_csv_movements(db_path, out_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT s.number,s.opus,s.subtitle,s.key,
                  m.number,m.label,m.tempo_marking,m.duration_min,m.voices,m.notes
           FROM movements m JOIN symphonies s ON s.id=m.symphony_id
           ORDER BY s.number,m.number""").fetchall()
    conn.close()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symphony_no","opus","subtitle","key",
                    "movement_no","label","tempo_marking","duration_min","voices","notes"])
        w.writerows(rows)
    print(f"Movements CSV exported to {out_path}")

def export_csv_instrumentation(db_path, out_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT s.number,ic.name,inst.name,si.count,si.notes
           FROM symphony_instruments si
           JOIN symphonies s ON s.id=si.symphony_id
           JOIN instruments inst ON inst.id=si.instrument_id
           JOIN instrument_categories ic ON ic.id=inst.category_id
           ORDER BY s.number,ic.id,inst.id""").fetchall()
    conn.close()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symphony_no","category","instrument","count","notes"])
        w.writerows(rows)
    print(f"Instrumentation CSV exported to {out_path}")

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    db   = os.path.join(base, "beethoven.db")
    build(db)
    export_json(db, os.path.join(base, "beethoven.json"))
    export_csv_movements(db, os.path.join(base, "beethoven_movements.csv"))
    export_csv_instrumentation(db, os.path.join(base, "beethoven_instrumentation.csv"))

if __name__ == "__main__":
    main()
