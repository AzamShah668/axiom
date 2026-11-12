import React from 'react';
import {
	AbsoluteFill,
	Img,
	OffthreadVideo,
	continueRender,
	delayRender,
	interpolate,
	random,
	staticFile,
	useCurrentFrame,
} from 'remotion';

// ---------- fonts ----------
const FONTS: [string, string, string][] = [
	['Anton', 'Anton-Regular.ttf', '400'],
	['Cinzel', 'Cinzel-SemiBold.ttf', '600'],
	['Baskerville', 'LibreBaskerville-Regular.ttf', '400'],
	['Baskerville', 'LibreBaskerville-Bold.ttf', '700'],
	['Montserrat', 'Montserrat-Black.ttf', '900'],
	['Montserrat', 'Montserrat-ExtraBold.ttf', '800'],
	['Elite', 'SpecialElite-Regular.ttf', '400'],
];
if (typeof document !== 'undefined') {
	const handle = delayRender('Loading fonts', {timeoutInMilliseconds: 120000, retries: 2});
	Promise.all(
		FONTS.map(([family, file, weight]) =>
			new FontFace(family, `url(${staticFile('fonts/' + file)})`, {weight})
				.load()
				.then((f) => document.fonts.add(f)),
		),
	)
		.then(() => continueRender(handle))
		.catch((e) => {
			console.error(e);
			continueRender(handle);
		});
}

export const RED = '#e3141f';
export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

// ---------- media (footage or still) with grade + camera motion ----------
export type MediaSpec = {src: string; video?: boolean; grade?: string; motion?: string; seed?: number};

const GRADES: Record<string, {filter: string; tint?: string; tintOpacity?: number}> = {
	ink: {filter: 'grayscale(1) contrast(1.5) brightness(0.8)'},
	red: {filter: 'grayscale(1) contrast(1.45) brightness(1)', tint: '#ff1f1f', tintOpacity: 0.88},
	cold: {filter: 'grayscale(0.85) contrast(1.35) brightness(0.8)', tint: '#3d64a8', tintOpacity: 0.5},
	sepia: {filter: 'sepia(0.85) contrast(1.3) brightness(0.8)'},
	gray: {filter: 'grayscale(0.9) contrast(1.35) brightness(0.85)'},
	color: {filter: 'saturate(1.2) contrast(1.25) brightness(0.9)'},
	dim: {filter: 'grayscale(0.6) contrast(1.2) brightness(0.38) blur(1px)'},
};

const motionTransform = (motion: string | undefined, p: number, frame: number, seed: number) => {
	const e = easeOut(p * 0.9 + 0.1 * p * p);
	switch (motion) {
		case 'in':
			return `scale(${1.04 + 0.13 * e})`;
		case 'out':
			return `scale(${1.17 - 0.13 * e})`;
		case 'left':
			return `scale(1.18) translateX(${4 - 8 * e}%)`;
		case 'right':
			return `scale(1.18) translateX(${-4 + 8 * e}%)`;
		case 'up':
			return `scale(1.18) translateY(${4 - 8 * e}%)`;
		case 'down':
			return `scale(1.18) translateY(${-4 + 8 * e}%)`;
		case 'shake': {
			const a = 16 * (1 - 0.5 * p);
			const k = Math.floor(frame / 2);
			return `scale(1.15) translate(${(random(seed + k) - 0.5) * a}px, ${(random(seed + k + 0.37) - 0.5) * a}px) rotate(${(random(seed + k + 0.71) - 0.5) * 1.4}deg)`;
		}
		default:
			return `scale(${1.05 + 0.05 * e})`;
	}
};

export const Media: React.FC<MediaSpec & {dur: number}> = ({src, video, grade = 'ink', motion, seed = 1, dur}) => {
	const frame = useCurrentFrame();
	const p = Math.min(1, frame / Math.max(1, dur));
	const g = GRADES[grade] ?? GRADES.ink;
	const style: React.CSSProperties = {
		width: '100%',
		height: '100%',
		objectFit: 'cover',
		filter: g.filter,
		transform: motionTransform(motion, p, frame, seed),
	};
	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			{video ? <OffthreadVideo src={staticFile(src)} muted style={style} /> : <Img src={staticFile(src)} style={style} />}
			{g.tint ? <AbsoluteFill style={{backgroundColor: g.tint, mixBlendMode: 'multiply', opacity: g.tintOpacity}} /> : null}
			<AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 42%, rgba(0,0,0,0.78) 100%)'}} />
		</AbsoluteFill>
	);
};

// ---------- red laser tunnel background (intro look) ----------
export const Laser: React.FC<{seed?: number}> = ({seed = 0}) => {
	const f = useCurrentFrame();
	const cx = 960;
	const cy = 540;
	const rays = Array.from({length: 18}, (_, i) => {
		const ang = (i / 18) * Math.PI * 2 + 0.17 + seed;
		return (
			<line
				key={i}
				x1={cx}
				y1={cy}
				x2={cx + Math.cos(ang) * 2300}
				y2={cy + Math.sin(ang) * 2300}
				stroke="#ff1414"
				strokeWidth={1.5 + (i % 3)}
				opacity={0.18 + 0.32 * Math.abs(Math.sin(f / 6 + i * 1.7))}
			/>
		);
	});
	const rects = Array.from({length: 7}, (_, k) => {
		const t = ((k + f / 14) % 7) / 7;
		const s = Math.pow(t, 2.2) * 1.7 + 0.04;
		return (
			<rect
				key={k}
				x={cx - 960 * s}
				y={cy - 540 * s}
				width={1920 * s}
				height={1080 * s}
				fill="none"
				stroke="#ff1414"
				strokeWidth={1 + 3 * t}
				opacity={0.1 + 0.55 * t}
			/>
		);
	});
	return (
		<AbsoluteFill style={{background: 'radial-gradient(circle at 50% 50%, #2b0303 0%, #0a0000 55%, #000 100%)'}}>
			<svg width={1920} height={1080} style={{filter: 'drop-shadow(0 0 7px #ff0000)'}}>
				{rays}
				{rects}
			</svg>
		</AbsoluteFill>
	);
};

export type BgSpec = 'laser' | MediaSpec | null | undefined;
export const Background: React.FC<{bg: BgSpec; dur: number}> = ({bg, dur}) => {
	if (bg === 'laser') return <Laser />;
	if (bg && typeof bg === 'object') return <Media {...bg} grade="dim" dur={dur} motion={bg.motion ?? 'in'} />;
	return <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 55%, #1c0505 0%, #050000 60%, #000 100%)'}} />;
};

// ---------- kinetic title (red word that slides up, fills pale→red, glitches) ----------
export const Word: React.FC<{big: string; small?: string; color?: string; bg?: BgSpec; dur: number; seed?: number}> = ({
	big,
	small,
	color = 'red',
	bg,
	dur,
	seed = 3,
}) => {
	const f = useCurrentFrame();
	const enter = easeOut(f / 7);
	const y = interpolate(enter, [0, 1], [150, 0]);
	const blur = interpolate(f, [0, 6], [12, 0], clamp);
	const fill = interpolate(f, [3, 11], [0, 1], clamp);
	const base =
		color === 'white'
			? '#f3f3f3'
			: `rgb(${Math.round(255 - 30 * fill)}, ${Math.round(205 - 185 * fill)}, ${Math.round(210 - 178 * fill)})`;
	const chars = big.split('');
	const glitchOn = [4, 11, 19, 31, 44].includes(f);
	const gi = glitchOn ? Math.floor(random(seed + f) * chars.length) : -1;
	const fontSize = Math.min(260, 1700 / Math.max(3.2, chars.length * 0.5));
	const shakeX = f < 4 ? (random(seed + f) - 0.5) * 18 : 0;
	return (
		<AbsoluteFill>
			<Background bg={bg} dur={dur} />
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column'}}>
				{small ? (
					<div
						style={{
							fontFamily: 'Cinzel',
							fontSize: 40,
							letterSpacing: '0.55em',
							textTransform: 'uppercase',
							color: '#e8e2e2',
							marginBottom: 6,
							opacity: interpolate(f, [2, 8], [0, 1], clamp),
							textShadow: '0 2px 12px rgba(0,0,0,0.9)',
						}}
					>
						{small}
					</div>
				) : null}
				<div
					style={{
						fontFamily: 'Anton',
						fontSize,
						lineHeight: 1,
						letterSpacing: '0.02em',
						transform: `translate(${shakeX}px, ${y}px)`,
						filter: `blur(${blur}px)`,
						textShadow: `-5px 0 rgba(0,220,255,0.35), 5px 0 rgba(255,0,40,0.45), 0 10px 40px rgba(0,0,0,0.9)`,
						whiteSpace: 'nowrap',
					}}
				>
					{chars.map((c, i) => (
						<span key={i} style={{color: i === gi ? '#ffffff' : base}}>
							{c}
						</span>
					))}
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ---------- typewriter text ----------
export const Typewriter: React.FC<{text: string; sub?: string; bg?: BgSpec; dur: number}> = ({text, sub, bg, dur}) => {
	const f = useCurrentFrame();
	const cps = Math.max(22, text.length / 0.85);
	const n = Math.min(text.length, Math.floor((f / 30) * cps));
	const typed = n >= text.length;
	const doneAt = Math.ceil((text.length / cps) * 30);
	const cursorOn = !typed || Math.floor(f / 8) % 2 === 0;
	const size = text.length > 34 ? 64 : text.length > 22 ? 80 : 104;
	return (
		<AbsoluteFill>
			<Background bg={bg} dur={dur} />
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column', padding: '0 180px'}}>
				<div
					style={{
						fontFamily: 'Elite',
						fontSize: size,
						lineHeight: 1.2,
						color: '#f5efe3',
						textAlign: 'center',
						textShadow: '0 3px 18px rgba(0,0,0,0.95)',
					}}
				>
					{text.slice(0, n)}
					<span style={{opacity: cursorOn ? 1 : 0, color: RED}}>▌</span>
				</div>
				{sub ? (
					<div
						style={{
							fontFamily: 'Cinzel',
							fontSize: 44,
							letterSpacing: '0.5em',
							color: RED,
							marginTop: 26,
							opacity: interpolate(f, [doneAt, doneAt + 6], [0, 1], clamp),
							textShadow: '0 2px 14px rgba(0,0,0,0.9)',
						}}
					>
						{sub}
					</div>
				) : null}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ---------- game-select carousel (◀ small / BIG ▶) ----------
const Arrow: React.FC<{dir: 1 | -1}> = ({dir}) => (
	<svg width={44} height={54} viewBox="0 0 44 54" style={{transform: `scaleX(${dir})`, filter: 'drop-shadow(0 0 8px rgba(255,255,255,0.4))'}}>
		<polygon points="4,4 40,27 4,50" fill="#e9e4e4" />
	</svg>
);

export const Carousel: React.FC<{big: string; small?: string; bg?: BgSpec; dur: number}> = ({big, small, bg, dur}) => {
	const f = useCurrentFrame();
	const slide = easeOut(f / 8);
	const x = interpolate(slide, [0, 1], [1100, 0]);
	const fill = interpolate(f, [8, 16], [0, 1], clamp);
	const col = `rgb(${Math.round(255 - 30 * fill)}, ${Math.round(205 - 185 * fill)}, ${Math.round(210 - 178 * fill)})`;
	return (
		<AbsoluteFill>
			<Background bg={bg} dur={dur} />
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `translateX(${x}px)`}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 70}}>
					<Arrow dir={-1} />
					<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
						{small ? (
							<div style={{fontFamily: 'Cinzel', fontSize: 46, letterSpacing: '0.6em', color: '#efe8e8', textShadow: '0 2px 10px #000'}}>
								{small}
							</div>
						) : null}
						<div
							style={{
								fontFamily: 'Montserrat',
								fontWeight: 900,
								fontSize: 190,
								lineHeight: 1,
								color: col,
								textShadow: '-4px 0 rgba(0,220,255,0.3), 4px 0 rgba(255,0,40,0.4), 0 10px 30px rgba(0,0,0,0.9)',
							}}
						>
							{big}
						</div>
					</div>
					<Arrow dir={1} />
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ---------- chapter card ----------
const ICONS: Record<string, React.ReactNode> = {
	mask: <path d="M10 18 Q30 8 50 18 Q48 44 30 52 Q12 44 10 18 Z M20 26 l8 3 M32 29 l8 -3" stroke={RED} strokeWidth={3} fill="none" />,
	stairs: <path d="M6 52 H18 V42 H30 V32 H42 V22 H54 V12" stroke={RED} strokeWidth={4} fill="none" />,
	ghost: <path d="M14 52 V28 Q14 10 30 10 Q46 10 46 28 V52 L40 46 L35 52 L30 46 L25 52 L20 46 Z M24 26 h2 M34 26 h2" stroke={RED} strokeWidth={3} fill="none" />,
	question: <path d="M20 22 Q20 10 31 10 Q42 10 42 21 Q42 29 31 33 V40 M31 47 v4" stroke={RED} strokeWidth={4} fill="none" />,
	bolt: <path d="M34 6 L16 34 H30 L24 56 L46 24 H32 Z" stroke={RED} strokeWidth={3} fill="none" />,
	eye: <path d="M6 30 Q30 8 54 30 Q30 52 6 30 Z M30 22 a8 8 0 1 0 0.1 0" stroke={RED} strokeWidth={3} fill="none" />,
};

export const ChapterCard: React.FC<{label: string; num?: string; title: string; icon?: string; dur: number}> = ({
	label,
	num,
	title,
	icon = 'eye',
	dur,
}) => {
	const f = useCurrentFrame();
	const flick = f < 7 ? (random(f + 11) > 0.45 ? 1 : 0.2) : 1;
	const s = 1 + 0.045 * (f / Math.max(1, dur));
	const head = num ? `${label} - ${num}` : label;
	const titleSize = title.length > 26 ? 44 : 54;
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<AbsoluteFill
				style={{
					background:
						'radial-gradient(ellipse at 30% 70%, rgba(120,0,0,0.35) 0%, rgba(0,0,0,0) 45%), radial-gradient(ellipse at 75% 30%, rgba(90,0,0,0.3) 0%, rgba(0,0,0,0) 40%), radial-gradient(circle at 50% 50%, #120202 0%, #000 75%)',
				}}
			/>
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column', transform: `scale(${s})`, opacity: flick}}>
				<svg width={150} height={130} viewBox="0 0 150 130" style={{opacity: 0.4, marginBottom: 6}}>
					<polygon points="75,8 142,122 8,122" fill="none" stroke={RED} strokeWidth={5} />
					<path d="M44 86 Q75 56 106 86 Q75 112 44 86 Z" fill="none" stroke={RED} strokeWidth={4} />
					<circle cx={75} cy={86} r={9} fill={RED} />
				</svg>
				<div
					style={{
						fontFamily: 'Montserrat',
						fontWeight: 800,
						fontSize: 132,
						lineHeight: 1.05,
						background: 'linear-gradient(180deg, #ff5a5a 0%, #e3141f 45%, #8e0009 100%)',
						WebkitBackgroundClip: 'text',
						color: 'transparent',
						filter: 'drop-shadow(0 6px 24px rgba(255,0,0,0.35))',
					}}
				>
					{head}
				</div>
				<div
					style={{
						fontFamily: 'Cinzel',
						fontSize: titleSize,
						letterSpacing: '0.42em',
						color: '#d8d3d3',
						marginTop: 10,
						maxWidth: 1700,
						textAlign: 'center',
						lineHeight: 1.35,
						opacity: interpolate(f, [6, 14], [0, 1], clamp),
					}}
				>
					{title}
				</div>
				<svg width={64} height={64} viewBox="0 0 60 60" style={{marginTop: 26, opacity: interpolate(f, [10, 18], [0, 1], clamp)}}>
					{ICONS[icon] ?? ICONS.eye}
				</svg>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ---------- captions (centered serif, 2-4 words, instant switch like the reference) ----------
export const Caption: React.FC<{text: string; low?: boolean}> = ({text, low}) => (
	<AbsoluteFill style={{justifyContent: low ? 'flex-end' : 'center', alignItems: 'center', paddingBottom: low ? 70 : 0}}>
		<div
			style={{
				fontFamily: 'Baskerville',
				fontSize: 66,
				color: '#ffffff',
				textAlign: 'center',
				maxWidth: 1500,
				lineHeight: 1.2,
				textShadow: '0 0 3px rgba(0,0,0,0.95), 0 3px 14px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.6)',
			}}
		>
			{text}
		</div>
	</AbsoluteFill>
);
