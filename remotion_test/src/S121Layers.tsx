import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';
import {useThree} from '@react-three/fiber';

// S121：分层生图摆进 3D 空间，真透视视差运镜。画面全部来自生图，three.js 只管机位与层深。
const FILES = ['L1_sky.png', 'L2_clouds_cut.png', 'L3_hero_cut.png', 'L4_fg_cut.png'];
const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const eio = (x: number) => { const u = clamp01(x); return u * u * (3 - 2 * u); };
function noise(t: number, s: number) { return Math.sin(t * 1.7 + s) * 0.5 + Math.sin(t * 3.1 + s * 2.3) * 0.3 + Math.sin(t * 5.3 + s * 0.7) * 0.2; }

const vert = `uniform float uT; uniform float uAmp; uniform float uFreq; varying vec2 vUv;
void main(){ vUv=uv; vec3 p=position; float w=uv.x; p.y+=sin(uv.x*uFreq - uT*4.0)*uAmp*w; p.z+=cos(uv.x*uFreq*0.7 - uT*3.0)*uAmp*0.6*w;
 gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.0);} `;
const frag = `uniform sampler2D map; uniform float uHaze; uniform vec3 uHazeCol; uniform float uOp; varying vec2 vUv;
void main(){ vec4 c=texture2D(map,vUv); if(c.a<0.02) discard; vec3 col=mix(c.rgb,uHazeCol,uHaze); gl_FragColor=vec4(col,c.a*uOp);
 #include <colorspace_fragment>
}`;

const Layer: React.FC<{tex: THREE.Texture; w: number; pos: [number, number, number]; t: number; amp?: number; freq?: number; haze?: number; hazeCol?: string; seg?: number}> = ({tex, w, pos, t, amp = 0, freq = 6, haze = 0, hazeCol = '#efe6d6', seg = 1}) => {
  const img = tex.image as HTMLImageElement; const h = w * img.height / img.width;
  const mat = useMemo(() => new THREE.ShaderMaterial({vertexShader: vert, fragmentShader: frag, transparent: true, depthWrite: false,
    uniforms: {map: {value: tex}, uT: {value: 0}, uAmp: {value: amp}, uFreq: {value: freq}, uHaze: {value: haze}, uHazeCol: {value: new THREE.Color(hazeCol)}, uOp: {value: 1}}}), [tex, amp, freq, haze, hazeCol]);
  mat.uniforms.uT.value = t;
  return <mesh position={pos} material={mat}><planeGeometry args={[w, h, seg, seg > 1 ? 4 : 1]} /></mesh>;
};

const Cam: React.FC<{u: number; t: number; shake: number}> = ({u, t, shake}) => {
  const {camera} = useThree(); const e = eio(u);
  camera.position.set(-1.1 + 2.0 * e + noise(t, 1) * 0.05 * shake, 0.25 - 0.35 * e + noise(t, 4) * 0.04 * shake, 10.5 - 1.8 * e);
  camera.lookAt(0.6 - 0.4 * e, 0.1, -6);
  camera.rotateZ(noise(t, 7) * 0.004 * shake);
  (camera as THREE.PerspectiveCamera).fov = 30; camera.updateProjectionMatrix();
  return null;
};

export const S121Layers: React.FC<{dir: string; hazeCol: string}> = ({dir, hazeCol}) => {
  const frame = useCurrentFrame(); const {width, height, durationInFrames} = useVideoConfig();
  const t = frame / 30; const u = frame / (durationInFrames - 1);
  const [handle] = useState(() => delayRender('tex'));
  const [tex, setTex] = useState<THREE.Texture[] | null>(null);
  useEffect(() => { (async () => {
    const L = new THREE.TextureLoader();
    const ts = await Promise.all(FILES.map((f) => L.loadAsync(staticFile(`${dir}/${f}`))));
    ts.forEach((x) => { x.colorSpace = THREE.SRGBColorSpace; x.anisotropy = 8; x.generateMipmaps = true; x.minFilter = THREE.LinearMipmapLinearFilter; });
    setTex(ts); continueRender(handle);
  })(); }, [handle, dir]);
  return (
    <AbsoluteFill style={{background: '#000'}}>
      {tex && <ThreeCanvas width={width} height={height} gl={{antialias: true, preserveDrawingBuffer: true}} onCreated={({gl}) => { gl.toneMapping = THREE.NoToneMapping; }}>
        <Cam u={u} t={t} shake={1} />
        <Layer tex={tex[0]} w={70} pos={[0.5, -4.5, -32]} t={t} />
        <Layer tex={tex[1]} w={30} pos={[-2.5 + t * 0.35, -4.4, -13]} t={t} amp={0.08} freq={3} haze={0.18} hazeCol={hazeCol} seg={24} />
        <Layer tex={tex[2]} w={5.2} pos={[1.9, -1.1, 0]} t={t} />
        <Layer tex={tex[3]} w={6.4} pos={[-1.6 + t * 0.5, -2.05, 4.2]} t={t} amp={0.12} freq={7} seg={48} />
      </ThreeCanvas>}
      <div style={{position: 'absolute', left: 0, top: 0, width: '100%', height: 120, background: '#000'}} />
      <div style={{position: 'absolute', left: 0, bottom: 0, width: '100%', height: 120, background: '#000'}} />
    </AbsoluteFill>
  );
};
