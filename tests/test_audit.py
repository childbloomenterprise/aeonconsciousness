from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from codebee_improve.audit import AuditLog


class AuditTests(unittest.TestCase):
    def test_hash_chain_detects_tampering(self) -> None:
        with TemporaryDirectory() as temp:
            path = Path(temp) / "audit.jsonl"
            log = AuditLog(path)
            log.append("candidate.proposed", actor="agent", details={"id": "one"})
            log.append("candidate.approved", actor="owner", details={"id": "one"})
            self.assertTrue(log.verify())

            text = path.read_text(encoding="utf-8").replace("approved", "rejected")
            path.write_text(text, encoding="utf-8")
            self.assertFalse(log.verify())


if __name__ == "__main__":
    unittest.main()
