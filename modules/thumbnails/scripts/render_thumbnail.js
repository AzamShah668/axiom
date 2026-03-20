const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function renderThumbnail(config) {
    const {
        templatePath,
        outputPath,
        params = {}
    } = config;

    console.log(`\n🚀 Rendering Thumbnail to: ${outputPath}`);

    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
    });
    
    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 720 });

        page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
        page.on('error', err => console.error('BROWSER ERROR:', err.message));
        page.on('pageerror', err => console.error('BROWSER PAGE ERROR:', err.message));

        let html = fs.readFileSync(templatePath, 'utf8');

        // Helper to convert local image to base64
        const toBase64 = (filePath) => {
            if (!filePath || !fs.existsSync(filePath)) {
                console.warn(`⚠️ Warning: Image not found at ${filePath}`);
                return '';
            }
            try {
                const ext = path.extname(filePath).toLowerCase().replace('.', '');
                const mime = ext === 'jpg' ? 'jpeg' : ext;
                const buffer = fs.readFileSync(filePath);
                return `data:image/${mime};base64,${buffer.toString('base64')}`;
            } catch (err) {
                console.error(`❌ Error converting ${filePath} to base64: ${err.message}`);
                return '';
            }
        };

        // Inject dynamic base64 images FIRST
        const injectImage = (placeholder, pathKey) => {
            if (params[pathKey]) {
                const b64 = toBase64(params[pathKey]);
                if (b64) {
                    console.log(`✅ Injecting base64 for ${pathKey} (length: ${b64.length})`);
                    html = html.split(placeholder).join(b64);
                }
            }
        };

        injectImage('{{BG_IMAGE_BASE64}}', 'BG_IMAGE_PATH');
        injectImage('{{HEADSHOT_BASE64}}', 'HEADSHOT_PATH');
        injectImage('{{LOGO_BASE64}}', 'LOGO_PATH');

        // Simple placeholder replacement for everything else
        for (const [key, value] of Object.entries(params)) {
            const placeholder = `{{${key}}}`;
            html = html.split(placeholder).join(value);
        }

        await page.setContent(html, { waitUntil: 'networkidle2' });
        
        // Wait for the background removal script to finish
        console.log("⏳ Waiting for canvas processing...");
        await page.waitForFunction(() => window.renderReady === true, { timeout: 10000 });
        
        // Small extra buffer for fonts
        await new Promise(r => setTimeout(r, 1000));

        await page.screenshot({
            path: outputPath,
            type: 'png',
            clip: { x: 0, y: 0, width: 1280, height: 720 }
        });

        console.log(`✅ Success: ${path.basename(outputPath)}`);
    } catch (err) {
        console.error(`❌ Error rendering thumbnail: ${err.message}`);
        throw err;
    } finally {
        await browser.close();
    }
}

// CLI usage
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.log('Usage: node render_thumbnail.js <output_path> <params_json>');
        process.exit(1);
    }

    const outputPath = args[0];
    const params = JSON.parse(args[1]);
    const templatePath = path.join(__dirname, '../../tools/thumbnail_generator.html');

    renderThumbnail({
        templatePath,
        outputPath,
        params
    }).catch(console.error);
}

module.exports = { renderThumbnail };
