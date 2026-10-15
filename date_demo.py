from datetime import date

last_login = date.fromisoformat("2026-10-13")
target_date = date.fromisoformat("2026-10-14")

print(last_login == target_date)
print(last_login < target_date)
print(last_login > target_date)
