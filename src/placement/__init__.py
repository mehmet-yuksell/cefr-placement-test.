"""CEFR-aligned English placement test (MVP).

The package is split so that everything except ``app.py`` is free of UI code:
``bank`` loads and validates items, ``engine`` decides what to show next,
``scoring`` turns responses into an ability estimate, ``report`` builds the
result card, and ``storage`` persists sessions to SQLite.
"""
