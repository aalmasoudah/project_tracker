"""Approved Gregorian and Umm al-Qura Hijri report dates."""

from datetime import date

from hijridate import Gregorian


def format_dual_date(value: date, language_code: str) -> str:
    """Return Gregorian and Hijri dates using Western digits."""
    gregorian = value.isoformat()
    try:
        hijri = Gregorian(value.year, value.month, value.day).to_hijri()
        hijri_value = f"{hijri.year:04d}-{hijri.month:02d}-{hijri.day:02d}"
    except OverflowError:
        hijri_value = "خارج نطاق أم القرى" if language_code == "ar" else "out of range"
    if language_code == "ar":
        return f"{gregorian} م / {hijri_value} هـ"
    return f"{gregorian} G / {hijri_value} AH"
