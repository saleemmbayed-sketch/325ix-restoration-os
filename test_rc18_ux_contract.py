#!/usr/bin/env python3
"""Dependency-free RC18 source and task-flow guard. Browser/device acceptance remains separate."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent

class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.routes=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if values.get('id'):self.ids.append(values['id'])
        if tag=='button' and values.get('data-tab'):self.routes.append(values['data-tab'])

def main():
    html=(ROOT/'index.html').read_text()
    js=(ROOT/'site.js').read_text()
    css=(ROOT/'site.css').read_text()
    m=Markup();m.feed(html)
    assert not [name for name,count in Counter(m.ids).items() if count>1], 'Duplicate HTML IDs'
    required={'garage','twin','lookup','guide','jobs','chat','expert','manuals','program','sources'}
    assert required==set(m.routes), 'Existing module route lost'
    assert all(name in m.ids for name in ('quick-query','mission-create','missionform','missionlist','garage-metrics','nav-toggle','workspace-title','detailpanel','partdossier'))
    assert 'history.replaceState' in js and 'openMissionCreate' in js and 'const key=row.part_number||row.assembly_id||row.id' in js
    assert 'await openAssembly(d.part.assembly_id)' in js, 'Direct component selection lost its parent assembly'
    assert 'partworkflowactions' in js and "tab('jobs')" in js and "tab('chat')" in js
    assert 'ix-app-layout' in css and '@media(max-width:760px)' in css
    assert 'https://cdn.' not in html, 'No new remote UI assets/dependencies'
    print('PASS RC18 ten existing routes retained; contextual navigation, task flows, no duplicate IDs')
if __name__=='__main__':main()
