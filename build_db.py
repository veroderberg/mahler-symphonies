#!/usr/bin/env python3
"""
Build a SQLite database of all Mahler symphonies,
their instrumentation, and movement running times.
"""

import sqlite3
import json
import csv
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "mahler.db")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS symphonies (
    id              INTEGER PRIMARY KEY,
    number          INTEGER NOT NULL,
    key             TEXT NOT NULL,
    subtitle        TEXT,
    year_composed   TEXT NOT NULL,   -- range when applicable
    year_premiered  INTEGER,
    total_duration_min REAL,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symphony_id     INTEGER NOT NULL REFERENCES symphonies(id),
    number          INTEGER NOT NULL,
    label           TEXT,            -- e.g. "Part I", "Nachtmusik I"
    tempo_marking   TEXT NOT NULL,
    duration_min    REAL NOT NULL,   -- typical/average performance time
    voices          TEXT,            -- soloists / chorus if applicable
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
    count         INTEGER,           -- players; NULL = standard section
    notes         TEXT               -- doublings, offstage, scordatura, etc.
);
"""

# ---------------------------------------------------------------------------
# Instrument categories
# ---------------------------------------------------------------------------
CATEGORIES = [
    "Woodwind", "Brass", "Percussion", "Keyboard", "Strings",
    "Plucked", "Voice"
]

# ---------------------------------------------------------------------------
# Master instrument list (name, category)
# ---------------------------------------------------------------------------
INSTRUMENTS = [
    # Woodwinds
    ("Piccolo",           "Woodwind"),
    ("Flute",             "Woodwind"),
    ("Oboe",              "Woodwind"),
    ("English Horn",      "Woodwind"),
    ("Eb Clarinet",       "Woodwind"),
    ("Clarinet",          "Woodwind"),
    ("Bass Clarinet",     "Woodwind"),
    ("Bassoon",           "Woodwind"),
    ("Contrabassoon",     "Woodwind"),
    # Brass
    ("Horn",              "Brass"),
    ("Trumpet",           "Brass"),
    ("Trombone",          "Brass"),
    ("Bass Trombone",     "Brass"),
    ("Tenor Tuba",        "Brass"),   # Mahler's Tenorhorn / Wagner tuba
    ("Tuba",              "Brass"),
    ("Contrabass Tuba",   "Brass"),
    ("Posthorn",          "Brass"),
    # Percussion
    ("Timpani",           "Percussion"),
    ("Bass Drum",         "Percussion"),
    ("Snare Drum",        "Percussion"),
    ("Cymbals",           "Percussion"),
    ("Triangle",          "Percussion"),
    ("Tam-tam",           "Percussion"),
    ("Glockenspiel",      "Percussion"),
    ("Xylophone",         "Percussion"),
    ("Celesta",           "Percussion"),
    ("Bells",             "Percussion"),   # tubular bells / orchestral bells
    ("Cowbells",          "Percussion"),
    ("Rute",              "Percussion"),   # birch switch
    ("Hammer",            "Percussion"),   # wooden hammer (Sym. 6)
    ("Deep Bells",        "Percussion"),   # low-pitched, often offstage
    # Keyboard
    ("Piano",             "Keyboard"),
    ("Organ",             "Keyboard"),
    ("Harmonium",         "Keyboard"),
    # Strings
    ("Violin I",          "Strings"),
    ("Violin II",         "Strings"),
    ("Viola",             "Strings"),
    ("Cello",             "Strings"),
    ("Double Bass",       "Strings"),
    ("Harp",              "Strings"),
    # Plucked
    ("Guitar",            "Plucked"),
    ("Mandolin",          "Plucked"),
    # Voices
    ("Soprano",           "Voice"),
    ("Mezzo-soprano",     "Voice"),
    ("Contralto",         "Voice"),
    ("Tenor",             "Voice"),
    ("Baritone",          "Voice"),
    ("Bass-baritone",     "Voice"),
    ("Mixed Chorus",      "Voice"),
    ("Women's Chorus",    "Voice"),
    ("Boys' Chorus",      "Voice"),
]

# ---------------------------------------------------------------------------
# Symphony data
# Each entry: (id, number, key, subtitle, years, premiere, total_min, notes)
# ---------------------------------------------------------------------------
SYMPHONIES = [
    (1,  1, "D major",          "Titan",
     "1887–1888, rev. 1893–96", 1889, 54.0,
     "Originally 5 movements; Mahler removed 'Blumine' (2nd mvt) in 1894."),

    (2,  2, "C minor",          "Resurrection",
     "1888–1894, rev. 1903",    1895, 87.0,
     "Soprano & contralto soloists; SATB chorus in finale."),

    (3,  3, "D minor",          None,
     "1893–1896, rev. 1906",    1902, 96.0,
     "Longest symphony in the standard repertoire (~96 min). "
     "Mezzo-soprano soloist; women's & boys' choruses."),

    (4,  4, "G major",          None,
     "1899–1900, rev. 1901–10", 1901, 56.0,
     "Comparatively modest orchestration. Soprano soloist in finale. "
     "Scordatura solo violin in mvt 2."),

    (5,  5, "C-sharp minor",    None,
     "1901–1902, rev. 1904–11", 1904, 69.0,
     "No voices. Structured in three parts (I–II, III, IV–V). "
     "Adagietto for strings and harp only."),

    (6,  6, "A minor",          "Tragic",
     "1903–1904, rev. 1906",    1906, 79.0,
     "No voices. Famous for three hammer blows in finale (later reduced to two). "
     "Debate over mvt 2/3 order (Scherzo vs Andante); entry follows Mahler's final revision."),

    (7,  7, "E minor",          "Song of the Night",
     "1904–1905, rev. 1909",    1908, 79.0,
     "No voices. Unique use of guitar and mandolin in Nachtmusik II. "
     "Two Tenorhorns (tenor tubas) in addition to standard brass."),

    (8,  8, "E-flat major",     "Symphony of a Thousand",
     "1906",                    1910, 83.0,
     "Eight soloists, two large mixed choruses, boys' chorus. "
     "Part I: Veni Creator Spiritus. Part II: Final scene from Goethe's Faust."),

    (9,  9, "D major",          None,
     "1908–1909",               1912, 78.0,
     "No voices. Last symphony Mahler completed. Posthumous premiere (Bruno Walter)."),

    (10, 10, "F-sharp major",   None,
     "1910 (unfinished)",       None, 80.0,
     "Only the Adagio was fully orchestrated by Mahler. "
     "Movement timings reflect the Deryck Cooke performing edition (1976). "
     "Other completions by Carpenter, Mazzetti, Samale–Cohrs–Voss, Wheeler."),
]

# ---------------------------------------------------------------------------
# Movements  (symphony_id, number, label, tempo_marking, duration_min, voices, notes)
# ---------------------------------------------------------------------------
MOVEMENTS = [
    # --- Symphony 1 ---
    (1, 1, None, "Langsam, schleppend (Wie ein Naturlaut)",         14.5, None,
     "Slow introduction evokes awakening nature."),
    (1, 2, None, "Kräftig bewegt, doch nicht zu schnell",            8.0, None,
     "Ländler-style scherzo."),
    (1, 3, None, "Feierlich und gemessen, ohne zu schleppen",        11.0, None,
     "Funeral march on 'Frère Jacques' canon in minor."),
    (1, 4, None, "Stürmisch bewegt",                                 20.5, None,
     "Turbulent finale; D major triumph at close."),

    # --- Symphony 2 ---
    (2, 1, None, "Allegro maestoso",                                 22.0, None,
     "Mahler asked for a 5-minute pause before mvt 2."),
    (2, 2, None, "Andante moderato",                                 14.0, None,
     "Ländler; nostalgic character."),
    (2, 3, None, "In ruhig fließender Bewegung",                     11.0, None,
     "Based on 'Des Antonius von Padua Fischpredigt' (Wunderhorn)."),
    (2, 4, "Urlicht", "Sehr feierlich, aber schlicht",                5.0, "Contralto",
     "Wunderhorn lied: 'O Röschen rot'."),
    (2, 5, None, "Im Tempo des Scherzos — Wild herausfahrend",       35.0, "Soprano, Contralto, Chorus",
     "Day of Judgment; offstage brass; final choral Resurrection hymn."),

    # --- Symphony 3 ---
    (3, 1, None, "Kräftig. Entschieden",                             33.0, None,
     "Longest single symphonic movement Mahler wrote. Summer marches in."),
    (3, 2, None, "Tempo di Menuetto",                                10.0, None,
     "What the flowers of the meadow tell me."),
    (3, 3, None, "Comodo. Scherzando. Ohne Hast",                    17.0, None,
     "What the animals of the forest tell me; posthorn solo offstage."),
    (3, 4, None, "Sehr langsam. Misterioso",                          9.0, "Mezzo-soprano",
     "What man tells me; setting of Nietzsche's 'Mitternacht'."),
    (3, 5, None, "Lustig im Tempo und keck im Ausdruck",              4.0, "Women's Chorus, Boys' Chorus",
     "What the angels tell me; bells, chorus."),
    (3, 6, None, "Langsam. Ruhevoll. Empfunden",                     23.0, None,
     "What love tells me; longest finale in Mahler."),

    # --- Symphony 4 ---
    (4, 1, None, "Bedächtig. Nicht eilen",                           17.0, None,
     "Sleigh bells open; classical in spirit."),
    (4, 2, None, "In gemächlicher Bewegung. Ohne Hast",              10.0, None,
     "Scherzo; scordatura violin ('Freund Hein')."),
    (4, 3, None, "Ruhevoll",                                         20.0, None,
     "Theme and variations; profound slow movement."),
    (4, 4, None, "Sehr behaglich",                                    9.0, "Soprano",
     "Das himmlische Leben (Wunderhorn); originally planned for Sym. 3."),

    # --- Symphony 5 ---
    (5, 1, "Part I", "Trauermarsch — In gemessenem Schritt. Streng. Wie ein Kondukt",
     12.0, None, "Funeral march; trumpet fanfare opens."),
    (5, 2, "Part I", "Stürmisch bewegt, mit größter Vehemenz",       15.0, None,
     "Raging, impassioned."),
    (5, 3, "Part II", "Scherzo — Kräftig, nicht zu schnell",         17.0, None,
     "Central pillar of the symphony; horn-dominated."),
    (5, 4, "Part III", "Adagietto — Sehr langsam",                   10.0, None,
     "Strings and harp only; famously used in Visconti's 'Death in Venice'."),
    (5, 5, "Part III", "Rondo-Finale — Allegro",                     15.0, None,
     "Contrapuntal brilliance; C major affirmation."),

    # --- Symphony 6 ---
    (6, 1, None, "Allegro energico, ma non troppo. Heftig, aber markig",
     23.0, None, "A minor march; Alma theme in E major."),
    (6, 2, None, "Scherzo — Wuchtig",                                12.0, None,
     "Placed second in Mahler's final revision (some conductors swap 2 & 3)."),
    (6, 3, None, "Andante moderato",                                 14.0, None,
     "Lyrical respite; E-flat major."),
    (6, 4, None, "Finale — Allegro moderato",                        30.0, None,
     "Tragic hammer blows (originally 3, Mahler reduced to 2). "
     "Longest finale Mahler wrote."),

    # --- Symphony 7 ---
    (7, 1, None, "Langsam (Adagio) — Allegro risoluto, ma non troppo",
     20.0, None, "Tenor-horn call opens; broad arch."),
    (7, 2, "Nachtmusik I", "Allegro moderato",                      17.0, None,
     "Night music; horn-dominated serenade."),
    (7, 3, None, "Scherzo — Schattenhaft",                           10.0, None,
     "Shadow-like; eerie, fleet."),
    (7, 4, "Nachtmusik II", "Andante amoroso",                      14.0, None,
     "Guitar and mandolin prominent; intimate serenade."),
    (7, 5, None, "Rondo-Finale — Allegro ordinario",                 18.0, None,
     "C major daybreak; sometimes criticised as enigmatically bright after dark movements."),

    # --- Symphony 8 ---
    (8, 1, "Part I", "Veni Creator Spiritus — Allegro impetuoso",   23.0,
     "3 Sopranos, 2 Mezzo-sopranos, Tenor, Baritone, Bass-baritone, 2 Mixed Choruses, Boys' Chorus",
     "Latin hymn by Hrabanus Maurus (9th c.). Dense double-fugue."),
    (8, 2, "Part II", "Poco adagio — Andante — Chorus mysticus",    60.0,
     "3 Sopranos, 2 Mezzo-sopranos, Tenor, Baritone, Bass-baritone, 2 Mixed Choruses, Boys' Chorus",
     "Goethe, Faust II, final scene. Through-composed; multiple tempos."),

    # --- Symphony 9 ---
    (9, 1, None, "Andante comodo",                                   27.0, None,
     "D major/minor; 'farewell' character; asymmetric phrasing."),
    (9, 2, None, "Im Tempo eines gemächlichen Ländlers. Etwas täppisch und sehr derb",
     16.0, None, "Three dance types juxtaposed (Ländler, waltz, minuet)."),
    (9, 3, None, "Rondo-Burleske — Allegro assai. Sehr trotzig",     11.0, None,
     "Savage counterpoint; 'To my brothers in Apollo' (Mahler's note)."),
    (9, 4, None, "Adagio — Sehr langsam und noch zurückhaltend",     24.0, None,
     "D-flat major valediction; dissolves into silence."),

    # --- Symphony 10 (Cooke edition) ---
    (10, 1, None, "Adagio — Andante",                                25.0, None,
     "Only movement fully orchestrated by Mahler. F-sharp major."),
    (10, 2, "Scherzo I", "Scherzo — Schnelle Viertel",               12.0, None,
     "Cooke completion. Demonic energy."),
    (10, 3, "Purgatorio", "Allegretto moderato",                      4.0, None,
     "Short intermezzo; B-flat minor."),
    (10, 4, "Scherzo II", "Allegro pesante",                         14.0, None,
     "Cooke completion. Drum stroke motive."),
    (10, 5, None, "Finale — Langsam, Adagio",                        25.0, None,
     "Cooke completion. Returns to Adagio material; F-sharp major resolution."),
]

# ---------------------------------------------------------------------------
# Instrumentation  (symphony_id, instrument_name, count, notes)
# ---------------------------------------------------------------------------
INSTRUMENTATION = [
    # ===== Symphony 1 =====
    (1, "Piccolo",          2, "3rd and 4th flutists double"),
    (1, "Flute",            4, None),
    (1, "Oboe",             4, "4th doubles English horn"),
    (1, "English Horn",     1, "doubled by 4th oboist"),
    (1, "Eb Clarinet",      1, None),
    (1, "Clarinet",         3, "in A and B-flat"),
    (1, "Bass Clarinet",    1, None),
    (1, "Bassoon",          3, None),
    (1, "Contrabassoon",    1, None),
    (1, "Horn",             7, "some offstage in mvt 4"),
    (1, "Trumpet",          4, "some offstage in mvt 4"),
    (1, "Trombone",         3, None),
    (1, "Tuba",             1, None),
    (1, "Timpani",          1, None),
    (1, "Bass Drum",        1, None),
    (1, "Cymbals",          1, None),
    (1, "Triangle",         1, None),
    (1, "Tam-tam",          1, None),
    (1, "Violin I",         None, None),
    (1, "Violin II",        None, None),
    (1, "Viola",            None, None),
    (1, "Cello",            None, None),
    (1, "Double Bass",      None, None),

    # ===== Symphony 2 =====
    (2, "Piccolo",          2, "3rd & 4th flutists double"),
    (2, "Flute",            4, None),
    (2, "Oboe",             4, "3rd & 4th double English horn"),
    (2, "English Horn",     1, None),
    (2, "Eb Clarinet",      1, None),
    (2, "Clarinet",         3, None),
    (2, "Bass Clarinet",    1, None),
    (2, "Bassoon",          3, None),
    (2, "Contrabassoon",    1, None),
    (2, "Horn",             10, "4 offstage (mvt 5)"),
    (2, "Trumpet",          10, "4 offstage (mvt 5)"),
    (2, "Trombone",         4, None),
    (2, "Tuba",             1, None),
    (2, "Timpani",          1, "2 players"),
    (2, "Bass Drum",        1, None),
    (2, "Snare Drum",       1, None),
    (2, "Cymbals",          1, None),
    (2, "Triangle",         1, None),
    (2, "Tam-tam",          1, None),
    (2, "Glockenspiel",     1, None),
    (2, "Bells",            1, "low tubular bells"),
    (2, "Organ",            1, None),
    (2, "Violin I",         None, None),
    (2, "Violin II",        None, None),
    (2, "Viola",            None, None),
    (2, "Cello",            None, None),
    (2, "Double Bass",      None, None),
    (2, "Harp",             2, None),
    (2, "Soprano",          1, "soloist (mvt 5)"),
    (2, "Contralto",        1, "soloist (mvts 4 & 5)"),
    (2, "Mixed Chorus",     1, "SATB (mvt 5)"),

    # ===== Symphony 3 =====
    (3, "Piccolo",          1, None),
    (3, "Flute",            4, None),
    (3, "Oboe",             4, None),
    (3, "English Horn",     1, None),
    (3, "Eb Clarinet",      1, None),
    (3, "Clarinet",         3, None),
    (3, "Bass Clarinet",    1, None),
    (3, "Bassoon",          4, None),
    (3, "Contrabassoon",    1, None),
    (3, "Horn",             8, "4 offstage (mvt 3)"),
    (3, "Posthorn",         1, "offstage (mvt 3); often played on flugelhorn"),
    (3, "Trumpet",          6, "4 offstage (mvt 1)"),
    (3, "Trombone",         4, None),
    (3, "Contrabass Tuba",  1, None),
    (3, "Timpani",          1, "2 players"),
    (3, "Bass Drum",        1, None),
    (3, "Snare Drum",       1, None),
    (3, "Cymbals",          1, None),
    (3, "Triangle",         1, None),
    (3, "Tam-tam",          1, None),
    (3, "Glockenspiel",     1, None),
    (3, "Bells",            1, None),
    (3, "Violin I",         None, None),
    (3, "Violin II",        None, None),
    (3, "Viola",            None, None),
    (3, "Cello",            None, None),
    (3, "Double Bass",      None, None),
    (3, "Harp",             2, None),
    (3, "Mezzo-soprano",    1, "soloist (mvt 4)"),
    (3, "Women's Chorus",   1, "(mvt 5)"),
    (3, "Boys' Chorus",     1, "(mvt 5); bells in hand"),

    # ===== Symphony 4 =====
    (4, "Piccolo",          1, None),
    (4, "Flute",            3, None),
    (4, "Oboe",             3, None),
    (4, "English Horn",     1, None),
    (4, "Eb Clarinet",      1, None),
    (4, "Clarinet",         3, None),
    (4, "Bass Clarinet",    1, None),
    (4, "Bassoon",          3, None),
    (4, "Contrabassoon",    1, None),
    (4, "Horn",             4, None),
    (4, "Trumpet",          3, None),
    (4, "Trombone",         3, None),
    (4, "Tuba",             1, None),
    (4, "Timpani",          1, None),
    (4, "Bass Drum",        1, None),
    (4, "Snare Drum",       1, None),
    (4, "Cymbals",          1, None),
    (4, "Triangle",         1, None),
    (4, "Tam-tam",          1, None),
    (4, "Glockenspiel",     1, None),
    (4, "Bells",            1, "sleigh bells (mvt 1)"),
    (4, "Violin I",         None, "scordatura soloist in mvt 2"),
    (4, "Violin II",        None, None),
    (4, "Viola",            None, None),
    (4, "Cello",            None, None),
    (4, "Double Bass",      None, None),
    (4, "Harp",             1, None),
    (4, "Soprano",          1, "soloist (mvt 4)"),

    # ===== Symphony 5 =====
    (5, "Piccolo",          1, None),
    (5, "Flute",            3, None),
    (5, "Oboe",             3, None),
    (5, "English Horn",     1, None),
    (5, "Eb Clarinet",      1, None),
    (5, "Clarinet",         3, None),
    (5, "Bass Clarinet",    1, None),
    (5, "Bassoon",          3, None),
    (5, "Contrabassoon",    1, None),
    (5, "Horn",             6, None),
    (5, "Trumpet",          4, None),
    (5, "Trombone",         3, None),
    (5, "Bass Trombone",    1, None),
    (5, "Tuba",             1, None),
    (5, "Timpani",          1, None),
    (5, "Bass Drum",        1, None),
    (5, "Snare Drum",       1, None),
    (5, "Cymbals",          1, None),
    (5, "Triangle",         1, None),
    (5, "Tam-tam",          1, None),
    (5, "Glockenspiel",     1, None),
    (5, "Rute",             1, "mvt 3 (birch switch on bass drum)"),
    (5, "Violin I",         None, None),
    (5, "Violin II",        None, None),
    (5, "Viola",            None, None),
    (5, "Cello",            None, None),
    (5, "Double Bass",      None, None),
    (5, "Harp",             1, "Adagietto: harp and strings only"),

    # ===== Symphony 6 =====
    (6, "Piccolo",          1, None),
    (6, "Flute",            4, None),
    (6, "Oboe",             4, None),
    (6, "English Horn",     1, None),
    (6, "Eb Clarinet",      1, None),
    (6, "Clarinet",         3, None),
    (6, "Bass Clarinet",    1, None),
    (6, "Bassoon",          4, None),
    (6, "Contrabassoon",    1, None),
    (6, "Horn",             8, None),
    (6, "Trumpet",          6, None),
    (6, "Trombone",         3, None),
    (6, "Bass Trombone",    1, None),
    (6, "Contrabass Tuba",  1, None),
    (6, "Timpani",          1, "2 players"),
    (6, "Bass Drum",        1, None),
    (6, "Snare Drum",       1, None),
    (6, "Cymbals",          1, None),
    (6, "Triangle",         1, None),
    (6, "Tam-tam",          2, "high and low"),
    (6, "Glockenspiel",     1, None),
    (6, "Xylophone",        1, None),
    (6, "Celesta",          1, None),
    (6, "Cowbells",         1, "various pitches; some offstage"),
    (6, "Deep Bells",       1, "low-pitched, offstage"),
    (6, "Hammer",           1, "large wooden hammer (Finale); Mahler reduced from 3 to 2 blows"),
    (6, "Violin I",         None, None),
    (6, "Violin II",        None, None),
    (6, "Viola",            None, None),
    (6, "Cello",            None, None),
    (6, "Double Bass",      None, None),
    (6, "Harp",             2, None),

    # ===== Symphony 7 =====
    (7, "Piccolo",          1, None),
    (7, "Flute",            3, None),
    (7, "Oboe",             3, None),
    (7, "English Horn",     1, None),
    (7, "Eb Clarinet",      1, None),
    (7, "Clarinet",         3, None),
    (7, "Bass Clarinet",    1, None),
    (7, "Bassoon",          3, None),
    (7, "Contrabassoon",    1, None),
    (7, "Horn",             4, None),
    (7, "Tenor Tuba",       2, "Tenorhorns / Wagner tubas (mvts 1 & 2)"),
    (7, "Trumpet",          3, None),
    (7, "Trombone",         3, None),
    (7, "Bass Trombone",    1, None),
    (7, "Contrabass Tuba",  1, None),
    (7, "Timpani",          1, None),
    (7, "Bass Drum",        1, None),
    (7, "Snare Drum",       1, None),
    (7, "Cymbals",          1, None),
    (7, "Triangle",         1, None),
    (7, "Tam-tam",          1, None),
    (7, "Glockenspiel",     1, None),
    (7, "Cowbells",         1, "various pitches"),
    (7, "Deep Bells",       1, None),
    (7, "Violin I",         None, None),
    (7, "Violin II",        None, None),
    (7, "Viola",            None, None),
    (7, "Cello",            None, None),
    (7, "Double Bass",      None, None),
    (7, "Harp",             2, None),
    (7, "Guitar",           1, "Nachtmusik II"),
    (7, "Mandolin",         1, "Nachtmusik II"),

    # ===== Symphony 8 =====
    (8, "Piccolo",          1, None),
    (8, "Flute",            4, None),
    (8, "Oboe",             4, None),
    (8, "English Horn",     1, None),
    (8, "Eb Clarinet",      1, None),
    (8, "Clarinet",         3, None),
    (8, "Bass Clarinet",    1, None),
    (8, "Bassoon",          4, None),
    (8, "Contrabassoon",    1, None),
    (8, "Horn",             8, None),
    (8, "Trumpet",          8, "4 offstage"),
    (8, "Trombone",         7, "4 offstage"),
    (8, "Contrabass Tuba",  1, None),
    (8, "Timpani",          1, "2 players"),
    (8, "Bass Drum",        1, None),
    (8, "Snare Drum",       1, None),
    (8, "Cymbals",          1, None),
    (8, "Triangle",         1, None),
    (8, "Tam-tam",          1, None),
    (8, "Glockenspiel",     1, None),
    (8, "Celesta",          1, None),
    (8, "Bells",            1, None),
    (8, "Piano",            1, None),
    (8, "Organ",            1, None),
    (8, "Harmonium",        1, None),
    (8, "Violin I",         None, None),
    (8, "Violin II",        None, None),
    (8, "Viola",            None, None),
    (8, "Cello",            None, None),
    (8, "Double Bass",      None, None),
    (8, "Harp",             4, None),
    (8, "Soprano",          3, "soloists"),
    (8, "Mezzo-soprano",    2, "soloists"),
    (8, "Tenor",            1, "soloist"),
    (8, "Baritone",         1, "soloist"),
    (8, "Bass-baritone",    1, "soloist"),
    (8, "Mixed Chorus",     2, "two large SATB choruses"),
    (8, "Boys' Chorus",     1, None),

    # ===== Symphony 9 =====
    (9, "Piccolo",          1, None),
    (9, "Flute",            4, None),
    (9, "Oboe",             4, None),
    (9, "English Horn",     1, None),
    (9, "Eb Clarinet",      1, None),
    (9, "Clarinet",         3, None),
    (9, "Bass Clarinet",    1, None),
    (9, "Bassoon",          4, None),
    (9, "Contrabassoon",    1, None),
    (9, "Horn",             4, None),
    (9, "Trumpet",          3, None),
    (9, "Trombone",         3, None),
    (9, "Bass Trombone",    1, None),
    (9, "Contrabass Tuba",  1, None),
    (9, "Timpani",          1, None),
    (9, "Bass Drum",        1, None),
    (9, "Snare Drum",       1, None),
    (9, "Cymbals",          1, None),
    (9, "Triangle",         1, None),
    (9, "Tam-tam",          1, None),
    (9, "Glockenspiel",     1, None),
    (9, "Cowbells",         1, "mvt 2"),
    (9, "Celesta",          1, None),
    (9, "Violin I",         None, None),
    (9, "Violin II",        None, None),
    (9, "Viola",            None, None),
    (9, "Cello",            None, None),
    (9, "Double Bass",      None, None),
    (9, "Harp",             2, None),

    # ===== Symphony 10 =====
    (10, "Piccolo",         1, None),
    (10, "Flute",           4, None),
    (10, "Oboe",            3, None),
    (10, "English Horn",    1, None),
    (10, "Eb Clarinet",     1, None),
    (10, "Clarinet",        3, None),
    (10, "Bass Clarinet",   1, None),
    (10, "Bassoon",         3, None),
    (10, "Contrabassoon",   1, None),
    (10, "Horn",            4, None),
    (10, "Trumpet",         3, None),
    (10, "Trombone",        3, None),
    (10, "Bass Trombone",   1, None),
    (10, "Contrabass Tuba", 1, None),
    (10, "Timpani",         1, None),
    (10, "Bass Drum",       1, "single stroke in Finale (mvt 5)"),
    (10, "Snare Drum",      1, None),
    (10, "Cymbals",         1, None),
    (10, "Tam-tam",         1, None),
    (10, "Cowbells",        1, None),
    (10, "Violin I",        None, None),
    (10, "Violin II",       None, None),
    (10, "Viola",           None, None),
    (10, "Cello",           None, None),
    (10, "Double Bass",     None, None),
    (10, "Harp",            2, None),
]

# ---------------------------------------------------------------------------
# Build the database
# ---------------------------------------------------------------------------
def build(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    # Categories
    for cat in CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO instrument_categories(name) VALUES (?)", (cat,))

    # Instruments
    for name, cat in INSTRUMENTS:
        conn.execute(
            "INSERT OR IGNORE INTO instruments(name, category_id) "
            "SELECT ?, id FROM instrument_categories WHERE name = ?",
            (name, cat)
        )

    # Symphonies
    conn.executemany(
        "INSERT OR REPLACE INTO symphonies"
        "(id, number, key, subtitle, year_composed, year_premiered, total_duration_min, notes)"
        " VALUES (?,?,?,?,?,?,?,?)",
        SYMPHONIES
    )

    # Movements
    for sym_id, num, label, tempo, dur, voices, notes in MOVEMENTS:
        conn.execute(
            "INSERT INTO movements"
            "(symphony_id, number, label, tempo_marking, duration_min, voices, notes)"
            " VALUES (?,?,?,?,?,?,?)",
            (sym_id, num, label, tempo, dur, voices, notes)
        )

    # Instrumentation
    for sym_id, inst_name, count, notes in INSTRUMENTATION:
        conn.execute(
            "INSERT INTO symphony_instruments(symphony_id, instrument_id, count, notes) "
            "SELECT ?, id, ?, ? FROM instruments WHERE name = ?",
            (sym_id, count, notes, inst_name)
        )

    conn.commit()
    conn.close()
    print(f"Database written to {db_path}")


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------
def export_json(db_path: str, out_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    data = []
    for row in conn.execute("SELECT * FROM symphonies ORDER BY number"):
        sym = dict(row)
        sym_id = sym["id"]

        sym["movements"] = [
            dict(m) for m in conn.execute(
                "SELECT number, label, tempo_marking, duration_min, voices, notes "
                "FROM movements WHERE symphony_id=? ORDER BY number", (sym_id,)
            )
        ]

        sym["instrumentation"] = [
            dict(i) for i in conn.execute(
                """SELECT ic.name AS category, inst.name AS instrument,
                          si.count, si.notes
                   FROM symphony_instruments si
                   JOIN instruments inst ON inst.id = si.instrument_id
                   JOIN instrument_categories ic ON ic.id = inst.category_id
                   WHERE si.symphony_id = ?
                   ORDER BY ic.id, inst.id""",
                (sym_id,)
            )
        ]
        data.append(sym)

    conn.close()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"JSON exported to {out_path}")


def export_csv_movements(db_path: str, out_path: str) -> None:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT s.number AS symphony, s.subtitle, s.key,
                  m.number AS movement, m.label, m.tempo_marking,
                  m.duration_min, m.voices, m.notes
           FROM movements m
           JOIN symphonies s ON s.id = m.symphony_id
           ORDER BY s.number, m.number"""
    ).fetchall()
    conn.close()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symphony_no","subtitle","key",
                         "movement_no","label","tempo_marking",
                         "duration_min","voices","notes"])
        writer.writerows(rows)
    print(f"Movements CSV exported to {out_path}")


def export_csv_instrumentation(db_path: str, out_path: str) -> None:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT s.number AS symphony, ic.name AS category,
                  inst.name AS instrument, si.count, si.notes
           FROM symphony_instruments si
           JOIN symphonies s     ON s.id   = si.symphony_id
           JOIN instruments inst ON inst.id = si.instrument_id
           JOIN instrument_categories ic ON ic.id = inst.category_id
           ORDER BY s.number, ic.id, inst.id"""
    ).fetchall()
    conn.close()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symphony_no","category","instrument","count","notes"])
        writer.writerows(rows)
    print(f"Instrumentation CSV exported to {out_path}")


# ---------------------------------------------------------------------------
def main():
    base = os.path.dirname(os.path.abspath(__file__))
    db   = os.path.join(base, "mahler.db")
    build(db)
    export_json(db, os.path.join(base, "mahler.json"))
    export_csv_movements(db, os.path.join(base, "mahler_movements.csv"))
    export_csv_instrumentation(db, os.path.join(base, "mahler_instrumentation.csv"))


if __name__ == "__main__":
    main()
