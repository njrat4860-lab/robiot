from engine.io.export import build_report


def test_report_contains_measurements_without_accuracy_word():
    result = {
        "mode": "frontal",
        "psl": 7.5,
        "blocks": {"misc": 6.0},
        "metrics": {
            "skin": {
                "id": "skin",
                "measured": 72.0,
                "unit": "score",
                "score": 0.6,
                "direction": "low",
                "name_ru": "Качество кожи",
                "band": [70.0, 100.0],
                "block": "misc",
                "points": 10.0,
                "tier": 2,
                "earned": 6.0,
            }
        },
        "warnings": [],
    }

    report = build_report(result, "male", "test_bot")

    assert "Качество кожи" in report
    assert "PSL: 7.5/10" in report
    assert "Сделано через @test_bot" in report
    assert "PSL " + "бот" not in report
    assert "точ" + "ность" not in report
    assert "ЧТО ИСПРАВЛЯТЬ" in report
    assert report.count("✦") >= 2
    assert "тир: t2" in report
    assert "КОЖА И СИММЕТРИЯ: 6.00/10" in report
