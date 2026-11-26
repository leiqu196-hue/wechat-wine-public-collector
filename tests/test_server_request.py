import unittest
from datetime import datetime

from validate_server_request import source_for_request


class ServerRequestTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime.fromisoformat("2026-11-24T11:00:00+08:00")

    def request(self, slot, source, time=None):
        return {
            "version": 1, "request_id": f"2026-11-24T{slot}",
            "date": "2026-11-24", "source": source,
            "requested_at": time or f"2026-11-24T{slot}:15+08:00",
        }

    def test_existing_yimao_slots_and_probe(self):
        for slot in ("07:10", "07:30", "07:50"):
            self.assertEqual(source_for_request(self.request(slot, "易茅时价"), self.now), "易茅时价")
        p = self.request("probe-081000", "易茅时价", "2026-11-24T08:10:00+08:00")
        self.assertEqual(source_for_request(p, self.now), "易茅时价")

    def test_each_new_source_selects_independently(self):
        for slot, source in (("10:15", "今日酒价"), ("10:45", "茅粉鲁智深")):
            self.assertEqual(source_for_request(self.request(slot, source), self.now), source)

    def test_retry_slots_select_only_their_source(self):
        for slots, source, other in ((("10:00", "10:10", "10:20"), "今日酒价", "茅粉鲁智深"),
                                     (("10:30", "10:40", "10:50"), "茅粉鲁智深", "今日酒价")):
            for slot in slots:
                ts = "2026-11-24T" + slot + ":02+08:00"
                self.assertEqual(source_for_request(self.request(slot, source, ts), self.now), source)
                with self.assertRaises(ValueError):
                    source_for_request(self.request(slot, other, ts), self.now)
                with self.assertRaises(ValueError):
                    source_for_request(self.request(slot, source, "2026-11-24T" + slot[:3] + "59:00+08:00"), self.now)

    def test_wrong_or_nonapproved_source_fails(self):
        for source in ("茅粉鲁智深", "易茅时价", "国酒酱香", "全部", "今日酒价\nsource=国酒酱香"):
            with self.assertRaises(ValueError):
                source_for_request(self.request("10:15", source), self.now)

    def test_stale_future_naive_and_outside_slot_fail(self):
        for ts in ("2026-11-23T10:15:00+08:00", "2026-11-24T10:15:00",
                   "2026-11-24T10:20:00+08:00", "2026-11-24T11:06:00+08:00"):
            with self.assertRaises(ValueError):
                source_for_request(self.request("10:15", "今日酒价", ts), self.now)
        stale = self.request("10:15", "今日酒价")
        stale["date"] = "2026-11-23"
        with self.assertRaises(ValueError):
            source_for_request(stale, self.now)
