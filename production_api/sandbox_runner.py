"""Offline opt-in test runner. Requires a separately configured Docker daemon.

Never call from a public HTTP endpoint. Running untrusted code is inherently risky;
use a dedicated isolated worker/VM, not the production API host.
"""
import json, os, subprocess, tempfile
from pathlib import Path
from artifact_review import review

IMAGE='python:3.12.7-slim@sha256:PLACEHOLDER_PIN_REQUIRED'

def run_python_tests(files, *, image_digest, enabled=False):
    if not enabled or os.environ.get('ENABLE_ISOLATED_TEST_RUNNER')!='1':
        raise RuntimeError('Runner desabilitado: requer operador e worker dedicado')
    if not image_digest.startswith('python:3.12.7-slim@sha256:') or len(image_digest.split('sha256:')[-1])!=64:
        raise ValueError('Informe imagem fixada por digest SHA-256 válido')
    review(files)
    # Only stdlib unittest; never pip install from submitted manifests.
    with tempfile.TemporaryDirectory(prefix='jobagent-run-') as temp:
        root=Path(temp)
        for f in files:
            target=root/f['path'];target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(f['content'],encoding='utf-8')
        cmd=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL',
             '--security-opt','no-new-privileges','--pids-limit','64','--memory','256m',
             '--cpus','0.5','--user','65534:65534','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
             '--mount',f'type=bind,src={root},dst=/work,readonly',
             '--workdir','/work',image_digest,'python','-B','-m','unittest','discover','-s','tests','-v']
        try:
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=35,check=False)
        except subprocess.TimeoutExpired:
            return {'status':'TIMEOUT','tests_executed':False,'output':'Limite de tempo excedido'}
        # Output is untrusted and may include data; cap and redact before persistence.
        return {'status':'PASS' if proc.returncode==0 else 'FAIL','tests_executed':True,
                'exit_code':proc.returncode,'output_truncated':True,
                'output':'Saída omitida por segurança; consulte logs efêmeros do worker com acesso restrito.'}
