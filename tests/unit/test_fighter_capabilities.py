"""Capability discovery is source-only and must stay aligned with the real API."""
import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_capability_manifest_matches_actual_parser_and_recipe():
    def no_duplicates(pairs):
        keys = [key for key, _ in pairs]
        assert len(keys) == len(set(keys)), f'duplicate keys in fighter-contract.json: {keys}'
        return dict(pairs)

    # Parallel branches each adding an "extensions" key once merged into a file with two of
    # them; json.loads keeps only the last, silently dropping capabilities.
    manifest = json.loads((ROOT / 'scripts/fighter-contract.json').read_text(encoding='utf-8'),
                          object_pairs_hook=no_duplicates)
    assert set(manifest) == {'api', 'commands', 'recipe_format', 'extensions'}
    assert manifest['extensions'] == ['retail-animation-preview-1', 'standalone-retail-outfits-1', 'caf-sculpt-normals-1',
                                     'caf-final-stats-1']
    assert type(manifest['api']) is int and manifest['api'] == 1
    tree = ast.parse((ROOT / 'scripts/fighter-contract.py').read_text(encoding='utf-8'))
    commands = next(ast.literal_eval(keyword.value)
                    for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument'
                    and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'command'
                    for keyword in node.keywords if keyword.arg == 'choices')
    assert len(manifest['commands']) == len(set(manifest['commands']))
    assert set(manifest['commands']) == set(commands)
    recipe = ast.parse((ROOT / 'setup/fighter_caf.py').read_text(encoding='utf-8'))
    declared = next(ast.literal_eval(node.value) for node in recipe.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'FORMAT' for target in node.targets))
    assert manifest['recipe_format'] == declared

    capability = next(ast.literal_eval(node.value) for node in recipe.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'FINAL_STATS_CAPABILITY' for target in node.targets))
    assert capability in manifest['extensions']
