import React from 'react';
import {AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {RED, clamp, easeOut} from './common';

const DarkBg: React.FC<{glow?: number}> = ({glow = 0.25}) => (
	<AbsoluteFill
		style={{background: `radial-gradient(circle at 50% 55%, rgba(110,0,0,${glow}) 0%, #050000 58%, #000 100%)`}}
	/>
);

// =====================================================================
// Shock generator (Milgram's "Type ZLB"), 30 switches, 15-450 V
// =====================================================================
const GROUPS = [
	'SLIGHT SHOCK',
	'MODERATE SHOCK',
	'STRONG SHOCK',
	'VERY STRONG SHOCK',
	'INTENSE SHOCK',
	'EXTREME INTENSITY SHOCK',
	'DANGER: SEVERE SHOCK',
	'XXX',
];
const SX = (i: number) => 148 + 56 * i; // screen x of switch i
const LIGHT_Y = 510;

export const ShockPanel: React.FC<{mode: string; group?: number; dur: number}> = ({mode, group = 0, dur}) => {
	const f = useCurrentFrame();
	const p = Math.min(1, f / Math.max(1, dur));
	let s = 1;
	let fx = 960;
	let fy = 540;
	let lit = (i: number) => 0; // 0 off, 0.4 dim, 1 on
	let hl = -1; // highlighted switch
	let hlGroup = -1;
	let flash = 0;
	switch (mode) {
		case 'reveal':
			s = interpolate(p, [0, 1], [0.92, 1.0]);
			lit = (i) => (i === 29 ? 0.25 + 0.25 * Math.sin(f / 3) : 0);
			break;
		case 'cascade': {
			const n = Math.floor(easeOut(Math.min(1, p / 0.75)) * 30);
			s = interpolate(p, [0, 1], [1, 1.04]);
			lit = (i) => (i < n ? 1 : 0);
			break;
		}
		case 'cascadeAll': {
			const n = Math.floor(Math.min(1, p / 0.85) * 30);
			s = interpolate(p, [0, 1], [1, 1.1]);
			fx = interpolate(p, [0, 1], [960, 1150]);
			lit = (i) => (i < n ? 1 : 0);
			flash = interpolate(p, [0.85, 0.9, 1], [0, 0.85, 0], clamp);
			break;
		}
		case 'sweep': {
			s = 1.3;
			const k = p * 29;
			fx = interpolate(p, [0, 1], [SX(3), SX(26)]);
			fy = 520;
			lit = (i) => (i <= k ? 1 : 0.2);
			hl = Math.floor(k);
			break;
		}
		case 'press3':
			s = 1.9;
			fx = SX(2);
			fy = 520;
			lit = (i) => (i === 0 && p > 0.12) || (i === 1 && p > 0.42) || (i === 2 && p > 0.72) ? 1 : 0;
			break;
		case 'zoomLast': {
			const e = easeOut(p);
			s = interpolate(e, [0, 1], [1, 2.8]);
			fx = interpolate(e, [0, 1], [960, SX(28.5)]);
			fy = interpolate(e, [0, 1], [540, 480]);
			lit = (i) => (i >= 28 ? 0.55 + 0.45 * Math.abs(Math.sin(f / 2.5)) : 0.35);
			hlGroup = 7;
			break;
		}
		case 'label': {
			const first = group * 4;
			const last = group === 7 ? 29 : first + 3;
			s = interpolate(p, [0, 1], [1.6, 2.0]);
			fx = (SX(first) + SX(last)) / 2;
			fy = 470;
			lit = (i) => (i >= first && i <= last ? 1 : 0.15);
			hlGroup = group;
			break;
		}
		case 'stepUp':
			s = 1.8;
			fx = SX(14);
			fy = 520;
			lit = (i) => (i < 14 ? 1 : i === 14 && p > 0.25 ? 1 : 0);
			flash = interpolate(p, [0.25, 0.3, 0.45], [0, 0.35, 0], clamp);
			hl = p > 0.25 ? 14 : -1;
			break;
		default:
			break;
	}
	const fadeIn = interpolate(f, [0, 5], [0, 1], clamp);
	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			<DarkBg glow={0.3} />
			<AbsoluteFill style={{transformOrigin: '0 0', transform: `translate(960px,540px) scale(${s}) translate(${-fx}px,${-fy}px)`, opacity: fadeIn}}>
				{/* panel body */}
				<div
					style={{
						position: 'absolute',
						left: 60,
						top: 260,
						width: 1800,
						height: 560,
						borderRadius: 14,
						background: 'linear-gradient(180deg, #4a4e52 0%, #2b2e31 40%, #1a1c1e 100%)',
						boxShadow: 'inset 0 2px 0 rgba(255,255,255,0.18), inset 0 -3px 0 rgba(0,0,0,0.6), 0 30px 80px rgba(0,0,0,0.8)',
						border: '3px solid #111',
					}}
				/>
				<div style={{position: 'absolute', left: 60, top: 282, width: 1800, textAlign: 'center', fontFamily: 'Montserrat', fontWeight: 800, fontSize: 34, color: '#d9d4c7', letterSpacing: '0.12em'}}>
					SHOCK GENERATOR, TYPE ZLB
				</div>
				<div style={{position: 'absolute', left: 60, top: 326, width: 1800, textAlign: 'center', fontFamily: 'Montserrat', fontWeight: 800, fontSize: 15, color: '#a7a297', letterSpacing: '0.18em'}}>
					DYSON INSTRUMENT COMPANY · WALTHAM, MASS. · OUTPUT 15 VOLTS – 450 VOLTS
				</div>
				{/* group labels */}
				{GROUPS.map((g, gi) => {
					const first = gi * 4;
					const n = gi === 7 ? 2 : 4;
					const on = hlGroup === gi;
					return (
						<div
							key={g}
							style={{
								position: 'absolute',
								left: SX(first) - 24,
								top: 382,
								width: n * 56 - 8,
								height: 58,
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
								textAlign: 'center',
								fontFamily: 'Montserrat',
								fontWeight: 800,
								fontSize: gi === 7 ? 24 : 13,
								lineHeight: 1.15,
								color: on ? '#fff' : '#cfc9bb',
								background: on ? 'rgba(227,20,31,0.85)' : 'rgba(0,0,0,0.35)',
								border: `2px solid ${on ? '#ff4d4d' : '#55585b'}`,
								boxShadow: on ? '0 0 30px rgba(255,0,0,0.8)' : 'none',
								borderRadius: 4,
							}}
						>
							{g}
						</div>
					);
				})}
				{/* switches */}
				{Array.from({length: 30}, (_, i) => {
					const l = lit(i);
					const x = SX(i);
					const isHl = hl === i;
					return (
						<React.Fragment key={i}>
							<div
								style={{
									position: 'absolute',
									left: x - 13,
									top: LIGHT_Y - 13,
									width: 26,
									height: 26,
									borderRadius: 13,
									background: l > 0 ? `rgba(255,${Math.round(40 + 60 * l)},${Math.round(40 * l)},${0.35 + 0.65 * l})` : '#3a0b0b',
									boxShadow: l > 0 ? `0 0 ${10 + 26 * l}px rgba(255,30,30,${0.9 * l})` : 'inset 0 2px 4px rgba(0,0,0,0.8)',
									border: '2px solid #151515',
								}}
							/>
							<div style={{position: 'absolute', left: x - 9, top: 548, width: 18, height: 86, borderRadius: 4, background: '#0c0c0c', boxShadow: 'inset 0 2px 6px rgba(0,0,0,0.9)'}} />
							<div
								style={{
									position: 'absolute',
									left: x - 15,
									top: l >= 1 ? 592 : 552,
									width: 30,
									height: 38,
									borderRadius: 6,
									background: isHl ? 'linear-gradient(180deg,#ff6a6a,#a30010)' : 'linear-gradient(180deg,#e8e4da,#9c978c)',
									boxShadow: '0 4px 6px rgba(0,0,0,0.7)',
								}}
							/>
							<div
								style={{
									position: 'absolute',
									left: x - 28,
									top: 652,
									width: 56,
									textAlign: 'center',
									fontFamily: 'Montserrat',
									fontWeight: 800,
									fontSize: 17,
									color: isHl ? '#ff4d4d' : '#d6d0c2',
								}}
							>
								{15 * (i + 1)}
							</div>
						</React.Fragment>
					);
				})}
				<div style={{position: 'absolute', left: 60, top: 690, width: 1800, textAlign: 'center', fontFamily: 'Montserrat', fontWeight: 800, fontSize: 16, color: '#8e897e', letterSpacing: '0.4em'}}>
					VOLTS
				</div>
			</AbsoluteFill>
			<AbsoluteFill style={{backgroundColor: '#fff', opacity: flash}} />
			<AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.75) 100%)'}} />
		</AbsoluteFill>
	);
};

// =====================================================================
// Voltage meter
// =====================================================================
export const VoltMeter: React.FC<{value: number; dur: number}> = ({value, dur}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const sp = spring({frame: f, fps, config: {damping: 7, stiffness: 120, mass: 0.7}});
	const jitter = f > 18 ? (random(f) - 0.5) * 6 : 0;
	const v = Math.max(0, value * sp + jitter);
	const cx = 960;
	const cy = 700;
	const r = 440;
	const ang = (vv: number) => Math.PI + (Math.min(450, vv) / 450) * Math.PI;
	const pt = (vv: number, rr: number) => [cx + rr * Math.cos(ang(vv)), cy + rr * Math.sin(ang(vv))];
	const ticks = Array.from({length: 31}, (_, k) => {
		const vv = k * 15;
		const [x1, y1] = pt(vv, r);
		const [x2, y2] = pt(vv, r - (k % 5 === 0 ? 46 : 24));
		return <line key={k} x1={x1} y1={y1} x2={x2} y2={y2} stroke={vv >= 300 ? RED : '#d8d2c4'} strokeWidth={k % 5 === 0 ? 5 : 3} />;
	});
	const labels = [0, 75, 150, 225, 300, 375, 450].map((vv) => {
		const [x, y] = pt(vv, r - 92);
		return (
			<text key={vv} x={x} y={y + 10} textAnchor="middle" fontFamily="Montserrat" fontWeight={800} fontSize={30} fill={vv >= 300 ? RED : '#d8d2c4'}>
				{vv}
			</text>
		);
	});
	const arc = (a0: number, a1: number, col: string) => {
		const [x0, y0] = pt(a0, r + 18);
		const [x1, y1] = pt(a1, r + 18);
		return <path d={`M ${x0} ${y0} A ${r + 18} ${r + 18} 0 0 1 ${x1} ${y1}`} stroke={col} strokeWidth={14} fill="none" />;
	};
	const [nx, ny] = pt(v, r - 30);
	const flick = 0.82 + 0.18 * random(f + 7);
	const shake = f < 12 && value >= 300 ? (random(f + 3) - 0.5) * 14 : 0;
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<DarkBg glow={0.12 + 0.5 * (value / 450)} />
			<svg width={1920} height={1080} style={{transform: `translateX(${shake}px)`}}>
				{arc(0, 150, '#bdb7aa')}
				{arc(150, 300, '#d99a1e')}
				{arc(300, 450, RED)}
				{ticks}
				{labels}
				<line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#fff" strokeWidth={9} strokeLinecap="round" style={{filter: 'drop-shadow(0 0 10px rgba(255,60,60,0.9))'}} />
				<circle cx={cx} cy={cy} r={26} fill="#1b1b1b" stroke="#d8d2c4" strokeWidth={5} />
			</svg>
			<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 90}}>
				<div style={{fontFamily: 'Anton', fontSize: 190, color: RED, opacity: flick, lineHeight: 1, textShadow: '0 0 40px rgba(255,0,0,0.6), -4px 0 rgba(0,220,255,0.3)'}}>
					{Math.round(Math.min(value, Math.max(0, v)))} VOLTS
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// =====================================================================
// Counter ("26 / 40", "65%", "40")
// =====================================================================
export const Counter: React.FC<{text: string; sub?: string; color?: string; dur: number}> = ({text, sub, color}) => {
	const f = useCurrentFrame();
	const [leftRaw, rightRaw] = text.split('/').map((t) => t.trim());
	const num = parseFloat(leftRaw);
	const t = easeOut(f / 16);
	const left = !Number.isNaN(num) && /^\d+$/.test(leftRaw) ? String(Math.round(num * t)) : leftRaw;
	const s = interpolate(f, [0, 8], [1.18, 1], clamp);
	const blur = interpolate(f, [0, 6], [8, 0], clamp);
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<DarkBg glow={0.3} />
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column', transform: `scale(${s})`, filter: `blur(${blur}px)`}}>
				<div style={{display: 'flex', alignItems: 'baseline', gap: 30}}>
					<span style={{fontFamily: 'Anton', fontSize: rightRaw ? 330 : 380, color: RED, lineHeight: 1, textShadow: '0 0 50px rgba(255,0,0,0.45), -5px 0 rgba(0,220,255,0.3)'}}>{left}</span>
					{rightRaw ? (
						<span style={{fontFamily: 'Anton', fontSize: 200, color: color === 'red' ? RED : '#efefef', lineHeight: 1}}>/ {rightRaw}</span>
					) : null}
				</div>
				{sub ? (
					<div style={{fontFamily: 'Cinzel', fontSize: 50, letterSpacing: '0.55em', color: '#e6e0e0', marginTop: 10, opacity: interpolate(f, [6, 12], [0, 1], clamp)}}>{sub}</div>
				) : null}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// =====================================================================
// 15-volt steps ticker
// =====================================================================
export const VoltSteps: React.FC<{dur: number}> = ({dur}) => {
	const f = useCurrentFrame();
	const p = Math.min(1, f / Math.max(1, dur));
	const k = p * 9; // how many steps advanced
	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			<DarkBg glow={0.25} />
			<div style={{position: 'absolute', top: 230, width: 1920, textAlign: 'center', fontFamily: 'Cinzel', fontSize: 48, letterSpacing: '0.55em', color: '#ddd'}}>15-VOLT STEPS</div>
			<div style={{position: 'absolute', top: 430, left: 960 - k * 300, display: 'flex'}}>
				{Array.from({length: 30}, (_, i) => {
					const d = Math.abs(i - k);
					const active = d < 0.5;
					return (
						<div key={i} style={{width: 300, marginLeft: -150 + (i === 0 ? 0 : 150), textAlign: 'center', fontFamily: 'Anton', fontSize: active ? 170 : 110, color: active ? RED : i < k ? '#7a1b1b' : '#555', lineHeight: '200px'}}>
							{15 * (i + 1)}
						</div>
					);
				})}
			</div>
			<div style={{position: 'absolute', top: 680, width: 1920, textAlign: 'center', fontFamily: 'Montserrat', fontWeight: 800, fontSize: 30, letterSpacing: '0.5em', color: '#8a8a8a'}}>VOLTS</div>
		</AbsoluteFill>
	);
};

// =====================================================================
// Staircase of voltages
// =====================================================================
export const Staircase: React.FC<{marksF?: number[]; all?: boolean; stopNext?: boolean; breakAtF?: number; named?: boolean; dur: number}> = ({
	marksF = [],
	all,
	stopNext,
	breakAtF,
	named,
	dur,
}) => {
	const f = useCurrentFrame();
	const p = Math.min(1, f / Math.max(1, dur));
	const N = all ? 30 : 8;
	const W = all ? 56 : 190;
	const H = all ? 25 : 82;
	const x0 = all ? 120 : 200;
	const y0 = all ? 980 : 940;
	let litN = 0;
	if (all) litN = Math.floor(easeOut(Math.min(1, p / 0.7)) * 30);
	else if (marksF.length) litN = marksF.filter((m) => f >= m).length;
	else if (stopNext) litN = 4;
	else if (breakAtF !== undefined) litN = 8;
	else litN = 8;
	const broke = breakAtF !== undefined && f >= breakAtF;
	const fall = broke ? easeOut((f - breakAtF) / 14) : 0;
	const shake = broke && f - (breakAtF ?? 0) < 8 ? (random(f) - 0.5) * 20 : 0;
	const s = all ? interpolate(p, [0, 1], [1.5, 1], clamp) : 1;
	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			<DarkBg glow={0.25} />
			<svg width={1920} height={1080} style={{transform: `translateX(${shake}px) scale(${s})`, transformOrigin: '20% 90%'}}>
				{Array.from({length: N}, (_, i) => {
					const x = x0 + i * W;
					const y = y0 - (i + 1) * H;
					const on = i < litN;
					const isNext = stopNext && i === litN;
					const dropped = broke && i >= 4;
					const tr = dropped ? `translate(0 ${fall * (300 + 60 * (i - 4))}) rotate(${fall * (8 + 3 * (i - 4))} ${x} ${y})` : '';
					return (
						<g key={i} transform={tr} opacity={dropped ? 1 - fall * 0.6 : 1}>
							<rect x={x} y={y} width={W} height={y0 - y} fill={on ? 'rgba(227,20,31,0.85)' : 'rgba(60,60,60,0.5)'} stroke={on ? '#ff6b6b' : '#777'} strokeWidth={all ? 1 : 3} style={{filter: on ? 'drop-shadow(0 0 12px rgba(255,0,0,0.6))' : undefined}} />
							{!all || i % 5 === 4 || i === 0 ? (
								<text x={x + W / 2} y={y - 14} textAnchor="middle" fontFamily="Anton" fontSize={all ? 26 : 50} fill={on ? '#fff' : '#9a9a9a'}>
									{15 * (i + 1)}
								</text>
							) : null}
							{isNext ? (
								<g>
									<line x1={x + 20} y1={y - 140} x2={x + W - 20} y2={y - 40} stroke={RED} strokeWidth={14} />
									<line x1={x + W - 20} y1={y - 140} x2={x + 20} y2={y - 40} stroke={RED} strokeWidth={14} />
								</g>
							) : null}
						</g>
					);
				})}
			</svg>
			{named ? (
				<AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'center', paddingTop: 120}}>
					<div style={{fontFamily: 'Anton', fontSize: 150, color: RED, opacity: interpolate(f, [4, 10], [0, 1], clamp), textShadow: '0 0 40px rgba(255,0,0,0.5)'}}>THE STAIRCASE</div>
				</AbsoluteFill>
			) : null}
			{stopNext ? (
				<AbsoluteFill style={{justifyContent: 'flex-start', alignItems: 'center', paddingTop: 140}}>
					<div style={{fontFamily: 'Cinzel', fontSize: 56, letterSpacing: '0.5em', color: '#eee', opacity: interpolate(f, [6, 12], [0, 1], clamp)}}>BEFORE THE NEXT STEP</div>
				</AbsoluteFill>
			) : null}
		</AbsoluteFill>
	);
};

// =====================================================================
// Astroten bottle label (Hofling 1966)
// =====================================================================
export const PillLabel: React.FC<{mode: string; dur: number}> = ({mode, dur}) => {
	const f = useCurrentFrame();
	const p = Math.min(1, f / Math.max(1, dur));
	let s = interpolate(p, [0, 1], [1, 1.08]);
	let ty = 0;
	if (mode === 'max') {
		const e = easeOut(p * 1.4);
		s = interpolate(e, [0, 1], [1.05, 1.6]);
		ty = interpolate(e, [0, 1], [0, -120]);
	}
	const circle = mode === 'max' ? interpolate(p, [0.25, 0.6], [1, 0], clamp) : 1;
	const stamp = mode === 'lethal' ? interpolate(f, [5, 9], [0, 1], clamp) : mode === 'max' ? interpolate(p, [0.55, 0.65], [0, 1], clamp) : 0;
	const stampText = mode === 'lethal' ? 'LETHAL DOSE' : 'ORDERED: 20 mg';
	const shake = mode === 'lethal' && f >= 9 && f < 15 ? (random(f) - 0.5) * 16 : 0;
	const line: React.CSSProperties = {fontFamily: 'Elite', color: '#1e1a14', textAlign: 'center'};
	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			<DarkBg glow={0.2} />
			<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `translate(${shake}px, ${ty}px) scale(${s})`}}>
				<div
					style={{
						width: 1080,
						padding: '46px 40px',
						background: 'linear-gradient(170deg, #f1e7cc 0%, #e2d4ad 100%)',
						border: '6px double #3b3326',
						transform: 'rotate(-2deg)',
						boxShadow: '0 40px 90px rgba(0,0,0,0.85)',
						position: 'relative',
					}}
				>
					<div style={{...line, fontSize: 30, letterSpacing: '0.3em'}}>Rx · HOSPITAL PHARMACY</div>
					<div style={{...line, fontSize: 130, fontWeight: 700, letterSpacing: '0.06em', margin: '6px 0'}}>ASTROTEN</div>
					<div style={{...line, fontSize: 52}}>5 mg Capsules</div>
					<div style={{...line, fontSize: 44, marginTop: 18}}>Usual dose: 5 mg</div>
					<div style={{...line, fontSize: 44, position: 'relative'}}>
						Maximum daily dose: 10 mg
						<svg width={760} height={110} style={{position: 'absolute', left: 120, top: -26}}>
							<ellipse cx={380} cy={55} rx={370} ry={48} fill="none" stroke={RED} strokeWidth={7} pathLength={1} strokeDasharray={1} strokeDashoffset={circle} />
						</svg>
					</div>
					<div style={{...line, fontSize: 30, color: '#8e0009', marginTop: 22}}>CAUTION: DO NOT EXCEED STATED DOSE</div>
					{stamp > 0 ? (
						<div
							style={{
								position: 'absolute',
								left: '50%',
								bottom: mode === 'max' ? 150 : 70,
								fontFamily: 'Anton',
								fontSize: mode === 'max' ? 84 : 96,
								whiteSpace: 'nowrap',
								color: RED,
								border: `8px solid ${RED}`,
								padding: '4px 26px',
								transform: `translateX(-50%) rotate(-12deg) scale(${interpolate(stamp, [0, 1], [2.2, 1])})`,
								opacity: stamp * 0.92,
								mixBlendMode: 'multiply',
							}}
						>
							{stampText}
						</div>
					) : null}
				</div>
			</AbsoluteFill>
			<AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.7) 100%)'}} />
		</AbsoluteFill>
	);
};

// =====================================================================
// Two piles: the good ones vs the monsters
// =====================================================================
const Person: React.FC<{c: string}> = ({c}) => (
	<svg width={46} height={70} viewBox="0 0 46 70">
		<circle cx={23} cy={12} r={10} fill={c} />
		<path d="M5 68 V36 Q5 24 23 24 Q41 24 41 36 V68 Z" fill={c} />
	</svg>
);

export const Split: React.FC<{left: string; right: string}> = ({left, right}) => {
	const f = useCurrentFrame();
	const lx = interpolate(easeOut(f / 9), [0, 1], [-960, 0]);
	const rx = interpolate(easeOut(f / 9), [0, 1], [960, 0]);
	const pile = (c: string, start: number) => (
		<div style={{display: 'grid', gridTemplateColumns: 'repeat(10, 52px)', gap: 8, marginTop: 40}}>
			{Array.from({length: 20}, (_, i) => (
				<div key={i} style={{opacity: interpolate(f, [start + i, start + i + 3], [0, 1], clamp)}}>
					<Person c={c} />
				</div>
			))}
		</div>
	);
	return (
		<AbsoluteFill style={{flexDirection: 'row', backgroundColor: '#000'}}>
			<div style={{width: 960, height: 1080, background: '#d6d1c7', transform: `translateX(${lx}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
				<div style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: 84, color: '#111'}}>{left}</div>
				{pile('#333', 6)}
			</div>
			<div style={{width: 960, height: 1080, background: '#6e0008', transform: `translateX(${rx}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
				<div style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: 84, color: '#fff'}}>{right}</div>
				{pile('#ff3b3b', 10)}
			</div>
		</AbsoluteFill>
	);
};

// =====================================================================
// Prediction vs reality bars
// =====================================================================
const Bar: React.FC<{label: string; sub: string; pct: number; val: string; col: string; show: number}> = ({label, sub, pct, val, col, show}) => (
	<div style={{display: 'flex', alignItems: 'center', marginBottom: 70, opacity: show}}>
		<div style={{width: 420, textAlign: 'right', paddingRight: 40}}>
			<div style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: 52, color: '#f0f0f0'}}>{label}</div>
			<div style={{fontFamily: 'Cinzel', fontSize: 26, letterSpacing: '0.3em', color: '#aaa'}}>{sub}</div>
		</div>
		<div style={{width: Math.max(10, 1100 * pct), height: 110, background: col, boxShadow: col === RED ? '0 0 40px rgba(255,0,0,0.5)' : 'none'}} />
		<div style={{fontFamily: 'Anton', fontSize: 110, color: col === RED ? RED : '#f0f0f0', marginLeft: 30}}>{val}</div>
	</div>
);

export const Prediction: React.FC<{actualAtF: number}> = ({actualAtF}) => {
	const f = useCurrentFrame();
	const grow = easeOut((f - actualAtF) / 12);
	const flash = interpolate(f - actualAtF, [0, 2, 8], [0, 0.5, 0], clamp);
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<DarkBg glow={0.2} />
			<div style={{position: 'absolute', top: 150, width: 1920, textAlign: 'center', fontFamily: 'Cinzel', fontSize: 44, letterSpacing: '0.4em', color: '#ddd'}}>WHO WOULD GO TO 450 VOLTS?</div>
			<AbsoluteFill style={{justifyContent: 'center', paddingLeft: 120, paddingTop: 80}}>
				<Bar label="PREDICTED" sub="BY PSYCHIATRISTS" pct={interpolate(f, [0, 10], [0, 0.01], clamp)} val="< 1%" col="#d9d4c7" show={1} />
				<Bar label="ACTUAL" sub="MILGRAM, 1963" pct={f >= actualAtF ? 0.65 * grow : 0} val={f >= actualAtF ? `${Math.round(65 * grow)}%` : ''} col={RED} show={f >= actualAtF ? 1 : 0.25} />
			</AbsoluteFill>
			<AbsoluteFill style={{backgroundColor: '#fff', opacity: flash}} />
		</AbsoluteFill>
	);
};

// =====================================================================
// Variations: same machine, different room
// =====================================================================
const VARS = [
	{label: 'YALE LAB (BASELINE)', val: 65, txt: '65%'},
	{label: 'TWO PEERS REFUSE', val: 10, txt: '10%'},
	{label: 'ORDERS BY PHONE', val: 20.5, txt: '20%'},
	{label: 'BRIDGEPORT OFFICE', val: 47.5, txt: '48%'},
];
export const Variations: React.FC<{step: number}> = ({step}) => {
	const f = useCurrentFrame();
	const t = easeOut(f / 14);
	return (
		<AbsoluteFill style={{backgroundColor: '#000'}}>
			<DarkBg glow={0.2} />
			<div style={{position: 'absolute', top: 120, width: 1920, textAlign: 'center', fontFamily: 'Cinzel', fontSize: 44, letterSpacing: '0.4em', color: '#ddd'}}>SAME MACHINE · DIFFERENT ROOM</div>
			<AbsoluteFill style={{justifyContent: 'center', paddingLeft: 150, paddingTop: 90}}>
				{VARS.slice(0, step + 1).map((v, i) => {
					const active = i === step;
					const val = active && i > 0 ? 65 + (v.val - 65) * t : v.val;
					return (
						<div key={v.label} style={{display: 'flex', alignItems: 'center', marginBottom: 46}}>
							<div style={{width: 560, textAlign: 'right', paddingRight: 40, fontFamily: 'Montserrat', fontWeight: 900, fontSize: 44, color: active ? '#fff' : '#9a9a9a'}}>{v.label}</div>
							<div style={{width: (1000 * val) / 65, height: 84, background: active ? RED : '#4a4a4a', boxShadow: active ? '0 0 30px rgba(255,0,0,0.5)' : 'none'}} />
							<div style={{fontFamily: 'Anton', fontSize: 84, color: active ? RED : '#9a9a9a', marginLeft: 26}}>{active && i > 0 ? `${Math.round(val)}%` : v.txt}</div>
						</div>
					);
				})}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// =====================================================================
// Marionette: a controller bar jerks a silhouette figure; "cut" snaps the strings
// =====================================================================
export const Puppet: React.FC<{mode: string; dur: number}> = ({mode, dur}) => {
	const f = useCurrentFrame();
	const p = Math.min(1, f / Math.max(1, dur));
	const cutAt = Math.round(dur * 0.35);
	const cut = mode === 'cut' && f >= cutAt;
	const fall = cut ? easeOut((f - cutAt) / 10) : 0;
	const jerk = (k: number) => (mode === 'control' || (!cut && mode === 'cut') ? Math.sin(f / 5 + k) * 14 : 0);
	const barY = 130 + (mode === 'control' ? Math.sin(f / 7) * 18 : 0);
	const barRot = mode === 'control' ? Math.sin(f / 9) * 8 : 0;
	// anchor points on the figure (head, two hands, two knees) in local coords
	const cx = 960;
	const baseY = 520 + fall * 260;
	const pts = [
		{x: cx, y: baseY - 170 + jerk(0)}, // head
		{x: cx - 150, y: baseY - 20 + jerk(1)}, // left hand
		{x: cx + 150, y: baseY - 20 + jerk(2.2)}, // right hand
		{x: cx - 60, y: baseY + 230 + jerk(3.1) * 0.6}, // left knee
		{x: cx + 60, y: baseY + 230 + jerk(4.3) * 0.6}, // right knee
	];
	const tops = [cx, cx - 230, cx + 230, cx - 120, cx + 120];
	const flash = mode === 'cut' ? interpolate(f - cutAt, [0, 2, 7], [0, 0.55, 0], clamp) : 0;
	const slump = cut ? fall : 0;
	const [h, lh, rh, lk, rk] = pts;
	return (
		<AbsoluteFill style={{backgroundColor: '#000', overflow: 'hidden'}}>
			<DarkBg glow={0.35} />
			<svg width={1920} height={1080}>
				<defs>
					<radialGradient id="spot" cx="50%" cy="45%" r="45%">
						<stop offset="0%" stopColor="rgba(255,40,40,0.28)" />
						<stop offset="100%" stopColor="rgba(0,0,0,0)" />
					</radialGradient>
				</defs>
				<ellipse cx={cx} cy={560} rx={620} ry={480} fill="url(#spot)" />
				{/* control bar */}
				<g transform={`rotate(${barRot} ${cx} ${barY})`} opacity={cut ? 1 - fall * 0.4 : 1}>
					<rect x={cx - 260} y={barY - 10} width={520} height={20} rx={6} fill="#c9c2b5" />
					<rect x={cx - 12} y={barY - 70} width={24} height={140} rx={6} fill="#c9c2b5" />
				</g>
				{/* strings */}
				{pts.map((pt, i) => {
					if (cut) {
						const len = 160 * (1 - fall);
						return <line key={i} x1={tops[i]} y1={barY} x2={tops[i] + (i % 2 ? -6 : 6) * fall} y2={barY + len} stroke="#e6e0d4" strokeWidth={2} opacity={0.8} />;
					}
					return <line key={i} x1={tops[i]} y1={barY} x2={pt.x} y2={pt.y} stroke="#e6e0d4" strokeWidth={2} opacity={0.85} />;
				})}
				{/* figure silhouette */}
				<g fill={RED} stroke={RED} strokeLinecap="round" style={{filter: 'drop-shadow(0 0 18px rgba(255,0,0,0.45))'}}
					transform={`rotate(${slump * 18} ${cx} ${baseY + 200})`}>
					<circle cx={h.x} cy={h.y} r={58} />
					<line x1={h.x} y1={h.y + 50} x2={cx} y2={baseY + 120} strokeWidth={70} />
					<line x1={cx} y1={baseY - 60} x2={lh.x} y2={lh.y + slump * 160} strokeWidth={30} />
					<line x1={cx} y1={baseY - 60} x2={rh.x} y2={rh.y + slump * 160} strokeWidth={30} />
					<line x1={cx} y1={baseY + 120} x2={lk.x} y2={lk.y} strokeWidth={36} />
					<line x1={cx} y1={baseY + 120} x2={rk.x} y2={rk.y} strokeWidth={36} />
					<line x1={lk.x} y1={lk.y} x2={lk.x - 10} y2={lk.y + 150} strokeWidth={32} />
					<line x1={rk.x} y1={rk.y} x2={rk.x + 10} y2={rk.y + 150} strokeWidth={32} />
				</g>
			</svg>
			<AbsoluteFill style={{backgroundColor: '#fff', opacity: flash}} />
			<AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.8) 100%)', opacity: 0.9 + 0.1 * p}} />
		</AbsoluteFill>
	);
};
