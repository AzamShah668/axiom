const { renderThumbnail } = require('./render_thumbnail.js');
const path = require('path');

async function test() {
    const params = {
        TOP_BADGE: "Demystifying Algorithms",
        MAIN_TITLE: "QUICK<br>SORT",
        SUBTITLE: "Algorithm Explained",
        SUB_LINE: "Divide <em>&</em> Conquer Strategy",
        MUST_WATCH_TEXT: "MUST WATCH",
        BG_IMAGE_DISPLAY: "block",
        TOP_BADGE_DISPLAY: "inline-block",
        MUST_WATCH_DISPLAY: "block",
        HEADSHOT_DISPLAY: "block",
        LOGO_DISPLAY: "block",
        BG_IMAGE_PATH: "D:\\notebook lm\\modules\\thumbnails\\assets\\bgs\\quicksort_bg.png",
        HEADSHOT_PATH: "D:\\notebook lm\\modules\\thumbnails\\assets\\headshots\\azam_smiling.png",
        LOGO_PATH: "D:\\notebook lm\\modules\\thumbnails\\assets\\axiom_logo.png",
    };

    try {
        const root = path.join(__dirname, '../../..');
        await renderThumbnail({
            templatePath: path.join(root, 'tools/thumbnail_generator.html'),
            outputPath: path.join(root, 'output/quicksort_thumbnail_final.png'),
            params
        });
        console.log("Test complete.");
    } catch (err) {
        console.error("Test failed:", err);
    }
}

test();
