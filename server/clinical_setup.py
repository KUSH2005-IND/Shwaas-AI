"""Generate local demo secrets without replacing an existing configuration."""
import os
import secrets
from pathlib import Path

def setup():
    root=Path(__file__).resolve().parent.parent
    path=root/'.env.clinical'
    if path.exists():raise SystemExit('.env.clinical already exists. Existing secrets were not changed.')
    uid=getattr(os,'getuid',lambda:10001)() or 10001
    gid=getattr(os,'getgid',lambda:10001)() or 10001
    values={"SHWAAS_JWT_SECRET":secrets.token_urlsafe(48),"ORTHANC_PASSWORD":secrets.token_urlsafe(32),
            "SHWAAS_DEMO_PASSWORD":secrets.token_urlsafe(16),
            "SHWAAS_UID":str(uid), "SHWAAS_GID":str(gid)}
    with path.open('x',encoding='utf-8') as f:
        os.chmod(path,0o600)
        f.write('# LOCAL SYNTHETIC DEMO ONLY. Do not commit.\n')
        for k,v in values.items():f.write(f'{k}={v}\n')
    (root/'data').mkdir(exist_ok=True)
    print('Created .env.clinical. The demo password is in SHWAAS_DEMO_PASSWORD. Never run server.seed on your existing records.')

if __name__=='__main__':setup()
