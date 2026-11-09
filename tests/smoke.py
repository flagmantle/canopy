import json, sys
from playwright.sync_api import sync_playwright

import os
HTML = 'file://' + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html'))

STUB = """
(function(){
  const mk = () => new Proxy(function(){}, {
    get(t, k) { if (k === Symbol.toPrimitive) return () => 0; if (typeof k === 'symbol') return undefined; if (k in t && k !== 'name' && k !== 'length') return t[k]; if (k === 'length') return 0; t[k] = mk(); return t[k]; },
    apply() { return mk(); }, construct() { return mk(); }, set(t, k, v) { t[k] = v; return true; }
  });
  window.THREE = mk();
  window.__stub = true;
})();
"""

TEST = r"""
() => {
  const errs = [];
  const run = (label, fn) => { try { fn(); } catch (e) { errs.push(label + ': ' + (e && e.stack ? e.stack.split('\n').slice(0,3).join(' | ') : e)); } };
  const T = state.tray, C = state.canopy;
  let n = 0;
  // bare chassis
  T.design = 'none'; C.shape = 'none'; clampState();
  run('vehicle bare', () => buildVehicle()); run('tray bare', () => buildTray()); run('canopy bare', () => buildCanopy());
  run('panel tray bare', () => panelTray()); run('panel canopy bare', () => panelCanopy()); run('panel fit bare', () => panelFit()); run('panel wiring bare', () => panelWiring()); run('panel load bare', () => panelLoad());
  run('hud bare', () => updateHud()); run('parts bare', () => partsList()); run('load bare', () => loadCheck()); run('export bare', () => importCode(exportCode()));
  // trays
  for (const d of Object.keys(TRAYS)) for (const hs of ['angled','square','custom']) for (const hd of ['none','half','full']) for (const ls of Object.keys(LIGHT_STYLES)) for (const lc of Object.keys(LIGHTS)) {
    T.design = d; T.headShape = hs; T.head = hd; T.lightStyle = ls; T.lights = lc; T.sides = d === 'flat' ? 'drop' : 'none'; T.boxes = 'both'; T.spare = ['none','door','carrier','under'][n % 4]; n++;
    C.shape = 'none'; clampState();
    run('tray ' + [d, hs, hd, ls, lc].join('/'), () => { buildTray(); buildVehicle(); });
  }
  // canopies
  for (const sh of ['aframe','square','custom']) for (const rear of ['solid','hatch','barn','drop']) for (const style of ['gull','barn']) for (const win of [false,true]) for (const jack of [false,true]) for (const rack of ['none']) {
    T.design = 'factory'; T.head = 'half'; T.spare = rear === 'solid' ? 'door' : 'door';
    C.shape = sh; C.rear = rear; C.style = style; C.windows = win; C.jack = jack; C.left = 2; C.right = 1; C.floor = win;
    if (sh === 'custom') { C.bend = 700; C.rise = 450; C.inset = 300; }
    clampState();
    run('canopy ' + [sh, rear, style, win, jack].join('/'), () => { buildCanopy(); buildTray(); });
    run('panels ' + sh, () => { panelCanopy(); panelTray(); panelFit(); panelWiring(); panelLoad(); updateHud(); partsList(); loadCheck(); layout(); roofTop(); });
  }
  // racks
  for (const rk of Object.keys(RACKS)) { C.shape = 'aframe'; C.rack = rk; clampState(); run('rack ' + rk, () => buildCanopy()); }
  C.rack = 'none';
  // extreme custom values
  for (const [b, r, i] of [[300,160,0],[300,160,600],[1400,160,600],[300,1000,600],[800,700,0],[10,10,10]]) { C.shape='custom'; C.bend=b; C.rise=r; C.inset=i; clampState(); run('custom '+[b,r,i], () => { buildCanopy(); panelCanopy(); layout(); }); }
  for (const [b, u, i] of [[100,0,0],[100,1000,400],[800,300,400],[250,10,50]]) { T.head='half'; T.headShape='custom'; T.hbBend=b; T.hbTop=u; T.hbIn=i; clampState(); run('hb custom '+[b,u,i], () => { buildTray(); panelTray(); }); }
  // gear in an A-frame canopy
  C.shape = 'aframe'; C.rear='hatch'; clampState();
  run('add gear', () => { ['slide75','bra63','jerry','battery','solar200','boards'].forEach(k => addItem(k)); layout(); /* syncItems() skipped: the stub THREE cannot fake an awning's userData */ });
  run('gear panels', () => { panelFit(); panelLoad(); updateHud(); partsList(); loadCheck(); });
  run('legacy code', () => { const o = { v: 1, paint: 'silver', tray: { veh: 'hilux', cab: 'dual', spare: 'none', len: 1826, wid: 1850, mat: 'steel', finish: 'checker', colour: 'black', head: 'full', sides: 'none', boxes: 'none', lights: 'red' }, canopy: { len: 1700, wid: 1850, hgt: 1150, mat: 'alu', finish: 'checker', colour: 'raw', left: 1, right: 1, style: 'gull', windows: false, rear: 'solid', rack: false }, payload: 1000, items: [], wires: [] };
    const ok = importCode(btoa(JSON.stringify(o))); if (!ok) throw new Error('import failed'); if (state.tray.design !== 'flat' || state.tray.headShape !== 'square' || state.canopy.shape !== 'square') throw new Error('legacy migration wrong: ' + state.tray.design + state.tray.headShape + state.canopy.shape); });
  run('roundtrip', () => { const c = exportCode(); importCode(c); if (exportCode() !== c) throw new Error('roundtrip differs'); });
  return { errs, n };
}
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1300, 'height': 800})
    msgs = []
    pg.on('console', lambda m: msgs.append(m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: msgs.append('PAGEERROR: ' + str(e)))
    pg.add_init_script(STUB)
    pg.goto(HTML)
    pg.wait_for_timeout(1500)
    r = pg.evaluate(TEST)
    print('RESULT', json.dumps(r, indent=1)[:6000])
    print('CONSOLE (network errors for the CDN are expected offline)', '\n'.join(m for m in msgs[:25] if 'ERR_TUNNEL' not in m))
    b.close()
