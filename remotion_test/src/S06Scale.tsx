import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig, Img} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';
import {useThree} from '@react-three/fiber';

const T0 = 5018 / 30;                       // 镜头起点（秒）
const ONS = [167.42, 167.56, 167.7, 167.98, 168.3, 168.74, 168.9, 169.16, 169.38];
const SENT = '什么叫以一人换千人';
const CINNABAR = '#c8281e';
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const eo = (x: number) => 1 - Math.pow(1 - clamp01(x), 2);
const sstep = (a: number, b: number, x: number) => { const u = clamp01((x - a) / (b - a)); return u * u * (3 - 2 * u); };
function rng(seed: number) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

// ——— 字形贴图（canvas 画「人」，含飞白/墨渗边） ———
function glyphTex(ch: string, color: string, font: string, size = 256, dry = 40) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d')!;
  g.fillStyle = color; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.font = `${size * 0.86}px ${font}`;
  g.shadowColor = color; g.shadowBlur = size * 0.03;
  g.fillText(ch, size / 2, size / 2 + size * 0.04);
  // 飞白：随机擦掉细条
  const r = rng(ch.charCodeAt(0) + size);
  g.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < dry; i++) { g.fillStyle = `rgba(0,0,0,${0.25 + r() * 0.5})`; g.fillRect(r() * size, r() * size, r() * size * 0.5, 1 + r() * 2); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}

const Camera: React.FC<{u: number}> = ({u}) => {
  const {camera} = useThree();
  // 真 3D 机位：缓推 + 微仰 + 小幅环绕（现版只能 2D 缩放/旋转）
  const yaw = THREE.MathUtils.degToRad(-7 + 9 * eo(u));
  const dist = 17.4 - 1.3 * eo(u);
  const h = 1.3 + 0.5 * u;
  camera.position.set(Math.sin(yaw) * dist, h, Math.cos(yaw) * dist);
  camera.lookAt(0, 1.05 - 0.1 * u, 0);
  camera.rotateZ(THREE.MathUtils.degToRad(-0.6 * u));
  (camera as THREE.PerspectiveCamera).fov = 34; camera.updateProjectionMatrix();
  return null;
};

const Scale: React.FC<{t: number; tex: any}> = ({t, tex}) => {
  const ang = THREE.MathUtils.degToRad(0.9 * Math.sin(t * 2.1)) * 1.6;   // 横梁绕支点轻摆（3D 里秤盘按摆锤自然下垂）
  const inkMat = useMemo(() => new THREE.MeshStandardMaterial({map: tex.ink, color: '#d2ccc0', roughness: 0.85, metalness: 0.05, side: THREE.DoubleSide}), [tex]);
  const darkMat = useMemo(() => new THREE.MeshStandardMaterial({map: tex.ink, color: '#8d877d', roughness: 0.9}), [tex]);
  const lineMat = useMemo(() => new THREE.MeshStandardMaterial({color: '#1d1b19', roughness: 0.6}), []);
  const panGeo = useMemo(() => {
    const pts = [] as THREE.Vector2[];
    for (let i = 0; i <= 24; i++) { const x = (i / 24) * 1.75; pts.push(new THREE.Vector2(x, 0.32 * Math.pow(x / 1.75, 2.2))); }
    return new THREE.LatheGeometry(pts, 64);
  }, []);
  const heap = useMemo(() => {
    const r = rng(66); const items: {p: THREE.Vector3; rot: THREE.Euler; s: number}[] = [];
    for (let i = 0; i < 620; i++) {
      const a = r() * Math.PI * 2, rad = Math.sqrt(r()) * 1.45, hgt = Math.pow(1 - (rad / 1.5) ** 2, 0.75);
      items.push({p: new THREE.Vector3(Math.cos(a) * rad, 0.15 + Math.pow(r(), 0.8) * hgt * 1.75, Math.sin(a) * rad * 0.8),
        rot: new THREE.Euler((r() - 0.5) * 0.9, (r() - 0.5) * 1.2, (r() - 0.5) * 1.2), s: 0.16 + r() * 0.2});
    }
    return items;
  }, []);
  const heapMesh = useMemo(() => {
    const m = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshStandardMaterial({map: tex.ren, transparent: true, alphaTest: 0.35, side: THREE.DoubleSide, roughness: 1}), heap.length);
    const o = new THREE.Object3D();
    heap.forEach((h, i) => { o.position.copy(h.p); o.rotation.copy(h.rot); o.scale.setScalar(h.s * 1.25); o.updateMatrix(); m.setMatrixAt(i, o.matrix); });
    m.castShadow = true; m.customDepthMaterial = new THREE.MeshDepthMaterial({depthPacking: THREE.RGBADepthPacking, map: tex.ren, alphaTest: 0.35});
    return m;
  }, [heap, tex]);
  const ARM = 4.0, PIVY = 3.2;
  const Hanger: React.FC<{x: number; children?: React.ReactNode}> = ({x, children}) => (
    // 吊点随横梁转，盘子保持铅垂：反向抵消横梁角度
    <group position={[x, 0, 0]} rotation={[0, 0, -ang]}>
      {[0, 1, 2].map((k) => { const a = (k / 3) * Math.PI * 2 + 0.5; const bx = Math.cos(a) * 1.55, bz = Math.sin(a) * 1.55; const len = Math.hypot(bx, 3.3, bz);
        const mid = new THREE.Vector3(bx / 2, -3.3 / 2 - 0.15, bz / 2); const dir = new THREE.Vector3(bx, -3.3, bz).normalize();
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
        return <mesh key={k} position={mid} quaternion={q} material={lineMat} castShadow><cylinderGeometry args={[0.018, 0.018, len, 6]} /></mesh>; })}
      <mesh position={[0, -0.12, 0]} material={lineMat} castShadow><torusGeometry args={[0.1, 0.025, 8, 20]} /></mesh>
      <group position={[0, -3.75, 0]}>
        <mesh geometry={panGeo} material={inkMat} castShadow receiveShadow />
        {children}
      </group>
    </group>
  );
  return (
    <group position={[0, -2.2, 0]}>
      {/* 底座三阶 + 立柱 */}
      {[[3.4, 0.35, 1.6, 0.17], [2.6, 0.3, 1.25, 0.5], [1.8, 0.3, 0.95, 0.8]].map(([w, h, d, y], i) => (
        <mesh key={i} position={[0, y, 0]} material={darkMat} castShadow receiveShadow><boxGeometry args={[w, h, d]} /></mesh>))}
      <mesh position={[0, (0.95 + PIVY + 2.8) / 2, 0]} material={inkMat} castShadow receiveShadow><cylinderGeometry args={[0.36, 0.45, PIVY + 2.8 - 0.95, 24]} /></mesh>
      {/* 支点 + 横梁 */}
      <group position={[0, PIVY + 2.2 + 0.6, 0]} rotation={[0, 0, ang]}>
        <mesh rotation={[Math.PI / 2, 0, 0]} material={inkMat} castShadow><cylinderGeometry args={[0.48, 0.48, 0.5, 32]} /></mesh>
        <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0.26]} material={darkMat}><cylinderGeometry args={[0.28, 0.28, 0.06, 32]} /></mesh>
        <mesh material={inkMat} castShadow receiveShadow><boxGeometry args={[ARM * 2 + 0.3, 0.26, 0.32]} /></mesh>
        {[-1, 1].map((s) => <mesh key={s} position={[s * (ARM + 0.25), 0.16, 0]} rotation={[0, 0, s * 0.5]} material={inkMat} castShadow><boxGeometry args={[0.45, 0.14, 0.32]} /></mesh>)}
        <Hanger x={-ARM}>
          <mesh position={[0, 0.62, 0.2]} castShadow><planeGeometry args={[1.25, 1.25]} /><meshStandardMaterial map={tex.redRen} transparent alphaTest={0.3} side={THREE.DoubleSide} roughness={0.7} /></mesh>
        </Hanger>
        <Hanger x={ARM}><primitive object={heapMesh} /></Hanger>
      </group>
    </group>
  );
};

const Motes: React.FC<{t: number}> = ({t}) => {
  const pts = useMemo(() => { const r = rng(45); return Array.from({length: 140}, () => [r() * 14 - 9, r() * 9 - 2, r() * 6 - 2, r(), r()]); }, []);
  return <group>{pts.map((p, i) => <mesh key={i} position={[p[0] + Math.sin(t * 0.7 + p[3] * 6) * 0.15, p[1] + ((t * 0.12 + p[4]) % 1) * 0.6, p[2]]}>
    <sphereGeometry args={[0.012 + p[3] * 0.02, 6, 6]} /><meshBasicMaterial color="#fff6e0" transparent opacity={0.35 + 0.4 * p[4]} /></mesh>)}</group>;
};

export const S06Scale: React.FC = () => {
  const frame = useCurrentFrame(); const {width, height} = useVideoConfig();
  const t = T0 + frame / 30; const u = frame / 40;
  const [handle] = useState(() => delayRender('fonts+tex'));
  const [tex, setTex] = useState<any>(null);
  useEffect(() => {
    (async () => {
      const fonts = [new FontFace('NSSB', `url(${staticFile('NotoSerifSC-SemiBold.otf')})`), new FontFace('NSBK', `url(${staticFile('NotoSerifSC-Black.otf')})`), new FontFace('NSB', `url(${staticFile('NotoSerifSC-Bold.otf')})`)];
      for (const f of fonts) { await f.load(); (document as any).fonts.add(f); }
      const L = new THREE.TextureLoader();
      const [paper, ink] = await Promise.all([L.loadAsync(staticFile('paper.png')), L.loadAsync(staticFile('ink.png'))]);
      paper.colorSpace = ink.colorSpace = THREE.SRGBColorSpace; ink.wrapS = ink.wrapT = THREE.RepeatWrapping; ink.repeat.set(1, 1);
      setTex({paper, ink, ren: glyphTex('人', '#141210', 'NSB'), redRen: glyphTex('人', CINNABAR, 'NSBK', 256, 6)});
      continueRender(handle);
    })();
  }, [handle]);
  return (
    <AbsoluteFill style={{background: '#000'}}>
      {tex && <ThreeCanvas width={width} height={height} shadows gl={{antialias: true, preserveDrawingBuffer: true}}
          onCreated={({gl}) => { gl.shadowMap.type = THREE.PCFSoftShadowMap; gl.toneMapping = THREE.ACESFilmicToneMapping; gl.toneMappingExposure = 1.05; }}>
        <Camera u={u} />
        <ambientLight intensity={0.95} color="#f3eadb" />
        {/* 左上主光 → 影落右后方纸面 */}
        <directionalLight position={[-7, 8, 14]} intensity={2.2} color="#fff3dc" castShadow
          shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-camera-left={-14} shadow-camera-right={14} shadow-camera-top={10} shadow-camera-bottom={-8} shadow-radius={10} shadow-bias={-0.0004} />
        <directionalLight position={[8, 2, -4]} intensity={0.5} color="#d8dde6" />
        {/* 纸墙（离秤 2.2 个单位，投影有真实距离感） */}
        <mesh position={[0, 1.5, -3.2]} receiveShadow><planeGeometry args={[40, 22.5]} /><meshStandardMaterial map={tex.paper} roughness={1} /></mesh>
        <mesh position={[0, -2.2, 4]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[40, 13]} /><meshStandardMaterial map={tex.paper} roughness={1} color="#f2ece2" /></mesh>
        <Scale t={t} tex={tex} />
        <Motes t={t} />
        <fog attach="fog" args={['#d9d2c4', 24, 46]} />
      </ThreeCanvas>}
      {/* 光束：左上斜射 */}
      <AbsoluteFill style={{background: `linear-gradient(118deg, rgba(255,246,225,0) 18%, rgba(255,246,225,${0.10 + 0.03 * Math.sin(t * 3)}) 27%, rgba(255,246,225,0) 38%)`, mixBlendMode: 'screen'}} />
      {/* 暗角 */}
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 30% 25%, rgba(0,0,0,0) 45%, rgba(20,16,12,0.35) 100%)'}} />
      {/* 横梁上的句子：DOM 排版，逐字落下 */}
      <AbsoluteFill>
        {SENT.split('').map((ch, i) => {
          const p = clamp01((t - (ONS[i] - 0.2)) / 0.2); if (p <= 0) return null;
          const big = i < 3; const x = big ? 360 + i * 96 : (i < 6 ? 640 + (i - 3) * 86 : 1110 + (i - 6) * 86);
          const y = (big ? 184 : 198) - 40 * (1 - eo(p)); const s = 1 + 0.35 * (1 - eo(p)); const fs = big ? 88 : 60;
          return <div key={i} style={{position: 'absolute', left: x - fs / 2, top: y - fs / 2, width: fs, height: fs, fontFamily: 'NSSB', fontSize: fs, lineHeight: `${fs}px`, textAlign: 'center',
            color: [2, 4, 5].includes(i) ? CINNABAR : '#14110e', opacity: Math.min(1, p * 1.5), transform: `scale(${s})`, filter: `blur(${(1 - eo(p)) * 3}px)`, textShadow: '0 0 1.5px rgba(20,17,14,0.5)'}}>{ch}</div>;
        })}
      </AbsoluteFill>
      {/* 2.39 遮幅 */}
      <div style={{position: 'absolute', left: 0, top: 0, width: '100%', height: 120, background: '#000'}} />
      <div style={{position: 'absolute', left: 0, bottom: 0, width: '100%', height: 120, background: '#000'}} />
    </AbsoluteFill>
  );
};
