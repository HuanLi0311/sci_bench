"""Standalone Docker runner; Python 3 standard library only. Run in Linux/WSL2."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parent
TASK = ROOT.name
ENV = f'delivery-{TASK}-env:20261128'
TESTS = f'delivery-{TASK}-tests:20261128'
NAME = f'delivery-{TASK}'


def docker(*args, **kwargs):
    return subprocess.run(['docker', *map(str, args)], check=True, **kwargs)


def grade(out, logs):
    out = out.resolve(); logs = logs.resolve()
    if not out.is_dir():
        raise SystemExit(f'Submission directory does not exist: {out}')
    logs.mkdir(parents=True, exist_ok=True)
    # Dedicated output directory, writable by the unprivileged verifier only.
    logs.chmod(0o777)
    for p in logs.iterdir():
        if p.name in {'reward.txt', 'metrics.json', 'stderr.log'} and p.is_file():
            p.unlink()
    command = ['docker', 'run', '--rm', '--network', 'none', '--read-only',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--user', '65534:65534', '--pids-limit', '256', '--cpus', '4',
               '--memory', '8g', '--shm-size', '1g', '--tmpfs', '/tmp:rw,nosuid,size=2g,mode=1777',
               '--entrypoint', 'bash', '-e', 'HOME=/tmp', '-e', 'OMP_NUM_THREADS=4',
               '--mount', f'type=bind,src={out},dst=/app/out,readonly',
               '--mount', f'type=bind,src={logs},dst=/logs/verifier', TESTS,
               '/tests/test.sh', '/app/out']
    result = subprocess.run(command, timeout=3660)
    metrics = logs / 'metrics.json'
    if not metrics.is_file():
        raise SystemExit(f'Infrastructure failure (docker exit {result.returncode}); no grading result')
    data = json.loads(metrics.read_text())
    if data.get('status') == 'infrastructure_error' or result.returncode not in (0, 1):
        raise SystemExit('Infrastructure failure; see verifier logs. Do not record reward 0.')
    return data['reward']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['load', 'build', 'start', 'stop', 'grade', 'oracle', 'nop'])
    parser.add_argument('--out', type=Path, default=ROOT/'output')
    parser.add_argument('--logs', type=Path, default=ROOT/'logs')
    parser.add_argument('--port', type=int, default=5901 if TASK == 'banner-stand' else 5902)
    args = parser.parse_args()
    if args.command == 'load':
        docker('load', '-i', ROOT/'runtime/images.tar')
        expected = json.loads((ROOT/'runtime/images.json').read_text())
        for tag, info in expected.items():
            actual = json.loads(docker('image','inspect',tag,capture_output=True,text=True).stdout)[0]
            if actual['Id'] != info['Id']:
                raise SystemExit(f'Image identity mismatch: {tag}')
    elif args.command == 'build':
        docker('build', '--network=default', '-t', ENV, ROOT/'environment')
        docker('build', '--network=default', '-t', TESTS, ROOT/'tests')
    elif args.command == 'start':
        args.out.mkdir(parents=True, exist_ok=True)
        docker('run', '-d', '--name', NAME, '--network', 'bridge', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--cpus','4','--memory','8g',
               '--pids-limit','512','--shm-size','1g',
               '-p', f'127.0.0.1:{args.port}:5900',
               '--mount', f'type=bind,src={args.out.resolve()},dst=/app/out', ENV)
        print(f'Blender desktop: VNC 127.0.0.1:{args.port}; output: {args.out.resolve()}')
    elif args.command == 'stop':
        docker('rm', '-f', NAME)
    elif args.command == 'grade':
        return 0 if grade(args.out,args.logs) == 1 else 1
    elif args.command in ('oracle', 'nop'):
        args.out.mkdir(parents=True,exist_ok=True)
        if any(args.out.iterdir()):
            raise SystemExit('Oracle/NOP requires an empty --out directory to prevent stale results')
        mounts = ['--mount',f'type=bind,src={args.out.resolve()},dst=/app/out']
        if args.command == 'oracle':
            mounts += ['--mount',f'type=bind,src={ROOT/"solution"},dst=/solution,readonly']
        docker('run','--rm','--network','none','--entrypoint','bash',*mounts,ENV,
               *(['/solution/solve.sh'] if args.command == 'oracle' else ['-c','/bin/true']))
        reward = grade(args.out,args.logs)
        expected = 1 if args.command == 'oracle' else 0
        if reward != expected:
            raise SystemExit(f'{args.command} failed: expected {expected}, received {reward}')
        print(f'{args.command}: PASS (reward={reward})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
