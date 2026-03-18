import { Composition } from "remotion";
import { AxiomIntro } from "./AxiomIntro";

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="AxiomIntro"
        component={AxiomIntro}
        durationInFrames={210}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
