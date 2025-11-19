from techno_engine.leads.lead_validation import LeadNote, validate_density, validate_register


def test_validate_density_within_bounds():
    notes = [
        LeadNote(bar=0, step=0, length=1, pitch=60),
        LeadNote(bar=0, step=4, length=1, pitch=62),
        LeadNote(bar=1, step=0, length=1, pitch=64),
    ]
    res = validate_density(notes, bounds=(1, 3))
    assert res.ok, res.reasons


def test_validate_density_out_of_bounds():
    notes = [LeadNote(bar=0, step=i, length=1, pitch=60) for i in range(6)]
    res = validate_density(notes, bounds=(1, 4))
    assert not res.ok
    assert any("too dense" in r for r in res.reasons)


def test_validate_register():
    notes = [
        LeadNote(bar=0, step=0, length=1, pitch=64),
        LeadNote(bar=0, step=4, length=1, pitch=70),
    ]
    res_ok = validate_register(notes, lo=60, hi=80)
    assert res_ok.ok

    notes_bad = notes + [LeadNote(bar=0, step=8, length=1, pitch=50)]
    res_bad = validate_register(notes_bad, lo=60, hi=80)
    assert not res_bad.ok
    assert any("out of register" in r for r in res_bad.reasons)
