import { AbsoluteFill, Audio, Sequence, Video, useVideoConfig } from 'remotion';
import { z } from 'zod';
import { HookIntro } from './HookIntro';

export const myCompSchema = z.object({
	videoSrc: z.string(),
	audioSrc: z.string(),
	hookText: z.string(),
	trimEndFrames: z.number(),
});

type Props = z.infer<typeof myCompSchema>;

export const VideoPostProcessor: React.FC<Props> = ({
	videoSrc,
	audioSrc,
	hookText,
	trimEndFrames,
}) => {
	const { fps, durationInFrames } = useVideoConfig();

	// 1. Intro sequence (e.g., 3 seconds)
	const introDuration = 3 * fps;

	// 2. Main video sequence
	// We trim the outro by stopping early
	const mainVideoDuration = durationInFrames - introDuration - trimEndFrames;

	if (!videoSrc) {
		return (
			<AbsoluteFill style={{ backgroundColor: '#111', justifyContent: 'center', alignItems: 'center', color: 'white', fontSize: 60 }}>
				Waiting for video source...
			</AbsoluteFill>
		);
	}

	return (
		<AbsoluteFill style={{ backgroundColor: 'black' }}>
			{/* INTRO HOOK */}
			<Sequence durationInFrames={introDuration} name="Hook Intro">
				<HookIntro text={hookText} />
			</Sequence>

			{/* MAIN VIDEO (Processed) */}
			<Sequence from={introDuration} durationInFrames={mainVideoDuration} name="Main Content">
				<AbsoluteFill>
					{/* Original Video with muted audio */}
					<Video src={videoSrc} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
					
					{/* New TTS Audio - synced to start with the main video */}
					{audioSrc && <Audio src={audioSrc} />}

					{/* Watermark Obfuscator (Bottom Right) */}
					<div
						style={{
							position: 'absolute',
							bottom: 20,
							right: 20,
							width: 300,
							height: 100,
							backgroundColor: '#000',
							color: 'white',
							display: 'flex',
							justifyContent: 'center',
							alignItems: 'center',
							fontSize: 30,
							fontWeight: 'bold',
							borderRadius: 15,
							boxShadow: '0 4px 6px rgba(0,0,0,0.5)',
						}}
					>
						EduContent
					</div>
				</AbsoluteFill>
			</Sequence>
		</AbsoluteFill>
	);
};
