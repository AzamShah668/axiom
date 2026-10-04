import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {Caption, Carousel, ChapterCard, Media, Typewriter, Word} from './common';
import {Counter, PillLabel, Prediction, Puppet, ShockPanel, Split, Staircase, Variations, VoltMeter, VoltSteps} from './gfx';
import edit from './edit.json';

type Scene = {from: number; dur: number; kind: string; [k: string]: any};
type Cap = {from: number; dur: number; text: string; low?: boolean};

const renderScene = (s: Scene) => {
	const dur = s.dur;
	switch (s.kind) {
		case 'media':
			return <Media src={s.src} video={s.video} grade={s.grade} motion={s.motion} seed={s.from} dur={dur} />;
		case 'word':
			return <Word big={s.big} small={s.small} color={s.color} bg={s.bg} dur={dur} seed={s.from} />;
		case 'type':
			return <Typewriter text={s.text} sub={s.sub} bg={s.bg} dur={dur} />;
		case 'carousel':
			return <Carousel big={s.big} small={s.small} bg={s.bg} dur={dur} />;
		case 'card':
			return <ChapterCard label={s.label} num={s.num} title={s.title} icon={s.icon} dur={dur} />;
		case 'flash':
			return <AbsoluteFill style={{backgroundColor: '#bdbdbd'}} />;
		case 'black':
			return <AbsoluteFill style={{backgroundColor: '#000'}} />;
		case 'gfx':
			switch (s.name) {
				case 'shockpanel':
					return <ShockPanel mode={s.mode} group={s.group} dur={dur} />;
				case 'voltmeter':
					return <VoltMeter value={s.value} dur={dur} />;
				case 'counter':
					return <Counter text={s.text} sub={s.sub} color={s.color} dur={dur} />;
				case 'voltsteps':
					return <VoltSteps dur={dur} />;
				case 'staircase':
					return <Staircase marksF={s.marksF} all={s.all} stopNext={s.stopNext} breakAtF={s.breakAtF} named={s.named} dur={dur} />;
				case 'pilllabel':
					return <PillLabel mode={s.mode} dur={dur} />;
				case 'split':
					return <Split left={s.left} right={s.right} />;
				case 'prediction':
					return <Prediction actualAtF={s.actualAtF} />;
				case 'variations':
					return <Variations step={s.step} />;
				case 'puppet':
					return <Puppet mode={s.mode} dur={dur} />;
				default:
					return <AbsoluteFill style={{backgroundColor: '#300'}} />;
			}
		default:
			return <AbsoluteFill style={{backgroundColor: '#000'}} />;
	}
};

export const Main: React.FC<{start?: number; end?: number}> = () => {
	const scenes = edit.scenes as Scene[];
	const caps = edit.captions as Cap[];
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			{scenes.map((s, i) => (
				<Sequence key={i} from={s.from} durationInFrames={s.dur} name={`${s.kind}:${s.name ?? s.big ?? s.text ?? s.src ?? ''}`.slice(0, 40)}>
					{renderScene(s)}
				</Sequence>
			))}
			{caps.map((c, i) => (
				<Sequence key={`c${i}`} from={c.from} durationInFrames={c.dur} name={`cap:${c.text}`}>
					<Caption text={c.text} low={c.low} />
				</Sequence>
			))}
		</AbsoluteFill>
	);
};
