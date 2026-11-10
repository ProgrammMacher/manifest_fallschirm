from datetime import date, timedelta
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest

from app.services.birthday_service import birthdays_around_today as _birthdays_around_today


def _person(name, birthdate):
    return SimpleNamespace(first_name=name, last_name="Test", birthdate=birthdate)


def test_birthdays_range_order_year_change_and_age():
    persons = [
        _person("TooLate", date(1980, 2, 20)),
        _person("LastDay", date(1980, 2, 19)),
        _person("NextYear", date(1979, 1, 1)),
        _person("Today", date(2000, 12, 25)),
        _person("Yesterday", date(1990, 12, 24)),
        _person("FirstDay", date(1990, 10, 30)),
        _person("TooEarly", date(1990, 10, 29)),
        _person("NoDate", None),
        _person("Future", date(2030, 1, 2)),
    ]

    birthdays = _birthdays_around_today(persons, date(2026, 12, 25))

    assert [(b["person"].first_name, b["date"], b["weekday"], b["age"]) for b in birthdays] == [
        ("FirstDay", date(2026, 10, 30), "Fr", 36),
        ("Yesterday", date(2026, 12, 24), "Do", 36),
        ("Today", date(2026, 12, 25), "Fr", 26),
        ("NextYear", date(2027, 1, 1), "Fr", 48),
        ("LastDay", date(2027, 2, 19), "Fr", 47),
    ]


def test_highlight_and_past_boundaries():
    today = date(2026, 12, 25)
    persons = []
    for offset in range(-4, 5):
        day = today + timedelta(days=offset)
        persons.append(_person(str(offset), date(1980, day.month, day.day)))
    birthdays = _birthdays_around_today(persons, today)
    assert [b["near_today"] for b in birthdays] == [False] + [True] * 7 + [False]
    assert [b["past"] for b in birthdays] == [True] * 4 + [False] * 5


def test_leap_day_occurs_only_in_leap_years():
    person = _person("Leap", date(2000, 2, 29))
    assert _birthdays_around_today([person], date(2027, 2, 1)) == []
    birthdays = _birthdays_around_today([person], date(2028, 2, 1))
    assert [(b["date"], b["weekday"], b["age"]) for b in birthdays] == [
        (date(2028, 2, 29), "Di", 28)
    ]


class BirthdaySectionParser(HTMLParser):
    def __init__(self, heading_id="birthdays-heading"):
        super().__init__()
        self.heading_id = heading_id
        self.in_section = False
        self.in_item = False
        self.items = []
        self.text = []
        self.item_attrs = {}
        self.div_depth = 0
        self.grid_depth = None
        self.section_in_grid = False
        self.link_depth = 0
        self.section_in_link = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            self.div_depth += 1
            if "app-grid" in attrs.get("class", "").split():
                self.grid_depth = self.div_depth
        if tag == "a":
            self.link_depth += 1
        if tag == "section" and attrs.get("aria-labelledby") == self.heading_id:
            self.in_section = True
            self.section_in_grid = self.grid_depth is not None
            self.section_in_link = self.link_depth > 0
        elif self.in_section and tag == "li":
            self.in_item = True
            self.text = []
            self.item_attrs = attrs

    def handle_data(self, data):
        if self.in_item:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "div":
            if self.grid_depth == self.div_depth:
                self.grid_depth = None
            self.div_depth -= 1
        if tag == "a":
            self.link_depth -= 1
        if self.in_section and tag == "li":
            self.items.append((self.item_attrs, " ".join("".join(self.text).split())))
            self.in_item = False
        elif self.in_section and tag == "section":
            self.in_section = False


@pytest.fixture()
def app_with_birthdays(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir()
    monkeypatch.setenv("MANIFEST_RUNTIME_HOME", str(runtime_home))
    monkeypatch.setenv("MANIFEST_DB_PATH", str(runtime_home / "manifest_test.db"))
    monkeypatch.setenv("MANIFEST_ENV", "dev")
    monkeypatch.setenv("MANIFEST_AUTO_CREATE_DB", "1")

    import app.helpers.db_migrations as db_migrations
    import app.routes.person as person_route
    from app import create_app, db
    from app.models.person import Person

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 25)

    monkeypatch.setattr(db_migrations, "run_startup_migrations", lambda: None)
    monkeypatch.setattr(person_route, "date", FixedDate)
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        for i in range(12):
            db.session.add(Person(
                first_name=f"Person{i:02}",
                last_name="Test",
                phone=f"123456{i:04}",
                weight_kg=70,
                birthdate=date(1980, 12, 20 + i) if i < 11 else date(1980, 1, 1),
                is_member=i < 10,
                is_student=i < 5,
            ))
        archived = Person(
            first_name="Archiv", last_name="Test", phone="1234569999",
            weight_kg=70, birthdate=date(1980, 12, 25), is_member=True,
        )
        db.session.add(archived)
        db.session.commit()
        archived.archive(reason="test")
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()


def _get_birthdays(client, query=""):
    response = client.get("/persons/" + query)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    parser = BirthdaySectionParser()
    parser.feed(html)
    return html, parser


def test_list_shows_all_rows_in_scroll_region_and_initial_anchor(app_with_birthdays):
    html, section = _get_birthdays(app_with_birthdays.test_client())

    assert len(section.items) == 12
    assert [i for i, (attrs, _) in enumerate(section.items) if "data-birthday-anchor" in attrs] == [3]
    assert [i for i, (attrs, _) in enumerate(section.items) if "list-group-item-warning" in attrs["class"]] == list(range(2, 9))
    assert "20.12.2026 (So) - Person00 Test - 46. Geburtstag" in section.items[0][1]
    assert "01.01.2027 (Fr) - Person11 Test - 47. Geburtstag" in section.items[-1][1]
    assert 'id="birthdaysScroll"' in html
    assert html.index('id="birthdays-heading"') < html.index('id="personTable"')


@pytest.mark.parametrize(
    "query, expected_names",
    [
        ("?filters=members", [f"Person{i:02}" for i in range(10)]),
        ("?filters=members,student", [f"Person{i:02}" for i in range(5)]),
        ("?filters=members&search=Person03", ["Person03"]),
        ("?filters=archived", ["Archiv"]),
        ("?search=notfound", []),
    ],
)
def test_birthdays_follow_current_person_filters(app_with_birthdays, query, expected_names):
    html, section = _get_birthdays(app_with_birthdays.test_client(), query)
    assert len(section.items) == len(expected_names)
    for (_, text), name in zip(section.items, expected_names):
        assert name in text
    if "filters=members&search=" in query:
        assert 'name="filters" value="members"' in html
    if not expected_names:
        assert "Keine Geburtstage innerhalb von 8 Wochen vor oder nach heute." in html


def test_dashboard_shows_active_members_around_today(app_with_birthdays, monkeypatch):
    import app.routes.pwa as pwa_route
    from app import db
    from app.models.person import Person

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 25)

    monkeypatch.setattr(pwa_route, "date", FixedDate)
    with app_with_birthdays.app_context():
        db.session.add_all([
            Person(first_name="HeuteLehrer", last_name="Test", phone="1234500001",
                   weight_kg=70, birthdate=date(1970, 12, 25), is_member=True, is_teacher=True),
            Person(first_name="HeuteSchueler", last_name="Test", phone="1234500002",
                   weight_kg=70, birthdate=date(1990, 12, 25), is_member=True, is_student=True),
            Person(first_name="Gast", last_name="Test", phone="1234500003",
                   weight_kg=70, birthdate=date(1980, 12, 25), is_tandem_guest=True),
        ])
        db.session.commit()

    response = app_with_birthdays.test_client().get("/pwa/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    section = BirthdaySectionParser("dashboard-birthdays-heading")
    section.feed(html)
    names = [text for _, text in section.items]

    assert len(names) == 8
    assert ["Person03" in names[0], "Person04" in names[1]] == [True, True]
    assert all(name in names[2 + i] for i, name in enumerate(["HeuteLehrer", "HeuteSchueler", "Person05"]))
    assert all(name in names[5 + i] for i, name in enumerate(["Person06", "Person07", "Person08"]))
    assert "25.12.2026 HeuteLehrer Test – 56. Geburtstag" in names[2]
    assert "Archiv" not in " ".join(names)
    assert "Gast" not in " ".join(names)
    assert all("list-group-item-warning" in attrs["class"] for attrs, _ in section.items)
    assert html.index('class="row g-4 app-grid"') < html.index('id="dashboard-birthdays-heading"')
    assert not section.section_in_grid
    assert not section.section_in_link
    assert "birthdaysScroll" not in html


def test_dashboard_empty_and_year_change(app_with_birthdays, monkeypatch):
    import app.routes.pwa as pwa_route
    from app import db
    from app.models.person import Person

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 31)

    monkeypatch.setattr(pwa_route, "date", FixedDate)
    with app_with_birthdays.app_context():
        Person.query.filter(Person.first_name == "Person11").one().is_member = True
        db.session.commit()
    client = app_with_birthdays.test_client()
    html = client.get("/pwa/").get_data(as_text=True)
    section = BirthdaySectionParser("dashboard-birthdays-heading")
    section.feed(html)
    assert any("01.01.2027 Person11 Test – 47. Geburtstag" in text for _, text in section.items)

    with app_with_birthdays.app_context():
        Person.query.update({Person.is_member: False})
        db.session.commit()
    html = client.get("/pwa/").get_data(as_text=True)
    section = BirthdaySectionParser("dashboard-birthdays-heading")
    section.feed(html)
    assert not section.items
    assert "Keine Geburtstage innerhalb von 8 Wochen vor oder nach heute." in html
