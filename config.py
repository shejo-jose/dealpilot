"""Product settings for DealPilot.

Edit the keywords here to change what the app looks for by default.
You can also change them in the app's sidebar without touching this file
(sidebar changes last until you refresh the page).

The descriptions are placeholders. Fill them in with a one-line summary
of each product so the team knows what each keyword list is aiming at.
"""

PRODUCTS = {
    "GDiaL": {
        "description": "TODO: one-line description of GDiaL.",
        "keywords": [
            "dialler",
            "dialer",
            "outbound calling",
            "outbound call",
            "auto dialler",
            "predictive dialler",
            "call centre",
            "call center",
        ],
    },
    "Voisense": {
        "description": "TODO: one-line description of Voisense.",
        "keywords": [
            "voice analytics",
            "speech analytics",
            "speech recognition",
            "call recording",
            "contact centre",
            "contact center",
            "sentiment analysis",
        ],
    },
    "WorkFabriQ": {
        "description": "TODO: one-line description of WorkFabriQ.",
        "keywords": [
            "HRMS",
            "HRIS",
            "HR system",
            "payroll",
            "workforce management",
            "time and attendance",
            "rostering",
        ],
    },
    "CasExpert": {
        "description": "TODO: one-line description of CasExpert.",
        "keywords": [
            "case management",
            "helpline",
            "complaints handling",
            "complaints management",
            "CRM",
        ],
    },
}

# How many extra points a notice gets when it is still open for bids.
OPEN_BONUS = 2

# Points per keyword found in the notice title.
TITLE_HIT_POINTS = 3

# Points per keyword found only in the description or category.
DESCRIPTION_HIT_POINTS = 1
