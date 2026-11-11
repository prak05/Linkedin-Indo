from indo_core import cover_letters


def test_generates_software_cover_letter_from_job_description():
    result = cover_letters.generate({
        "track": "software_ai_cloud",
        "job_title": "Cloud Engineering Intern",
        "company": "Example Cloud",
        "job_description": "Build Python services with AWS, Terraform and Docker.",
    })
    assert "Cloud Engineering Intern" in result
    assert "Example Cloud" in result
    assert "AWS" in result and "Terraform" in result
    assert "Dear Hiring Manager" in result


def test_management_track_mentions_hosted_events():
    result = cover_letters.generate({
        "track": "management_hr",
        "job_title": "Community Programs Intern",
        "company": "Example",
    })
    assert "AWS Student Builder Group exposure talk show" in result
    assert "Vidya Sadhnam" in result


def test_validation_rejects_unknown_track():
    try:
        cover_letters.validate_request({"track": "executive", "job_title": "x", "company": "y"})
    except ValueError as exc:
        assert "track must be one of" in str(exc)
    else:
        raise AssertionError("unknown track was accepted")
