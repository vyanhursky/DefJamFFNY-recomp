"""Compile all six source portraits per added fighter through the ordinary path.

Reports exact source/compiled identities and unsupported layouts. It does not
copy source menu movies or establish native visual acceptance. Other source
screen families remain separately accountable; this audit never excludes them.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_build import retail_catalog
from fighter_portrait import Portrait, PortraitBaseline, variant_path
from fighter_resource_files import PORTRAIT_PARTS, PORTRAIT_EXTENDED_PARTS
from fighter_sod import Database


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--game', type=Path, default=ROOT / 'game')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--extended',action='store_true',help='Include authored selector/result/loading logos and loading portraits')
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Choose a new audit report path')
    pins = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text())
    catalog = retail_catalog(args.game / 'assets/djv2.sod')
    baseline = PortraitBaseline((args.game / 'screens/screens.viv').read_bytes(), pins['screens_sha256'])
    candidates = {key: row['native_binding']['selection_key'] for key, row in catalog.rows.items()}
    by_core = {row['native_binding']['core_id']: (key, row) for key, row in catalog.rows.items()}
    mapping = {}
    for line in (args.source / 'coreid.txt').read_text().splitlines():
        words = line.split('#', 1)[0].split()
        if words:
            core, donor, _voice = map(int, words)
            if core in mapping:
                raise ValueError('Duplicate source core mapping')
            mapping[core] = donor
    names = {row['name'] for row in catalog.rows.values()}
    added = [row for row in Database((args.source / 'assets/djv2.sod').read_bytes()).character_metadata()['characters']
             if row['name'] not in names]
    rows = []
    for actor in added:
        core = actor['native_binding']['core_id']
        row = {'source_symbol': actor['name'], 'source_core': core, 'selection': actor['native_binding']['selection_key'],
               'inputs': {}, 'passed': False}
        try:
            behavior_donor, _retail = by_core[mapping[core]]
            files = {}
            for part in PORTRAIT_EXTENDED_PARTS if args.extended else PORTRAIT_PARTS:
                path, stem = variant_path(part, row['selection'])
                source = (args.source / path).read_bytes()
                archive = Archive(unpack(source))
                data = unpack(archive.read(stem + '.xsh'))
                row['inputs'][part] = {'path': path, 'sha256': digest(source), 'texture_sha256': digest(data)}
                files[part] = data
            matches = baseline.matching_layouts(files, candidates)
            if not matches:
                raise ValueError('No verified retail donor matches all six source portrait layouts')
            donor = behavior_donor if behavior_donor in matches else matches[0]
            retail = catalog.rows[donor]
            source = {'format': 'eagl-portrait-2' if args.extended else 'eagl-portrait-1', 'donor': donor,
                      **{part: {'path': part + '.xsh', 'sha256': digest(data)} for part, data in files.items()}}
            portrait = Portrait('converted/portrait-' + str(core), source, files, baseline,
                                retail['native_binding']['selection_key'])
            row.update(passed=True, donor=donor, matching_layouts=matches, receipt=portrait.summary,
                       compiled={path: digest(data) for path, data in portrait.files.items()})
        except (ValueError, OSError, KeyError) as error:
            row['error'] = str(error)
        rows.append(row)
    report = {'schema': 'fighter-conversion-portrait-audit-1', 'rows': rows,
              'summary': {'fighters': len(rows), 'passed': sum(row['passed'] for row in rows),
                          'source_files': sum(len(row['inputs']) for row in rows)},
              'native_playtest': False, 'whole_pack_conversion': False,
              'ancillary_screen_accounting': ('all eighteen portrait/logo variants covered; whole selector movies remain separate'
                                              if args.extended else 'not covered; no other source art is implicitly excluded')}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as output:
        output.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary']))
    return 0 if rows and all(row['passed'] for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
