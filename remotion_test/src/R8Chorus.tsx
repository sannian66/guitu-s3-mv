import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, Sequence, interpolate} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';
import {useThree} from '@react-three/fiber';

// 第八轮试做：副歌一 S028–S030（59.48–62.833s，帧 1784–1885）。风格 D 分层生图 → 3D 深度摆层 → 真视差运镜。
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const eio = (x: number) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
const eo = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const nz = (t: number, s: number) => Math.sin(t * 1.7 + s) * 0.5 + Math.sin(t * 3.1 + s * 2.3) * 0.3 + Math.sin(t * 5.3 + s * 0.7) * 0.2;
const FOV = 30; const TAN = Math.tan((FOV / 2) * Math.PI / 180);
const fillW = (z: number, camZ: number, m = 1.15) => 2 * (camZ - z) * TAN * (16 / 9) * m;

const vert = `uniform float uT; uniform float uAmp; uniform float uFreq; varying vec2 vUv;
void main(){ vUv=uv; vec3 p=position; p.y+=sin(uv.x*uFreq-uT*4.0)*uAmp; p.z+=cos(uv.y*uFreq*0.7-uT*3.0)*uAmp*0.6;
 gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);} `;
const frag = `uniform sampler2D map; uniform float uOp; varying vec2 vUv;
void main(){ vec4 c=texture2D(map,vUv); if(c.a<0.02) discard; gl_FragColor=vec4(c.rgb,c.a*uOp);
 #include <colorspace_fragment>
}`;
type L = {f: string; z: number; m?: number; dx?: number; dy?: number; amp?: number; freq?: number; s?: number; vx?: number; vy?: number; vs?: number};
const Plane: React.FC<{tex: THREE.Texture; l: L; camZ: number; t: number; tc: number}> = ({tex, l, camZ, t, tc}) => {
  const img = tex.image as HTMLImageElement; const w = fillW(l.z, camZ, l.m ?? 1.15) * (1 + (l.vs ?? 0) * tc); const h = w * img.height / img.width;
  const seg = l.amp ? 24 : 1;
  const mat = useMemo(() => new THREE.ShaderMaterial({vertexShader: vert, fragmentShader: frag, transparent: true, depthWrite: false,
    uniforms: {map: {value: tex}, uT: {value: 0}, uAmp: {value: l.amp ?? 0}, uFreq: {value: l.freq ?? 4}, uOp: {value: 1}}}), [tex, l.amp, l.freq]);
  mat.uniforms.uT.value = t;
  return <mesh position={[(l.dx ?? 0) + (l.vx ?? 0) * tc, (l.dy ?? 0) + (l.vy ?? 0) * tc, l.z]} material={mat}><planeGeometry args={[w, h, seg, seg]} /></mesh>;
};
type CamF = (u: number, t: number) => {x: number; y: number; z: number; lx: number; ly: number; fov: number; roll: number};
const Cam: React.FC<{c: ReturnType<CamF>}> = ({c}) => {
  const {camera} = useThree(); const pc = camera as THREE.PerspectiveCamera;
  pc.position.set(c.x, c.y, c.z); pc.lookAt(c.lx, c.ly, 0); pc.rotateZ(c.roll); pc.fov = c.fov; pc.near = 0.1; pc.far = 200; pc.updateProjectionMatrix();
  return null;
};
const Shot: React.FC<{dir: string; layers: L[]; dur: number; cam: CamF; camZ: number}> = ({dir, layers, dur, cam, camZ}) => {
  const f = useCurrentFrame(); const t = f / 30; const u = f / Math.max(1, dur - 1);
  const [h] = useState(() => delayRender('tex' + dir + layers[0].f));
  const [tex, setTex] = useState<THREE.Texture[] | null>(null);
  useEffect(() => { (async () => {
    const ld = new THREE.TextureLoader();
    const ts = await Promise.all(layers.map((l) => ld.loadAsync(staticFile(`${dir}/${l.f}`))));
    ts.forEach((x) => { x.colorSpace = THREE.SRGBColorSpace; x.anisotropy = 8; x.minFilter = THREE.LinearMipmapLinearFilter; });
    setTex(ts); continueRender(h);
  })(); }, [h, dir, layers]);
  if (!tex) return null;
  return <ThreeCanvas width={1920} height={1080} gl={{antialias: true, preserveDrawingBuffer: true}} onCreated={({gl}) => { gl.toneMapping = THREE.NoToneMapping; }}>
    <Cam c={cam(u, t)} />
    {layers.map((l, i) => <Plane key={i} tex={tex[i]} l={l} camZ={camZ} t={t} tc={t - (dur - 1) / 60} />)}
  </ThreeCanvas>;
};

// 相机规则：镜头中点（u=0.5）相机正对 (0,0,camZ)，各层严格按构图对齐；其余时刻相机平移/推拉、始终盯住主体层（z=0）。
const m0 = (u: number) => eio(u) - 0.5; // -0.5→+0.5，中点为 0
// S028 ECU 刃上滴血：慢推 + 轻微横移
const S028: CamF = (u, t) => ({x: 0.25 * m0(u), y: -0.08 * m0(u), z: 10 - 0.6 * m0(u), lx: 0, ly: 0, fov: FOV, roll: 0});
// S029 MCU 握刀手：手持 + 推近（手持抖动以主体为中心）
const S029: CamF = (u, t) => { const hx = nz(t * 3, 1) * 0.05, hy = nz(t * 3, 4) * 0.04;
  return {x: hx, y: hy, z: 9.5 - 0.65 * m0(u), lx: hx * 0.3, ly: hy * 0.3, fov: FOV, roll: nz(t * 3, 7) * 0.005}; };
// S030 LS 升镜 + 开头冲推回落：相机升，视线始终盯住人物胸口
const S030: CamF = (u, t) => ({x: 0.3 * m0(u), y: 1.2 * m0(u), z: 10, lx: 0, ly: 0, fov: FOV / (1 + 0.08 * (1 - eo(u * 6))), roll: 0});

const SHOTS = [
  {id: 'S028', from: 0, dur: 32, cam: S028, camZ: 10, layers: [
    {f: 'S028_L1.png', z: -22, m: 1.2},
    {f: 'S028_L2_cut.png', z: 0, m: 1.12},
    {f: 'S028_L3_cut.png', z: 3, m: 1.15, vs: 0.15}]},
  {id: 'S029', from: 32, dur: 28, cam: S029, camZ: 9.5, layers: [
    {f: 'S029_L1.png', z: -18, m: 1.2},
    {f: 'S029_L2_cut.png', z: 0, m: 1.02, dy: 0.55},
    {f: 'S029_L3_cut.png', z: 3, m: 0.85, dx: -0.6, dy: -0.9, vx: 1.6, vy: 0.6}]},
  {id: 'S030', from: 60, dur: 41, cam: S030, camZ: 10, layers: [
    {f: 'S030_L1.png', z: -45, m: 1.25},
    {f: 'S030_L2_cut.png', z: -16, m: 1.25, vx: 0.4, amp: 0.05, freq: 3},
    {f: 'S030_L3_cut.png', z: 0, m: 0.72, dy: -0.35},
    {f: 'S030_L4_cut.png', z: 3, m: 1.25, dy: -0.25}]},
] as const;

export const R8Chorus: React.FC<{sub?: boolean}> = ({sub = true}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [0, 4, 92, 101], [0, 1, 1, 0.85], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{background: '#fff'}}>
    <style>{`@font-face{font-family:ZMX;src:url(${staticFile('ZhiMangXing-Regular.ttf')});}`}</style>
    {SHOTS.map((s) => <Sequence key={s.id} from={s.from} durationInFrames={s.dur}><Shot dir="r8" layers={s.layers as unknown as L[]} dur={s.dur} cam={s.cam} camZ={s.camZ} /></Sequence>)}
    <div style={{position: 'absolute', left: 0, top: 0, width: '100%', height: 120, background: '#000'}} />
    <div style={{position: 'absolute', left: 0, bottom: 0, width: '100%', height: 120, background: '#000'}} />
    {sub && <div style={{position: 'absolute', bottom: 150, width: '100%', textAlign: 'center', fontFamily: 'ZMX', fontSize: 76, letterSpacing: 18, color: '#fff', opacity: op,
      textShadow: '0 0 3px #000, 0 0 10px #000, 3px 3px 0 #000'}}>血未冷　刀不放</div>}
  </AbsoluteFill>;
};
