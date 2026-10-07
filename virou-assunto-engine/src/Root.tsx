import React from 'react';
import {Composition} from 'remotion';
import {VirouAssuntoReel} from './Reel';

export const Root: React.FC = () => {
  return (
    <Composition
      id="VirouAssunto"
      component={VirouAssuntoReel}
      durationInFrames={960}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
