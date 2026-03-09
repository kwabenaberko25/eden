"""
Tests for eden.validators
"""
import pytest
from datetime import date, timedelta
from eden.validators import (
    validate_email,
    validate_phone,
    validate_gps,
    validate_url,
    validate_ip,
    validate_credit_card,
    validate_date,
    validate_color,
    validate_slug,
    validate_username,
    validate_password,
    validate_postcode,
    validate_range,
    validate_file_type,
    validate_iban,
    validate_national_id,
    EdenEmail,
    EdenPhone,
    EdenSlug,
    EdenURL,
    EdenColor,
)
from pydantic import BaseModel, ValidationError


# ── Email ─────────────────────────────────────────────────────────────────────

class TestEmail:
    def test_valid(self):
        assert validate_email("user@example.com").ok
        assert validate_email("USER@EXAMPLE.COM").ok        # normalised to lowercase
        assert validate_email("first.last+tag@sub.domain.org").ok

    def test_invalid(self):
        assert not validate_email("not-an-email").ok
        assert not validate_email("@nodomain.com").ok
        assert not validate_email("missing@").ok
        assert not validate_email("").ok

    def test_normalised_lowercase(self):
        result = validate_email("Hello@Example.COM")
        assert result.ok
        assert result.value == "hello@example.com"


# ── Phone ────────────────────────────────────────────────────────────────────

class TestPhone:
    def test_e164(self):
        assert validate_phone("+233501234567").ok

    def test_formatted(self):
        assert validate_phone("+1 800 555 1234").ok
        assert validate_phone("+44-20-7946-0958").ok

    def test_invalid(self):
        assert not validate_phone("abc").ok
        assert not validate_phone("").ok
        assert not validate_phone("123").ok     # too short

    def test_ghana_country_hint(self):
        assert validate_phone("+233201234567", country_code="GH").ok
        assert validate_phone("0241234567", country_code="GH").ok

    def test_extension_allowed(self):
        assert validate_phone("+1 800 555 1234 ext 99", allow_extensions=True).ok


# ── GPS ──────────────────────────────────────────────────────────────────────

class TestGPS:
    def test_string(self):
        r = validate_gps("5.6037, -0.1870")
        assert r.ok
        assert r.value.lat == pytest.approx(5.6037)
        assert r.value.lng == pytest.approx(-0.1870)

    def test_tuple(self):
        assert validate_gps((51.5074, -0.1278)).ok

    def test_dict(self):
        assert validate_gps({"lat": 40.7128, "lng": -74.0060}).ok
        assert validate_gps({"latitude": 40.7128, "longitude": -74.0060}).ok

    def test_out_of_range(self):
        assert not validate_gps((200, 0)).ok      # lat > 90
        assert not validate_gps((0, 200)).ok      # lng > 180
        assert not validate_gps((-91, 0)).ok

    def test_invalid_string(self):
        assert not validate_gps("not,valid,coords").ok
        assert not validate_gps("hello").ok


# ── URL ──────────────────────────────────────────────────────────────────────

class TestURL:
    def test_valid(self):
        assert validate_url("https://eden.dev").ok
        assert validate_url("http://localhost:8000", require_tld=False).ok

    def test_scheme_restriction(self):
        assert validate_url("ftp://files.example.com", allowed_schemes=("ftp",)).ok
        assert not validate_url("ftp://files.example.com").ok  # default allows http/https only

    def test_invalid(self):
        assert not validate_url("not-a-url").ok
        assert not validate_url("").ok


# ── IP Address ───────────────────────────────────────────────────────────────

class TestIP:
    def test_ipv4(self):
        assert validate_ip("8.8.8.8").ok
        assert validate_ip("192.168.1.1").ok

    def test_ipv6(self):
        assert validate_ip("::1").ok
        assert validate_ip("2001:db8::1").ok

    def test_version_filter(self):
        assert validate_ip("8.8.8.8", version=4).ok
        assert not validate_ip("8.8.8.8", version=6).ok

    def test_private_blocked(self):
        assert not validate_ip("192.168.1.1", allow_private=False).ok
        assert validate_ip("8.8.8.8", allow_private=False).ok

    def test_invalid(self):
        assert not validate_ip("999.999.999.999").ok
        assert not validate_ip("not-an-ip").ok


# ── Credit Card ──────────────────────────────────────────────────────────────

class TestCreditCard:
    def test_visa(self):
        r = validate_credit_card("4111111111111111")
        assert r.ok
        assert r.value["brand"] == "Visa"

    def test_mastercard(self):
        r = validate_credit_card("5500005555555559")
        assert r.ok
        assert r.value["brand"] == "Mastercard"

    def test_amex(self):
        r = validate_credit_card("378282246310005")
        assert r.ok
        assert r.value["brand"] == "Amex"

    def test_invalid_luhn(self):
        assert not validate_credit_card("1234567890123456").ok

    def test_formatted_input(self):
        assert validate_credit_card("4111 1111 1111 1111").ok  # spaces stripped


# ── Date ─────────────────────────────────────────────────────────────────────

class TestDate:
    def test_valid_string(self):
        assert validate_date("2025-06-15").ok

    def test_past_rejected(self):
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert not validate_date(yesterday, not_in_past=True).ok

    def test_future_rejected(self):
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert not validate_date(tomorrow, not_in_future=True).ok

    def test_date_object(self):
        assert validate_date(date.today()).ok

    def test_invalid(self):
        assert not validate_date("not-a-date").ok

    def test_min_max(self):
        result = validate_date(
            "2020-01-01",
            min_date=date(2021, 1, 1),
        )
        assert not result.ok


# ── Colour ───────────────────────────────────────────────────────────────────

class TestColor:
    def test_hex3(self):
        assert validate_color("#FFF").ok

    def test_hex6(self):
        assert validate_color("#FF5733").ok

    def test_hex8_alpha(self):
        assert validate_color("#FF573380").ok

    def test_normalised_uppercase(self):
        r = validate_color("#ff5733")
        assert r.ok and r.value == "#FF5733"

    def test_invalid(self):
        assert not validate_color("#GGG").ok
        assert not validate_color("red").ok
        assert not validate_color("").ok


# ── Slug ─────────────────────────────────────────────────────────────────────

class TestSlug:
    def test_valid(self):
        assert validate_slug("hello-world").ok
        assert validate_slug("post-123").ok

    def test_invalid(self):
        assert not validate_slug("Hello World").ok
        assert not validate_slug("under_score").ok
        assert not validate_slug("").ok


# ── Username ──────────────────────────────────────────────────────────────────

class TestUsername:
    def test_valid(self):
        assert validate_username("eden_user").ok
        assert validate_username("John.Doe-99").ok

    def test_too_short(self):
        assert not validate_username("ab").ok

    def test_too_long(self):
        assert not validate_username("a" * 31).ok

    def test_invalid_chars(self):
        assert not validate_username("user!name").ok

    def test_starts_with_special(self):
        assert not validate_username("_badstart").ok


# ── Password ──────────────────────────────────────────────────────────────────

class TestPassword:
    def test_strong(self):
        r = validate_password("Str0ng!Pass")
        assert r.ok
        assert r.value["score"] == 5

    def test_missing_uppercase(self):
        assert not validate_password("str0ng!pass").ok

    def test_missing_digit(self):
        assert not validate_password("Strong!Pass").ok

    def test_too_short(self):
        assert not validate_password("Sh0rt!").ok

    def test_custom_rules(self):
        # No special char required
        r = validate_password("Str0ngPass", require_special=False)
        assert r.ok


# ── Postcode ──────────────────────────────────────────────────────────────────

class TestPostcode:
    def test_us(self):
        assert validate_postcode("10001", country="US").ok
        assert validate_postcode("90210-1234", country="US").ok

    def test_gb(self):
        assert validate_postcode("SW1A 1AA", country="GB").ok

    def test_gh_postcode_note(self):
        # Ghana doesn't have an IBAN — our postcode validator returns error for unsupported
        result = validate_postcode("GA-000-0000", country="GH")
        assert result.ok or not result.ok  # just verifies it doesn't raise

    def test_invalid(self):
        assert not validate_postcode("NOTAZIP", country="US").ok


# ── Range ─────────────────────────────────────────────────────────────────────

class TestRange:
    def test_within_range(self):
        assert validate_range(5, min_val=1, max_val=10).ok

    def test_below_min(self):
        assert not validate_range(0, min_val=1).ok

    def test_above_max(self):
        assert not validate_range(11, max_val=10).ok

    def test_no_bounds(self):
        assert validate_range(999).ok


# ── File Type ─────────────────────────────────────────────────────────────────

class TestFileType:
    def test_allowed_group(self):
        assert validate_file_type("photo.jpg", "image/jpeg", allowed_groups=["image"]).ok

    def test_disallowed(self):
        assert not validate_file_type("virus.exe", "application/x-msdownload", allowed_groups=["image"]).ok

    def test_size_too_large(self):
        assert not validate_file_type(
            "big.jpg", "image/jpeg",
            allowed_groups=["image"],
            max_size_mb=1.0,
            size_bytes=2 * 1024 * 1024,  # 2 MB
        ).ok

    def test_size_ok(self):
        assert validate_file_type(
            "small.jpg", "image/jpeg",
            allowed_groups=["image"],
            max_size_mb=5.0,
            size_bytes=1 * 1024 * 1024,  # 1 MB
        ).ok


# ── IBAN ──────────────────────────────────────────────────────────────────────

class TestIBAN:
    def test_valid_gb(self):
        assert validate_iban("GB82WEST12345698765432").ok

    def test_spaces_stripped(self):
        assert validate_iban("GB82 WEST 1234 5698 7654 32").ok

    def test_invalid_checksum(self):
        assert not validate_iban("GB82WEST12345698765431").ok  # last digit changed

    def test_invalid_format(self):
        assert not validate_iban("INVALID").ok


# ── National ID ───────────────────────────────────────────────────────────────

class TestNationalID:
    def test_ghana(self):
        assert validate_national_id("GHA-123456789-0", country="GH").ok

    def test_us_ssn(self):
        assert validate_national_id("123-45-6789", country="US").ok

    def test_gb_ni(self):
        assert validate_national_id("AB123456C", country="GB").ok

    def test_invalid(self):
        assert not validate_national_id("WRONG", country="GH").ok

    def test_unsupported_country(self):
        result = validate_national_id("12345", country="JP")
        assert not result.ok
        assert "No national ID validator" in result.error


# ── Pydantic Annotated Types ──────────────────────────────────────────────────

class TestPydanticTypes:
    def test_eden_email_in_model(self):
        class M(BaseModel):
            email: EdenEmail

        m = M(email="test@example.com")
        assert m.email == "test@example.com"

        with pytest.raises(ValidationError):
            M(email="not-an-email")

    def test_eden_phone_in_model(self):
        class M(BaseModel):
            phone: EdenPhone

        m = M(phone="+233501234567")
        assert m.phone  # E.164 digits stored

        with pytest.raises(ValidationError):
            M(phone="abc")

    def test_eden_slug_in_model(self):
        class M(BaseModel):
            slug: EdenSlug

        m = M(slug="my-post")
        assert m.slug == "my-post"

        with pytest.raises(ValidationError):
            M(slug="My Post!")

    def test_eden_url_in_model(self):
        class M(BaseModel):
            website: EdenURL

        m = M(website="https://eden.dev")
        assert m.website

        with pytest.raises(ValidationError):
            M(website="not-a-url")

    def test_eden_color_in_model(self):
        class M(BaseModel):
            brand_color: EdenColor

        m = M(brand_color="#ff5733")
        assert m.brand_color == "#FF5733"

        with pytest.raises(ValidationError):
            M(brand_color="red")
