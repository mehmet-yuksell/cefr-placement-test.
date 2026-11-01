from placement import admin


def test_exposure_table_sorts_and_handles_no_sessions():
    rows = admin.exposure_table({"B": 3, "A": 3, "C": 1}, 4, ["A", "B", "C", "D"], "en")
    assert [r["Item"] for r in rows] == ["A", "B", "C", "D"]
    assert rows[0]["Share of sessions"] == "75%" and rows[-1]["Shown"] == 0
    assert admin.exposure_table({}, 0, ["A"], "tr")[0]["Oturumların oranı"] == "–"
