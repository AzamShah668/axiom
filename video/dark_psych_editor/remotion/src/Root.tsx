import React from 'react';
import {Composition} from 'remotion';
import {Main} from './Main';
import edit from './edit.json';

export const Root: React.FC = () => (
	<Composition id="Milgram" component={Main} durationInFrames={edit.durationInFrames} fps={30} width={1920} height={1080} />
);
