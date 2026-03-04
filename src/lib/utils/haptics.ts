import { createWebHaptics } from 'web-haptics/svelte';
import { browser } from '$app/environment';

export const HAPTIC_PRESETS = {
    SUCCESS: 'success',
    NUDGE: 'nudge',
    ERROR: 'error',
    BUZZ: 'buzz',
    // AI "typing" pattern: 1.5 - 3 seconds
    TYPING: [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50]
};

// Global instance for maximum performance (reuse across components)
const { trigger, isSupported } = browser
    ? createWebHaptics({ debug: false })
    : { trigger: (p: any) => { }, isSupported: false };

export const haptics = { trigger, isSupported };

export const triggerHaptic = (pattern: string | number | number[] = 'success') => {
    if (isSupported) trigger(pattern);
};
