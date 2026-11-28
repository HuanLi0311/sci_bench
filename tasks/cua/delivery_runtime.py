from pathlib import Path
ROOT=Path(__file__).resolve().parent
for task in ('banner-stand','drawer-cabinet'):
    p=ROOT/task/'environment/Dockerfile'
    s=p.read_text(encoding='utf-8')
    s=s.replace('CMD ["sleep", "infinity"]', '''# Open a usable Blender session on the desktop, without the first-run overlay.
RUN blender --background --factory-startup --python-expr "import bpy; bpy.context.preferences.view.show_splash=False; bpy.ops.wm.save_userpref()"
CMD ["blender", "--disable-autoexec"]''')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=ROOT/task/'tests/grade.py';s=p.read_text(encoding='utf-8')
    s=s.replace('CHECKS = []','CHECKS = []\nINFRA_ERRORS = []')
    s=s.replace('    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)', '''    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        INFRA_ERRORS.append(str(exc))
        raise
    if r.returncode in (-9, 137):
        INFRA_ERRORS.append(f'Blender killed: {r.returncode}')''')
    s=s.replace('    must = [c for c in CHECKS', '''    if INFRA_ERRORS:
        raise RuntimeError('; '.join(INFRA_ERRORS))
    must = [c for c in CHECKS''')
    s=s.replace('print(json.dumps({"reward": 0, "must_pass": False, "critical_pass": False,', 'print(json.dumps({"status": "infrastructure_error", "reward": None, "must_pass": False, "critical_pass": False,')
    s=s.replace('        sys.exit(1)', '        sys.exit(2)')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=ROOT/task/'tests/test.sh';s=p.read_text(encoding='utf-8')
    s=s.replace('else\n  echo 0', 'elif [ "$STATUS" -eq 1 ]; then\n  echo 0')
    s=s.replace('fi\n\ncat', '''else
  rm -f /logs/verifier/reward.txt
fi

cat''')
    p.write_text(s,encoding='utf-8',newline='\n')
