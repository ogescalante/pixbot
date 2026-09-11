"""The payload a bank app actually parses."""

from __future__ import annotations

from pix.brcode import br_code, crc16


def _tlv_parse(payload: str) -> dict[str, str]:
    out, i = {}, 0
    while i + 4 <= len(payload):
        tag, ln = payload[i:i + 2], int(payload[i + 2:i + 4])
        out[tag] = payload[i + 4:i + 4 + ln]
        i += 4 + ln
    return out


def test_crc_matches_the_standard_check_vector():
    assert crc16("123456789") == "29B1"


def test_the_code_carries_the_key_verbatim():
    code = br_code("11144477735", 250.0)
    account = _tlv_parse(_tlv_parse(code)["26"])
    assert account["00"] == "BR.GOV.BCB.PIX"
    assert account["01"] == "11144477735"


def test_the_amount_is_two_decimals_and_optional():
    assert _tlv_parse(br_code("11144477735", 1234.5))["54"] == "1234.50"
    assert "54" not in _tlv_parse(br_code("11144477735"))


def test_an_unknown_receiver_is_left_to_dict():
    """Tag 59 is what the *paying* bank overrides from DICT anyway."""
    assert _tlv_parse(br_code("11144477735"))["59"] == "NAO INFORMADO"


def test_accents_are_stripped_from_the_receiver_name():
    assert _tlv_parse(br_code("11144477735", None, "José Antônio"))["59"] == \
        "JOSE ANTONIO"


def test_the_crc_covers_its_own_tag():
    code = br_code("11144477735", 250.0)
    assert code[-8:-4] == "6304"
    assert crc16(code[:-4]) == code[-4:]
