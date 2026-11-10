from datetime import timedelta


def birthdays_around_today(persons, today):
    birthdays_by_day = {}
    for person in persons:
        if person.birthdate:
            key = (person.birthdate.month, person.birthdate.day)
            birthdays_by_day.setdefault(key, []).append(person)

    weekdays = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
    birthdays = []
    for offset in range(-56, 57):
        birthday_date = today + timedelta(days=offset)
        people = birthdays_by_day.get((birthday_date.month, birthday_date.day), [])
        for person in sorted(people, key=lambda p: (p.last_name.casefold(), p.first_name.casefold())):
            if person.birthdate <= birthday_date:
                birthdays.append({
                    "person": person,
                    "date": birthday_date,
                    "weekday": weekdays[birthday_date.weekday()],
                    "age": birthday_date.year - person.birthdate.year,
                    "near_today": abs(offset) <= 3,
                    "past": offset < 0,
                })
    return birthdays
