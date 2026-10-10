from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / 'deployment' / 'local-state.ps1'
SHELL = shutil.which('pwsh') or shutil.which('powershell')


@unittest.skipUnless(sys.platform == 'win32' and SHELL, 'Native Windows DPAPI/PowerShell required')
class LocalStateBackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='aeon-backup-drill-')
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.archive = self.root / 'state.aeon-dpapi'
        self.target = self.root / 'restored'
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            self.port = listener.getsockname()[1]
        # Synthetic fixtures only; no provider files or real queue/worker state.
        (self.source / 'worker' / 'jobs' / 'job-fixture' / 'state').mkdir(parents=True)
        (self.source / 'objects').mkdir()
        (self.source / 'empty-directory').mkdir()
        (self.source / 'worker' / 'connection.json').write_text(
            json.dumps({'worker_id': 'synthetic-worker-identity', 'token': 'SYNTHETIC-TOKEN-NOT-A-CREDENTIAL'}))
        (self.source / 'worker' / 'jobs' / 'job-fixture' / 'state' / 'checkpoint.json').write_text(
            json.dumps({'status': 'interrupted', 'step': 3, 'memory': ['qualified fixture lesson']}))
        (self.source / 'worker' / 'approved-memory.json').write_text(
            json.dumps({'entries': [{'id': 'fixture-lesson', 'evidence': 'fixture-ledger-event', 'approved': True}]}))
        (self.source / 'objects' / 'artifact.bin').write_bytes(bytes(range(256)) * 8)
        database = sqlite3.connect(self.source / 'queue.sqlite3')
        database.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY, status TEXT)')
        database.execute('INSERT INTO jobs VALUES (?, ?)', ('job-fixture', 'interrupted'))
        database.commit()
        database.close()
        ledger = sqlite3.connect(self.source / 'worker' / 'jobs' / 'job-fixture' / 'state' / 'events.sqlite3')
        ledger.execute('CREATE TABLE events (sequence INTEGER, event TEXT, previous_hash TEXT)')
        ledger.execute('INSERT INTO events VALUES (1, ?, ?)', ('fixture-checkpoint', 'synthetic-chain-hash'))
        ledger.commit()
        ledger.close()

    def tearDown(self):
        # Only the exact tempfile-created root is removed by TemporaryDirectory.
        self.temporary.cleanup()

    def invoke(self, action, *, archive=None, target=None, extra=()):
        args = [SHELL, '-NoProfile', '-NonInteractive', '-File', str(SCRIPT),
                '-Action', action, '-ArchivePath', str(archive or self.archive), '-Port', str(self.port)]
        if action == 'backup':
            args += ['-StateRoot', str(self.source)]
        else:
            args += ['-RestoreRoot', str(target or self.target)]
        return subprocess.run(args + list(extra), capture_output=True, text=True, timeout=60)

    def assert_passed(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def assert_refused(self, result, phrase):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(phrase, result.stdout + result.stderr)

    def protect_zip(self, entries, name='malicious.aeon-dpapi', manifest_override=None):
        # Construct and DPAPI-protect hostile archive as its legitimate owner.
        # The utility still must validate decrypted entries before extracting.
        buffer = io.BytesIO()
        manifest = {'version': 1, 'source': str(self.source), 'port': self.port,
                    'files': [], 'directories': [], 'created': 'synthetic'}
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for entry, content in entries:
                archive.writestr(entry, content)
                entry_name = entry.filename if isinstance(entry, zipfile.ZipInfo) else entry
                manifest['files'].append({'path': entry_name, 'bytes': len(content),
                                          'sha256': hashlib.sha256(content).hexdigest()})
            if manifest_override:
                manifest.update(manifest_override)
            archive.writestr('_aeon_snapshot_manifest.json', json.dumps(manifest))
        plain = self.root / 'synthetic-zip-input.bin'
        plain.write_bytes(buffer.getvalue())
        output = self.root / name
        helper = self.root / 'protect-synthetic.ps1'
        helper.write_text('''param([string]$InputFile,[string]$OutputFile)
Add-Type -AssemblyName System.Security
$entropy=[Text.Encoding]::UTF8.GetBytes('AEON local-state snapshot v1')
$cipher=[Security.Cryptography.ProtectedData]::Protect([IO.File]::ReadAllBytes($InputFile),$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
[IO.File]::WriteAllBytes($OutputFile,$cipher)
''', encoding='utf-8')
        result = subprocess.run([SHELL, '-NoProfile', '-NonInteractive', '-File', str(helper),
                                 '-InputFile', str(plain), '-OutputFile', str(output)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return output

    def test_roundtrip_restores_all_hashes_identity_checkpoint_sqlite_and_empty_directory(self):
        before = {path.relative_to(self.source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in self.source.rglob('*') if path.is_file()}
        backed = self.assert_passed(self.invoke('backup'))
        self.assertEqual(backed['files'], len(before))
        ciphertext = self.archive.read_bytes()
        self.assertNotIn(b'SYNTHETIC-TOKEN-NOT-A-CREDENTIAL', ciphertext)
        self.assertFalse(ciphertext.startswith(b'PK'))
        self.assertEqual(backed['sha256'], hashlib.sha256(ciphertext).hexdigest())
        restored = self.assert_passed(self.invoke('restore'))
        after = {path.relative_to(self.target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in self.target.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(restored['files'], len(before))
        self.assertTrue((self.target / 'empty-directory').is_dir())
        db = sqlite3.connect(self.target / 'queue.sqlite3')
        try:
            self.assertEqual(db.execute('SELECT id,status FROM jobs').fetchall(), [('job-fixture', 'interrupted')])
        finally:
            db.close()
        acl = subprocess.run([SHELL, '-NoProfile', '-Command',
                              '$a=Get-Acl -LiteralPath $env:AEON_BACKUP_TEST_ARCHIVE; '
                              '$a.AreAccessRulesProtected; $a.Access.IdentityReference.Value'],
                             capture_output=True, text=True, timeout=30,
                             env={**os.environ, 'AEON_BACKUP_TEST_ARCHIVE': str(self.archive)})
        self.assertEqual(acl.returncode, 0, acl.stderr)
        self.assertIn('True', acl.stdout)
        self.assertNotIn('BUILTIN\\Users', acl.stdout)
        self.assertNotIn('Everyone', acl.stdout)

    def test_live_port_and_live_registry_refuse_without_stopping_process(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', self.port))
            listener.listen()
            self.assert_refused(self.invoke('backup'), 'port remains live')
            self.assertEqual(listener.getsockname()[1], self.port)
        (self.source / 'processes.json').write_text(json.dumps({'origin': f'http://127.0.0.1:{self.port}',
                                                              'server': {'pid': os.getpid()}}))
        self.assert_refused(self.invoke('backup'), 'Recorded process remains live')
        self.assertFalse(self.archive.exists())

    def test_unregistered_source_worker_process_refused(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)',
                                    'aeon_enterprise.local_service', str(self.source)])
        try:
            self.assert_refused(self.invoke('backup'), 'Source worker/job process remains live')
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            process.wait(timeout=10)

    def test_tampered_ciphertext_refuses_before_creating_target(self):
        self.assert_passed(self.invoke('backup'))
        tampered = bytearray(self.archive.read_bytes())
        tampered[len(tampered) // 2] ^= 1
        self.archive.write_bytes(tampered)
        self.assert_refused(self.invoke('restore'), 'DPAPI decryption/integrity failed')
        self.assertFalse(self.target.exists())

    def test_existing_archive_nonempty_target_source_and_hosted_overlap_refused(self):
        self.assert_passed(self.invoke('backup'))
        self.assert_refused(self.invoke('backup'), 'Archive already exists')
        self.target.mkdir()
        marker = self.target / 'keep.txt'
        marker.write_text('keep')
        self.assert_refused(self.invoke('restore'), 'new and empty')
        self.assertEqual(marker.read_text(), 'keep')
        self.assert_refused(self.invoke('restore', target=self.source), 'overlaps source')
        hosted = Path(os.environ['LOCALAPPDATA']) / 'AEON' / 'enterprise-private' / 'synthetic-refused'
        self.assert_refused(self.invoke('restore', target=hosted), 'separate from hosted')
        self.assertFalse(hosted.exists())

    def test_repository_archive_and_source_size_guard_refused(self):
        repository_path = SCRIPT.parents[1] / 'should-never-be-created.aeon-dpapi'
        self.assert_refused(self.invoke('backup', archive=repository_path), 'outside the repository')
        self.assertFalse(repository_path.exists())
        (self.source / 'large.bin').write_bytes(b'0' * (1024 * 1024 + 1))
        self.assert_refused(self.invoke('backup', extra=('-MaxMegabytes', '1')), 'exceeds size limit')
        self.assertFalse(self.archive.exists())

    def test_source_junction_refused_before_reading_target(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'keep.txt').write_text('unchanged')
        created = subprocess.run([SHELL, '-NoProfile', '-Command',
                                  'New-Item -ItemType Junction -Path $env:AEON_BACKUP_TEST_LINK '
                                  '-Target $env:AEON_BACKUP_TEST_OUTSIDE | Out-Null'],
                                 capture_output=True, text=True, timeout=30,
                                 env={**os.environ, 'AEON_BACKUP_TEST_LINK': str(self.source / 'link'),
                                      'AEON_BACKUP_TEST_OUTSIDE': str(outside)})
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assert_refused(self.invoke('backup'), 'State contains a reparse point')
        self.assertEqual((outside / 'keep.txt').read_text(), 'unchanged')
        self.assertFalse(self.archive.exists())

    def test_encrypted_traversal_absolute_duplicates_symlinks_hash_and_size_attacks_refused(self):
        symlink = zipfile.ZipInfo('link')
        symlink.create_system = 3
        symlink.external_attr = 0o120777 << 16
        attacks = [([('../escape.txt', b'escape')], 'Unsafe archive entry'),
                   ([('C:/escape.txt', b'escape')], 'Unsafe archive entry'),
                   ([('/escape.txt', b'escape')], 'Unsafe archive entry'),
                   ([('same.txt', b'a'), ('SAME.txt', b'b')], 'Duplicate archive entry'),
                   ([(symlink, b'../escape')], 'symlink/reparse entry'),
                   ([('parent', b'a'), ('parent/child.txt', b'b')], 'file/directory conflict'),
                   ([('directory/', b'invalid')], 'Nonempty archive directory'),
                   ([('artifact.bin', b'payload')], 'Manifest hash mismatch'),
                   ([('expanded.bin', b'0' * (1024 * 1024 + 1))], 'Expanded archive exceeds')]
        for number, (entries, phrase) in enumerate(attacks):
            with self.subTest(attack=phrase):
                override = {'files': [{'path': 'artifact.bin', 'bytes': 7, 'sha256': '0' * 64}]} if phrase == 'Manifest hash mismatch' else None
                archive = self.protect_zip(entries, name=f'attack-{number}.aeon-dpapi', manifest_override=override)
                extra = ('-MaxMegabytes', '1') if phrase == 'Expanded archive exceeds' else ()
                self.assert_refused(self.invoke('restore', archive=archive, extra=extra), phrase)
                self.assertFalse(self.target.exists())
                self.assertFalse((self.root / 'escape.txt').exists())


if __name__ == '__main__':
    unittest.main()
