import { hapticTrigger } from './haptics';

/**
 * Simulates a "typing" haptic feel while the AI model streams a response.
 * Fires rapid subtle taps (~every 120ms) for a duration of 1.5–2.5s.
 *
 * Call this ~200ms after the first streamed text appears.
 * Returns a `stop()` function to cancel early.
 */
export function startTypingHaptic(durationMs: number = 2000): () => void {
    let stopped = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const stop = () => {
        if (stopped) return;
        stopped = true;
        if (intervalId) clearInterval(intervalId);
        if (timeoutId) clearTimeout(timeoutId);
    };

    // Fire a subtle tap every 120ms
    intervalId = setInterval(() => {
        if (stopped) return;
        hapticTrigger('selection');
    }, 120);

    // Auto-stop after the specified duration
    timeoutId = setTimeout(() => {
        stop();
    }, durationMs);

    return stop;
}
