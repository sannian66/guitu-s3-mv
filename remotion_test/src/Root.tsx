import React from 'react';
import {Composition} from 'remotion';
import {S06Scale} from './S06Scale';
// D 段 S06_Scale：167.25–168.62s（帧 5018–5058，41 帧）
export const RemotionRoot: React.FC = () => (
  <Composition id="S06" component={S06Scale} durationInFrames={41} fps={30} width={1920} height={1080} />
);
