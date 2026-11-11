"""Take a consistent SQLite backup without interrupting Vaultwarden."""
from pathlib import Path
from datetime import datetime,timezone
import sqlite3,tempfile,tarfile,os
source=Path('/data');target=Path('/backups');target.mkdir(exist_ok=True)
os.umask(0o077)
with tempfile.TemporaryDirectory() as tmp:
 db=Path(tmp)/'db.sqlite3'
 with sqlite3.connect('file:/data/db.sqlite3?mode=ro',uri=True) as src,sqlite3.connect(db) as dst:
  src.backup(dst)
  assert dst.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  users=dst.execute('SELECT count(*) FROM users').fetchone()[0]
  items=dst.execute('SELECT count(*) FROM ciphers').fetchone()[0]
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 out=target/('vaultwarden-'+stamp+'.tar.gz')
 with tarfile.open(out,'w:gz') as archive:
  archive.add(db,arcname='db.sqlite3')
  for p in source.iterdir():
   if p.name in ['db.sqlite3','db.sqlite3-shm','db.sqlite3-wal','tmp','icon_cache']:continue
   archive.add(p,arcname=p.name)
 out.chmod(0o600)
 with tarfile.open(out,'r:gz') as archive:
  names=archive.getnames();assert 'db.sqlite3' in names and 'rsa_key.pem' in names
 print('Verified local backup:',out.name,'users:',users,'encrypted items:',items)
