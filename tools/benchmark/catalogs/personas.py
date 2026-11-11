"""
Catalog of Personas for GuardSLM Benchmark V2.
Captures all 54 seeded accounts across Administrator, Faculty, TA, and Student tiers.
"""

PERSONAS = {
    # Institutional Administrators (2)
    "admin01": {
        "username": "admin01",
        "display_name": "Alex Admin",
        "global_role": "admin",
        "department": "SYS",
        "course_memberships": {},  # Universal admin privileges
    },
    "admin02": {
        "username": "admin02",
        "display_name": "Sarah Connor",
        "global_role": "admin",
        "department": "SYS",
        "course_memberships": {},
    },
    
    # Professors (4)
    "prof01": {
        "username": "prof01",
        "display_name": "Dr Mira Shah",
        "global_role": "professor",
        "department": "CS",
        "course_memberships": {
            "CSE301": {"role": "professor", "section": "SEC01"},
            "CSE303": {"role": "professor", "section": "SEC01"},
        },
    },
    "prof02": {
        "username": "prof02",
        "display_name": "Dr Kabir Rao",
        "global_role": "professor",
        "department": "EE",
        "course_memberships": {
            "CSE302": {"role": "professor", "section": "SEC01"},
            "HCI401": {"role": "professor", "section": "SEC01"},
        },
    },
    "prof03": {
        "username": "prof03",
        "display_name": "Dr Elena Vance",
        "global_role": "professor",
        "department": "HCI",
        "course_memberships": {
            "HCI401": {"role": "professor", "section": "SEC02"},
        },
    },
    "prof04": {
        "username": "prof04",
        "display_name": "Dr Alan Turing",
        "global_role": "professor",
        "department": "DS",
        "course_memberships": {},
    },
    
    # Teaching Assistants (8)
    "ta01": {
        "username": "ta01",
        "display_name": "Sam Lee",
        "global_role": "ta",
        "department": "CS",
        "course_memberships": {
            "CSE301": {"role": "ta", "section": "SEC02"},
            "CSE302": {"role": "student", "section": "SEC01"},  # Dual role!
        },
    },
    "ta02": {
        "username": "ta02",
        "display_name": "Noor Khan",
        "global_role": "ta",
        "department": "EE",
        "course_memberships": {
            "CSE302": {"role": "ta", "section": "SEC02"},
            "HCI401": {"role": "ta", "section": "SEC02"},
        },
    },
    "ta03": {
        "username": "ta03",
        "display_name": "Dev Patel",
        "global_role": "ta",
        "department": "CS",
        "course_memberships": {
            "CSE303": {"role": "ta", "section": "SEC02"},
            "HCI401": {"role": "student", "section": "SEC01"},  # Dual role!
        },
    },
    "ta04": {
        "username": "ta04",
        "display_name": "Elena Rostova",
        "global_role": "ta",
        "department": "CS",
        "course_memberships": {
            "CSE303": {"role": "ta", "section": "SEC01"},
            "CSE301": {"role": "student", "section": "SEC02"},  # Dual role!
        },
    },
    "ta05": {"username": "ta05", "display_name": "Liam O'Connor", "global_role": "ta", "department": "CS", "course_memberships": {}},
    "ta06": {"username": "ta06", "display_name": "Mei Lin", "global_role": "ta", "department": "EE", "course_memberships": {}},
    "ta07": {"username": "ta07", "display_name": "Tariq Mansour", "global_role": "ta", "department": "HCI", "course_memberships": {}},
    "ta08": {"username": "ta08", "display_name": "Zoe Washington", "global_role": "ta", "department": "DS", "course_memberships": {}},
    
    # Core Enrolled Students (student01 to student16)
    "student01": {
        "username": "student01",
        "display_name": "Asha Mehta",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC01"},
            "CSE302": {"role": "student", "section": "SEC01"},
            "CSE303": {"role": "student", "section": "SEC01"},
            "HCI401": {"role": "student", "section": "SEC01", "group": "Design Team Alpha"},
        },
    },
    "student02": {
        "username": "student02",
        "display_name": "Rohan Das",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC01"},
            "CSE302": {"role": "student", "section": "SEC01"},
            "CSE303": {"role": "student", "section": "SEC01"},
        },
    },
    "student03": {
        "username": "student03",
        "display_name": "Isha Roy",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC01"},
            "HCI401": {"role": "student", "section": "SEC01", "group": "Design Team Alpha"},
        },
    },
    "student04": {
        "username": "student04",
        "display_name": "Vikram Sen",
        "global_role": "student",
        "course_memberships": {
            "CSE302": {"role": "student", "section": "SEC01"},
            "CSE303": {"role": "student", "section": "SEC01"},
            "HCI401": {"role": "student", "section": "SEC01"},
        },
    },
    "student05": {
        "username": "student05",
        "display_name": "Tara Bose",
        "global_role": "student",
        "course_memberships": {
            "CSE303": {"role": "student", "section": "SEC01"},
            "HCI401": {"role": "student", "section": "SEC01", "group": "Design Team Beta"},
        },
    },
    "student06": {
        "username": "student06",
        "display_name": "Arjun Nair",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC01"},
            "CSE302": {"role": "student", "section": "SEC01"},
            "CSE303": {"role": "student", "section": "SEC01"},
            "HCI401": {"role": "student", "section": "SEC01", "group": "Design Team Beta"},
        },
    },
    "student07": {
        "username": "student07",
        "display_name": "Priya Sharma",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC02"},
            "HCI401": {"role": "student", "section": "SEC02", "group": "Design Team Gamma"},
        },
    },
    "student08": {
        "username": "student08",
        "display_name": "Marcus Chen",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC02"},
            "CSE302": {"role": "student", "section": "SEC02"},
            "CSE303": {"role": "student", "section": "SEC02"},
            "HCI401": {"role": "student", "section": "SEC02"},
        },
    },
    "student09": {
        "username": "student09",
        "display_name": "Fatima Zahra",
        "global_role": "student",
        "course_memberships": {
            "CSE302": {"role": "student", "section": "SEC02"},
            "HCI401": {"role": "student", "section": "SEC02", "group": "Design Team Delta"},
        },
    },
    "student10": {
        "username": "student10",
        "display_name": "Lucas Silva",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC02"},
            "CSE303": {"role": "student", "section": "SEC02"},
        },
    },
    "student11": {
        "username": "student11",
        "display_name": "Chloe Bennett",
        "global_role": "student",
        "course_memberships": {
            "CSE302": {"role": "student", "section": "SEC02"},
            "CSE303": {"role": "student", "section": "SEC02"},
            "HCI401": {"role": "student", "section": "SEC02", "group": "Design Team Gamma"},
        },
    },
    "student12": {
        "username": "student12",
        "display_name": "David Kim",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC02"},
            "CSE302": {"role": "student", "section": "SEC02"},
        },
    },
    "student13": {
        "username": "student13",
        "display_name": "Ananya Iyer",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC02"},
            "CSE302": {"role": "student", "section": "SEC02"},
            "CSE303": {"role": "student", "section": "SEC02"},
            "HCI401": {"role": "student", "section": "SEC02", "group": "Design Team Delta"},
        },
    },
    "student14": {
        "username": "student14",
        "display_name": "Omar Farooq",
        "global_role": "student",
        "course_memberships": {
            "CSE303": {"role": "student", "section": "SEC02"},
        },
    },
    "student15": {
        "username": "student15",
        "display_name": "Sofia Morales",
        "global_role": "student",
        "course_memberships": {
            "CSE301": {"role": "student", "section": "SEC02"},
            "HCI401": {"role": "student", "section": "SEC02", "group": "Design Team Gamma"},
        },
    },
    "student16": {
        "username": "student16",
        "display_name": "Kevin Zhao",
        "global_role": "student",
        "course_memberships": {
            "CSE302": {"role": "student", "section": "SEC02"},
            "CSE303": {"role": "student", "section": "SEC02"},
        },
    },
}

# Add student17 through student40 programmatically to dictionary
names = [
    ("student17", "Maya Lin", {"CSE301": {"role": "student", "section": "SEC01"}}),
    ("student18", "Jamal Washington", {"CSE301": {"role": "student", "section": "SEC01"}}),
    ("student19", "Hannah Schmidt", {"CSE301": {"role": "student", "section": "SEC02"}}),
    ("student20", "Carlos Hernandez", {"CSE301": {"role": "student", "section": "SEC02"}}),
    ("student21", "Yuki Tanaka", {"CSE302": {"role": "student", "section": "SEC01"}}),
    ("student22", "Amara Okafor", {"CSE302": {"role": "student", "section": "SEC01"}}),
    ("student23", "Benjamin Cohen", {"CSE302": {"role": "student", "section": "SEC02"}}),
    ("student24", "Leila Al-Mansoor", {"CSE302": {"role": "student", "section": "SEC02"}}),
    ("student25", "Alex Rivera", {"CSE303": {"role": "student", "section": "SEC01"}}),
    ("student26", "Grace Hopper", {"CSE303": {"role": "student", "section": "SEC01"}}),
    ("student27", "Dmitri Ivanov", {"CSE303": {"role": "student", "section": "SEC02"}}),
    ("student28", "Fatima Al-Hassan", {"CSE303": {"role": "student", "section": "SEC02"}}),
    ("student29", "Lars Andersson", {}),  # Unenrolled student
    ("student30", "Zack Suspended", {"CSE301": {"role": "student", "section": "SEC01", "status": "suspended"}}),
    ("student31", "Rachel Revoked", {"CSE302": {"role": "student", "section": "SEC02", "status": "revoked"}}),
    ("student32", "Kavita CrossSection", {"CSE301": {"role": "student", "section": "SEC01"}, "CSE302": {"role": "student", "section": "SEC02"}}),
    ("student33", "Arthur Auditor", {}),
    ("student34", "Oliver Twist", {}),
    ("student35", "Zoe Saldana", {"HCI401": {"role": "student", "section": "SEC01"}}),
    ("student36", "Brian Cox", {"HCI401": {"role": "student", "section": "SEC01"}}),
    ("student37", "Nadia Comaneci", {"HCI401": {"role": "student", "section": "SEC02"}}),
    ("student38", "Leo Tolstoy", {"HCI401": {"role": "student", "section": "SEC02"}}),
    ("student39", "Ada Lovelace", {"HCI401": {"role": "student", "section": "SEC02"}}),
    ("student40", "Nikola Tesla", {"HCI401": {"role": "student", "section": "SEC02"}}),
]

for uname, dname, memberships in names:
    PERSONAS[uname] = {
        "username": uname,
        "display_name": dname,
        "global_role": "student",
        "course_memberships": memberships,
    }
