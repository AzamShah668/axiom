/**
 * Generic retry wrapper with exponential backoff.
 * Used by TTS, Colab launcher, and NotebookLM controller.
 *
 * @param {Function} fn        - Async function to retry
 * @param {object}   opts
 * @param {number}   opts.maxRetries  - Max attempts (default 3)
 * @param {number[]} opts.delays      - Backoff delays in ms (default [5000, 15000, 45000])
 * @param {string}   opts.label       - Label for logging
 * @param {Function} opts.onRetry     - Optional async callback before each retry
 * @returns {Promise<*>}
 */
async function withRetry(fn, { maxRetries = 3, delays = [5000, 15000, 45000], label = 'operation', onRetry } = {}) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            return await fn(attempt);
        } catch (err) {
            console.error(`[retry] ${label} attempt ${attempt}/${maxRetries} failed: ${err.message}`);

            if (attempt >= maxRetries) {
                throw new Error(`${label} failed after ${maxRetries} attempts. Last error: ${err.message}`);
            }

            if (onRetry) {
                try { await onRetry(attempt, err); } catch (_) {}
            }

            const delay = delays[attempt - 1] || delays[delays.length - 1];
            console.log(`[retry] Waiting ${delay / 1000}s before retry...`);
            await new Promise(r => setTimeout(r, delay));
        }
    }
}

module.exports = { withRetry };
