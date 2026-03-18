import React from 'remotion';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

export const HookIntro: React.FC<{ text: string }> = ({ text }) => {
	const frame = useCurrentFrame();
	
	const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
	const scale = interpolate(frame, [0, 20], [0.8, 1], { extrapolateRight: 'clamp' });

	return (
		<AbsoluteFill
			style={{
				backgroundColor: '#3b82f6', // Premium Blue
				justifyContent: 'center',
				alignItems: 'center',
				color: 'white',
			}}
		>
			<div
				style={{
					fontSize: 80,
					fontWeight: 'bold',
					textAlign: 'center',
					padding: '0 100px',
					opacity,
					transform: `scale(${scale})`,
					fontFamily: 'sans-serif',
					textShadow: '0 10px 20px rgba(0,0,0,0.3)',
				}}
			>
				{text}
			</div>
		</AbsoluteFill>
	);
};
