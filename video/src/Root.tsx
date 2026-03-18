import { Composition } from 'remotion';
import { VideoPostProcessor, myCompSchema } from './VideoPostProcessor';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="EduContent"
				component={VideoPostProcessor}
				durationInFrames={300} // Will be dynamically overridden when rendering
				fps={30}
				width={1920}
				height={1080}
				schema={myCompSchema}
				defaultProps={{
					videoSrc: '',
					audioSrc: '',
					hookText: 'Understand this topic in five minutes!',
					trimEndFrames: 150, // Trim 5 seconds of outro
				}}
			/>
		</>
	);
};
