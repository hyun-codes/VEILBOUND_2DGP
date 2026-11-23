"""Build editable late-game rooms. Object coordinates are native pixel units."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def properties(values):
    return [{'name': key, 'type': 'bool' if isinstance(value, bool) else
             'int' if isinstance(value, int) else 'string', 'value': value}
            for key, value in values.items()]


def build(number, filename, title, objects, backdrop='stage_06/reservoir_hall.png'):
    layers = [{'id': 1, 'name': 'Common', 'type': 'imagelayer', 'x': 0, 'y': 0,
               'visible': True, 'opacity': 1,
               'image': '../../assets/environments/' + backdrop,
               'properties': properties({'visualRole': 'backdrop'})}]
    groups = {'Terrain': [], 'Objects': []}
    for index, (name, kind, x, y, width, height, props) in enumerate(objects, 1):
        obj = dict(id=index, name=name, type=kind, x=x, y=y, width=width, height=height)
        obj['properties'] = properties(props)
        groups['Terrain' if kind in ('Ground', 'Wall', 'LightPlatform') else 'Objects'].append(obj)
    for index, (name, group) in enumerate(groups.items(), 2):
        layers.append(dict(id=index, name=name, type='objectgroup', objects=group,
                           x=0, y=0, visible=True, opacity=1))
    data = dict(type='map', version='1.10', tiledversion='1.10.2', orientation='orthogonal',
                renderorder='right-down', infinite=False, width=33, height=25,
                tilewidth=8, tileheight=8, backgroundcolor='#101018', layers=layers,
                nextlayerid=4, nextobjectid=len(objects)+1,
                properties=properties({'title': title, 'stage': number}))
    path = ROOT / f'maps/stage_{number:02d}' / filename
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def obj(name, kind, x, y, width=0, height=0, **props):
    return name, kind, x, y, width, height, props


def foundry():
    result = [
        obj('Service floor', 'Ground', 8, 184, 248, 12),
        obj('Bulkhead', 'Wall', 130, 92, 12, 92),
        obj('Return gallery', 'LightPlatform', 8, 80, 121, 6),
        obj('Right lower stair', 'LightPlatform', 202, 160, 46, 5),
        obj('Right middle stair', 'LightPlatform', 176, 136, 30, 5),
        obj('Right beacon stair', 'LightPlatform', 154, 112, 30, 5),
        obj('Bridge over bulkhead', 'LightPlatform', 130, 88, 28, 5),
        obj('PlayerStart', 'Spawn', 24, 184),
        obj('Starting cradle', 'Socket', 28, 184, initial=True, radius=55),
        obj('Cargo', 'PushCrate', 46, 168, 16, 16),
        obj('Weight treadle', 'PressurePlate', 78, 184, 16, 3, projector='Balance lamp'),
        obj('Balance lamp', 'Projector', 86, 184),
        obj('Bulkhead rest', 'Focus', 129, 125, projector='Balance lamp', radius=50),
        obj('Loaded stair', 'Focus', 213, 160, projector='Balance lamp', radius=70),
        obj('Return beacon', 'Beacon', 180, 112, radius=112),
        obj('Upper gallery pilot', 'FixedLight', 38, 67, radius=40),
        obj('East key', 'Key', 233, 153, 7, 7),
        obj('Upper west key', 'Key', 32, 73, 7, 7),
        obj('Rest receiver', 'Receiver', 129, 105),
        obj('Exit', 'Exit', 13, 160, 13, 24, socket='Starting cradle'),
    ]
    result += [obj(f'Floor pilot {x}', 'FixedLight', x, 199, radius=32) for x in (30, 82, 134, 186, 238)]
    return result


def from_map(path):
    data = json.loads((ROOT / path).read_text(encoding='utf-8'))
    return [obj(item['name'], item['type'], item['x'], item['y'],
                item.get('width', 0), item.get('height', 0),
                **{p['name']: p['value'] for p in item.get('properties', [])})
            for layer in data['layers'] if layer['type'] == 'objectgroup'
            for item in layer['objects'] if 'gid' not in item]


def reversal():
    result = []
    for name, kind, x, y, w, h, props in foundry():
        if name == 'Return gallery':
            for part in [obj('Upper west gallery', 'LightPlatform', 8, 80, 58, 6),
                         obj('Upper east gallery', 'LightPlatform', 86, 80, 43, 6),
                         obj('One-way key alcove', 'LightPlatform', 72, 122, 35, 5),
                         obj('Alcove key', 'Key', 91, 115, 7, 7)]:
                pn, pk, px, py, pw, ph, pp = part
                result.append(obj(pn, pk, 264-px-pw, py, pw, ph, **pp))
            continue
        if name == 'Cargo':
            x = 78
        if name == 'Bulkhead rest':
            x, y, props = 213, 160, dict(projector='Balance lamp', radius=70)
        if name == 'Loaded stair':
            x, y, props = 129, 125, dict(projector='Balance lamp', radius=50)
        result.append(obj(name, kind, 264 - x - w, y, w, h, **props))
    return result


def freight():
    result = from_map('maps/stage_04/stage4_counterweight.tmj')
    result = [obj(n, k, x, y, w, h, **(dict(socket='Outlet cradle') if k == 'Exit' else p))
              for n, k, x, y, w, h, p in result]
    result += [
        obj('Return step', 'LightPlatform', 63, 132, 23, 5),
        obj('Sump landing', 'Ground', 18, 178, 50, 8),
        obj('Sump return stair', 'LightPlatform', 42, 156, 18, 5),
        obj('Sump key', 'Key', 23, 171, 7, 7),
        obj('Sump oil lamp', 'FixedLight', 36, 168, radius=32),
        obj('Weight treadle', 'PressurePlate', 181, 156, 15, 3, projector='Load lamp'),
        obj('Load lamp', 'Projector', 190, 156),
        obj('Sump focus', 'Focus', 56, 146, projector='Load lamp', radius=40),
        obj('Exit focus', 'Focus', 221, 111, projector='Load lamp', radius=42),
        obj('Exit load receiver', 'Receiver', 241, 90),
        obj('Outlet cradle', 'Socket', 241, 116, radius=28),
        obj('Load pilot', 'FixedLight', 190, 151, radius=21),
    ]
    return result


def reservoir():
    result = from_map('maps/stage_06/stage6_flooded_reservoir.tmj')
    result += [
        obj('Pump load', 'PushCrate', 70, 144, 16, 16),
        obj('West service pilot', 'FixedLight', 75, 150, radius=25),
        obj('Pump pilot', 'FixedLight', 120, 153, radius=29),
        obj('Load pilot', 'FixedLight', 166, 153, radius=19),
        obj('Weight treadle', 'PressurePlate', 158, 160, 16, 3, projector='Interlock lamp'),
        obj('Interlock lamp', 'Projector', 166, 160),
        obj('Filter inspection', 'Focus', 50, 131, projector='Interlock lamp', radius=25),
        obj('Outlet power', 'Focus', 241, 105, projector='Interlock lamp', radius=35),
        obj('Outlet receiver', 'Receiver', 247, 84),
    ]
    return result


if __name__ == '__main__':
    build(6, 'stage6_pressure_foundry.tmj', 'The weight of light', foundry())
    build(7, 'stage7_reverse_foundry.tmj', 'An unloaded path', reversal(), 'stage_01/pump_hall.png')
    build(8, 'stage8_freight_interlock.tmj', 'Borrowed weight', freight(), 'stage_01/pump_hall.png')
    build(9, 'stage9_reservoir_interlock.tmj', 'Last water, last light', reservoir())
