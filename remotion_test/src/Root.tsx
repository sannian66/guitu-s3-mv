import React from 'react';
import {Composition} from 'remotion';
import {S06Scale} from './S06Scale';
import {S121Layers} from './S121Layers';
export const RemotionRoot: React.FC = () => (<>
  <Composition id="S06" component={S06Scale} durationInFrames={41} fps={30} width={1920} height={1080} />
  {/* S121 原镜 207.3–208.469s = 35 帧；Demo 版 90 帧便于看视差 */}
  <Composition id="S121A" component={S121Layers} durationInFrames={35} fps={30} width={1920} height={1080} defaultProps={{dir: 'layersA', hazeCol: '#efe6d6'}} />
  <Composition id="S121B" component={S121Layers} durationInFrames={35} fps={30} width={1920} height={1080} defaultProps={{dir: 'layersB', hazeCol: '#ffffff'}} />
  <Composition id="S121A-demo" component={S121Layers} durationInFrames={90} fps={30} width={1920} height={1080} defaultProps={{dir: 'layersA', hazeCol: '#efe6d6'}} />
  <Composition id="S121B-demo" component={S121Layers} durationInFrames={90} fps={30} width={1920} height={1080} defaultProps={{dir: 'layersB', hazeCol: '#ffffff'}} />
</>);
