from engine.score import aggregate


def test_disabled_metric_is_removed_from_report_result():
    values = {"fwhr": 1.76, "skin": 100.0}

    result = aggregate(values, "frontal", "male", {"skin"})

    assert "skin" not in result["results"]
