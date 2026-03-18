const fs = require('fs');
const pdf = require('pdf-parse');
const path = require('path');

async function extractPdf(pdfPath, txtPath) {
    try {
        console.log(`Extracting ${pdfPath}...`);
        let dataBuffer = fs.readFileSync(pdfPath);
        let data = await pdf(dataBuffer);
        
        const dir = path.dirname(txtPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        
        fs.writeFileSync(txtPath, data.text, 'utf-8');
        console.log(`Successfully extracted to ${txtPath}`);
    } catch (err) {
        console.error(`Error extracting ${pdfPath}:`, err.message);
    }
}

const btechPdf = "d:\\notebook lm\\syllabus\\BTech_Syllabus_detailed.pdf";
const mbbsPdf = "d:\\notebook lm\\syllabus\\Syllabus - MBBS.pdf";
const btechTxt = "d:\\notebook lm\\data\\btech_extracted.txt";
const mbbsTxt = "d:\\notebook lm\\data\\mbbs_extracted.txt";

async function run() {
    await extractPdf(btechPdf, btechTxt);
    await extractPdf(mbbsPdf, mbbsTxt);
}

run();
